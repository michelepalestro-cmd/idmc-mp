#!/usr/bin/env python3
"""idmc_package_edit.py - edit a v3 export package OFFLINE and keep it importable: change a file, fix
exportMetadata.v2.json objectRefs, and rewrite ONLY the changed files' SHA-256 lines in exportPackage.chksum.
Never talks to IDMC. Never prints file contents (packages can hold plaintext secrets).

  python idmc_package_edit.py inspect pkg.zip             # files, objects, refs, checksum verdict per line
  python idmc_package_edit.py verify  pkg.zip             # exit 1 if a path-keyed checksum line is wrong
  python idmc_package_edit.py replace pkg.zip --file <entry> --with local.file --out new.zip [--execute]
  python idmc_package_edit.py sub pkg.zip --file <entry>[!<inner member>] --pattern REGEX (--repl TEXT | --repl-file F)
                               [--count 1] --out new.zip [--execute]
  python idmc_package_edit.py drop pkg.zip --name <objectName>[,<objectName>] --out new.zip [--execute]
  python idmc_package_edit.py remap pkg.zip --old <guid> --new <guid> [--refs remap|keep] [--drop-entry] --out new.zip

Default is DRY-RUN (the plan is printed); --execute writes --out (never over the input; --force to replace --out).
Rules (PROVEN 2026-09 in real imports):
  * chksum lines are 'path=SHA256' in UPPER-case hex, keys escaped like Java properties (a space is '\\ ').
    Replace only the lines of changed files, including exportMetadata.v2.json when it changes (else
    MigrationSvc_073 'package has been modified'); copy every other line byte for byte (the GUID-keyed opaque
    lines can stay as they are).
  * Removing an object: drop its files, its exportMetadata entry, its chksum lines and its CSV rows, and refuse
    while another object still lists it in objectRefs (a dangling ref fails with MigrationSvc_031, empty details).
  * Remap (proven for a runtime-environment reference the target lacked): swap the id inside every file, nested
    zips included, drop the old entry (--drop-entry) and remap every objectRefs list. For a CONNECTION swap a
    2026-08 lesson found that adding the new GUID to objectRefs failed MigrationSvc_031: use --refs keep.
  * Pretty-printed XML: match whitespace-tolerantly with 'sub', e.g. --pattern '<process\\b.*?</process>'
    (re.S) and assert the count. Write regex-bearing replacement text to a file (--repl-file), not a heredoc:
    shells turned \\b into a backspace byte in a real incident.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402

META, CHK = "exportMetadata.v2.json", "exportPackage.chksum"
sha = lambda b: hashlib.sha256(b).hexdigest().upper()  # noqa: E731


def unescape_key(k):
    """Java-properties key unescape: '\\ ' -> ' ', '\\:' -> ':', '\\=' -> '=', '\\uXXXX'."""
    out, i = [], 0
    while i < len(k):
        if k[i] == "\\" and i + 1 < len(k):
            n = k[i + 1]
            if n == "u" and i + 6 <= len(k):
                out.append(chr(int(k[i + 2:i + 6], 16)))
                i += 6
                continue
            out.append({"t": "\t", "n": "\n", "r": "\r", "f": "\f"}.get(n, n))
            i += 2
            continue
        out.append(k[i])
        i += 1
    return "".join(out)


class Pkg:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.infos = {i.filename: i for i in self.z.infolist()}
        self.data = {n: self.z.read(n) for n in self.infos}
        self.changed = set()
        self.meta = json.loads(self.data[META]) if META in self.data else {"exportedObjects": []}

    def objects(self):
        return self.meta.get("exportedObjects") or []

    def set(self, name, b):
        if self.data.get(name) != b:
            self.data[name], _ = b, self.changed.add(name)

    def set_meta(self):
        self.set(META, json.dumps(self.meta, indent=2).encode())

    def check_lines(self):
        """[(line, key, verdict)] verdict: comment | OK | MISMATCH | STALE(changed) | opaque (not a file path)."""
        out = []
        for line in self.data.get(CHK, b"").decode().splitlines():
            if not line or line.startswith("#") or "=" not in line:
                out.append((line, None, "comment"))
                continue
            k, v = line.rsplit("=", 1)
            real = unescape_key(k)
            if real not in self.data:
                out.append((line, real, "opaque"))
            else:
                out.append((line, real, "OK" if sha(self.data[real]) == v.strip().upper() else "MISMATCH"))
        return out

    def new_chksum(self):
        lines, done = [], set()
        for line, real, _ in self.check_lines():
            if real in self.changed:
                line = f"{line.rsplit('=', 1)[0]}={sha(self.data[real])}"
                done.add(real)
            lines.append(line)
        unlisted = sorted(n for n in self.changed - done - {CHK} if n in self.data)
        if unlisted:   # e.g. the ContentsofExportPackage CSV: the package never checksummed it, so no line is added
            print(f"  note: changed but not checksummed by this package (left unlisted): {unlisted}")
        return ("\n".join(lines) + "\n").encode()

    def write(self, out):
        chk = self.new_chksum()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as w:
            for n, info in self.infos.items():
                if n in self.data:
                    w.writestr(info, chk if n == CHK else self.data[n])


def edit_inner(outer, member, fn):
    """Apply fn(bytes)->bytes to one member of a nested zip; returns the rebuilt inner zip bytes."""
    zin, buf = zipfile.ZipFile(io.BytesIO(outer)), io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as w:
        for i in zin.infolist():
            b = zin.read(i.filename)
            w.writestr(i, fn(b) if i.filename == member else b)
    return buf.getvalue()


def cmd_inspect(p, strict):
    print(f"{len(p.data)} files, {len(p.objects())} exported objects")
    for o in p.objects():
        refs = (o.get("metadata") or {}).get("objectRefs") or []
        print(f"  {o.get('objectType', ''):22} {o.get('objectName')}  guid={o.get('objectGuid')} path={o.get('path')} refs={len(refs)}")
    bad = 0
    for line, real, v in p.check_lines():
        if v in ("OK", "MISMATCH", "opaque"):
            print(f"  chksum {v:8} {real}")
            bad += v == "MISMATCH"
    print(f"checksum: {bad} mismatch(es) on path-keyed lines")
    if strict and bad:
        sys.exit(1)


def op_drop(p, names):
    drop = [o for o in p.objects() if o.get("objectName") in names]
    if len(drop) != len(names):
        H.die(f"not in exportMetadata: {sorted(names - {o.get('objectName') for o in drop})}")
    guids = {o["objectGuid"] for o in drop}
    users = [o["objectName"] for o in p.objects() if o["objectGuid"] not in guids
             and set((o.get("metadata") or {}).get("objectRefs") or []) & guids]
    if users:
        H.die(f"still referenced by {users}: drop those too, or remap their refs first")
    p.meta["exportedObjects"] = [o for o in p.objects() if o["objectGuid"] not in guids]
    p.set_meta()
    files = [n for n in p.data if any(n.split("/")[-1].startswith(x + ".") for x in names)]
    chk = [(ln, k) for ln, k, v in p.check_lines() if k in files]
    for n in files:
        del p.data[n]
    for n in [n for n in p.data if n.endswith(".csv")]:
        p.set(n, b"\n".join(r for r in p.data[n].split(b"\n") if not any(b"," + x.encode() + b"," in r for x in names)))
    kept = [ln for ln, k, _ in p.check_lines() if k not in files]
    p.data[CHK] = ("\n".join(kept) + "\n").encode()
    print(f"drop {sorted(names)}: {len(files)} file(s), {len(chk)} chksum line(s), metadata entries {len(drop)}")


def op_remap(p, old, new, refs, drop_entry):
    ob, nb, hits = old.encode(), new.encode(), 0
    for n in list(p.data):
        b = p.data[n]
        if n.endswith(".zip") and b[:2] == b"PK":
            inner = zipfile.ZipFile(io.BytesIO(b))
            for m in inner.namelist():
                if ob in inner.read(m):
                    b = edit_inner(b, m, lambda x: x.replace(ob, nb))
                    hits += 1
            p.set(n, b)
        elif n not in (META, CHK) and ob in b:
            p.set(n, b.replace(ob, nb))
            hits += 1
    if drop_entry:
        p.meta["exportedObjects"] = [o for o in p.objects() if o.get("objectGuid") != old]
    if refs == "remap":
        for o in p.objects():
            r = (o.get("metadata") or {}).get("objectRefs")
            if r and old in r:
                o["metadata"]["objectRefs"] = list(dict.fromkeys(new if x == old else x for x in r))
    p.set_meta()
    left = sum(p.data[n].count(ob) for n in p.data if n != CHK and not n.endswith(".zip"))
    print(f"remap: {hits} file/member(s) rewritten, refs={refs}, drop_entry={drop_entry}, old id left outside zips: {left}")


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description="offline v3 package editor")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("inspect", "verify"):
        sub.add_parser(c).add_argument("package")
    parsers = {c: sub.add_parser(c) for c in ("replace", "sub", "drop", "remap")}
    for c, sp in parsers.items():
        sp.add_argument("package")
        sp.add_argument("--out", required=True)
        sp.add_argument("--execute", action="store_true")
        sp.add_argument("--force", action="store_true")
    parsers["replace"].add_argument("--file", required=True)
    parsers["replace"].add_argument("--with", dest="src", required=True)
    s = parsers["sub"]
    s.add_argument("--file", required=True)
    s.add_argument("--pattern", required=True)
    s.add_argument("--repl")
    s.add_argument("--repl-file")
    s.add_argument("--count", type=int, default=1)
    parsers["drop"].add_argument("--name", required=True)
    r = parsers["remap"]
    r.add_argument("--old", required=True)
    r.add_argument("--new", required=True)
    r.add_argument("--refs", default="remap", choices=["remap", "keep"])
    r.add_argument("--drop-entry", action="store_true")
    a = ap.parse_args()
    p = Pkg(a.package)
    if a.cmd in ("inspect", "verify"):
        return cmd_inspect(p, a.cmd == "verify")
    if os.path.abspath(a.out) == os.path.abspath(a.package) or (os.path.exists(a.out) and not a.force):
        H.die("--out must be a new file (never the input; --force to replace an existing --out)")
    if a.cmd == "replace":
        if a.file not in p.data:
            H.die(f"no entry {a.file}")
        p.set(a.file, open(a.src, "rb").read())
    elif a.cmd == "sub":
        repl = open(a.repl_file, encoding="utf-8").read() if a.repl_file else a.repl
        if repl is None:
            H.die("give --repl or --repl-file")
        outer, _, member = a.file.partition("!")
        if outer not in p.data:
            H.die(f"no entry {outer}")
        count = [0]

        def fn(b):
            txt, k = re.subn(a.pattern, lambda m: repl, b.decode("utf-8"), flags=re.S)
            count[0] = k
            return txt.encode("utf-8")
        p.set(outer, edit_inner(p.data[outer], member, fn) if member else fn(p.data[outer]))
        if count[0] != a.count:
            H.die(f"pattern matched {count[0]} time(s), expected {a.count}: nothing written")
    elif a.cmd == "drop":
        op_drop(p, set(a.name.split(",")))
    else:
        op_remap(p, a.old, a.new, a.refs, a.drop_entry)
    print("changed files:", sorted(p.changed - {CHK}) or "none")
    if not a.execute:
        print("DRY-RUN: nothing written. Re-run with --execute to write", a.out)
        return
    p.write(a.out)
    q = Pkg(a.out)
    bad = [k for _, k, v in q.check_lines() if v == "MISMATCH"]
    print(f"wrote {a.out}; path-keyed checksum mismatches after edit: {bad or 'none'}")


if __name__ == "__main__":
    main()
