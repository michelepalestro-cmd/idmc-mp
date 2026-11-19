# Environment Traps (Windows, git-bash, az, gcloud, Docker)

**Answers:** Why does a working IDMC call or a healthy host look broken from this workstation or VM? Which shell,
cloud-CLI, Docker, network, disk and BI-tool traps cause it, and what is the exact fix?

**Read when:** before diagnosing IDMC for any failure that involves git-bash, `az`, `gcloud`, run-command, Docker, an
agent host's disks, a firewall, a certificate, or a BI tool or gateway over the IDMC-built warehouse; when setting up a
new workstation or agent host; before resizing or rebooting an agent VM.

**Key rules:**
- On Windows git-bash call Azure as `python -m azure.cli`, export `MSYS_NO_PATHCONV=1` only for the IDMC REST helpers,
  and write scripts with the file tools, with LF endings and no heredoc backslashes (L-ENV-016, L-ENV-017, L-ENV-023,
  L-ENV-023).
- Run-command is a per-VM singleton with a 4 KB output tail; pin `--account` on every gcloud call (L-ENV-003,
  L-ENV-009).
- A service account with IAP-tunnel and SSH rights replaces a lapsed human login for the IAP hop
  (L-ENV-008).
- Keys and the gcloud default project die with their project: check project liveness during every key inventory
  (L-ENV-052).
- Moving Docker's data-root does not move containerd's store; watch both volumes on an agent host and reclaim space in
  a safe order (L-ENV-032, L-ENV-071).
- An Azure resize to a size offered on the current cluster is one reboot; run the post-boot checklist afterwards
  (L-ENV-069).
- BI tools over the warehouse: Tableau refuses any non-OAuth BigQuery credential headless (403132), and custom SQL must
  not contain `<` (400011) (L-ENV-064, L-ENV-081, L-ENV-085).

**Related:** [01 How Claude Reaches and Drives IDMC](01-how-claude-reaches-and-drives-idmc.md) · [06 Secrets Hygiene](06-secrets-hygiene.md) · [Secure Agent - Install, Run & Tune](../02-secure-agent-connections/01-secure-agent-install-run-tune.md) · [Serving Outputs to BI and Apps](../03-cdi-data-integration/10-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) · [Lessons: Environment & Ops](../../lessons/by-domain/13-environment-ops.md)

**Last verified:** 2026-11-03

> **Summary.** None of these is an IDMC problem, and every one of them made a working IDMC call or a healthy host look
> broken: git-bash swallowing `az` output, MSYS rewriting REST paths, the agent's own shell eating backslashes, CRLF in
> scripts written from Windows, run-command channels that are shared singletons, gcloud accounts that flip globally,
> keys whose project is gone, egress addresses that rotate, hairpin NAT, Docker and containerd stores on the wrong disk,
> and BI-tool API quirks. Each row gives the symptom, the cause and the fix, with the lesson that proved it. Check this
> list before diagnosing IDMC.

---

## 1. Windows and git-bash

