# Editing Packages Safely

**Answers:** How do I change a file inside an export package so it still imports? Which checksum lines change? How
do I drop failing objects, remap objects off the reserved hosted runtime, swap a mapping's connection, retarget a
mapping task, or change a DBMI runtime property?

**Read when:** you are about to edit an export zip; an upload says `checksumValid:false`; a start fails with
`MigrationSvc_073`, `MigrationSvc_031` or `MigrationSvc_030`.

**Key rules:**
- Keep three things consistent: the changed inner file, every `metadata.objectRefs` list in `exportMetadata.v2.json`,
  and one upper-case SHA-256 line per changed file in `exportPackage.chksum` (L-MIG-019, L-MIG-020).
- Re-hash only the files you changed, including `exportMetadata.v2.json` itself; copy every other line byte for byte
  (L-MIG-019).
- Every objectRef must point at an object in the package; never add a ref to a connection the package lacks
  (L-MIG-020).
- Mapping bodies are IMF JSON in `bin/@<n>.bin`; a 22-character GUID swap keeps every offset intact (L-MIG-029,
  L-MIG-020).
- Retarget a mapping task by re-importing its mapping with `OVERWRITE` under the same GUID; the v2 target-parameter
  update is a silent no-op (L-MIG-030).
- Never print package contents: packages can carry plaintext secrets (L-MIG-018).

**Related:** [Export & Import](<01 Export & Import (v3 Migration API).md>) · [Migration-Clone Authoring](<03 Migration-Clone Authoring.md>) · [Org-to-Org Migration Runbook](<04 Org-to-Org Migration Runbook.md>) · [DBMI over REST](<../04 - Mass Ingestion & CDC/01 DBMI over REST (create, deploy, run, stop).md>) · [Lessons: Migration & Org Management](<../13 - Lessons Learned/10 Migration & Org Management.md>)

**Last verified:** 2026-10-03

> An export package can be edited and re-imported; that is how headless clones, retargets, repairs and in-place
> changes are made. Get the consistency rules wrong and the import fails with `MigrationSvc_073` (a hash not updated)
> or `MigrationSvc_031` (a dangling objectRef, often with empty details).

---

## 1. Package anatomy (L-MIG-021)

```
<export>.zip
├─ Explore/<project>/<folder>/
│   ├─ <task>.DBMI_TASK.dat              plain JSON (the DBMI task definition)
│   ├─ <conn>.TOOL_CONNECTION.dat        plain JSON (an MCP tool connection)
│   ├─ <process>.PROCESS.xml             CAI process (repository-item XML)
│   ├─ <conn>.AI_CONNECTION.xml          CAI app connection
│   ├─ <sc>.AI_SERVICE_CONNECTOR.xml     CAI service connector
│   ├─ <mapping>.DTEMPLATE.zip           a nested zip:
│   │     ├─ mappingTemplate.json        stub: assetFrsGuid, templateId "@2", documentType MAPPING,
│   │     │                              references[] {refObjectId "@<conn guid>", refType "connection"}
│   │     ├─ fileRecord.json             id "@2", type IMFOBJECT
│   │     ├─ bin/@<n>.bin                the mapping body (IMF JSON in the September exports)
│   │     └─ metadata.meta
│   └─ ... one entry per object (mapping tasks, workflows, rule specs, profiles ...)
├─ Explore/<project>/<folder>.Folder.json and Explore/<project>.Project.json
├─ SYS/<conn>.Connection.zip             each referenced connection (secrets masked)
├─ SYS/<re>.AgentGroup.zip               each referenced runtime environment
├─ exportMetadata.v2.json                exportedObjects[]: objectGuid, objectName, objectType, path,
│                                        metadata.objectRefs (dependency guids), additionalInfo,
│                                        repoInfo.repoHandle (= the v2 id)
├─ exportPackage.chksum                  one line per file: <path>=<SHA-256 hex, upper case>,
│                                        plus a few opaque object-hash lines
└─ <export>.csv                          one row per object
```

Notes:

- The DBMI `.dat` and the tool-connection `.dat` are plain JSON; CAI assets are XML. The September mapping exports held IMF JSON text in `bin/@<n>.bin`, not an opaque binary (L-MIG-029).
- `repoInfo.repoHandle` gives each object's **v2 id** in the source org. Keep it for the id map.
- Paths with spaces are escaped as `\ ` in the checksum keys.

## 2. The three rules

1. **Change the inner file.** For a nested zip (a mapping), rewrite the inner zip and hash the new inner zip as a whole.
2. **Keep `exportMetadata.v2.json` consistent.** When you rename, re-GUID, remove or remap an object, update its `exportedObjects[]` entry and every `metadata.objectRefs` list that points at it. Every objectRef must point at an object **present in the package**. A dangling ref gives `MigrationSvc_031` with empty details; adding a ref to a connection that is not in the package breaks the import the same way (L-MIG-020).
3. **Re-hash only what changed.** In `exportPackage.chksum`, replace the line of every file you changed with `<path>=<SHA256(bytes).hexdigest().upper()>`, **including `exportMetadata.v2.json` itself** if you touched it. Copy every other line byte for byte; the opaque object-hash lines stay valid. A changed file whose line was not updated gives `MigrationSvc_073 'package has been modified'` (L-MIG-019).

