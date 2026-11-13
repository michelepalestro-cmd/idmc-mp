# Environment traps

> **July 2026 snapshot.** Where this file says "UI-only", "no REST verb" or "walled", read it as a dated verdict:
> many were overturned later (KB `13 - Lessons Learned/Overturned Beliefs.md`, Laws 16-19). Before telling a user
> something is not possible, work the workaround ladder in KB `00 - Start Here/08 New Pipeline Milestones`.
> "Org A" / "Org B" are two example orgs; derive your own values (Law 1).

Everything here cost real session time and none of it is an IDMC API problem. These are the things
that make a working call look broken.

## Secrets — the rule

**Never paste a token, cookie, private key, or a browser Network-tab request into chat.** A Network tab
dump carries `Cookie:` and `Authorization:` headers; session cookies are full account credentials that
bypass password *and* MFA. Once pasted, they are in the transcript.

- Share the **error text**, not the request.
- Credentials arrive via **environment variables** or a **file path** — a path is enough, never contents.
- If a secret is exposed anyway: say so plainly, tell the user to **rotate the token and log out** (which
  invalidates the session), do not use it, and do not write it to disk.
- Do not put secrets in scripts you write. Read them from `os.environ` at run time.

Org IDs, pod names, agent IDs and agent host IPs are configuration, not secrets.

## Corporate egress rotates — IP-pinned firewall rules go stale

Outbound traffic can leave through a corporate proxy pool whose address changes mid-session
(observed: `<host-ip>` → `<host-ip>`, different /24s, both a corporate egress proxy). Symptoms: a port that
worked minutes ago now times out, and a firewall rule you just added appears to do nothing.

- **Check egress per destination, not once.** A public echo service can be on a proxy bypass list and
  report your real IP while traffic to the actual target goes through the proxy. Sample the egress a
  few times.
- Confirm ownership with RDAP before trusting an address: `curl https://rdap.arin.net/registry/ip/<ip>`.
- Allowlisting a shared proxy IP is fragile and not exclusively yours. A jump host or tailnet is the
  durable answer; a `/24` is a POC compromise worth flagging to the user.
- **Diagnose before re-probing.** A rotated egress IP looks exactly like an outage.

## A browser console has its own source address

A provider's web console does **not** connect from the user's laptop — it SSHes from the provider's
infrastructure. Narrowing `:22` to the user's home IPs plus yours silently breaks it:
`Timed out while waiting for handshake`.

Before narrowing an SSH allowlist, keep the provider's console reachable — otherwise you remove the
user's own fallback access. Verify with a `TimeoutError` vs `Permission denied` distinction: timeout is
**network/firewall**, permission-denied is **authentication**. They are different problems.

## Reachability is not authentication

`SSH-2.0-OpenSSH_…` banner means the port is open. `Permission denied (publickey)` means the port was
never the issue. Check `ssh -v` for `Authentications that can continue:` — if it says `publickey` only,
no credential pasted into chat can help; it must be a key file on this machine or a key of yours on the
host.

Account-level SSH keys at a cloud provider apply **only to newly created instances**, not running ones.

## A pasted key can arrive corrupted

A long key line wrapped across lines by the terminal writes a broken `authorized_keys` entry, and sshd
silently ignores it. If auth still fails right after the user pastes a key, suspect wrapping, not the
user.

Have them verify (`ssh-keygen -lf <ssh-key>`), or split the key into shell variables and
rejoin on the host so no single pasted line can wrap:

```bash
K1=<first-half>
K2=<second-half>
mkdir -p ~/.ssh && chmod 700 ~/.ssh
printf 'ssh-ed25519 %s%s comment\n' "$K1" "$K2" >> <ssh-key>
chmod 600 <ssh-key>
ssh-keygen -lf <ssh-key>
```

Use `>>` unless you have confirmed the file holds nothing you need.

## Prefer the provider REST API over its CLI

A CLI can hold its own stale stored credential and return `401 Unable to authenticate you` while the
token you were given is valid. Test the token directly against the REST API before believing the CLI.