| Symptom | Cause | Fix | Lesson |
|---|---|---|---|
| `az... -o json` prints nothing, exit code 0; a create "succeeded" but the resource is missing | git-bash's `az.cmd` wrapper loses its stdout handle | `python -m azure.cli <args>`; `AZURE_CORE_USE_PAGER=false`, `PYTHONUTF8=1`; read the resource back | (L-ENV-016) |
| a REST path argument such as `/api/v2/connection` arrives as `C:/Program Files/...` | MSYS path conversion of leading-slash arguments | `export MSYS_NO_PATHCONV=1` for the IDMC REST helpers only; never globally (it breaks the az launcher and the gcloud/bq wrappers); for az use `-g`/`-n` instead of `--ids /subscriptions/...` | (L-ENV-017) |
| a gate that shells out to `bash <wrapper>.sh` reports RED over good data | `/c/...` drive paths rewritten under git-bash | run the gate from cmd or PowerShell, or call the tool without a shell wrapper | (L-ENV-018) |
| `az... --query '{a:b}'` fails with "invalid jmespath_type" | git-bash brace expansion | `-o tsv` with a brace-free query (`value[0].message`), `-o table`, or `-o none` | (L-ENV-019) |
| `cmd //c "mklink /J..."` fails with "filename, directory name, or volume label syntax is incorrect" | path mangling into cmd builtins | write the command into a `.bat` and run it (junctions need no elevation) | (L-ENV-019) |
| a folder literally named `%LOCALAPPDATA%` appears, holding a key file | `%VAR%` does not expand in bash | `$LOCALAPPDATA` or an absolute path; then search for stray literal folders and key files | (L-ENV-020) |
| `os.path.exists` is False for a file that exists | path longer than MAX_PATH (260) | the `\\?\` prefix, or `cd` in and use short relative names | (L-ENV-021) |
| `gcloud` / `bq` launchers fail; long runs die with "Reauthentication failed, cannot prompt" | a space in the Cloud SDK path; a human token that expired | wrap the SDK's bundled python with `CLOUDSDK_ROOT_DIR` exported; use a service account for long headless runs | (L-ENV-022), (L-ENV-008) |
| `gcloud compute scp --recurse` fails | pscp and a local path with spaces | copy files one by one | (L-ENV-022) |
| a Python writer crashes on emoji or accented text | Windows console cp1252 | `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1`; pass payloads through files, not heredocs | (L-ENV-022) |
| a regex deployed from a heredoc stops matching; a 0x08 byte appears in code | the agent shell turned `\b` into a backspace and dropped `\p`, `\s` | write regex-bearing files with the file-editing tools; quote heredocs (`<<'EOF'`); `grep -P '\x08'` before deploying | (L-ENV-023) |
| a path or patch written through a quoted heredoc is corrupted; a long Python heredoc fails with "unexpected EOF" | the agent shell still turns `\\` into `\` inside quoted heredocs (a path segment `\2026` became an octal escape) | write scripts and patches with the file tools; use `chr(92)` where a script must emit a backslash | (L-ENV-023), (L-ENV-023) |
| a shell script written from Windows fails on the Linux host with `$'\r': command not found` | Python `open(p, 'w')` on Windows writes CRLF | write with `newline='\n'` (or `newline=''` to keep the source's endings), keep the live file's newline style when patching, and run `bash -n` before deploying | (L-ENV-023) |
| `grep -c $'\r'` reports the wrong number of carriage returns | git-bash grep miscounts `\r` | count on the bytes in Python: `open(p, 'rb').read.count(b'\r\n')` | (L-ENV-023) |
| a write to a config file fails, or the file loses its Hidden attribute | the Windows Hidden attribute | `attrib -h <file>` before the write, `attrib +h <file>` after | (L-ENV-023) |
| a workflow script fails to load, or throws `ReferenceError: VAR is not defined` | non-ASCII in the script file; `${VAR}` or a backtick inside an agent prompt template | keep workflow scripts ASCII; escape as `\${VAR}` or reword | (L-ENV-024) |
| an import such as Playwright breaks for no reason | a stray `inspect.py` (or similar) in a shared temp folder shadows the stdlib | run automation from a private scratch directory | (L-ENV-025) |
| a backgrounded script's log stays empty | block-buffered stdout | `python -u` or `PYTHONUNBUFFERED=1` | (L-ENV-036) |

## 2. Azure CLI and cloud run-command

| Symptom | Cause | Fix | Lesson |
|---|---|---|---|
| `Conflict: Run command extension execution is in progress`, sometimes for more than 5 minutes | `run-command invoke` is a per-VM singleton shared by every session | retry with 25-60 s backoff; one session drives the channel at a time | (L-ENV-003) |
| the head of the output is missing | only the last ~4 KB of output is returned | print small filtered results; write big dumps to a file and read them in chunks | (L-ENV-003) |
| `FileNotFoundError` for `~/...` paths inside the script | the script runs as root with `HOME=/root` | `sudo -u <user> -H...` or set `HOME=/home/<user>` | (L-ENV-003) |
| an inline multi-line script arrives mangled | quoting through the CLI; Windows command lines cap at 32 KB | `--scripts @file` | (L-ENV-003) |
| invoke stays jammed | a peer or a stuck call holds the singleton | a managed run-command (`vm run-command create`, then `show --instance-view`); output is not inline and front-truncates at ~4 KB; chunk with `split -b 3000` or use `--output-blob-uri` | (L-ENV-004) |
| `BadRequest` on a new managed run-command | 25 managed run-commands per VM; a `CanNotDelete` lock keeps them from being deleted (`ScopeLocked`) | fall back to invoke; do not remove the lock | (L-ENV-004) |
| an agent or daemon started through run-command is gone after a reboot | it lived in the extension's transient cgroup | start it through its systemd unit; check `/system.slice/<unit>.service` | (L-ENV-005) |
| intermittent resets during bulk management calls from a proxied laptop | bursts through the enterprise proxy | space the calls out and retry each one | (L-ENV-015) |
| a run-command script sent from Windows breaks on spaces | quoting through the CLI | base64 the whole script and pass `--scripts 'echo${IFS}'"$B64"'\|base64${IFS}-d\|bash'`; single-quote the `${IFS}` so your local shell does not expand it | (L-ENV-073) |
| an upload to Blob storage from the VM returns 409 (azcopy fails the same way) | the raw SAS's `&` was mangled inside nested quotes | send the SAS base64-encoded and decode it on the VM (section 2.1) | (L-ENV-073) |
| a VM "rename" is impossible | Azure VM resource names cannot change (a rename is a delete and recreate) | label with tags (`alias=`, `role=`, `keep=true`, `status=`); change the OS hostname only after checking what has it built in | (L-ENV-076) |
| existing tags vanish after a tag write; `vm update --set tags.keep=true` is rejected | `resource tag... --tags k=v` replaces the whole tag set (older CLI builds have no `--operation merge`); a boolean-looking value fails through `--set` | read the tags first and send them back with the new ones through `resource tag`; one resource per call, spaced out and retried; read back with `-o tsv` and include a positive control | (L-ENV-076) |

### 2.1 Getting backups off a VM without sending a secret

Use this to move database dumps or agent-host configuration off a VM before a migration or decommission (L-ENV-073).

1. **Preferred, no secret at all:** give the VM a managed identity, grant it **Storage Blob Data Contributor** on one
   private container only, and upload from the VM with `az storage blob upload --auth-mode login` (or
   `azcopy login --identity`). Remove the role assignment when the move is done.
2. **Only if a managed identity is impossible:** use a SAS that can only create and write (`cw`, never `racwl`), scoped
   to that one container, expiring within hours. Copy it to the VM as a root-only 0600 file (for example with `scp`),
   never through `az vm run-command`: run-command scripts and their parameters are kept on the VM and in Azure logs, and
   base64 is encoding, not protection. Delete the file and let the SAS expire when you are done.
3. Upload one file per Put Blob call (dumps of about 300 MB went in one call; recent service versions accept much larger
   single uploads), then check the blob size against the local file.
4. For recurring backups, use the managed identity from `/etc/cron.d`, add a lifecycle rule (for example delete after
   90 days), and list the cron entry and script for removal at decommission.

```bash
az storage blob upload --auth-mode login --account-name <account> --container-name <container> \
  --name "<host>/$(date -u +%Y%m%dT%H%MZ)/dump.pgc" --file dump.pgc