Upload: `checksumValid:true` in the upload answer means rule 3 held. Start: `SUCCESSFUL` means rules 1 and 2 held too.

## 3. A small toolkit (Python, standard library)

```python
import hashlib, io, json, zipfile

def read_pkg(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}          # never print these values

def sha_upper(b):
    return hashlib.sha256(b).hexdigest().upper()

def chk_key(name):
    return name.replace(" ", "\\ ")                          # spaces are escaped in the keys

def rehash(files, changed):
    """Replace only the checksum lines of the changed files; keep every other line byte-identical."""
    want = {chk_key(n): sha_upper(files[n]) for n in changed}
    out, seen = [], set()
    for line in files["exportPackage.chksum"].decode("utf-8").splitlines():
        key = line.split("=", 1)[0]
        if key in want:
            out.append(f"{key}={want[key]}"); seen.add(key)
        else:
            out.append(line)
    missing = set(want) - seen
    assert not missing, f"no checksum line for {missing}: add one only if the file is new"
    files["exportPackage.chksum"] = ("\n".join(out) + "\n").encode("utf-8")

def write_pkg(files, path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in files.items():
            z.writestr(n, b)
```

## 4. Worked example: change a DBMI task's runtime property and re-import

Goal: set `FlushPeriod` to 5 s on an existing CDC task. There is no DBMI update verb (L-DBMI-007).

1. Stop and undeploy the job; DBMI refuses an import while the task is deployed.

```
POST https://<pod>-ing.<domain>.informaticacloud.com/dbmi/public/api/v2/job/stop      {"jobId":<n>}
POST https://<pod>-ing.<domain>.informaticacloud.com/dbmi/public/api/v2/job/undeploy  {"jobId":<n>}
```

2. Export the task by its `frsId` (dependencies not needed) and download the package; keep an untouched copy as the undo.

```
POST /public/core/v3/export {"name":"<task>_edit","objects":[{"id":"<frsId>","includeDependencies":false}]}
GET  /public/core/v3/export/<id>             until status.state == SUCCESSFUL
GET  /public/core/v3/export/<id>/package     Accept: application/zip
```

3. Edit the one inner file and re-hash it:

```python
files = read_pkg("task_export.zip")
dat = "Explore/<project>/<folder>/<task>.DBMI_TASK.dat"
d = json.loads(files[dat])
d["common"]["runtimeSettings"]["runtimePropsMap"].update({"FlushPeriod": "5"})
files[dat] = json.dumps(d).encode("utf-8")
rehash(files, [dat])                  # exportMetadata.v2.json is unchanged, so its line stays
write_pkg(files, "task_edited.zip")
```

4. Upload (multipart, part `package`) and start with `OVERWRITE`:

```python
import urllib.request, uuid
b = uuid.uuid4().hex
body = (f"--{b}\r\nContent-Disposition: form-data; name=\"package\"; filename=\"pkg.zip\"\r\n"
        f"Content-Type: application/zip\r\n\r\n").encode() + open("task_edited.zip", "rb").read() + f"\r\n--{b}--\r\n".encode()
req = urllib.request.Request(BASE + "/public/core/v3/import/package", data=body, method="POST",
      headers={"INFA-SESSION-ID": SID, "Content-Type": f"multipart/form-data; boundary={b}", "Accept": "application/json"})
job = json.load(urllib.request.urlopen(req))["jobId"]          # expect checksumValid: true
# then: POST /public/core/v3/import/<job>
#   {"name":"<task>_edit","importSpecification":{"defaultConflictResolution":"OVERWRITE","includeObjects":[]}}
# and poll GET /public/core/v3/import/<job> until status.state == SUCCESSFUL
```

5. Deploy and start again: `POST .../dbmi/public/api/v2/task/deploy/<taskId>` (**a new job id**), then `job/start`. Check `GET .../dbmi/public/api/v2/task/details?taskId=<n>` shows the new value.

Measured result: the change took effect, and the target views gapped for about 3 minutes during the re-baseline. For connection, slot or table changes, creating a new task with `task/create` is simpler (see [DBMI over REST](<../04 - Mass Ingestion & CDC/01 DBMI over REST (create, deploy, run, stop).md>)).

## 5. Worked example: drop objects that fail validation

An import is all-or-nothing, and `includeObjects` does not exclude objects from validation (L-MIG-012). To import the rest of a package without some objects:

1. Collect the object guids to drop, and **refuse** if any object you keep still references one of them in its `objectRefs`.
2. Delete their files (the inner file, and for a mapping its nested zip).
3. Remove their entries from `exportMetadata.v2.json` `exportedObjects[]`.
4. Remove their checksum lines, and re-hash `exportMetadata.v2.json`.
5. Remove their rows from the CSV, and re-hash the CSV if it has a checksum line.
6. Upload and start. Import the dropped objects later on their own (or create them another way).