## Databases in containers are not on localhost

Containers commonly bind the **private interface**, not loopback — every `localhost` port is closed. A
connector sheet saying `Host: localhost` will fail.

```bash
ss -ltnp                                  # what is actually listening, and on which address
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}'
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' <container>   # real db/user names
```

Observed on `<agentName>`: PostgreSQL 16.13, ClickHouse 25.3 and MongoDB 7.0.31 all on
**`<host-ip>`** (`:5432`, `:8123`/`:9000`, `:27017`), not `localhost`. Also note a host can report a
second private address in its login banner that differs from the provider's API value — trust `ss`.

**Verify the data is real before governing it.** Count the rows of the tables in scope first.
Governance over empty tables is vacuous, and a scan that finds nothing looks like a broken scan.

## The Secure Agent host

- **Refuses to run as root.** Create a normal user first.
- **A naive `systemd` unit fails silently** — `infaagent` resolves paths relative to its own directory,
  so without `WorkingDirectory` it dies with `cannot open ./agent_start.sh`. It also forks, so it needs
  `RemainAfterExit`. Symptom: `systemctl is-active` says `inactive` while the process runs — meaning a
  reboot leaves the agent down.

```ini
[Service]
Type=forking
RemainAfterExit=yes
User=infa
WorkingDirectory=/home/infa/infaagent/apps/agentcore
ExecStart=/home/infa/infaagent/apps/agentcore/infaagent startup
ExecStop=/home/infa/infaagent/apps/agentcore/infaagent shutdown
```

  Do not add `Restart=on-failure` while a manual instance is running — two JVMs then fight the
  singleton lock (`SingularApplicationLock: Cannot acquire lock`), and the agent never reaches
  `readyToRun: true`. Verify `pgrep -af "agentcore.*MainApp" | wc -l` is 1, then `systemctl restart`
  and confirm `READY` afterwards.
- **Disk:** the installer is ~382 MB and needs ~2 GB to unpack. Check free space first; a full disk
  produces blank logs and stuck runs that look like application bugs.
- `nohup` logs can come back empty due to buffering — do not read that as silence.

## Profiling dies at the OS layer, not the IDMC layer

Two failures that present as "IDMC profiling is broken / not entitled" and are neither:

- **`pmdtm: error while loading shared libraries: libidn.so.11` → exit 127.** The native profiling
  engine is a C++ binary; Debian 12 ships only `libidn.so.12`, and `libidn11` is not in the repos.
  Symptom on Org B was 1,965 profiling deaths, **every one** exit 127, and **zero**
  `OutOfMemoryError`. Fix: symlink `libidn.so.11 → libidn.so.12` (ABI-compatible) on the agent's
  library path, then re-fire. Do not chase a JVM heap theory — exit 127 is an ELF loader failure, and
  a Java OOM would be exit 137 with a stack trace.
- **Coverage looks catastrophic and is actually complete.** Profiling samples rows, so a table with
  `NumberOfRows = 0` can never profile — `core.profiled` stays false forever and correctly so. On
  Org B, 97.9% of unprofiled columns were in **empty** tables; the 21% headline figure tracked each
  source's non-empty-table ratio exactly. Before reporting a coverage problem, compute
  profiled% against **tables that hold rows**, not all tables.

Related, same family: the native PostgreSQL connector refuses custom enum types
(`native type system does not support the data type [BOOKING_KIND]`) and plain `json` columns
(`could not identify an equality operator for type json`). `jsonb` profiles fine. Mitigation is a
view layer casting `enum::text` / `json::text` — but on a real corpus it recovered only ~0.25% of
columns, so price that work before doing it.

## Verify a fix, do not assume it

After changing a firewall, a unit file or a permission: re-test the thing that was broken **and** the
access you rely on. Confirm a firewall actually filters (probe a port you did *not* allow) rather than
trusting that it applied. When you open something temporarily, close it in the same session and verify
your own access survived.