```

## 3. gcloud and IAP

| Symptom | Cause | Fix | Lesson |
|---|---|---|---|
| a script piped into `gcloud compute ssh` on Windows gets a stray `y` | gcloud on Windows uses plink.exe, which answers its host-key prompt on stdin | `gcloud compute scp` the script, or inline it base64-encoded in `--command` | (L-ENV-002) |
| an IAP hop lands as a user without the key (`Permission denied (publickey)`) | a peer session switched the global gcloud account | pin `--account=<user>` or `CLOUDSDK_CORE_ACCOUNT` on every call | (L-ENV-009), (L-ENV-001) |
| SSH/IAP fails right after a service-account step | `gcloud auth activate-service-account` flips the active account globally | pin the account per call; never activate an SA in scheduled self-heal jobs | (L-ENV-009) |
| IAP SSH fails while the human token sits in a reauthentication window | the call runs as the lapsed human account; a warehouse-only service account has no IAP or SSH rights | run the hop as a service account that holds IAP-tunnel and SSH rights on the jump VM ([01 How Claude Reaches and Drives IDMC](01-how-claude-reaches-and-drives-idmc.md), section 7.1); check the human login with `timeout 15 gcloud auth print-access-token`; direct SSH with a registered OS Login key also kept working | (L-ENV-008), (L-ENV-008) |
| every call with a service-account key fails `403 CONSUMER_INVALID` although the key file parses | the key's project was deleted; the project id is in the key's `client_email` (`<sa>@<cloud-project>.iam.gserviceaccount.com`), which is also the `clientEmail` of an IDMC BigQuery V2 connection | `gcloud projects describe <cloud-project>` for every key's project during key inventory; remove dead keys from hosts, secret stores and connection definitions and log them as inert, never as a fallback | (L-ENV-052), (L-ENV-052) |
| billing and API calls fail through a dead quota project | gcloud `core/project` still names a deleted project | `gcloud config get-value project`, then `gcloud config set project <live-project>` on every workstation and VM | (L-ENV-052) |
| a backup that copies data before archiving runs out of space | it needs about twice the data size free on the same disk | grow the disk online: `gcloud compute disks resize <disk> --size <GB> --zone <zone> --account <identity>`, rescan the device on the VM, `sudo resize2fs /dev/<dev>`; no reboot or unmount; disk growth is spend, so get the approvals first (archives to object storage grow with the data too) | (L-ENV-070) |
| the disk resize is refused | the ops service account lacks `compute.disks.resize` | pin an identity that has it on the call (L-ENV-009) | (L-ENV-070) |
| an IAP session drops during a long command | IAP tunnels drop long-lived sessions | ship the script, start it detached with `setsid` / `nohup`, poll the log | (L-ENV-006) |
| a read of a large archive object freezes the VM until sshd stops answering | streaming `gcloud storage cp <obj> -` into `head` retry-loops on the broken pipe and re-downloads the whole object | bounded range reads: `gsutil cat -r 0-5242879 gs://<bucket>/<object>` | (L-ENV-039) |
| the VM is IO-saturated and sshd returns no banner | runaway IO | `gcloud compute instances reset <vm>` (safe with a `RequiresMountsFor` drop-in; needs an operator login) | (L-ENV-032) |