```python
meta_name = "exportMetadata.v2.json"
meta = json.loads(files[meta_name])
drop = {"<guid1>", "<guid2>"}
keep = [o for o in meta["exportedObjects"] if o["objectGuid"] not in drop]
for o in keep:
    refs = set((o.get("metadata") or {}).get("objectRefs") or [])
    assert not refs & drop, f"{o['objectName']} still references a dropped object"
meta["exportedObjects"] = keep
files[meta_name] = json.dumps(meta).encode("utf-8")
# delete the dropped objects' files from `files` (match on their path + name), drop their chksum lines,
# then rehash(files, [meta_name])
```

(Five failing objects were dropped this way and the other 214 imported.) The exact position of `objectRefs` inside each entry is `metadata.objectRefs`. Check your export, because the file layout is not documented.

## 6. Worked example: remap objects off a reserved runtime environment

The runtime environment named `Informatica Cloud Hosted Agent` cannot be created by import (`REPO_38210`). When the target is not entitled to the hosted runtime, rebind the objects that use it before importing (L-MIG-015):

1. Find every object whose inner file or `objectRefs` points at the hosted runtime's `SYS/<re>.AgentGroup.zip` entry.
2. Point them at the self-hosted runtime environment's entry instead (its `AgentGroup` entry must be in the package, or the runtime must exist in the target under the same name).
3. Remove the hosted runtime's entry and its checksum line, and fix every `objectRefs` list that named it.
4. Re-hash every inner file you changed plus `exportMetadata.v2.json`.

Fifteen objects (a SaaS connection and its tasks) were remapped this way.

## 7. Worked example: swap a mapping's connection in place

IDMC GUIDs are 22 characters, so replacing one connection GUID with another inside a mapping entry keeps every offset intact (L-MIG-020):

```python
inner = "Explore/<project>/<folder>/<mapping>.DTEMPLATE.zip"
iz = read_pkg(io.BytesIO(files[inner]))              # zipfile accepts a file-like object
b = iz["bin/@3.bin"]
assert b.count(OLD_GUID.encode()) == 1 and len(OLD_GUID) == len(NEW_GUID) == 22
iz["bin/@3.bin"] = b.replace(OLD_GUID.encode(), NEW_GUID.encode())
buf = io.BytesIO(); write_pkg(iz, buf); files[inner] = buf.getvalue()
rehash(files, [inner])
# Do NOT add NEW_GUID to objectRefs: if that connection is not in the package, the import fails with MigrationSvc_031.
```

The clone imported with `checksumValid:true` and ran 52/52 rows into a warehouse of a different type. Check whether the new connection type is proven for your mapping first; a rebind to a new connection type needs that connection's package entry or an existing seed (L-MIG-027).

## 8. Retarget a mapping task by re-importing its mapping (L-MIG-030)

Changing a mapping task's target through the v2 update idiom (`POST /saas/api/v2/mttask/<taskId>` with new target parameters) returns 200 and changes **nothing**: the task re-derives its targets from the mapping. Retarget by editing the mapping's package and re-importing it with `OVERWRITE` under the **same GUID**, then read the task back.

## 9. Security while editing

- Packages can carry plaintext secrets (a CAI app connection with `encrypted="false"`). Never print file contents, diff outputs or package dumps into a transcript or log; print names, sizes and hashes only (L-MIG-018).
- When you inject a real value (for example a live endpoint URL or a bearer token into a tool connection), read it from a 0600 file at run time, write the package to a private temp location, and delete it after the import.
- Keep the original export as the undo, with the same care.

## 10. When it still fails

| Symptom | Likely cause | Check |
|---|---|---|
| upload `checksumValid:false` | a changed file without a new line, or a stale line | recompute with the toolkit; escape spaces as `\ ` |
| `MigrationSvc_073 'package has been modified'` | `exportMetadata.v2.json` (or another file) changed without a re-hash | rule 3 |
| `MigrationSvc_031` with **empty** details | a dangling objectRef | rule 2 |
| `MigrationSvc_031` naming one object, all others 'skipped because of previous failures' | that object fails validation in the target | drop it (section 5) or fix its dependency |
| `MigrationSvc_031` 'Internal error' on a `TOOL_CONNECTION` | a platform limit | recreate it in the designer (L-MIG-039) |
| `MigrationSvc_030` | the upload is not a valid package (empty or malformed zip) | rebuild the zip; keep the Folder/Project JSON entries |
| `SUCCESSFUL`, but the change is not visible | you edited a copy the target reused (`REUSE`) | import with `OVERWRITE` |

## 11. Lessons in this doc

L-MIG-015, L-MIG-018 to L-MIG-022, L-MIG-027, L-MIG-029, L-MIG-030, L-MIG-039, L-DBMI-007. Full text: [Lessons: Migration & Org Management](<../13 - Lessons Learned/10 Migration & Org Management.md>).