## 4. Network, firewalls and SSH

| Symptom | Cause | Fix | Lesson |
|---|---|---|---|
| SSH worked minutes ago and now times out, while the public app returns 200 | the corporate egress IP rotated out of an IP allowlist | sample egress per destination; RDAP the address; prefer a jump host or tailnet; widen additively; relaunch subagents afterwards | (L-ENV-011) |
| `Permission denied (publickey)` | authentication, not the network | `ssh -v`; if only `publickey` can continue, you need a key file here or your key on the host | (L-ENV-012) |
| the provider's browser console stops connecting after a firewall change | it connects from the provider's addresses | keep the console path allowed before narrowing port 22 | (L-ENV-012) |
| a scan or long job reached through a temporary SSH tunnel dies after one DNS error | the helper that polled the job also owned the tunnel, and its cleanup closed the tunnel when the poll crashed | run the tunnel as its own process for the whole window; retry DNS and socket errors in the poll; close the tunnel only at a final job state | (L-ENV-099) |
| a pasted key is silently ignored by sshd | terminal line wrap broke the key line | paste in two variables and rejoin with `printf`; verify with `ssh-keygen -lf` | (L-ENV-012) |
| the CLI returns `401 Unable to authenticate you` with a valid token | the CLI's own stale stored credential | test the token directly against the provider's REST API | (L-ENV-013) |
| no way to run a command on a VM | some clouds have no remote-exec API | plan SSH or the provider's web console for agent installs | (L-ENV-013) |
| a healthy host looks down | outbound DNS blocked; SNI vhosts refuse IP-only probes; `curl -k https://localhost` returns 000 | `curl --resolve <host>:443:<ip> https://<host>/`; probe with the right Host header from inside the proxy container | (L-ENV-014) |
| a new subdomain resolves to the wrong server | a zone wildcard record | add an explicit record for the new host | (L-ENV-014) |
| a fix "worked" but you lost your own access | the change was not re-tested end to end | re-test the broken thing and your access; probe a port you did not allow; close temporary openings | (L-ENV-013) |
| a VM, or a container on it, cannot reach its own public IP or hostname; a server-side OIDC token exchange fails while browsers work | no hairpin NAT: the cloud does not route that traffic back to the same VM | use the internal service URL for back-channel calls (`http://<idp-container>:8080`), keep the public issuer for browsers and accept both issuers when validating tokens; a Secure Agent connection to a database on the same host uses localhost or the Docker network alias, never the public name | (L-ENV-014) |
| a reverse-proxy source-IP allowlist answers 403 in local tests only | Docker's `userland-proxy` rewrites host-originated (and hairpinned) requests to the bridge gateway (`172.x.0.1`) | test allowlists from a genuinely external client; the proxy's access log shows the real source address | (L-ENV-014) |
| `NET::ERR_CERT_DATE_INVALID` (HSTS blocks click-through) on one machine only | a stale hosts-file entry pins the name to a retired host whose certificate expired | compare `openssl s_client -connect <host>:443 -servername <host>` with the same call against the public DNS address; back up and fix `/c/Windows/System32/drivers/etc/hosts`, run `ipconfig //flushdns` (double slash in git-bash), verify `curl --resolve <host>:443:<ip> https://<host>/` gives 200 and `ssl_verify_result=0`, then clear the browser's HSTS entry (`chrome://net-internals/#hsts`); test whether your own shell can write the file before handing a human an elevated step | (L-ENV-072) |

## 5. Docker and hosts

| Symptom | Cause | Fix | Lesson |
|---|---|---|---|
| `docker ps` shows 0 containers on a busy host | the login user is not in the docker group | always `sudo docker...` | (L-ENV-026) |
| a fixed credential file on the host does not help the container | bind mounts are resolved at container start; `docker restart` does not reload `env_file` | `docker compose up -d --force-recreate <service>` for every service that mounts it | (L-ENV-027) |
| containers Up (healthy) while every job fails with `[Errno 21] Is a directory` | the mount source did not exist, so Docker created an empty directory | fix the source path, then force-recreate | (L-ENV-027) |
| a config edit never reaches a running container | the edit replaced the file (new inode) | write in place (`r+`, `seek(0)`, write, `truncate`, or `sudo tee`); restart after replacing a mounted directory | (L-ENV-028) |
| a change to a file is not live | the file was baked into the image (`COPY`) | rebuild the service (`--profile` for profiled services; `--no-cache` when source changed) | (L-ENV-029) |
| a fix vanished after a rebuild | it was made in the container's writable layer | put it in the repository or image and record the commit | (L-ENV-029) |
| mapping or taskflow files mounted over the image are ignored | the tool reads definitions from the image layer | bake them and rebuild | (L-ENV-029) |
| a stack moved to another cloud starts but its jobs fail | a `/home/<cloud-default-user>/...` path in a volume mount | project-relative paths, Docker secrets or a secret manager; audit with `docker compose config` | (L-ENV-030) |
| a containerized Secure Agent shows up under a random name | it registers under the container hostname | set `hostname: <agent-name>` in the compose file | (L-ENV-031) |
| a native agent is missing from a host inventory | agents run as OS processes, not containers | look for the agent directory and its Java processes; snapshot agent volumes before deleting a VM | (L-ENV-031) |
| the stack does not start after a reboot | Docker raced its data-disk mount | systemd drop-in `RequiresMountsFor=<mount>` on `docker.service` | (L-ENV-032) |
| the OS disk fills (92%, then 100%) although Docker's data-root is on a data disk | containerd's own store (`/var/lib/containerd`: image content and snapshots) stayed on the root disk | check both `sudo docker info --format '{{.DockerRootDir}}'` and `sudo du -sh /var/lib/containerd`; stop docker and containerd, copy the store, point `root` in `/etc/containerd/config.toml` at the data disk (or bind-mount it), add the same `RequiresMountsFor=<mount>` drop-in, start both and verify; the pressure then moves to the data volume | (L-ENV-032), (L-ENV-071) |
| disk space must be reclaimed on a live agent host | blind prunes remove rollback images, old database volumes or files a service runs from | in this order: `sudo docker builder prune -f --filter until=24h` (build cache only), journals and package caches; then review unused images and unreferenced volumes by hand; never prune Docker volumes, the agent's `downloads/` directory (services run from it, L-AGENT-094) or a live agent's directory; backups are the owner's to dispose of; keep about 20 GB free for the agent (L-AGENT-052) | (L-ENV-071), (L-ENV-069) |
| after a reboot one container exits 255 with "Address already in use" | a compose service with a dynamic address took another service's static `ipv4_address` | give every service on that network a fixed address, or an `ip_range` that excludes the static ones | (L-ENV-069) |
| every request to a service fails instantly after a config swap | the daemon kept its old environment | restart through its launcher and verify with one real run | (L-ENV-033) |
| a "compile" run rebuilt live tables | the dbt image's entrypoint runs `dbt build` | `docker run --entrypoint dbt <image> compile...` | (L-ENV-034) |
| a remote script truncated a live file | a relative write after `cd` | absolute paths; back up before writing | (L-ENV-035) |
| the host has no warehouse client or key | they live in a container | `sudo docker exec -i <container> python -` with the script on stdin | (L-ENV-010) |

## 6. Shell and scripts

| Symptom | Cause | Fix | Lesson |
|---|---|---|---|
| a gate reports rc=0 over real failures | the runner was piped through `tail` | capture the runner's own exit code; read its summary line | (L-ENV-036) |
| every cron fire fails with Permission denied while the entry looks fine | `sudo cmd > rootfile` redirects as the caller | `sudo sh -c 'cmd > log 2>&1'`; prove it with one autonomous fire | (L-ENV-036) |
| a script exits 0 and its log is empty | `exec > >(tee /var/log/x)` without write permission | log to a writable path and check it is written | (L-ENV-036) |
| manual runs fail at stage 1 while cron runs pass | a shared `/tmp` path created root-owned by cron | per-UID temp dirs (`/tmp/<name>.$(id -u)`) with a writability check | (L-ENV-036) |
| a lock is held forever | `kill -0` succeeds for a zombie pid | check `ps -o stat=` is not Z; pid plus heartbeat liveness | (L-METHOD-019) |
| a sync hangs silently for hours | no deadline | `timeout <n>` plus an expiring lock, a heartbeat and a stale-heartbeat alert | (L-ENV-037) |
| an HTTP sweep hangs | `urlopen(timeout=...)` does not bound a slow body; server-sent-event streams never end | a hard-deadline watchdog; skip stream paths | (L-ENV-037) |
| a nightly backup "succeeds" after a rename | it dumps the old, now empty target (a 20-byte dump) | monitor dump size against a floor; update backup targets in every rename | (L-ENV-038) |
| a grep picks an unrelated series | dots in `grep -E` match any character | `grep -F` for literal keys | (L-ENV-036) |

## 7. Moving code and running long jobs on a VM

1. Write the file locally with a file tool (never a heredoc for regex-bearing code) (L-ENV-023).
2. `base64 -w0 file` locally; send the text; `base64 -d > file` on the VM; verify with a checksum or `od -c`
   (L-ENV-007).
3. Ship the script on its own, then start it detached in a separate command:
   `setsid nohup bash /tmp/job.sh > /tmp/job.log 2>&1 < /dev/null &` (L-ENV-006).
4. Poll with short, independent calls (`tail -n 5 /tmp/job.log`) until a DONE marker; never treat the end of an SSH
   stream as completion.
5. Keep each poll's output small enough for the channel (about 4 KB through run-command) (L-ENV-003).

## 8. Two Secure Agents on one host

When a second agent shares a VM (for example during an org-to-org migration), give it its own OS user, directory and
systemd unit with memory limits and CPU/IO weights; keep its process engine off so it cannot clash with the first
agent's ports (7080, 7443, 7005, 14479, 5432); deny it the apps' secret files; and run a read-only host watcher that
logs memory, swap, load, disk, unit state, per-user RSS, Java process counts, a port-clash check and the agents' recent
ERROR counts once a minute (L-ENV-040), (L-ENV-005). Details:
[knowledge/02-secure-agent-connections](../02-secure-agent-connections/).

### 8.1 Resizing or rebooting the agent VM

(L-ENV-069)

1. Check that the target size is offered on the VM's current cluster:
   `python -m azure.cli vm list-vm-resize-options -g <rg> -n <vm-name> -o table`. If it is, the resize is one reboot with
   no deallocation; a static public IP and the OS and data disks are kept, and a `CanNotDelete` lock does not block it.
   Resizing is spend: get the approvals first.
2. Announce the window to every session and job that uses the host, drain the lane controller, and keep the one-line
   rollback (the same command with the old size).
3. `python -m azure.cli vm resize -g <rg> -n <vm-name> --size <new-size>` (about 10 minutes, then the reboot).
4. After boot run the fixed post-boot checklist in [Secure Agent - Install, Run & Tune](../02-secure-agent-connections/01-secure-agent-install-run-tune.md): stale
   `.pid` files under the agent's apps (L-AGENT-095), containers that lost a static address (section 5), CDC jobs that
   pass through `awaiting_auto_restart` back to running, and every agent READY with its engines RUNNING.

Sizing evidence: an agent with 17 services plus a second agent on 4 vCPU ran at load 12-31 with swap at 100%; on 8 vCPU
the load was 11 for the same work. A stopped agent installation still occupies about 46 GB of disk.

## 9. Data-platform command lines

| Symptom | Cause | Fix | Lesson |
|---|---|---|---|
| client-side counts and joins are too small | `bq query` returns 100 rows by default | `--max_rows=100000` or aggregate in SQL | (L-ENV-041) |
| an automated query scans far more than intended | no spend cap | `maximum_bytes_billed=<bytes>` in `.bigqueryrc` | (L-ENV-041) |
| "Unrecognized name: <new column>" right after a schema change | metadata propagates lazily | sleep about 15 s and retry once | (L-ENV-041) |
| a SQL Server client gets "Read: EOF" from a Fabric warehouse | go-mssqldb cannot do the Entra TDS handshake | pyodbc with ODBC Driver 18 and a service-principal token; a JSON sidecar for BI tools | (L-ENV-042) |
| a Fabric row count reads 0 | `sys.partitions` returned 0 | a real `COUNT(*)` | (L-ENV-042) |
| a warehouse capacity bills while nothing runs | Fabric F-SKUs bill while Active | pause the capacity | (L-ENV-042) |
| you cannot tell whether a dataset is absent or only unreadable | the two answers differ | `bq show <cloud-project>:<dataset>`: "Not found" (404) = absent, "Access Denied" (403) = exists but unreadable; calibrate with a made-up name first | (L-ENV-041) |
| it is unclear which identity may create datasets, run jobs or mint keys | rights differ per identity | `POST https://cloudresourcemanager.googleapis.com/v1/projects/<cloud-project>:testIamPermissions` with `{"permissions": ["bigquery.datasets.create", "bigquery.jobs.create", "iam.serviceAccountKeys.create", "serviceusage.quotas.update"]}` returns the granted subset; run it for the operator and, from the VM with the metadata-server token, for the VM's service account; metadata reads (`__TABLES__`, `datasets.list`) bill 0 bytes | (L-ENV-041) |
| a runaway query is not stopped by any quota | the project quota `QueryUsagePerDay` defaults to 200 TiB a day and per-user usage is unlimited | `maximum_bytes_billed` on every automated job and a default table expiration on sample datasets; a custom daily quota needs `serviceusage.quotas.update` | (L-ENV-041), (L-ENV-041) |

### 9.1 BI tools and API gateways over the IDMC-built warehouse

The serving patterns (extract refill with a credential-less republish, push on change, the hidden-twin view swap, the
serving-mode decision, zero-copy activation) are in [Serving Outputs to BI and Apps](../03-cdi-data-integration/10-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md)
(L-ENV-081). This table holds only the command-line and API traps.

| Symptom | Cause | Fix | Lesson |
|---|---|---|---|
| a Tableau publish with a BigQuery service-account credential returns 403132 in 0.2 s; `PUT.../connections/<id>` with an `authenticationType` returns 404020 | Tableau refuses any non-OAuth BigQuery credential before calling Google (a bogus value gets the identical code); service-account connections are authored in Tableau Desktop | fix the session-control policy behind the OAuth expiry (L-ENV-064), or refill the extracts yourself and republish without credentials (see the serving doc) | (L-ENV-081) |
| a REST publish returns 406000 | a form-data upload (Python `requests` with `files=`) | send the publish as `multipart/mixed` | (L-ENV-081) |
| a publish fails after about 3 minutes with 400011 "non-existent parameter" | any `<` followed later by a `>` in custom SQL is read as a parameter reference | write `b >= a`, `500 > status` or BETWEEN, and lint tile SQL for `<`; 400011 also follows a sheet added by XML without a window and a viewpoint (L-ENV-061) | (L-ENV-085) |
| a drift keeper republishes in a loop | Tableau stores SQL newlines as `&#10;` / `&#13;`, so a patch that compares raw SQL rewrites it on every run | map those entities before comparing or replacing | (L-ENV-085) |
| 403132 on a publish that should ride a saved OAuth credential; every sheet becomes a tab | a per-connection credential block; no `<views>` list | one workbook-level `<connectionCredentials name='<user>@example.com' password='' embed='true' oAuth='true'/>` inside `<workbook>`; send a `<views>` list with `hidden='true'` entries | (L-ENV-084) |
| `GET.../jobs/<id>` returns 400031 for an extract job | create_extracts jobs cannot be polled by id | poll `GET.../jobs?filter=createdAt:gte:<ts>&pageSize=100` and match the id; `createExtract` needs API 3.27+ and the JWT scopes `tableau:extracts:create`, `tableau:tasks:run`, `tableau:jobs:read`; a refresh answering 409093 is already queued | (L-ENV-084) |
| a workbook is "not found" by name | `filter=name:eq:` splits on commas | list and match the exact name in code | (L-ENV-084) |
| parsing `extractUpdateTime` fails | UTC text with a U+202F narrow no-break space before AM/PM | normalize that space before parsing | (L-ENV-085) |
| data-triggered refreshes stop for the rest of the day | Tableau Cloud allows about 8 backgrounder hours a day per Creator licence; a refresh every 5 minutes would need about 15 h | cap data-triggered refreshes (about 180 minutes a day) | (L-ENV-085) |
| sorting the warehouse view changes nothing in the sheet | row order comes from the sheet, not the view | carry an explicit `row_number` column and sort the sheet by its MIN; check the SQL does not filter new rows out | (L-ENV-085) |
| a Direct Trust connected app cannot get a new secret over the API (401 on every scope and version) | secret creation has no JWT scope | move consumers to an External Authorization Server connected app with your own RSA key and a public JWKS: JWT `aud` = `tableau:<site-luid>` (plain `tableau` gives 10084), no header `iss` on an embed token (409 "UUID string too large"); deleting an old Direct Trust secret needs `tableau:connected_app_direct_trust_secrets:delete` | (L-ENV-086) |
| an embed token opens views it was not meant to | a `tableau:views:embed` token is not limited to one view: its subject can open any view that user can see | a dedicated viewer user or a project-restricted connected app; mint tokens server-side for a known referer only | (L-ENV-086) |
| headless Chromium loses `bootstrapSession` with ERR_NETWORK_CHANGED | `--network host` on a busy Docker host (veth churn) | time pages from a bridge network or another machine; the Embedding API test needs a connected-app JWT with `tableau:views:embed` (a REST cookie login does not work there) | (L-ENV-085) |
| creating a Data Cloud connection returns 400 "not supported" | `connectorType` casing | `BIGQUERY` in upper case on `/ssot/connections`; count headless with `POST /ssot/query-sql` `{"sql": "SELECT COUNT(*) FROM <object>__dll"}` | (L-ENV-087) |
| `FUNCTIONALITY_NOT_ENABLED` on segment create or publish, schedule changes or data-stream runs | an API-only integration user with the Data Cloud User permission set | that user can run identity resolution (`POST /ssot/identity-resolutions/<rulesetId>/actions/run-now`); segment and activation steps need a Data Cloud admin or the UI | (L-ENV-087) |
| a Grafana BigQuery datasource health check shows 403 | the Cloud Resource Manager API is disabled in the project; real queries still work | judge the datasource with `POST /api/ds/query` | (L-ENV-056), (L-ENV-056) |
| `docker cp` into Grafana provisioning fails | the provisioning directory is bind-mounted read-only | write the host-side directory, then `POST /api/admin/provisioning/dashboards/reload` | (L-ENV-056) |
| Grafana GETs work but POST or DELETE answer "Permissions needed"; curl returns 000 | an e-mail admin login inside the URL splits the host; wrong admin credentials fall back silently to the anonymous Viewer | `curl -u '<user>@example.com'` (curl then asks for the password, so it never sits on the command line or in shell history) | (L-ENV-056) |
| an API gateway cannot time calls (`now` is a parse error, `uuid` is evaluated once) | gateway policy expressions have no clock | each backend adds a `server-timing: app;dur=<ms>` response header and the access log carries it; analytics on gateway traffic go through IDMC (CAI or CDC/CDI into the warehouse), per the integration-layer split in [CAI Runtime](../05-cai-application-integration/02-cai-runtime-invoke-urls-control.md) | (L-ENV-088) |

## 10. Pre-flight for a new workstation or host

Run through this once per machine before blaming IDMC for anything:

1. On Windows git-bash: does `az` print output? If not, use `python -m azure.cli` (L-ENV-016).
2. Is `MSYS_NO_PATHCONV=1` set only in the shells that call IDMC REST helpers (L-ENV-017)?
3. Are `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1` set for Python writers (L-ENV-022)?
4. Which gcloud account is active, and do your scripts pin `--account` (L-ENV-009)?
5. Is the human cloud login alive (`timeout 15 gcloud auth print-access-token`), and is there a service-account path
   for headless work (L-ENV-008)?
6. What is your egress address right now, per destination, and is anything allowlisted on it (L-ENV-011)?
7. On each host: is the login user in the docker group, or must every call be `sudo docker` (L-ENV-026)?
8. Does Docker's data-root live on a separate mount with `RequiresMountsFor` set (L-ENV-032)?
9. Is the Secure Agent under systemd, not under a run-command scope (L-ENV-005)?
10. Where do scratch scripts go? A private directory, never a shared temp folder (L-ENV-025).
11. Do scripts written on Windows reach the Linux host with LF endings (`bash -n` there before the first run)
    (L-ENV-023)?
12. Does every service-account key's project still exist, and is the gcloud default project live (L-ENV-052)?
13. On agent hosts: are both Docker's data-root and containerd's store off the OS disk (L-ENV-071)?

## 11. Overturned beliefs (kept so nobody re-learns them)

| Belief | Believed | Overturned by |
|---|---|---|
| Set `MSYS_NO_PATHCONV=1` (or run from cmd) for the bq/gcloud wrappers | 2026-07-04 | export it only for IDMC REST helpers, never globally (L-ENV-017); was L-ENV-053 |
| Allowlisting the corporate proxy's /24 is a durable reach path | 2026-09-14 to 2026-09-21 | egress rotates; IAP hops and control-plane channels (L-ENV-011); was L-ENV-054 |
| `docker exec -i... < file` does nothing through run-command | to 2026-09-22 | it works through a managed run-command (L-ENV-004); was L-ENV-055 |
