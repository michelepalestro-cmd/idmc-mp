# Field lessons: an end-to-end IDMC build on a property data platform

> Field lessons from one end-to-end IDMC build on a commercial-property data platform (ClickHouse + PostgreSQL + BigQuery sources; profiling, DQ rules, mastering, catalog). Generic: names and ids removed. Cross-referenced to lessons.jsonl ids.
> 600 lessons. Part 1 (`PD-P1-`): access, connections, CDI mappings, profiling and DQ. Part 2 (`PD-P2-`): MDM and golden
> records, catalog, ClickHouse and databases, storage and backups, method. `KB:` = ids in `lessons.jsonl` (`new` = only
> here). `Status: superseded` marks a belief a later lesson overturned: always read the later one.

## Access & orgs

### PD-P1-001 A guest app in a shared org needs its own job budget, paused below the incumbent's breaker
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** The org (its pod), shared by the property app and the live demo app; guard card M1
- **Lesson:** The two apps draw on one hidden monthly job cap (assumed 10,000, reset date unknown). The live demo app's `budget_scan()` reads the whole org activity log into its own ledger (SOFT 8,500 / HARD 9,500), so the property app jobs push the demo app toward its breaker. The demo app ran about 944 jobs/day (Oct 1-3: 2,775 org jobs, none from the property app), so if the cap rolled the org would reach 10,000 around Oct 8, before the demo app's own calendar-month breaker tripped. Pausing the property app at 9,000 would have inverted "the demo app has priority". The property app got hard caps of 300/month, 20/day and 10/hour, a warning at 7,000 org jobs, and a pause at 8,000, below the demo app's 8,500 soft breaker.
- **Fix / do this:** In a shared org, give each tenant its own counted budget and set the guest's pause below the owner's breaker (or at the soft breaker minus the guest's daily maximum). Prove the pause with one refused test. Report org headroom as information, not as the verdict.
- **KB:** L-IPU-041, L-IPU-043

### PD-P1-002 When the job-cap reset window is unknown, take org usage as the max over 4 windows
- **Date:** 2026-10-03
- **Context:** The budget guard (vendor question on the reset date unanswered)
- **Lesson:** Nobody knew when the cap resets (org timezone America/Los_Angeles, licences started 06-25/06-30). On 10-04 the calendar month UTC showed 2,899 jobs, but since-the-25th / rolling-30-days showed 6,774, so the runway shrank from about Oct 12-13 to about Oct 6-8.
- **Fix / do this:** Org usage = max(calendar month UTC, calendar month Pacific, since the 25th, rolling 30 days). Drop a window only when the vendor rules it out. Project the dates for 7,000 / 8,000 / 8,500 / 9,500 / 10,000 at the recent pace.
- **KB:** L-IPU-059

### PD-P1-003 The licence record can flip Trial to Production under you: diff it every cycle
- **Date:** 2026-10-03
- **Context:** Org licence state, read by the guard and by the idmc-org / idmc-limits lanes
- **Lesson:** At 15:35Z on 10-03 `GET /saas/public/core/v3/license/org/<uuid>` showed orgType flip from Trial to Production, while all 7 customLicenses stayed TRIAL. `license-service/api/v1/OrgLicenseAssignment('<uuid>')/EffectiveLicenses()` listed 470 licences and 32 limits, all set to -1. The -1 limits still say nothing about the hidden job cap.
- **Fix / do this:** Before each IDMC cycle, diff EffectiveLicenses and the v3 licence record and take a metering baseline. Run a weekly metering export, and if any billed IPU is above 0, freeze runs and tell the owner.
- **KB:** L-IPU-030, L-IPU-057, L-AUTH-072, L-MDM-058

### PD-P1-004 One cached v2 session, at most one re-login per 24-25 min, a block file on any 4xx: the IDMC user is shared with a live demo
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** guard, gate and laptop session helpers; all property-app lanes use the same IDMC user as the live demo app
- **Lesson:** A v2 session expires 30 min after it is granted, however active it is. Rejected logins add up across sessions, and about 6 lock the user (IDS_086, roughly 6 h), which would also stop the live demo. The password was already stored in 5+ places, and rotating it breaks the MCP OAuth client. The guard reuses its session file while it is under 24 min old (`session_max_age_s` 1440). Any 4xx login writes a login block file, and the guard never logs in again until a person removes it.
- **Fix / do this:** Keep one session file per tool (0600, for example `~/.idmc/tgt_session.json`) and re-login at most once per 24-25 min through the host helper. Never retry a failed login, fail closed on the block file, back off 6 h on IDS_086, and record every login in the call log. Use an OAuth client (accessTimeout 1440) for MCP, or a dedicated app IDMC user.
- **KB:** L-AUTH-027, L-AUTH-031, L-AUTH-034, L-AUTH-036, L-AUTH-040, L-AUTH-041, L-METHOD-004, L-METHOD-070

### PD-P1-005 Reuse the host's existing IDMC helper session under its lock instead of adding a second login path
- **Date:** 2026-10-04
- **Context:** guard on the shared agent host (session provider "host helper")
- **Lesson:** On the shared host, the guard imports the host's `idmc.py` and uses its cached target session (its own 25-min rule). Only when that cache is stale does it call idmc.py's own flock-serialized login(), which re-checks the cache under the lock and honours the login block file. The guard reads no credentials and writes no session file. Its cron runs at :00/:30, the same minutes as the host's health job, so any login that falls due is shared (0 extra logins). The CDGC orgUuid header comes from config.
- **Fix / do this:** On a host that already has an IDMC session helper, plug into it as a provider: one login path per host. Force IDMC_ORG=target so the call never reaches the retired source org, and fail closed on a session for any other org. Wrap urlopen to count the logins it triggers, and record login calls in every status.
- **KB:** L-AUTH-030, L-AUTH-031, L-AUTH-038, L-AUTH-041

### PD-P1-006 Fail closed if the session belongs to an unexpected org
- **Date:** 2026-10-04
- **Context:** guard and gate session checks
- **Lesson:** After the migration off the retired source org, two orgs were reachable with similar tooling. The guard compares the session's orgId with `expected_org_id` (<org>) and refuses to continue on any other org. The gate checks the orgId prefix.
- **Fix / do this:** Put the expected org id in the config and check it after every login or session reuse, before any read or write.
- **KB:** L-AUTH-054

### PD-P1-007 Build every service host from the login serverUrl; CDGC calls also need X-INFA-ORG-ID = the org UUID
- **Date:** 2026-10-04
- **Context:** guard readers (profiling, CDGC datasources and observable jobs, idmc-api)
- **Lesson:** Each service has its own host and auth:
  - **Profiling:** `https://<pod>-dqprofile.<domain>/profiling-service/api/v1`, with the session in `IDS-SESSION-ID`.
  - **CDGC JWT:** minted at `POST https://<domain>/identity-service/api/v1/jwt/Token?client_id=cdlg_app&nonce=..`, sending the session as `IDS-SESSION-ID` plus the `USER_SESSION` cookie.
  - **CDGC and idmc-api calls:** `Authorization: Bearer <jwt>`, `IDS-SESSION-ID` and `X-INFA-ORG-ID` = orgUuid.

  The laptop v2 login returns orgUuid. The shared host's reused session does not, so the UUID is kept in config (`org_uuid`).
- **Fix / do this:** Split the serverUrl host into pod and domain, and build every service host from those parts. Store the org UUID in config as a fallback. Mint one CDGC JWT per session, cache it for at most 20 min, and re-mint it from the cached session. Assert the org id (`GET /api/v2/org` == <org>) in every writer script.
- **KB:** L-CDGC-001, L-AUTH-002, L-AUTH-003, L-AUTH-022, L-AUTH-028, L-AGENT-068 (related)

### PD-P1-008 Treat a zero-byte 200 or an HTML 200 as a failed read
- **Date:** 2026-10-04
- **Context:** guard HTTP layer
- **Lesson:** The guard maps a 200 whose body starts with `<` (wrong plane or a gateway artifact) and a zero-byte 200 to a failed read. Its `check` then blocks instead of treating either as an empty, healthy answer. Back in July, catalog and profile runs on the second org stayed pending on exactly this data360 zero-byte-200 anomaly.
- **Fix / do this:** In every HTTP helper, reject empty or HTML bodies on 200 and record them as read errors.
- **KB:** L-AUTH-006, L-CDGC-006, L-METHOD-025

### PD-P1-009 Credentials: one helper or session file per host, one named writer per run, a rotation runbook that lists every copy
- **Date:** 2026-10-04
- **Context:** gate G1 / plan v3 decision 27
- **Lesson:** Password copies had spread across the shared host, laptop `~/.idmc`, the uiwalk env and the MCP OAuth client, and several fleet sessions reached the same org with their own copies. That multiplies both lockout risk and rotation work, and a lockout of the shared account would stop the live demo as well.
- **Fix / do this:** Route every IDMC REST call through the shared host helper or the laptop session file, and make no new password copies. Name ONE property-app IDMC writer per run and record it on the guard card. Keep a rotation runbook that lists every copy, and keep the credentials map updated.
- **KB:** L-AUTH-043, L-AUTH-054, L-CDI-149, L-METHOD-060

### PD-P1-010 An org judged "unreachable" was reachable: verify before you declare a wall
- **Date:** 2026-07-24
- **Context:** first property-app governance attempt on the second org (<org>)
- **Lesson:** The first status report wrongly judged the second org unreachable, and it was superseded two days later. A native IDMC user of the second org was then created and the local CLAIRE MCP re-pointed to it.
- **Fix / do this:** Before a status calls an org unreachable, re-test it with the correct login host and a native user.
- **KB:** L-AUTH-035

### PD-P1-011 The MDM probe found a 403 role gap, not a 404 missing feature, and MDM goes headless after one UI publish
- **Date:** 2026-07-27
- **Context:** The second org MDM surface probes (mdm_probe*.py)
- **Lesson:** The probes separated a 403 (the role lacks a privilege) from a 404 (no route). The verdict: MDM was entitled but had zero modeled content, and it runs headless after one UI publish. The probe scripts read the login from a file outside the KB and hold no credential literals.
- **Fix / do this:** Classify 403 vs 404 per route before calling something unlicensed. Keep probe credentials in an external file.
- **KB:** L-AUTH-071

### PD-P1-012 MDM host is the pod label plus -mdm with /saas stripped
- **Date:** 2026-08-03
- **Context:** Property MDM design probes on the second org (usw1 / dmp-us)
- **Lesson:** The MDM runtime host is not the login baseApiUrl: add `-mdm` to the pod label and drop the trailing `/saas` (for example `https://usw1-mdm.dmp-us.informaticacloud.com`). Record ingest is `POST <pod>-mdm.<domain>/business-entity/public/api/v1/entity/{be}?sourceSystem=X`.
- **Fix / do this:** Derive the MDM host from the login answer with both mutations; never reuse the `/saas` base.
- **KB:** L-MDM-002, L-MDM-001

### PD-P1-013 MDM writes need the three-header set; a Bearer alone gets 401
- **Date:** 2026-08-03
- **Context:** MDM ingest / read-back design (`ops.py Session`)
- **Lesson:** MDM calls authenticate with `Authorization: Bearer <jwt>` plus `IDS-SESSION-ID` plus `INFA-SESSION-ID`. The Bearer alone returns 401 on writes.
- **Fix / do this:** Send all three headers on every MDM call through one session helper.
- **KB:** L-MDM-003

### PD-P1-014 The JWT dies 30 minutes after grant: re-mint it from the cached IDS session during a bulk run
- **Date:** 2026-08-03
- **Context:** Planned bulk REST ingest of ~98,115 Idaho properties into MDM
- **Lesson:** The JWT expires 30 minutes after it is minted, whatever the activity. At ~10 req/s, 98,115 sequential POSTs take ~2.73 h, so a client that mints once finishes only ~18 %. Re-minting via `POST /identity-service/api/v1/jwt/Token?client_id=cdlg_app` with `IDS-SESSION-ID` takes ~0.5 s and needs no password login; reuse `client_id=cdlg_app` (not `idmc_api`) to keep the same audience.
- **Fix / do this:** Track mint time; re-mint when age > ~25 min or on any 401 and retry once; add 429 backoff and a checkpoint.
- **KB:** L-AUTH-028, L-MDM-033

### PD-P1-015 How to read a status code: 404 sweep with no 405 = no route, 405 = verb exists read-only, 400/415/422 = body wrong
- **Date:** 2026-08-03
- **Context:** Headless vs UI split for Property MDM on the second org
- **Lesson:** A route is only "absent" when every route/host/Content-Type shape 404s and none returns 405. 405 means a read-only verb exists; 400/415/422 means the verb exists and the body is wrong (keep going). With no HEAD/OPTIONS, probe a write verb with an empty POST.
- **Fix / do this:** Sweep the host family and content types before declaring a UI wall; record the verdict per shape.
- **KB:** L-METHOD-026, L-METHOD-027, L-METHOD-029

### PD-P1-016 Bogus-twin every probe: an ACL 403 fires before metadata lookup
- **Date:** 2026-08-03
- **Context:** The second org MDM probes rounds 1-4
- **Lesson:** `GET entity/{be}/{id}` returned 403 for a fabricated entity name as well, so a 403 on a real name proves nothing about existence. The ingest POST 404'd "metadata with GUID 'X' cannot be found" identically for Person, person, c360.person and ZZFAKEENTITY, which proved zero entities were deployed.
- **Fix / do this:** Pair every real path/name with a fabricated twin (ZZFAKEENTITY, ZZFAKESRC); discard a run where the twin flips to success.
- **KB:** L-MDM-009, L-MDM-008, L-METHOD-024

### PD-P1-017 data360 zero-byte 200s on the second org are gateway artifacts
- **Date:** 2026-08-03
- **Context:** CDGC catalog-scan probe on the second org
- **Lesson:** The second org's `data360/*` plane returned 200 for real and bogus paths alike (mounted, not serving). The catalog-scan verb (`POST .../data360/executable/v1/catalogsource/{id}` with `{"capabilityNames":["CATALOG_EXTRACT"]}`, poll `/data360/observable/api/v1/jobs`) was proven only on the other org.
- **Fix / do this:** Never count a zero-byte or twin-identical 200 as a capability; keep the estate scan as a recommendation until a real job id comes back.
- **KB:** L-CDGC-006, L-AUTH-006, L-METHOD-025

### PD-P1-018 The import route looked absent only because of the Content-Type
- **Date:** 2026-08 (probe rounds 4-6)
- **Context:** Clone-authoring path for an MDM business entity on the second org
- **Lesson:** `POST /public/core/v3/import/package` with application/json gave 404 MigrationSvc_025 and was wrongly read as "no import route". With multipart/form-data the same path returned 400 MigrationSvc_030 (package parsed and validated) and application/zip gave 415, so the route exists.
- **Fix / do this:** Vary the Content-Type (multipart first) before declaring an upload route absent; correct the earlier verdict in writing.
- **KB:** L-MDM-014, L-METHOD-028, L-MDM-068 (superseded)

### PD-P1-019 Clone-authoring needs a same-type template: an empty org answers MigrationSvc_041
- **Date:** 2026-08-03
- **Context:** Headless business-entity authoring on the second org
- **Lesson:** Export-retarget-reimport works only when a same-type object (BUSINESS_ENTITY) already exists. The second org held one object (Project "Default"), so export gave 400 MigrationSvc_041, a content verdict. Import also never deploys: the BE still needs a Modeler Publish.
- **Fix / do this:** Run an unfiltered `GET /public/core/v3/objects?limit=50` census first; if no same-type template exists, author the first one in the UI, then clone from it. Do not hand-build a zip.
- **KB:** L-MIG-026, L-MIG-005, L-MDM-013

### PD-P1-020 Entitled is not usable: 83 MDM privileges and zero design objects
- **Date:** 2026-08-03
- **Context:** second org MDM readiness
- **Lesson:** The user had 83 MDM privileges (create/update/delete `.mdm.asset.be`) and 7 MDM/C360 roles, but the org had zero modeled content, so every runtime call 404'd. `POST /v3/objects` = 405.
- **Fix / do this:** Read entitlement from privileges, roles and design-object census together; report "entitled, nothing deployed" separately from "licensed".
- **KB:** L-MDM-011, L-METHOD-033

### PD-P1-021 Profiling and metric-store hosts are derived from the pod
- **Date:** 2026-11-04
- **Context:** Headless profiling helper `idmc.py` for the org 
- **Lesson:** From the login baseApiUrl host `<pod>.dm-us...` the profiling service is `https://<pod>-dqprofile.<domain>.informaticacloud.com/profiling-service/api/v1` and the metric store is `https://<pod>-dqprofile.<domain>.informaticacloud.com/metric-store/api/v1/odata`. The helper sends `icSessionId`, `INFA-SESSION-ID` and `IDS-SESSION-ID` together and caches the session for 20 minutes.
- **Fix / do this:** Build both hosts from the login answer; keep one cached session per org and log in again only when the cache is stale.
- **KB:** L-DQ-020, L-METHOD-007, L-METHOD-003, L-AUTH-024, L-AUTH-003

### PD-P1-022 Metering export dates need full ISO-8601 with Z
- **Date:** 2026-08-03
- **Context:** Planned MDM IPU measurement via metering export
- **Lesson:** The metering export rejects `2026-06-01` with 400 V3API_007 and accepts `2026-06-01T00:00:00Z`; the download is a ZIP (read as bytes). All `/license` paths 404, so the export is the only license read that works.
- **Fix / do this:** Always send full timestamps with Z and read the ZIP as bytes.
- **KB:** L-IPU-021, L-IPU-022

### PD-P1-023 The API Center 13.33 IPU row is a baseline artifact, not an MDM rate
- **Date:** 2026-08-03
- **Context:** second org IPU estimate for MDM
- **Lesson:** The only metering row (`MeterName='API Center'`, `IPURate=13.33`/MILLION_API_CALLS, usage 1.0 for July) belongs to an org where nothing ran. It says nothing about ingest, match, merge, index or tokenize cost; C360 docs contain no IPU numbers. The earlier "~2.6 IPU ingest" figure and the national extrapolation were withdrawn.
- **Fix / do this:** Treat MDM record-processing IPU as UNKNOWN; take metering snapshots before ingest, after ingest, before match and after merge, and diff them to get the first real unit cost. Do not extrapolate nationally.
- **KB:** L-MDM-057

### PD-P1-024 A v3 objects query on a project does not list its folders' contents
- **Date:** 2026-11-03
- **Context:** Inventory of every address-verification asset in the target project, the old project and Default
- **Lesson:** `GET /public/core/v3/objects?q=location=='<project>'` returns the folders, not the assets inside them; the inventory had to list `type=='Folder'` first and then query `location=='<project>/<folder>'` per folder, paging with `limit=200&skip=`.
- **Fix / do this:** Enumerate folders, then query each folder, and page until a page returns fewer than 200 objects.
- **KB:** L-CDI-237 (paging); folder walk new

### PD-P1-025 Find who starts a run from the activity log, not from the schedule list
- **Date:** 2026-11-03
- **Context:** `mt_<p>_av_cert_s1..s4` address-verification tasks
- **Lesson:** The runs carried `runContextType` REST_API_V2, a user in `startedBy` and no `scheduleName`, while the old `sch_<p>_*` schedules existed but were attached to nothing. The mappings' `updateTime` changing every few minutes was the second sign: an external runner rewrote their SQL before each run.
- **Fix / do this:** Read `runContextType`, `startedBy` and `scheduleName` per run (`/api/v2/activity/activityLog?taskId=`) and compare mapping update times before concluding what drives a lane.
- **KB:** L-IPU-061, L-CDI-294

### PD-P1-026 Job-burn counts from the activity log are a window of about 1,000 rows
- **Date:** 2026-11-12
- **Context:** IDMC job-burn audit for the property-app master
- **Lesson:** The audit read `activityLog?rowLimit=1000` and could only report jobs per day inside that window (11-11 = 728 jobs: 572 `<p>_r7_av_verify_mt`, 156 `mt_<p>_av_cert_s1..s4`; 11-10 only from 22:10Z = 225).
- **Fix / do this:** Label activity-log counts with their window, or count jobs where they are started (the runner's own log).
- **KB:** L-CDI-288

### PD-P1-027 Reusing one shared service account widens the blast radius
- **Date:** 2026-10-03
- **Context:** The property-app sample was read through the demo app's IDMC service account
- **Lesson:** That SA can read the demo-app datasets, so a CLAIRE mis-bind on the property-app sample could query demo-app data. Each new connection also holds another copy of the key, and a key rotation on 09-08 had followed a 38 h outage.
- **Fix / do this:** Use a dataset-scoped SA where one can be minted. Otherwise record the blast radius, and list every connection that holds a copy in the rotation runbook.
- **KB:** new

### PD-P1-028 Session files in build trees; chmod 600 does nothing on Windows
- **Date:** 2026-10-04
- **Context:** A build/verify-* folder held a live session file (<redacted>)
- **Lesson:** A raw session file sat in the build tree, kept out of git only by an `*_session*.json` exclude. "mode 600" on Windows has no effect.
- **Fix / do this:** Keep sessions in memory or under ~/.idmc, and scrub build artefacts. Don't rely on chmod on Windows.
- **KB:** new

### PD-P1-029 One v2 login is enough: its JWT session works on every plane
- **Date:** 2026-10-03
- **Context:** idmc-org inventory lane, org <org> 
- **Lesson:** Here the v2 `icSessionId` is a JWT of about 1,680 characters. It was accepted on v2 (`icSessionId`), v3 (`INFA-SESSION-ID`), runtime selections and licence-service (`IDS-SESSION-ID`), `<pod>-dqprofile`, and the `cdlg_app` CDGC JWT mint, so no v3 login was needed. On other pods dqprofile wanted a v3 session.
- **Fix / do this:** Log in once with v2 and change only the header name per plane. Fall back to a v3 login only if dqprofile returns 401 "Exception encountered while processing JWT".
- **KB:** L-AUTH-020, L-AUTH-026, L-DQ-020, L-CDGC-001

### PD-P1-030 Wrong-org trap: the default env file pointed at the retired org
- **Date:** 2026-10-03
- **Context:** earlier sessions
- **Lesson:** The default `idmc.env` holds the retired org on pod dmp-us. The current org's login lives in separate files on the shared host (a separate target file) and in a uiwalk env file. Sessions that used the default file worked in the wrong org.
- **Fix / do this:** Name the org and pod explicitly in every IDMC script. Map each credential file to its org in the credentials map.
- **KB:** new

### PD-P1-031 GET /api/v2/org returns identity and timezone, but no job limit
- **Date:** 2026-10-03
- **Context:** Org identity read
- **Lesson:** `GET <serverUrl>/api/v2/org` returns the id, orgUUID, parentOrgId (<org> is a sub-org), subOrgLimit 0, maxLogRows 1000, restApiSessionLimit 0, timezone America/Los_Angeles, and 2FA off. It shows no job limit.
- **Fix / do this:** Use it for identity and for the org timezone, which defines the cap window. Don't look there for the job cap.
- **KB:** L-AUTH-049

### PD-P1-032 The hidden 10,000 jobs/month cap: what fails when it is hit
- **Date:** 2026-10-03
- **Context:** The property app shares org <org>'s cap with the demo app
- **Lesson:** When the retired org hit the cap on 09-28, every Data Integration start (mapping tasks, taskflows, DQ, read-backs) failed within about 5 s with "You have exceeded your monthly limit of 10,000 jobs". CDC, CAI and the address-verify MCP kept working. The vendor lifted the cap about 8.5 h later. No API shows the cap: the org record, customLimits, EffectiveLicenses and the audit log are all silent about it.
- **Fix / do this:** Treat the cap as about 10,000 shared across the whole org. Ask the vendor for the real value and reset date. Make the circuit breaker match the error text.
- **KB:** L-IPU-041, L-CDI-131

### PD-P1-033 Job arithmetic: what counts toward the cap, and weight a profile run at 1 + 3 + ceil((columns + rules) / 50) jobs until measured
- **Date:** 2026-10-03
- **Context:** budget design and guard weights
- **Lesson:** Each task run is 1 job, and each taskflow run is 1 more. A taskflow bills no compute but still counts, so a 5-task flow every 5 min is 1,440 jobs a day. Address-verify MCP calls are not jobs. A profile run = the run + 3 fixed subtasks (row count, generate mappings, load to metric store) + one s_profiling subtask per 50 columns-plus-rule-outputs; for about 183 columns that is 4 s_profiling subtasks. Whether profile subtasks count against the cap was not measured, so the upper bound is used. Each CDGC capability job = 1 and each preview = 1. An unknown column count is assumed to be 200 (heavy).
- **Fix / do this:** Budget profiles with this formula and keep columns + rules small. Measure once: run a profile on a 1,000-row table and diff the job counters before and after.
- **KB:** L-IPU-042, L-IPU-055, L-DQ-017, L-DQ-098

### PD-P1-034 v2 time fields end in Z but are org-local (UTC-4)
- **Date:** 2026-10-04
- **Context:** a verifier lane; again 11-01 (an auditor misread a start as 19:45Z when it was 23:45Z)
- **Lesson:** v2 `startTime`, `createTime` and `updateTime` show org-local EDT time with a Z suffix, 4 h off.
- **Fix / do this:** Use `startTimeUtc` / `endTimeUtc` (the *UTC fields), or your own clock, for every window decision.
- **KB:** L-AUTH-014, L-AUTH-094, L-CDI-063

### PD-P1-035 Metering exports: a header-only CSV does not mean $0, and detail windows are at most 30 days
- **Date:** 2026-10-03
- **Context:** Metering baseline in a trial sub-org
- **Lesson:** A SUMMARY `POST /saas/public/core/v3/license/metering/ExportMeteringData` for Sep 1 to Oct 3 took about 4.5 min (0 IPU) and returned only a header row. Trial and embedded sub-orgs show 0 even while capabilities run. A PROJECT_FOLDER export over 33 days was refused with 400 LS_298 ("can not be apart 30 days").
- **Fix / do this:** Run the SUMMARY export every cycle and store MeterUsage per meter. Treat a header-only CSV as "unknown", not zero. Split detail exports into windows of 30 days or less.
- **KB:** L-IPU-021, L-IPU-023, L-IPU-024, L-IPU-036

### PD-P1-036 IPU rates, and the property app's cost if it were billed
- **Date:** 2026-10-03
- **Context:** Cost estimate
- **Lesson:** CPDS v39.1 tier-1 rates:
  - DI: 0.16 IPU per compute-hour
  - DQ/Profiling: 0.38
  - DGC Scanner: 0.32
  - Catalog: 0.83 per 100K daily assets (columns count as assets)
  - CLAIRE GPT: 50 per 1,000 queries
  - CAI: 1.453 per 1K calls

  Development, connection tests, taskflow orchestration and metering exports are free. The property app sample work came to about 25-30 IPU/month.
- **Fix / do this:** Keep catalog scope to the sample, because asset count drives the daily meter. Cap CLAIRE GPT at 20 queries/day.
- **KB:** L-IPU-003, L-MCP-116, L-CDGC-103

### PD-P1-037 Standing guardrails for the shared org
- **Date:** 2026-09-30
- **Context:** Shared org rules the property-app plan follows
- **Lesson:** Never add MCP tool connections on <org>. Ticking all RE services overloads the shared VM. The DAM Agent/Proxy restart loop is known and harmless. The central IDMC log card had 0 property-app entries.
- **Fix / do this:** Limit changes to the app RE and <APP>_* / DQ_<P>_* / av_ objects. Post each IDMC action to the central log.
- **KB:** L-MCP-081 (MCP part); rest new

### PD-P1-038 Narrowing a dataset ACL doesn't stop project-level readers; a row access policy does
- **Date:** 2026-10-04
- **Context:** Loading the masked sample into a shared project
- **Lesson:** The project IAM policy gave roles/bigquery.dataViewer to several other service accounts. Narrowing the dataset ACL with a datasets.patch (If-Match etag) did not remove them. `CREATE ROW ACCESS POLICY ... GRANT TO (<sa>, <owner>) FILTER USING (TRUE)` made every other principal see 0 rows, and the DDL billed 0 bytes.
- **Fix / do this:** Check the project IAM policy, not only the dataset ACL. Add a TRUE-filter row access policy for the allowed principals. Undo with DROP ALL ROW ACCESS POLICIES.
- **KB:** new

### PD-P1-039 Secret masks that expect key=value miss one-value-per-line files
- **Date:** 2026-10-04
- **Context:** Read-only probe of a shared-host IDMC target credential file
- **Lesson:** The mask assumed key=value lines, but the file stored one value per line, so the IDMC password reached a local transcript. Rotating it means updating every stored copy in the same step. Otherwise the next scheduled login gets a 4xx, writes the login block, and stops every IDMC user on the host, including the demo app's health job.
- **Fix / do this:** Inspect credential files of unknown format with stat or wc only. Rotate with all copies at once, then do one confirmed login.
- **KB:** L-METHOD-087, L-AUTH-043

### PD-P1-040 On a Trial org the job cap and AV spend are unreadable; budget before scaling
- **Date:** 2026-11-01
- **Context:** The org (Trial edition)
- **Lesson:** The licence API returned 7 TRIAL licences, `customLimits: []` and 3 DI meters (max 10,000, used 0), with no AV or DQ meter. `EffectiveLicenses` returned 404 on this pod. Two schedules alone launched about 350 of the org's 563 jobs in 24 h. A full AV sweep of about 135M rows would cost an unknown amount of IPU.
- **Fix / do this:** Run `ExportMeteringData` before and after one wave, keep a job-count breaker, and get both spend approvals before any full AV sweep.
- **KB:** L-IPU-041, L-IPU-043, L-IPU-062, L-IPU-056

### PD-P1-041 Operational Insights GraphQL needs IDS-SESSION-ID, not Bearer
- **Date:** 2026-11-01
- **Context:** Run-ledger and monitoring probe
- **Lesson:** `GET <pod>-cai.../active-bpel/opsanalytics-das/metrics?query={processJobReport...}` returned 200 with `IDS-SESSION-ID`. The documented `Authorization: Bearer <session>` returned 401. `restadmin/scheduler/schedules` returned 401 "not authorized from context".
- **Fix / do this:** Send IDS-SESSION-ID for OI exports.
- **KB:** L-CAI-159

### PD-P1-042 Reach the GCP DB and agent VMs through IAP with a pinned account and base64 commands in argv
- **Date:** 2026-10-29 / 2026-11-03
- **Context:** chq.sh (both folders); the database VM and the production DB VM
- **Lesson:** Access is `gcloud compute ssh <vm> --account=<service account> --project <project> --zone us-central1-a --tunnel-through-iap`. On Windows, stdin piped into it breaks, so the helpers base64-encode the shell command or SQL and pass `echo <b64> | base64 -d | bash` as `--command` (for ClickHouse: `echo <b64> | base64 -d | sudo <query limiter> -- --readonly=1 --multiquery --format=TSVWithNames`), filtering out gcloud's advisory and banner lines. No stdin piping or heredocs. The shared query limiter caps memory and threads, and its default read cap (about 1.86 GiB) failed a GROUP BY over market_indexes with code 241.
- **Fix / do this:** Pin the account on every call, ship commands as base64 in argv, and never pipe stdin. Use the wrapper with a timeout, and `--readonly=2` when the query carries SETTINGS. For heavier reads, ask the limiter for `--mem` and `--threads`.
- **KB:** L-ENV-001, L-ENV-002, L-ENV-007, L-ENV-009, L-ENV-112

### PD-P1-043 Probe permissions with the job's own method and read writes back
- **Date:** 2026-10-13
- **Context:** valuation-backtest.sh
- **Lesson:** After the 10-08 credential split, the wrapper's writes and its read-back were refused with ACCESS_DENIED 497 (HTTP 500) for 10 runs, while the job exited 0. In ClickHouse HTTP, GET is read-only, so a GET probe proves nothing about writes. The default 30 s client timeout also killed the city query.
- **Fix / do this:** Give the job's client the protected job credential, only in a throwaway container's env-file. Count data as persisted only after reading back rows and the model hash. Probe with POST, and set a 300 s timeout.
- **KB:** new (related L-METHOD-047, L-ENV-036)

### PD-P1-044 An approved disk resize was blocked by the identity's permissions
- **Date:** 2026-10-29
- **Context:** step 00a: growing ClickHouse disk <data disk> 600 -> 800 GB (approved spend) and a dedicated agent VM
- **Lesson:** No available credential had `compute.disks.resize` or `compute.instances.create`, and the human logins had expired in a non-interactive session, so the approved change could not run headless.
- **Fix / do this:** Test the identity's permission before promising an infrastructure change. Hand the owner one interactive `gcloud auth login`, then run `gcloud compute disks resize ... --size=800GB` online and `resize2fs`. Keep at least 40 GiB unreserved.
- **KB:** L-ENV-119, L-ENV-070

## Connections & agents

### PD-P1-045 Size the agent host before you enable services: 23 engines on a 7.8 GiB host OOM-killed ClickHouse
- **Date:** 2026-07-26
- **Context:** The second org Secure Agent on the data host
- **Lesson:** Connection tests first failed with APP_105060 because only OpsInsightsDataCollector was deployed. Enabling services in the UI deployed 23 engines, which OOM-killed ClickHouse twice and pushed disk use from 79% to 95-96%. The agent was trimmed back to a governance set.
- **Fix / do this:** Size the host for the engines you select. On a shared DB host, enable only the needed services.
- **KB:** L-AGENT-052, L-CONN-018

### PD-P1-046 The Secure Agent systemd unit needed WorkingDirectory and RemainAfterExit
- **Date:** 2026-07-26
- **Context:** The second org agent install as user `infa` on the host
- **Lesson:** The agent unit had to be fixed with WorkingDirectory and RemainAfterExit before it ran reliably. The install itself needed the cloud-firewall :22 allowlist opened, and the corporate egress IP rotated mid-session.
- **Fix / do this:** Use a systemd unit with WorkingDirectory and RemainAfterExit. Expect egress IP rotation when you allowlist a laptop.
- **KB:** L-AGENT-009, L-ENV-011

### PD-P1-047 Deleting a host silently de-registers the Secure Agent on it
- **Date:** 2026-09-07
- **Context:** platform teardown of the data host
- **Lesson:** The teardown inventory found the second org agent still running on the host (Metadata_Platform_Service, about 6 JVMs) next to an unrelated runtime. Deleting the host would have de-registered the agent with no warning, so the deletion became an owner decision.
- **Fix / do this:** Inventory agent processes before any VM teardown and record the de-registration as an explicit decision.
- **KB:** new

### PD-P1-048 Profiling on the prod DB host saturated it and knocked out DIS (PROFILE_SVC_00014): move IDMC compute off the database VM
- **Date:** 2026-10-03
- **Context:** The agent on the prod ClickHouse/Postgres VM (4 vCPU / 31 GB); <profile_ID> run 1
- **Lesson:** The 17:40Z profile run (one 181-column profile, two DTM sessions of 33-36 threads each) took the host to load 63 and thrashed the agent's 4 GB / 1 vCPU slice. The slice was cut to 0.5 vCPU, and DIS, CIC, Connector and Mass Ingestion sat in ERROR from 18:14Z to 20:43Z; nobody noticed for 2.5 h. The next profile create failed with PROFILE_SVC_00014 "No running service found of type Data_Integration_Server", and one agent restart brought everything back to RUNNING. Decision: no property-app IDMC compute on the prod DB host from then on; retire the agent and have the shared agent read a masked copy elsewhere.
- **Fix / do this:** Never run profiling agents on a production DB host; stage a masked copy on another host. On PROFILE_SVC_00014, read the agent's engines and restart once. Alert on services in ERROR, on slice pressure and on FAILED profiles.
- **KB:** L-DQ-098, L-AGENT-052, L-AGENT-076

### PD-P1-049 Two DTMs by default thrash a small agent: set maxDTMProcesses=1, cap profiled columns, or serialize in a controller
- **Date:** 2026-10-03
- **Context:** prod-DB-host agent profile of 48,890 rows x 181 columns (<profile_ID>, 17:40Z); hardening the prod DB host
- **Lesson:** DIS runs 2 DTMs at once by default. The profile ran 4 s_profiling subtasks on 2 concurrent pmdtm processes (33-36 threads each), pushed infaagent.slice to 4,140 MB of its 4,096 MB cap, ran for more than 58 min and put services in ERROR. Two DTMs plus the DIS JVM in a 4 GB slice risk an OOM (pmdtm exit 137), and the vendor's BigQuery "GC overhead" fix (-Xmx4096m) does not fit such a slice; the shared agent runs -Xmx2048m with maxDTMProcesses=4 set cloud-side. Host load stayed around 56 even after the agent was CPU-capped, because ClickHouse INSERT/CTAS jobs and root Python jobs were also loading the host. The spec set DIS Tomcat `maxDTMProcesses=1` on the dedicated agent (UI path Administrator > Runtime Environments > agent > Edit > DIS, or the agent.do Custom Configuration form; it restarts DIS). On the shared agent the concurrency was left alone, because the demo app relies on it, and the property app runs were serialized in a controller instead.
- **Fix / do this:** On a dedicated small agent, set maxDTMProcesses=1 off-peak, keep DTM heap at or below -Xmx1024m and 512 MB per mapping, or cap the profiled columns at ≤50 (one subtask). On a shared agent, serialize runs with a lock in your own controller. Run one profile at a time, and budget the warehouse's own load separately.
- **KB:** L-AGENT-056, L-AGENT-088, L-AGENT-099, L-DQ-098, L-DQ-103

### PD-P1-050 Never fix a missing engine with a selections PUT on a shared agent; gate only the engines you use
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** shared agent (live demo-app host), gates G2 / G2b; "Deselect Mass Ingestion" on the prod DB host (DIS 77.0.5 there versus 77.0.11 on the shared agent)
- **Lesson:** Every runtime-environment selections PUT also rolls DIS, Mass Ingestion and Connector_Service to their newest builds, and jobs queue for about 5 minutes meanwhile. An RE change on the prod DB host redeployed about 15 JVMs in the middle of an outage, and restoring the selections afterwards does not restore the engine versions. On the shared agent, Data_Access_Management_Agent/_Proxy loop in RESTARTING and FileIntegrationService sits in ERROR; both are known and harmless, so a gate that requires every engine RUNNING can never pass, and a session chasing green would restart the live demo agent. G2b therefore only reads state: the needed engines (Data_Integration_Server, Connector_Service, Metadata_Foundation_Agent, Metadata_Platform_Service, and IDMC_Data_Gateway_Service where used) must be RUNNING, plus readyToRun and memory headroom, with DAM and FIS listed as known exceptions.
- **Fix / do this:** Read `/api/v2/agent/details/<id>` agentEngines and keep the gate read-only. If something is missing, ask the agent's owner in one comment; never PUT selections yourself. If a selections change is unavoidable, make it with the agent stopped or in a quiet window, and write the rollback as "selections restored; engine versions stay rolled forward". When retiring an agent, prefer `systemctl disable --now infaagent`.
- **KB:** L-AGENT-028, L-AGENT-040, L-AGENT-042, L-AGENT-048 (partial)

### PD-P1-051 Check a shared agent that hosts a live demo before a guest scan or profile
- **Date:** 2026-10-04
- **Context:** shared agent on the shared host, which also runs the live demo (MemoryHigh 12G / MemoryMax 14G); decision 11
- **Lesson:** Extra scan or profile load can slow the demo or use up its memory. Before any property-app scan or profile on the demo-app host, all of these must hold: free memory ≥ 8 GB, load1 < 4, no demo-app run in progress (activityMonitor empty), not within 20 min of :10 (the hourly evidence workflow job), and outside the 06:20/06:55/07:10/07:50Z demo-app jobs. Only one scan runs at a time.
- **Fix / do this:** Encode the host owner's schedule and capacity as pre-run gates in the guest's runner. Never PUT selections; if the Metadata services are off, ask the demo-app lane in one comment.
- **KB:** L-CDGC-045

### PD-P1-052 Retire a time-windowed agent by stopping it and emptying its window, not by disabling the enforcer timer
- **Date:** 2026-10-04
- **Context:** prod-DB-host agent retire (C6): the agent ran only 23:00-02:00Z under `infaagent-window.timer`, with an override in `/etc/<agent>/infaagent-window.conf`
- **Lesson:** The timer's 02:00Z stop was verified: 91 s, slice tasks 231 → 0, memory 3.34 → 0.16 GB. Disabling the enforcer timer itself fires the WindowEnforcerStale alert, and a first draft that said "disable the timer" was caught by a verifier. `systemctl is-active` says "inactive" even for a unit that doesn't exist, so it proves nothing on its own.
- **Fix / do this:**
  1. Back up `/etc/<agent>/infaagent-window.conf`.
  2. Set WINDOW_START_HOUR=0 and WINDOW_END_HOUR=0 (the window's retire switch).
  3. Run `systemctl disable --now infaagent`, then `systemctl start infaagent-window.service`. Leave the enforcer timer running.
  4. Verify: no pmdtm processes, window metric 0, and IDMC showing the agent active=false. Record the rollback.
- **KB:** L-AGENT-120 (related); new

### PD-P1-053 A runtime environment without Metadata services or a Data Gateway cannot catalog or run "Query the data"
- **Date:** 2026-10-03
- **Context:** The app RE (Platform + DI + DQ only) vs RE <shared RE>
- **Lesson:** The app RE had no Metadata services and no Data Gateway. Catalog scans and CLAIRE GPT "Query the data" therefore had to run on the shared RE, which has Metadata services, a Data Gateway, -Xmx2048m and maxDTMProcesses=4 cloud-side.
- **Fix / do this:** Check the RE's service set before you choose where a catalog source or a gateway query runs.
- **KB:** L-AGENT-097, L-CDGC-045

### PD-P1-054 A connection cannot be made connectivity-only: delete PII-capable connections after a v3 export, and expect masked passwords on restore
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** <APP>_CH_BRONZE, _CH_GOV, _PG_MCP, _PG_CRE_APP among the 11 <APP>_* connections left live
- **Lesson:** IDMC has no connectivity-only state for a connection. Any profile, preview or CLAIRE action on a live connection runs on the agent and uploads value frequencies, so the PII path stays open. Four connections could read raw owner data or personal stores (MCP audit logs, app DB). They were exported over v3 (job <id>) and then deleted on 10-04 07:15-07:21Z. The export package masks passwords, so a restore must re-supply them.
- **Fix / do this:** Delete the connections you don't need, or unbind them from every RE, after a v3 export backup, and note that its secrets are masked. Revoke the IDMC DB user's SELECT on the bronze and gov schemas.
- **KB:** L-CONN-007

### PD-P1-055 Trimming a DB user's grants breaks the INVOKER views that read the revoked databases
- **Date:** 2026-10-04
- **Context:** ClickHouse user `idmc` after losing <bronze_db> / <gov_db>
- **Lesson:** After the grant trim, 6 SQL SECURITY INVOKER views fail for `idmc` with error 497 (access denied), for example `<idmc_db>.dq_repair_queue` and `<silver_db>.listing_metric`. No IDMC object may read them through those connections.
- **Fix / do this:** Before revoking grants, list the views that depend on the revoked DBs and document which connections can no longer read them.
- **KB:** new

### PD-P1-056 Harden the DB side of an IDMC connection: least-privilege users, no admin rights, no ::/0
- **Date:** 2026-10-04
- **Context:** C6 hardening of the prod DB host ClickHouse users (`idmc`, `<app user>`)
- **Lesson:** ClickHouse user `idmc` held global CREATE/ALTER/DROP USER and ROLE, NAMED COLLECTION ADMIN and SET DEFINER, plus SELECT on bronze and gov (raw owner data). User `<app user>` accepted ::/0 with displaySecretsInShowAndSelect. Several connections could read personal stores, and a _T test connection was left over. The plan revoked idmc's bronze/gov SELECT and its unused global admin rights and restricted `<app user>` from ::/0, all in one batched OK with the rollback recorded.
- **Fix / do this:** Give each IDMC connection a DB user that can read only what IDMC may see. Unbind or delete the PII-capable connections and the leftover, REVOKE the global rights, and restrict hosts to the VPC and the Docker bridge. Batch all of it into one prod-change approval.
- **KB:** L-CONN-012

### PD-P1-057 Run IDMC against a masked copy in a small isolated container on an off-prod agent host, with one least-privilege role and connection per purpose
- **Date:** 2026-10-04
- **Context:** plan v3 decision 3; <APP>_PG_SAMPLE and <APP>_PG_SAMPLE_PARITY on RE <shared RE>; roles <idmc_ro> and <parity_rw>
- **Lesson:** A connection whose host is localhost on the prod DB host pins all job compute to that host, and a second agent on another VM was rejected (only 9 GB free; another service peaks at 9.5 GB). So IDMC reads only the shared host's PII-masked container `<sample-pg>` (localhost:5439, 1 GB / 1 CPU) through the shared RE; each refresh copies about 45 MB (about $0.01). The catalog/profiling connection uses a SELECT-only role (<idmc_ro>, with INSERT, CREATE and TEMP verified as denied). The CDI parity probe writes through a separate connection, <APP>_PG_SAMPLE_PARITY, whose role `<parity_rw>` may only INSERT and SELECT on `public.dq_parity`. On the shared host, root disk was at 92% with swap in use, so disk and memory are checked before each load.
- **Fix / do this:** Put the masked sample in a small capped container on the agent host, and check its disk and swap first. Use one role and one connection per purpose (reader versus result writer), and set default privileges so tables created later get SELECT automatically. Grant `GRANT TEMPORARY ON DATABASE` only if CDGC or profiling ever needs temp tables.
- **KB:** new (later related: L-DQ-158)

### PD-P1-058 A connection test is the free health check, but it does not prove metadata import: gate on the needed test AND the absence of forbidden connections
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** readiness gate G3; acceptance item 1; re-test of <APP>_PG_SAMPLE on 10-04
- **Lesson:** All <APP>_* connections (ClickHouse JDBC V2 with socket_timeout=3600000, and Postgres) passed `GET /api/v2/connection/test/<id>` in 1.3-22 s, at 0 jobs and 0 IPU (success in the body), yet the ClickHouse ones still failed metadata import. A real agent login shows on the database as pg_stat_database.sessions rising (92 to 94). G3 lists `/api/v2/connection`, tests <APP>_PG_SAMPLE, and goes amber while any PII-capable connection name still exists.
- **Fix / do this:** Gate on a successful test of the needed connection AND the absence of forbidden ones. Pair the test with a database-side proof and a separate metadata or preview check.
- **KB:** L-CONN-014, L-CONN-015

### PD-P1-059 A JDBC V2 ClickHouse connection exposes only its own database: one connection per database, and REST cannot copy the password
- **Date:** 2026-11-04
- **Context:** profiling every ClickHouse table: the legacy production server (920 tables in 27 databases pending) plus `<serve_db>` on the new server
- **Lesson:** A JDBC V2 profile resolves `<schema>/<table>` through its connection, and the connection sees only its own schema; any other database fails with "Please provide correct path for the Object. [<db>] was not found". 920 legacy tables in 27 databases (<gov_db> 651, <graph_db> 57, ...) stayed pending for that reason. REST never returns the stored password, so a headless session cannot clone the connection, and the inventory marks those tables "pending: no IDMC connection has database X as its schema".
- **Fix / do this:** Create one connection per database at provisioning time. If that was missed, copy the read-only connection (`<APP>_SOURCE_ISOLATED`) in Administrator and change its Schema to each database (the copy keeps the password), or give the session the reader password through a file. Then register the connection in the profiler's `CONNS` map and run create/run.
- **KB:** L-DQ-134, L-CONN-136

### PD-P1-060 A hyphenated systemd slice nested the new agent under the old 4 GB slice and caused an IO storm on the prod DB host
- **Date:** 2026-10-29
- **Context:** new Secure Agent on the prod DB host (production ClickHouse host) for gold DQ; it took over registration <id>, the app RE
- **Lesson:** Because of the hyphen, the new agent's slice nested under the old `infaagent.slice` (MemoryMax 4 GB). Its page cache starved and its JVMs kept re-reading `/data` until the disk ran out of IOPS: load 125 from 07:30 to 07:47 UTC. The same cause very likely retired the agent on 10-05.
- **Fix / do this:** Use a top-level slice (`infagolddq.slice`: 10/12 GB memory, 2 CPU, 40 MB/s and 600/400 IOPS) and verify the limits in the cgroup. Add a guard that kills the agent when IO pressure or load climbs. Keep the unit disabled at boot until it is proven, and prefer a dedicated agent VM.
- **KB:** L-AGENT-110, L-AGENT-119, L-ENV-119

### PD-P1-061 DTM heap: without -Xmx4096m the JDBC reader died with GC overhead and the session hung
- **Date:** 2026-11-01
- **Context:** Property MDM mappings on the docker DQ agent (runtime <dq-re>)
- **Lesson:** The JDBC V2 reader failed with `GC overhead limit exceeded` and the session hung until the DTM heap was raised via `pmrdtm.cfg` `JVMOption1=-Xmx4096m` in DIS v78.0.7.1. A host edit lives in one DIS version directory, so a DIS version roll drops it.
- **Fix / do this:** Set JVMOption1 cloud-side (agent Custom Configuration) to make it permanent; keep a `.bak` of any host edit.
- **KB:** L-AGENT-056, L-AGENT-088, L-AGENT-112

### PD-P1-062 Address-verification throughput: ~550-600 addresses/s per DTM, two DTMs per DQ agent
- **Date:** 2026-11-01
- **Context:** National property address verification with the on-agent Verifier
- **Lesson:** One DTM verified ~550-600 addresses/s, so 63.7M properties is ~32 h on one stream; the DQ agent allows 2 concurrent DTMs. MA (2.5M) took one run.
- **Fix / do this:** Size verification runs by this rate, shard by hash (`p_shard`) across the 2 DTMs, and budget days, not hours, for national scope.
- **KB:** new

### PD-P1-063 Read production ClickHouse over the network from a separate agent with a read-only user
- **Date:** 2026-11-04
- **Context:** Legacy production ClickHouse profiling (the website's database)
- **Lesson:** Legacy profiles ran on the new server's Secure Agent and read the legacy server over the network through a read-only connection, so no profiling engine ran on the website host. After the 10-29 slice incident this was the safe shape.
- **Fix / do this:** Put the profiling runtime on a different host from the production DB; use a read-only DB user; cap every query in the SQL override.
- **KB:** L-DQ-158

### PD-P1-064 ClickHouse JDBC driver: Administrator upload of the -shaded JAR, never a file copy
- **Date:** 2026-08-03
- **Context:** Native ClickHouse connection on the second org agent (deferred native path)
- **Lesson:** Copying the driver into 4 agent locations never made it load. The `-all` JAR omits `com.clickhouse.client.*` (NoClassDefFoundError); a 554-byte HTML 404 saved as `.jar` is a common trap.
- **Fix / do this:** Use the Administrator upload-JAR flow with the `-shaded` JAR; before upload check `unzip -l <jar> | grep -c client/` > 0 and the byte size.
- **KB:** L-CONN-054
- **Status:** superseded by PD-P1-077 (current KB: a driver file copy plus an agent restart does load the driver; the upload-JAR-only claim is withdrawn)

### PD-P1-065 JDBC V2 plugin declares no username/password, and connParams.user is the wrong key
- **Date:** 2026-08-03
- **Context:** Native ClickHouse JDBC V2 connection create
- **Lesson:** The JDBCV2 plugin XML declares HASUSERNAME=NO HASUSERPASSWORD=NO, so IDMC sends no password and ClickHouse authenticates as its default account. The CLI also sent `connParams.user` where the manifest wants `username`.
- **Fix / do this:** Put credentials in the connection string or the manifest's keys, and fix the server side so the handshake resolves to a real read-only account (a gated DB-config change).
- **KB:** new

### PD-P1-066 A connection create returning 200 proves nothing; only the connection test does
- **Date:** 2026-08-03
- **Context:** Native connections on the second org (`POST /api/v2/connection`, type `TOOLKIT_CCI`, connector in `instanceName`)
- **Lesson:** The definition saves with 200 even with no engine, adapter or driver. `GET /api/v2/connection/test/{id}` (0 IPU) names the missing gate: 403 APP_105060 (engine), "Unable to fetch Connector attributes" (adapter), "Unable to load driver" (driver). Under memory pressure the named engine rotates, which is progress, not a new wall. Updates use `POST /connection/{id}` (no PUT). DBs bind to the private address `<ip>`, never localhost.
- **Fix / do this:** Always run the test after create; treat the test PASS as the only proof.
- **KB:** L-CONN-014

### PD-P1-067 GET /api/v2/connector is the global catalog, not what the agent has installed
- **Date:** 2026-08-03
- **Context:** Verifying JDBCV2 / MongoDB adapters on the agent
- **Lesson:** The endpoint lists 342 connector types for the product, not the adapters deployed on the agent.
- **Fix / do this:** Verify on the host: `ls <agent>/apps/Connector_Service/<ver>/connectors/cci/plugins/`.
- **KB:** L-CONN-021

### PD-P1-068 REST push from the data host sidesteps every connector blocker for MDM ingest
- **Date:** 2026-08-03
- **Context:** Pilot ingest path for Property MDM
- **Lesson:** With the ClickHouse driver not loading and Postgres/Mongo adapters missing, pushing record bodies from the host straight to the MDM ingest REST API needed no engine, adapter or driver.
- **Fix / do this:** For a pilot, extract on the data host and POST to the MDM API; leave the native connector path as a deferred track.
- **KB:** new

### PD-P1-069 A replacement agent took over the old registration
- **Date:** 2026-10-29
- **Context:** Secure Agent on the prod DB host (the app RE)
- **Lesson:** The new agent install took over the old registration `<id>`, so tasks bound to the runtime kept working. The retired install was left on `/data` (39 GB) until a set date (after 11-05) to reclaim.
- **Fix / do this:** Reuse the runtime registration when replacing an agent; schedule removal of the old install after a stable period.
- **KB:** new

### PD-P1-070 ClickHouse JDBC V2 connection body that works headless
- **Date:** 2026-10-31
- **Context:** `<APP>_DQ_CLICKHOUSE` and `<APP>_WORK_DQ_PROFILE` on runtime `<dq-re>`
- **Lesson:** Both are `type` TOOLKIT_CCI, `instanceName` JDBCV2, connector `com.informatica.adapter.jdbc_v2`, driver `com.clickhouse.jdbc.ClickHouseDriver`, `connParams` with `username`/`password`, `schemaname`, `quoteChar` backtick, `supportmixedcaseidentifier=true`, `autocommit=true` and a connection string `jdbc:clickhouse:https://<host>:<port>/<db>?ssl=true&sslmode=STRICT&sslrootcert=<agent cert path>&http_connection_provider=HTTP_URL_CONNECTION&socket_timeout=3600000`.
- **Fix / do this:** Clone this body for a new ClickHouse database; keep TLS verification strict with a pinned cert; set the long socket timeout for multi-hour reads.
- **KB:** L-CONN-054, L-CONN-001

### PD-P1-071 Give address verification its own runtime environment
- **Date:** 2026-11-03
- **Context:** Runtime environment `<dq-re>` (a Secure Agent in a Docker container on a GCP VM)
- **Lesson:** The proven setup runs a dedicated Secure Agent and runtime environment used only for DQ and address work, so address runs do not compete with ingest lanes for DTMs and memory.
- **Fix / do this:** In a new org create a separate runtime environment for address verification and DQ, next to the database (same VM or VPC).
- **KB:** new

### PD-P1-072 Put an nginx buffer between the agent and ClickHouse; sizes take only k/m units
- **Date:** 2026-11-01
- **Context:** `<dq-http-buffer>` container in front of ClickHouse HTTP
- **Lesson:** Without a buffering proxy, large reads failed with `Premature EOF`. A `proxy_max_temp_file_size` larger than the result fixed it, but nginx accepts only k/m suffixes: `200g` crash-loops the proxy (write `204800m`). Runs died after 1.9M and 9.9M rows before the temp limit was raised from 512 MB.
- **Fix / do this:** Front ClickHouse with nginx `proxy_buffering on` plus a big temp-file limit on a big disk, written in m units.
- **KB:** L-CDI-267

### PD-P1-073 Parallel lanes without per-query memory caps kill each other's long reads
- **Date:** 2026-11-01
- **Context:** 11 `mt_<p>_ingest_capture` lanes plus the MDM national match on one ClickHouse
- **Lesson:** At 07:53Z ClickHouse hit its 64 GiB limit: a capture lane failed MEMORY_LIMIT_EXCEEDED and the national match died with `Premature EOF` after 9.7M rows (9,869,816 read, 9,702,576 written). The MDM queries then capped themselves (max_memory_usage 8-10 GB, external sort and group-by spill at 2 GB, grace-hash joins) and ran one match plus one golden DTM at a time.
- **Fix / do this:** Put `SETTINGS max_memory_usage`, `max_threads` and spill thresholds in every lane's source query, and limit how many heavy lanes run at once.
- **KB:** L-CDI-292

### PD-P1-074 A database restart mid-run shows as an SSL error, then a failed connection test
- **Date:** 2026-11-01
- **Context:** National MDM backfill against ClickHouse on the new database VM
- **Lesson:** While ClickHouse went down, a running match failed with `Non-retryable SQL error: SSL peer shut down incorrectly (SQLState: 07000, ErrorCode: 1002)` and the golden run with `[FATAL] SSL peer shut down incorrectly`. The immediate retries failed within a second with `The test connection for <APP>_DQ_CLICKHOUSE failed ... Connection refused`, so both groups were marked failed twice.
- **Fix / do this:** On SSL-peer or connection-refused errors, wait until the database answers a health check before retrying; do not count these as logic failures.
- **KB:** new

### PD-P1-075 Establish host, engine, adapter and driver in order; read engines from agent details
- **Date:** 2026-08-01
- **Context:** First IDMC connections to the property-app data host (ClickHouse, Postgres, MongoDB)
- **Lesson:** The four layers fail with four different errors that all look like a broken connection. The ground truth for engines is `GET /api/v2/agent/details/{agentId}` → `agentEngines[].appname`, not `products[]`; for adapters it is the agent's own registry `<agent>/apps/Connector_Service/<ver>/connectors/...`, not the 342-row global `GET /api/v2/connector` list. Enabling engines does not enable connectors.
- **Fix / do this:** Check host:port reachability from the agent box, then engines, then adapter jars on disk, then the driver.
- **KB:** L-AGENT-034

### PD-P1-076 Create connections as TOOLKIT_CCI; a connector name in `type` gives 403 APP_10519
- **Date:** 2026-08-01
- **Context:** The property app connection creation over REST
- **Lesson:** `POST /api/v2/connection` needs `type: TOOLKIT_CCI`, the connector in `instanceName` and fields in `connParams`; `type: "PostgreSQL"` returns `403 APP_10519`, which is a wrong type string, not an entitlement wall.
- **Fix / do this:** Always use TOOLKIT_CCI plus instanceName; take field names from the connector manifest (`username`, not `user`).
- **KB:** L-CONN-001

### PD-P1-077 Read the sub-message of a connection-test failure to know which wall it is
- **Date:** 2026-08-01
- **Context:** Connection tests for `POSTGRES-app`, `CLICKHOUSE-app`, `MONGODB-app`
- **Lesson:** `APP_105060` wraps several walls: "Unable to fetch Connector attributes ... com.informatica.adapter.X" = adapter not deployed; "Unable to load driver"/bad JDBC string = driver; "No running service" = engine not on the agent. In August the ClickHouse adapter jars were present and the shaded driver staged but not registered, while Postgres and Mongo adapters were absent.
- **Fix / do this:** Classify by message text with `GET /api/v2/connection/test/{id}` (free, no scan). Current KB: a driver file copy plus a restart loads it; the upload-JAR-only claim is superseded.
- **KB:** L-CONN-018, L-CONN-014, L-CONN-051 (L-CONN-077, L-AGENT-080 superseded)
- **Status:** overturns PD-P1-064 (the upload-JAR-only rule for the ClickHouse driver)

### PD-P1-078 Session-log warnings that show on every healthy JDBC V2 run
- **Date:** 2026-11-01
- **Context:** Session logs of `mt_<p>_mdm_20_match_merge`, `mt_<p>_event_gap_06`, `mt_<p>_property_resume_10`
- **Lesson:** Runs that wrote 1.8M-6.9M rows with 0 rejects all carried: "The Error Log DB Connection value should have Relational: as the prefix", "Invalid table attribute: Exec SQL", "Invalid value false for attribute Reject Truncated/Overflow Rows / Truncate Target / Apply Custom Schema", "Invalid value None for attribute Pushdown Optimization Context", "The value entered is not a valid integer", and `VAR_27062 Cannot find section for worklet ... in parameter file`.
- **Fix / do this:** Treat these as noise when diagnosing a failure; look at the load summary, thread statistics and FATAL lines instead.
- **KB:** new

### PD-P1-079 Export packages carry connection passwords
- **Date:** 2026-11-03
- **Context:** v3 export of the AV mappings with dependencies
- **Lesson:** `includeDependencies: true` pulled the two ClickHouse connections into the package, and each `connection.json` has a `password` field in `connParams`.
- **Fix / do this:** Treat every export zip as a secret; redact `connParams.password` before sharing or committing.
- **KB:** L-MIG-018, L-CONN-064

### PD-P1-080 On a shared agent, bound profile fan-out per profile, not per agent
- **Date:** 2026-10-03
- **Context:** Moving the property app profiling onto the demo-app shared agent (maxDTMProcesses=4, -Xmx2048m per DTM)
- **Lesson:** "One property-app profile at a time" is not one DTM, because s_profiling subtasks run in parallel up to maxDTMProcesses. A 183-column profile could take about 8 GB of DTM heap. The demo app depends on the agent-wide setting, so lowering it is not an option.
- **Fix / do this:** Limit fan-out per profile: ≤50 profiled columns, or `runtimeOptions.profileAdvProps.maxColumnsPerMapping`. Before each run, check that memory.events high and oom_kill are not rising, that swap is not growing, that the CDC jobs are healthy, and that activityMonitor is empty.
- **KB:** L-DQ-103, L-DQ-098

### PD-P1-081 maxDTMProcesses has no REST verb, and agent.do changes engine config only
- **Date:** 2026-10-03
- **Context:** C6 / changes to the prod-DB-host agent
- **Lesson:** maxDTMProcesses is set through the legacy agent.do form, which needs UI session cookies and a CSRF token. That is a separate UI login and counts against the lockout budget. The change restarts DIS and can roll it to a newer build. agent.do cannot unbind connections from a runtime environment.
- **Fix / do this:** Mark agent.do steps as workarounds, not REST, and count their UI login in the lockout budget. Unbind connections through the connection or RE APIs.
- **KB:** L-AGENT-088, L-AGENT-099

### PD-P1-082 Never select all services, or the Metadata services, on a small or shared agent
- **Date:** 2026-10-03
- **Context:** shared RE <id> with all 17 services selected
- **Lesson:** Selecting all 17 services caused the 09-28 incident: 18 GB downloaded, load 189, swap full. Metadata services should run only in scan windows. Never select Metadata services or the Data Gateway on a 4 GB agent.
- **Fix / do this:** Read the selections before a scan. If the Metadata services are off, ask the owning lane for a scan window instead of turning them on with a PUT yourself. Keep before and after snapshots.
- **KB:** L-AGENT-041, L-AGENT-043, L-CDGC-045

### PD-P1-083 IDMC's BigQuery jobs bill the connection's project, with no byte cap
- **Date:** 2026-10-03
- **Context:** The spend OK named only <project>
- **Lesson:** Profiling, CDGC DQ and Data Gateway queries run in the connection's project (<demo project>, the demo-app project), so the cost lands there. The BigQuery V2 connector, the CDGC scanner and the Data Gateway expose no maximum_bytes_billed. A "1 GB cap per job" holds only for dbt/Airflow.
- **Fix / do this:** Name the project that will be billed in the spend request. Bound IDMC jobs through sample size (≤0.5 GB) or a custom QueryUsagePerDay quota.
- **KB:** L-ENV-041 (partial); IDMC no-cap = new

### PD-P1-084 Cloning a BigQuery connection needs the private key re-supplied
- **Date:** 2026-10-03
- **Context:** New BigQuery connection cloned from <demo BQ connection>
- **Lesson:** GET masks the private key, so a clone must re-supply it, and no new key could be minted (iam.serviceAccountKeys.create was denied). The key formats that work differ between CDI and the Data Gateway, which is why the demo app runs two BigQuery connections.
- **Fix / do this:** Re-supply the key from the existing key file, in the same format as the working connection. Test each consumer (CDI, scanner, Data Gateway), and split into a separate _DG connection if one fails.
- **KB:** L-CONN-007, L-CONN-035 (L-CONN-083 overturned)

### PD-P1-085 Each connection browse GET opens a session on the live database
- **Date:** 2026-10-04
- **Context:** Shared-host-db lane used the demo app's <demo PG connection> as a template
- **Lesson:** Each v2 connection browse GET opens an agent session on the target database. Two of them hit the demo-app Postgres, and the run log under-counted the calls (it said 4; there were 5).
- **Fix / do this:** Count and log browse calls per connection. Read the template's body instead of browsing through it.
- **KB:** new

### PD-P1-086 Configured agent heap (~9.5 GB) far exceeded its 4 GB cgroup
- **Date:** 2026-10-03
- **Context:** infaagent.slice on the prod DB host
- **Lesson:** The slice was MemoryMax 4G / MemoryHigh 3.5G / cpu.max 50%, but its Java processes were configured for about 9.5 GB of heap. memory.events showed high=12M with a 4.16 GB peak, and CPU was throttled in 24% of periods. An idle registered agent needs about 1 GB; a DI-enabled host needs about 16 GB.
- **Fix / do this:** Read `/sys/fs/cgroup/<slice>/memory.events`, `memory.peak` and `cpu.stat` before blaming jobs. Make every -Xmx fit under MemoryMax, or raise the slice off-peak.
- **KB:** L-AGENT-017, L-AGENT-052, L-AGENT-053

### PD-P1-087 A deselected Mass Ingestion runtime kept running, so judge health per agent
- **Date:** 2026-10-03
- **Context:** The app RE trimmed to Platform + DI + DQ
- **Lesson:** After the trim, MassIngestionRuntime was still running (363 MB) and Common_Integration_Components stayed in ERROR. The prod DB host engines were also behind shared (DIS 77.0.5 vs 77.0.11, Connector 21.0.4 vs 21.0.7).
- **Fix / do this:** Judge health from agentEngines in `GET /api/v2/agent/details/<agentId>`, not from the RE selection. Ready means every needed engine is RUNNING and readyToRun is true, with known exceptions listed.
- **KB:** L-AGENT-048, L-AGENT-020; the stale Mass Ingestion runtime is new

### PD-P1-088 The Data Gateway licence deploys to every agent, so check where it is live
- **Date:** 2026-10-03
- **Context:** Data Gateway trial licence (09-30 to 2027-06-26)
- **Lesson:** The licence deploys IDMC_Data_Gateway_Service to every agent within about 10 minutes. A tracker comment said the prod DB host had it, but the live agentdetails read showed it only on the shared agent (4.0.3).
- **Fix / do this:** Read agentEngines before assuming placement. Bind "Query the data" connections to the shared RE, so NL-to-SQL never runs on the prod DB host.
- **KB:** L-MCP-090, L-AGENT-097

### PD-P1-089 ClickHouse object-metadata import over JDBC V2 failed with JDBC_V2_ERROR_205, so profiling first went through a Postgres stage
- **Date:** 2026-10-03
- **Context:** The 7 ClickHouse JDBC V2 connections (<APP>_CH_*) on the app RE, profiling ClickHouse gold
- **Lesson:** All 11 connections tested OK, but every object or field fetch failed with `JDBC_V2_ERROR_205 'entry [<db>] already exists in the collection [null]'`, whether using the URL default DB, `databaseTerm=schema` or no schema name. The driver's own DatabaseMetaData was clean, so the fault was in the connector's catalog builder. Profiling went through the Postgres stage `<stage_db>` instead, and ClickHouse was not cataloged in IDMC (OpenMetadata covered it). A hand-built-fields attempt failed (L-DQ-119).
- **Fix / do this:** Clone a working JDBC V2 profile body before staging elsewhere (see the lesson below that supersedes this one). Keep a staged Postgres sample as the fallback for profiling and cataloging.
- **KB:** L-CONN-089 (disputed), L-CONN-054, L-DQ-134, L-DQ-128, L-DQ-119
- **Status:** superseded by PD-P1-214 and PD-P1-240 (from 11-02 ClickHouse was profiled headless over JDBC V2 by cloning a working profile body with real columns and native types)

### PD-P1-090 The PostgreSQL connector's FK metadata query errors on PG16, but the run succeeds
- **Date:** 2026-10-04
- **Context:** Shared-host Postgres during the parity probe
- **Lesson:** The connector's foreign-key query contains `THEN 0WHEN`, which Postgres 16 rejects ("trailing junk after numeric literal") in bursts of errors. The run still succeeds, but imports carry no keys.
- **Fix / do this:** Filter this text out of DB error alerts, and don't expect PK/FK metadata from PG 15+ imports.
- **KB:** L-CONN-090, L-CONN-104

### PD-P1-091 No identity could mint SA keys: reuse the existing IDMC service account through a dataset grant
- **Date:** 2026-10-03
- **Context:** BigQuery estate lane
- **Lesson:** Neither the ops service account nor the platform VM SA has iam.serviceAccountKeys.create. The existing IDMC service-account key already serves the demo-app BigQuery connection.
- **Fix / do this:** Have the dataset owner grant READER to the existing IDMC SA, so no new key is needed. Jobs bill to that SA's project.
- **KB:** new

### PD-P1-092 Clone a native PostgreSQL connection from a working one on the same runtime environment
- **Date:** 2026-10-04
- **Context:** sample-db lane: <APP>_PG_SAMPLE on RE <shared RE>
- **Lesson:** The body was cloned read-only from the demo app's <demo PG connection>. Type is TOOLKIT_CCI, connectorGuid `com.informatica.adapter.postgres`, timeout 60. connParams: hostName, port (as a string), database, userName, password, authenticationType=UserIdPassword, encryptionMethod=noEncryption, agentId, agentGroupId, orgId. The password was read on the host from a 0600 env file and never left the shared host.
- **Fix / do this:** Clone from a known-good connection on the same RE and change only host, port, database and user. Inject the secret on the host. Create idempotently (skip if the name exists), then read the connection back.
- **KB:** L-CONN-004, L-CONN-001, L-CONN-122

### PD-P1-093 An empty v2 browse proves nothing, and each browse opens a real database session
- **Date:** 2026-10-04
- **Context:** sample-db browse reads
- **Lesson:** `GET /api/v2/connection/source/<id>` returned `200 []` for the new connection and also for the known-good demo-app connection used as a control. Every browse opened an agent session on the live database behind it.
- **Fix / do this:** Prove table visibility through a consumer, for example a CDGC Metadata Extraction. Log every browse of another team's database as a touch.
- **KB:** L-CONN-016, L-CDI-017

### PD-P1-094 The RE list's readyToRun is stale; read health per agent
- **Date:** 2026-10-04
- **Context:** shared agent pre-test guard
- **Lesson:** The runtime-environment list reported readyToRun=false for the shared agent while the agent's own read was healthy.
- **Fix / do this:** Read the agent directly: readyToRun, plus DIS, Connector_Service and the Metadata services RUNNING.
- **KB:** L-AGENT-021

### PD-P1-095 Unbind a connection through the v2 connection API, not agent.do
- **Date:** 2026-10-04
- **Context:** unbinding 4 PII-capable connections
- **Lesson:** The first plan sent the unbind through the legacy agent.do form, which only edits engine configuration.
- **Fix / do this:** Take a v3 export first. Then either `POST /api/v2/connection/<id>` with a different runtimeEnvironmentId, or `DELETE` the connection. Read it back.
- **KB:** L-AGENT-088 (agent.do scope); unbind route new

### PD-P1-096 The Data Gateway picks the BigQuery connection itself
- **Date:** 2026-10-04
- **Context:** data_explore ran on the demo app's <demo BQ connection 2>
- **Lesson:** The gateway tried the org's BigQuery V2 connections for the project one after another ("Error occurred while creating connection"). It used the first one whose key it could open: the two header-less CDI-form connections failed and the full-PEM one worked. The order is not by id or creation time. Deleting or re-keying that connection breaks other teams' prompts without any warning.
- **Fix / do this:** For each new source, read the gateway log (`IDMC_Data_Gateway_Service/<ver>/log/system/log/`) for the "SQL [...] and Connection ID [...]" line.
- **KB:** L-MCP-125, L-MCP-060, L-CONN-035

### PD-P1-097 A gateway-only PEM connection fails the v2 test by design
- **Date:** 2026-10-04
- **Context:** <APP>_BQ_SAMPLE_GW (<id>)
- **Lesson:** A copy holding the full PEM (BEGIN/END lines and newlines) failed `GET /api/v2/connection/test/<id>` with 403 APP_105060 "Invalid PKCS#8 data", yet the next data_explore ran on it. The v2 test exercises the CDI connector's key handling, not the gateway's. The header-less CDI copy passes the test.
- **Fix / do this:** Keep one connection per consumer: header-less for CDI and the scanner, full PEM for the gateway. Write "gateway-only, test fails by design" in the description. Prove it works with one data query plus the gateway log.
- **KB:** L-MCP-127, L-CONN-035

### PD-P1-098 Every BigQuery connection the gateway can't open slows the project's data prompts
- **Date:** 2026-10-04
- **Context:** Gateway traces from 10-01 and 10-04
- **Lesson:** Each connection on the project whose key the gateway can't open costs a failed attempt of 1.3-3.5 s before the query runs, and the delay repeats on later requests.
- **Fix / do this:** Give every connection on the project the gateway's key form, or point CDI-only connections at another project. Count the "Error occurred while creating connection" lines.
- **KB:** L-MCP-126

### PD-P1-099 The Data Gateway log rolls hourly with no archive
- **Date:** 2026-10-04
- **Context:** Verifier re-check of the 08:40Z trace
- **Lesson:** The log rolled at 09:00Z and the newest archive was dated 10-01, so the live proof was gone. Only the lane's excerpt and the BigQuery job id remained.
- **Fix / do this:** Within the hour, copy the relevant gateway lines (with key material filtered out) into the evidence. Record the warehouse job id as independent proof.
- **KB:** new

### PD-P1-100 Cloning a connection inherits another app's credentials and staging bucket
- **Date:** 2026-10-04
- **Context:** <APP>_BQ_SAMPLE cloned from the demo app's <demo BQ connection>
- **Lesson:** The clone reuses the demo-app key and the demo-app GCS staging bucket, so rotating the demo-app key breaks the property-app connection too. The clone body is the GET result minus id, federatedId, stamps and orgId, with the key re-supplied because GET masks it.
- **Fix / do this:** Give each app its own service account and staging path. If you must clone, list the shared dependencies in the description.
- **KB:** L-CONN-122, L-CONN-007 (coupling aspect: new)

### PD-P1-101 A deleted connection reads back as 403 APP_13407
- **Date:** 2026-10-04
- **Context:** deleting 4 PII-capable connections
- **Lesson:** Order used: check v3 used-by (0 references), then `DELETE /api/v2/connection/<id>` (200). Reading it back by id or name then returned 403 APP_13407, not 404. Look connections up by exact name, and refuse if more than one matches.
- **Fix / do this:** Treat 403 or 404 on read-back as "gone", and confirm with the full connection list.
- **KB:** L-CONN-017, L-CLEAN-004 (403 signature: new)

### PD-P1-102 One agent ran 14 mapping-task jobs at once; the 15th waited QUEUED
- **Date:** 2026-11-01
- **Context:** 12 PU lanes + 2 ML lanes on the new RE
- **Lesson:** A 15th `POST /api/v2/job` returned a runId, but the job sat at `executionState: QUEUED` in activityMonitor, not yet in activityLog, for about 6 minutes until a lane finished.
- **Fix / do this:** Leave a slot free for control jobs, or expect them to queue.
- **KB:** L-AGENT-113, L-AGENT-099

### PD-P1-103 When many jobs fail in the same minute, check the host's boot time first
- **Date:** 2026-11-01
- **Context:** Every wf_<p> workflow failed at 20:32Z on 10-31
- **Lesson:** `uptime -s` showed a boot at 20:31:58Z, caused by another session's VM resize. The agents and the target ClickHouse share that VM.
- **Fix / do this:** Compare `uptime -s` / `last reboot` on the agent host with the failure time before debugging.
- **KB:** L-ENV-122, L-ENV-069

### PD-P1-104 CAI's cloud runtime can't reach a private database
- **Date:** 2026-11-01
- **Context:** CAI considered for on-demand reruns
- **Lesson:** The CAI cloud runtime cannot reach the private ClickHouse. The only Process Server was on another agent. CAI calls are not jobs and add no lineage.
- **Fix / do this:** Use CAI only for small on-demand APIs, published to an agent with network reach. Never use it for bulk.
- **KB:** L-CAI-057, L-CAI-056

### PD-P1-105 The agent on the VM being retired was the runtime for the writer into the new target
- **Date:** 2026-11-01
- **Context:** The app RE on the prod DB host was the runtime for <APP>_CLICKHOUSE (42 tasks)
- **Lesson:** Retiring the old DB VM would have killed 42 writer tasks into the new ClickHouse. The new target also allowed the IDMC user only from the old host's IP. The same VM ran about 50 other containers.
- **Fix / do this:** Before retiring a host, list connections and tasks per RE, move them to a runtime that will stay, and fix allow-lists. Treat "stop the database" and "delete the VM" as separate steps.
- **KB:** new

## Ingestion & CDI mappings

### PD-P1-106 Skip CDC, CDI at scale, CAI, MDM and IDMC schedules for a low-volume guest app in a capped org
- **Date:** 2026-10-03
- **Context:** plan v3 "just like the demo app": the demo-app-parity matrix of 33 capabilities (11 keep / 14 adapt / 8 skip)
- **Lesson:** At the property app's volume (a 120M-row estate), DBMI/CDC, CDI lanes at scale, CAI, Data 360, MDM, reverse-ETL, pushdown, IDMC schedules and FAST/ECONOMY modes would burn the shared job cap. IDMC learns on the sample; dbt and Airflow move and check the data at scale. The only IDMC job lane is one parity CDI task (1 job per cycle).
- **Fix / do this:** Mirror only the capabilities that matter for understanding (catalog, CLAIRE, rules, score), and let open-source tools do the volume work. Triggers come from Airflow or a session, never from IDMC schedules.
- **KB:** L-IPU-043

### PD-P1-107 No IDMC schedules: a controller triggers runs after gates
- **Date:** 2026-10-03
- **Context:** profile runs and catalog scans for the property app
- **Lesson:** IDMC schedules cannot check host load or the job quota. A controller (or a Claude session) calls `POST /profile/<id>/execute` only after the window, load, drift and quota gates pass, and skips the run when less than 2 h of the window is left.
- **Fix / do this:** Trigger runs from your own controller with pre-run gates. Never schedule inside IDMC under a cap.
- **KB:** L-IPU-043

### PD-P1-108 Count rule-spec previews and DI jobs from the activity log by name and runtime environment
- **Date:** 2026-10-04
- **Context:** guard counting
- **Lesson:** The guard counts 1 per top-level activity-log row plus 1 per NAMED child of a WORKFLOW/TASKFLOW row. `PreviewMapping*` rows count as previews (weight 1). A row is the property app's when its name matches `^(DQ_<P>_|<APP>_|app_|av_|mt_<p>_|m_<p>_)` or its runtimeEnvironmentId is the property-app RE.
- **Fix / do this:** Attribute jobs by a name prefix convention and the RE id, and count taskflow children separately.
- **KB:** L-IPU-042, L-CDI-201, L-IPU-005

### PD-P1-109 The v2 activity log keeps only about 3-4 days: keep your own hourly ledger
- **Date:** 2026-10-04
- **Context:** guard ledger
- **Lesson:** The activity log purges a whole day at a time (3.2 days of history at 10-04 03:21Z). The guard appends a JSONL snapshot every 30 min with per-hour maxima, and fills hours nobody observed from dated estimates flagged as estimates. A laptop guard that does not run its ledger undercounts once the log has purged hours only the shared host saw.
- **Fix / do this:** Run one ledger on one host continuously, merge per-hour maxima, and label assumed gaps.
- **KB:** L-IPU-059

### PD-P1-110 Detect the cap from error text and block for a while
- **Date:** 2026-10-04
- **Context:** guard cap_error_patterns
- **Lesson:** The cap is invisible until it is hit. The guard scans activity-log messages for "exceeded your monthly limit" / "monthly limit of" and writes a cap block for 60 min (`cap_block_minutes`).
- **Fix / do this:** Watch run error text for the cap message and block new runs for a while after it appears.
- **KB:** L-IPU-041, L-IPU-060

### PD-P1-111 Per-rule parity: exact counts from ValueFrequencies, or one CDI task that writes per-rule counts (proven)
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** translation parity, gate G9 (decision 16); the app's Explore project, folder <p>_cdi_probe
- **Lesson:** CDGC's dataQuality segment returns per-dimension scores only, and a percentage cannot prove that counts match (1 row in 50k is 0.002%). The plan had two routes. Route 1: the profile metric store's `Profiles('<id>')/Columns('<colId>')/ValueFrequencies` on a rule output column (columnKey 40000+) returns exact VALID/INVALID counts. Route 2 ("Pattern A"): one CDI mapping task runs the exported rule specs as Rule Specification transformations over the shared host sample and writes (rule, checked, failed) rows to a shared-host table (1 job per cycle). Route 2 was proven headless on the shared RE at 10-04 06:39Z (task `<p>_cdi_probe_mt_dq_parity`): compared with SQL on the same rows it MATCHED exactly, for 1 job. The ClickHouse JDBC V2 variant is still untested.
- **Fix / do this:** Read ValueFrequencies on the rule output columns first. Otherwise run a single CDI task with Rule Specification transformations that writes per-rule checked and failed counts to a table you can compare. Keep a rule at accepted/needs_review, never active, until it matches.
- **KB:** L-DQ-031, L-DQ-100 (now proven), L-DQ-123, L-CDGC-144

### PD-P1-112 The inherited build was 357 one-off mappings with logic in SQL strings and fake lineage literals: keep logic in transformations
- **Date:** 2026-11-01
- **Context:** target project audit before the Property MDM rebuild
- **Lesson:** 357 mappings, 354 tasks and 149 taskflows (104 at the project root, 45 in Default); about 16 MB of SQL in source queries and task customQuery (median 15.6 KB, max 679 KB), including dictionary content carried as literal arrays or `values()` in overrides of 2.6-236 KB; 222 mappings hard-coded `_mapping_id`, `_task_id` and even `_run_id` literals. Logic in task customQuery is invisible to CDGC and CLAIRE: no column lineage and no rules, and the catalog saw none of the dictionary content.
- **Fix / do this:** Measure the project (counts, SQL size, literal ids) before building. Replace it with a few parameterized mappings: the source SQL in the mapping's source or behind a `$$SRC_SQL` parameter, the logic in real transformations, and reference content loaded as a staged file.
- **KB:** L-CDI-293, L-CDI-097, L-CDI-115, L-CDI-285, L-MDM-081

### PD-P1-113 A mapping whose Source query does survivorship is not mastering
- **Date:** 2026-11-02
- **Context:** Inspection of the 54 target-project mappings
- **Lesson:** `m_<p>_gold2_ma` was a 35,738-char ClickHouse query -> Rule Specification -> Expression -> Target with no Sorter, Aggregator or Router; `m_<p>_cut_dictionary_vocab` was 24,097 chars of SQL; `m_<p>_av_cert_s1` ("native certified AV") had no Verifier. CDGC lineage showed only "SQL blob -> table". None of the 5 exported mappings had parameters.
- **Fix / do this:** Keep the Source to select and order rows only; move standardization, vocabularies, survivorship and routing into Cleanse/Lookup/Rule Spec/Sorter/Aggregator/Router transformations.
- **KB:** L-MDM-081

### PD-P1-114 Target set: 9 parameterized mastering assets replace 40+ one-offs
- **Date:** 2026-11-02
- **Context:** Mastering design for sources, data_dictionary, model_registry, property_master
- **Lesson:** Planned set: `m_<p>_master_sources`, `m_<p>_master_dictionary`, `m_<p>_master_models`, `m_<p>_mdm_10/20/30/40`, `m_<p>_master_gates` and taskflow `wf_<p>_master_all`, each with `p_scope` (state list / ALL), `p_shard` (k/N) and `p_run_label`, rules as assets in `02 Data Quality`. The 13 per-state `m_<p>_gold2_<st>` copies fold into Aggregator groups of mdm_30.
- **Fix / do this:** One mapping per archetype/step, scope as a parameter, never a copy per state or shard.
- **KB:** L-MDM-081

### PD-P1-115 Change a task's scope headless: GET mttask, set inOutParameters currentValue, strip server fields, POST
- **Date:** 2026-11-01
- **Context:** `setparam.py`, backfill drivers for the MDM tasks
- **Lesson:** `GET /api/v2/mttask/{id}`, set `currentValue` on the named `inOutParameters` entry (`p_state_list=MA|MA,NH|ALL`, `p_shard=k/N`), remove `createTime`, `updateTime`, `createdBy`, `updatedBy`, `lastRunTime`, then `POST /api/v2/mttask/{id}` and read back.
- **Fix / do this:** Use this instead of cloning tasks per scope; read back the parameter list after every POST.
- **KB:** L-METHOD-010, L-CDI-022

### PD-P1-116 Task parameters are shared state: run scoped jobs from one driver process
- **Date:** 2026-11-01
- **Context:** National MDM backfill drivers v2 -> v5
- **Lesson:** Scope lives on the task, so two processes setting `p_state_list` on the same task race and run the wrong scope. v3 moved to "one process (no cross-process scope races)", waits while the task appears in `/api/v2/activity/activityMonitor` before setting parameters, and v5 resets the task to MA / ALL at the end.
- **Fix / do this:** One driver per task; check activityMonitor for a running instance before changing parameters; restore default parameter values when done.
- **KB:** new

### PD-P1-117 Start a mapping task over v2 and poll the activity log by runId
- **Date:** 2026-11-01
- **Context:** `runjob.py`, `waitrun.py`
- **Lesson:** `POST /api/v2/job` with `{"@type":"job","taskId":...,"taskType":"MTT"}` returns `runId`; poll `GET /api/v2/activity/activityLog?rowLimit=40..80` for the entry with that `objectName` and `runId`; `state == 1` is success, and the entry carries `successSourceRows`, `successTargetRows`, `failedTargetRows`, `errorMsg`.
- **Fix / do this:** Match on both name and runId; re-login inside long polls; treat a missing entry as still running.
- **KB:** L-METHOD-031, L-CDI-288, L-CDI-056, L-CDI-059

### PD-P1-118 Bounded retries in the backfill: 1 retry, then 3 attempts with a 120 s pause and a GAVE-UP log
- **Date:** 2026-11-01
- **Context:** National golden/publish backfill
- **Lesson:** Each step retried a failed run (v3 once, v4/v5 up to 3 times, 120 s apart) and logged GAVE-UP rather than looping. Re-runs were safe because a rerun rewrites the same record ids at a newer version.
- **Fix / do this:** Make steps idempotent first, then retry a bounded number of times; classify the errorMsg before retrying.
- **KB:** L-CDI-287

### PD-P1-119 ClickHouse final sort over the 10 GB cap: add a hash-shard parameter and smaller sort blocks
- **Date:** 2026-11-01
- **Context:** Golden-record mapping for 8 national state groups
- **Lesson:** 8 groups failed in ClickHouse's `MergeSortingTransform` over the 10 GB memory cap. Adding `p_shard` (`k/N`, default ALL) and smaller sort blocks, then running each group as 2 shards with one publish per group, fixed it. State groups of ~6-9M observations bounded memory and the work lost to a failure.
- **Fix / do this:** For big sorted reads feeding a sorted Aggregator, shard by `cityHash64(id) % N` and shrink merge blocks instead of raising memory.
- **KB:** L-CDI-272

### PD-P1-120 ClickHouse write storm: rows per INSERT are capped by DTM block size over declared row width, and by writer batch size
- **Date:** 2026-11-01
- **Context:** Property MDM writes and bronze capture through JDBC V2 (all target-project targets); Mappings from another code generator with summed target precision up to 2,010,367 characters
- **Lesson:** A batch never spans DTM blocks, so rows per INSERT are capped at block size divided by declared row width. A 128K-character JSON port gave 60-82 rows per INSERT (a new ClickHouse part per insert, ~52 inserts/s, ~150 rows/s per task), and the default 200-row batch was the next cap. Over-wide runs rejected 60, 72 or 12 rows, and the target got about 80 rows per part: 125,174 parts and 10.06M rows in one hour, so the remaining 3.27B rows would have taken about 11 days; seven mappings over 1M characters wide also ran out of Java heap (OutOfMemoryError). A default task shows "Total Buffer Pool size is 22110880 bytes and Block size is 1226160 bytes" and "Waiting for consumer to free buffer block. Please increase the dtm buffer pool size". Task `sessionProperties` `DTM buffer size` 1-2 GB and `Default buffer block size` 32-64 MB plus writer `batchSize` 10,000-20,000 gave about 2,100 rows per INSERT for wide golden rows and about 10,000 for narrow cross-reference rows; MA golden (2.5M rows) then ran in 13-38 min.
- **Fix / do this:** Declare real widths and keep ports narrow; carry payloads as ordered chunks of 8,000 code points or fewer, inside the 16,384-unit IDMC string precision. Then set the two session properties on the mttask (GET -> merge -> POST -> read back, backup kept) and the target batch size, and raise the DTM heap at the same time.
- **KB:** L-CDI-262, L-CDI-290, L-AGENT-112

### PD-P1-121 Lineage ids typed into SQL are not lineage: use the runtime variables, and build twice on first import because the mapping id is embedded
- **Date:** 2026-11-01
- **Context:** lineage columns on every MDM row; the old build stamped `'3' AS _run_id`, `_task_id` and `_mapping_version` as literals
- **Lesson:** Literal run ids pointed rows at runs that never produced them, including an aborted run (3,156 rows). One MDM load stamped the same `idmc_processed_at` on all 1.7M rows, a CHECK constraint (`actual_idmc_lineage`) only validated the id format, and large loads did not even appear under their task ids in the activity log. The rebuild stamps `$CurrentTaskId` / `$CurrentRunId` (substituted in expression literals) and `SESSSTARTTIME`, plus the mapping id and `idmc_mapping_version` = SHA-256 of the mapping spec. The mapping id comes from `ids.json`, which exists only after the first import, so a first deploy needs a second build+deploy (OVERWRITE under the same id).
- **Fix / do this:** Use `'$CurrentTaskId'`, `'$CurrentRunId'` and `SESSSTARTTIME` in an Expression. Keep a name -> v2 id file: deploy once, fill the ids, rebuild, deploy again. Verify the stamps against real activity-log runs.
- **KB:** L-CDI-265, L-CDI-293, L-CDI-295, L-AGENT-115

### PD-P1-122 Version rows from the session start time so re-runs replace in ReplacingMergeTree
- **Date:** 2026-11-01
- **Context:** record_version / dictionary_version in MDM and registry mappings
- **Lesson:** `record_version` = run start (YYYYMMDDHH24MISS), or in the 11-02 specs `TO_DECIMAL(DATE_DIFF(SESSSTARTTIME, TO_DATE('1970-01-01 00:00:00',...), 'SS'), 0)`. A re-run writes the same record ids at a higher version and the engine keeps the newest.
- **Fix / do this:** Derive the version column from SESSSTARTTIME in an Expression; keep record ids stable across runs. Mind that SESSSTARTTIME follows the runtime's clock zone.
- **KB:** L-AGENT-115

### PD-P1-123 Array/Map columns: write a scalar staging batch, then merge it with the target's Post SQL
- **Date:** 2026-11-02
- **Context:** `m_<p>_master_sources` writing `<target_db>.sources`
- **Lesson:** The JDBC writer cannot round-trip the table's Array/Map columns. The mapping writes conformed scalars to `<work_db>.sources_fix`; Post SQL runs `INSERT INTO <target_db>.sources SELECT s.* REPLACE (f.source_name AS source_name, ..., f.idmc_run_id AS idmc_run_id) FROM <target_db>.sources AS s FINAL INNER JOIN (latest batch of sources_fix) AS f ON f.source_id = s.source_id WHERE f.version > s.version`. Run 1: 1,790 in/out, 0 failed, 17 s, Array/Map columns intact.
- **Fix / do this:** Use `SELECT * REPLACE(...)` from FINAL joined to the latest staging batch, guarded by version; keep an undo copy (`sources_pre_master_20261102`).
- **KB:** L-CDI-273

### PD-P1-124 JDBC V2 type rules for ClickHouse reads and writes
- **Date:** 2026-11-01
- **Context:** Property MDM mappings reading and writing `<target_db>.property_master`; ingest test runs 3-4 (record_version); dictionary_registry tasks
- **Lesson:**
  - **Timestamps:** the reader rejects ClickHouse DateTime64 text ("Timestamp format must be yyyy-mm-dd hh:mm:ss[.fffffffff]"); reading `toString(toDateTime(x,'UTC'))` and converting with `TO_DATE` fixed it.
  - **UInt64:** bigint at the source and NUMERIC/decimal(20,0) at the target port. An integer port where the driver hands over a wider Java type fails with "BigDecimal cannot be cast to Long". In mapping sources UInt64 reads as NULL unless cast with `toInt64`.
  - **Other types:** UInt32 -> bigint, UInt16 -> integer, Float32 -> double; non-nullable columns reject NULL.
  - **Strings:** precision 0 needs `toFixedString(substring(x,1,N),N)`.
- **Fix / do this:** Map ports to these types in the generator, read timestamps as text, and cast strings to a fixed length in the source SQL.
- **KB:** L-CDI-264, L-CDI-291, L-CDI-172, L-CONN-054, L-CONN-055

### PD-P1-125 Matching reads in key order from ClickHouse with no DTM sorter cache
- **Date:** 2026-11-01
- **Context:** `m_<p>_mdm_20_match_merge`
- **Lesson:** Match keys are standardized in an Expression and the Source reads them ORDER BY key; master ids are assigned with variable ports (R1 source identity, R2 same state + ZIP5 + parcel + address + unit + class = one physical property, lowest id survives). No Sorter cache is needed on the agent.
- **Fix / do this:** Let the warehouse sort; assign masters with variable ports; never merge on parcel or address alone.
- **KB:** L-MDM-075

### PD-P1-126 Generating a Verifier transformation: the designer shape to copy
- **Date:** 2026-11-01
- **Context:** mapgen extension `verifier` node
- **Lesson:** A designer-built Verifier (TmplVerifier, version R37) has input group "Input group:" with MANUAL field mapping (incoming field -> asset input port) and output group "MappletOutputTx_Output" with the asset's output ports; incoming fields pass through. `verifierAssetId` references the existing asset's frs id; ports left out of the map receive nothing.
- **Fix / do this:** Harvest the shape from one designer-built mapping, list the asset in the spec's assets, and lint map keys against the asset's input ports.
- **KB:** L-CDI-266

### PD-P1-127 A Verifier writes no geocodes unless its own settings request them: output ports alone are not enough
- **Date:** 2026-11-01 / 2026-11-02
- **Context:** vfr_<p>_address_verify / _components / _status; the Standard geocode fallback `vfr_<p>_geocode_standard` + `m_<p>_av_standard_geocode` (AK 41,602, TX 300)
- **Lesson:** The geocode and enrichment files were installed, yet 0 rows had a geocode or DPV value: none of the three verifiers had geocode, DPV/CASS or enrichment outputs configured. The later Standard-geocode fallback run COMPLETED but returned no geocodes, because no geocoding option reached the engine. Still open.
- **Fix / do this:** Configure geocode and enrichment in the Verifier asset's own settings and map them to columns, not only its output ports. Test on a handful of addresses before a state run.
- **KB:** L-DQ-130, L-DQ-125

### PD-P1-128 Rule specs inside mappings: normalize Output and route on VALID
- **Date:** 2026-11-02
- **Context:** `m_<p>_master_sources`, `m_<p>_av_enrichment_registry`
- **Lesson:** Each rule spec's `Output` is normalized in an Expression (`UPPER(LTRIM(RTRIM(Output)))`) and Router groups test `= 'VALID'`; failures build a steward reason string (`SCOPE_UNKNOWN;URL_UNRESOLVED;STATUS_INVALID;DESCRIPTION_MISSING;NAME_DISAMBIGUATED;`) plus changed-flags per field. Steward queue: 986 rows with reason codes.
- **Fix / do this:** Use the same rule spec assets in mappings and profiles; route invalid rows to a steward queue with reason codes instead of dropping them.
- **KB:** new

### PD-P1-129 Aggregator + Joiner name groups find feeds that share a name
- **Date:** 2026-11-02
- **Context:** sources registry mastering
- **Lesson:** A name key `LOWER(TRIM(name))|state|county_fips|town` is counted in an Aggregator, joined back on a sorted Joiner, and names in groups > 1 get a ` [dataset suffix]` instead of being merged: 12 shared names disambiguated, 0 merges.
- **Fix / do this:** Use Aggregator + sorted Joiner for group counts in-mapping; disambiguate distinct feeds by name, merge only true duplicates.
- **KB:** L-MDM-077

### PD-P1-130 Keep the property MDM chain out of a taskflow that would duplicate golden rows after the swap
- **Date:** 2026-11-02
- **Context:** `wf_<p>_master_all` (<id>)
- **Lesson:** The taskflow ran sources -> AV enrichment registry (1,792 + 156 rows, 0 failed), unscheduled. The property MDM chain was left out because, with a separate cutover build owning the finished table, running it would write a second golden.
- **Fix / do this:** One golden writer per entity; add the property step only after the swap, writing the finished table.
- **KB:** L-MDM-079

### PD-P1-131 A gates mapping driven by per-table SQL in a parameter file
- **Date:** 2026-11-02
- **Context:** Planned `m_<p>_master_gates`
- **Lesson:** The G1-G9 queries are longer than an in-out parameter can hold, so the design uses Source = `$$GATE_SQL` from a parameter file per table -> Expression pass/fail vs threshold -> run_manifest rows (`<p>-mastering-gates-v1`), with a taskflow Decision after each gate that stops on a failed exact gate.
- **Fix / do this:** Put long per-run SQL in an agent parameter file; write gate results as rows so the trend comes from IDMC.
- **KB:** L-CDI-285
- **Status:** superseded by PD-P1-151 for the taskflow Decision step (Decision taskflows cannot be published headless); the parameter-file part stands

### PD-P1-132 Back-fill AV fields from the stored response JSON instead of calling the service again
- **Date:** 2026-11-02
- **Context:** Cloud AV Certified results (about 100M address rows, full JSON on every row, max 5,642 chars, 0 truncated)
- **Lesson:** 17 returned fields (LACS/LACSLink, SuiteLink, DPVConfirmation3553, DPV footnotes, DPVNoStatReason, DefaultFlag, ...) plus 3 block statuses lived only in the JSON. Because the full response was kept, an IDMC mapping can back-fill new columns from it with no API calls and no units.
- **Fix / do this:** Always store the full verification response; add columns later and parse them from the stored JSON.
- **KB:** L-DQ-132

### PD-P1-133 Archive superseded assets with FRS MoveEntities, export first, keep ids
- **Date:** 2026-11-02
- **Context:** Organizing the target project (140 -> 80 objects)
- **Lesson:** 76 superseded objects (13 `m_<p>_gold2_*` + tasks, probes, `m_<p>_tbl_*`, one-off dictionary loads, never-run profiles) moved to `Archive/<project> superseded 2026-11-02` with `POST /frs/api/v1/MoveEntities` (chunks of 25, from/to logged to `moves_log.jsonl` for undo, zip backups first). Ids were kept because loaded rows reference them; profiles move too. 3 orphan profile shells with FRS_108 were left for an owner decision.
- **Fix / do this:** Export, then move (never delete) superseded assets; log each move with its undo; reconcile row counts before retiring a loader.
- **KB:** L-CDI-016, L-MIG-054, L-DQ-124, L-MIG-079
- **Status:** overturns PD-P1-191 (profiles can be moved with MoveEntities)

### PD-P1-134 Folder descriptions as maps of their live assets
- **Date:** 2026-11-02
- **Context:** The 8 target-project folders
- **Lesson:** All 8 folder descriptions were rewritten to list the live assets in each, so a reader can navigate the project without the export.
- **Fix / do this:** PATCH folder descriptions after each reorganization.
- **KB:** L-MIG-085

### PD-P1-135 A table written by a Python script carried "native:" lineage; lineage checks must require real IDMC ids
- **Date:** 2026-11-02
- **Context:** sources mastering
- **Lesson:** `sources` turned out to have been written by a Python script stamped `native:...`. After `m_<p>_master_sources` re-stamped every row with real IDMC lineage, the evaluator's S-L01 check was tightened to "written by a real IDMC mapping / task / run (ids, not script names)".
- **Fix / do this:** Check what actually wrote a table before crediting IDMC; make lineage checks reject non-IDMC ids.
- **KB:** L-METHOD-043, L-CDI-295

### PD-P1-136 A JDBC V2 load into ClickHouse is writer-bound: read the thread busy percentages
- **Date:** 2026-11-01
- **Context:** Bronze capture tasks `mt_<p>_property_resume_10` and `mt_<p>_event_gap_06`
- **Lesson:** The writer thread was 99.8-100% busy while reader and transformation threads were 0.3-3% busy. 1,826,611 rows took 4 h 03 min (about 125 rows/s) and 6,858,522 rows 3 h 07 min (about 610 rows/s), both at the default commit interval 10,000.
- **Fix / do this:** Check the "Busy Percentage" block at the end of the session log first; when the writer is the bottleneck, tune writer batch size, DTM block size and port widths, not the source query.
- **KB:** L-CDI-262

### PD-P1-137 Set session properties on a v2 mapping task with GET, merge, POST and read back; raise the DTM heap first
- **Date:** 2026-11-01
- **Context:** `taskprops.py` and `setparam.py` on the MDM tasks; throughput tests on mt_<p>_ingest_capture
- **Lesson:** `GET /api/v2/mttask/<id>`, merge into `sessionProperties` / `sessionPropertiesList` (or edit `inOutParameters[].currentValue`), drop `createTime`, `updateTime`, `createdBy`, `updatedBy`, `lastRunTime`, POST the whole body back, then GET again to confirm. The scripts kept `task_backup_<id>.json` before each change. The generator cannot set `sessionPropertiesList`. Ingest test run 1 died with a reader OOM and hung until it was stopped; later runs used a 128 MB block, a 1.5 GB pool and a 3 GB heap, and the lanes then moved to a 256 MB block and a 3 GB pool.
- **Fix / do this:** After deploy, back up the task JSON, strip the audit fields, POST the full object and read back. Raise the heap before the block size, and confirm the effective buffers in the session log (TM_6660).
- **KB:** L-CDI-022, L-CDI-262, L-CDI-290, L-AGENT-112

### PD-P1-138 The DTM Sorter's 512 MB default cache forced a 2-pass sort; let the warehouse sort
- **Date:** 2026-11-01
- **Context:** First version of `m_<p>_mdm_20_match_merge` (Sorter `SRT_BY_MATCH_KEY`)
- **Lesson:** 2,519,596 rows (1.69 GB) needed a 2-pass sort with 1.70 GB temp I/O; the run took 29 min and the log said "set the cache size to 1816 MB or higher for 1-pass". The later version dropped the Sorter (6 to 5 transformations) and read in match-key order with ClickHouse ORDER BY, recomputing the key visibly in an Expression.
- **Fix / do this:** For big sorted inputs, ORDER BY in the source query; keep a DTM Sorter only for small sets or size its cache from the log hint.
- **KB:** L-MDM-075

### PD-P1-139 Guard port precision in the source SQL with throwIf so overflow fails loudly
- **Date:** 2026-10-31
- **Context:** Bronze capture mappings reading the legacy property universe
- **Lesson:** Every source column is wrapped as `if(throwIf(length(ifNull(x,''))>N,'<target_db> field exceeds native precision: <col>')=0, x, NULL)` (N = 64 for short text, 128 for source system, 8,192 or 131,072 for the raw JSON payload). An oversize value aborts the query with a named column instead of being truncated silently by the connector.
- **Fix / do this:** Generate a throwIf length guard per string port that matches the port precision.
- **KB:** new (related L-CDI-172)

### PD-P1-140 Scope one mapping with in-out parameters instead of copying it per state
- **Date:** 2026-11-01
- **Context:** `m_<p>_mdm_10/20/30/40` with `p_state_list`, `p_batch_limit`, `p_shard`
- **Lesson:** Inside a custom query `$$p_state_list` is substituted anywhere, also inside quotes (`('$$p_state_list' = 'ALL' OR has(splitByChar(',', '$$p_state_list'), toString(state)))`); in an Expression a quoted `'$$p'` stays literal and wrote the text into a manifest. Parameters were declared with `retention: NEVER` and set per run through `inOutParameters[].currentValue`.
- **Fix / do this:** Use one parameterized mapping per stage; reference parameters unquoted in Expressions; reset the parameter to its default after a backfill (the runner reset `p_state_list=MA, p_shard=ALL`).
- **KB:** L-CDI-265

### PD-P1-141 mapgen deploy cycle: dry run, REUSE to create, OVERWRITE to change, ids kept
- **Date:** 2026-11-01
- **Context:** 27 mapgen deploys of the four `m_<p>_mdm_*` mappings in one day
- **Lesson:** A dry run lints and packages; the first live deploy imports with REUSE ("Create object") and creates plus moves the task; later deploys import with OVERWRITE ("Overwrite existing object") and keep the v2 mapping id (for example `<id>`) and the task. Changing the spec's folder re-filed the mapping under the same id. Every deploy writes a run record with lint counts, import job id and validity.
- **Fix / do this:** Iterate with OVERWRITE redeploys and keep the per-deploy run records as the change log.
- **KB:** new (related L-METHOD-129)

### PD-P1-142 An import gives the mapping a different id and FRS guid than the package
- **Date:** 2026-10-04 / 2026-11-01
- **Context:** parity-mapping import; first deploy of `m_<p>_mdm_10_verify_address` and `m_<p>_mdm_30_golden_record`
- **Lesson:** The import created mapping id <id>, not the package's <id>. mapgen warned "the imported mapping has frs guid <id>, the package said <id>" (same for the golden mapping). The guid in the package is not the one the org assigns on a REUSE import.
- **Fix / do this:** After the first import, look objects up by name and path, record the guid and v2 id the org returned (`ids.json`), and use those for moves, references and later builds. Check how OVERWRITE matches before you re-import.
- **KB:** L-CDI-256 (mapplet case); the mapping case is new

### PD-P1-143 Back up the whole project with a v3 export before changes
- **Date:** 2026-11-01
- **Context:** `<p>_backup_20261101T053846Z.zip` of the target project
- **Lesson:** `POST /public/core/v3/export` with the project id and `includeDependencies: true`, poll until not IN_PROGRESS/QUEUED, then `GET .../package` with `Accept: application/zip`. The package nests one zip per object (connections and agent groups under `SYS/`); the full project was 7.5 MB.
- **Fix / do this:** Take a timestamped project export before any bulk change; unpack nested zips to inspect objects.
- **KB:** L-MIG-003, L-MIG-021

### PD-P1-144 A linear workflow chains the stages and stops on the first error
- **Date:** 2026-11-01
- **Context:** `wf_<p>_mdm_property_master` (10 → 20 → 30 → 40)
- **Lesson:** Created over `/api/v2/workflow` with four MTT tasks, each `stopOnError: true`, unscheduled; the scope comes from the tasks' in-out parameters. No publish step was needed.
- **Fix / do this:** Use a linear taskflow for a fixed pipeline; add a schedule only after the gate step exists.
- **KB:** L-CDI-069

### PD-P1-145 Retry only transient error signatures: retrying a deterministic failure only burns jobs
- **Date:** 2026-11-01
- **Context:** national golden-record backfill (`backfill_v4`); build/lane_runner.py
- **Lesson:** backfill_v4 retried each failed step 3 times with 2-minute waits. Every golden group (TX, CA, FL, NY+OH, NJ+TN+MD, ...) failed all three tries with the same `Code: 241 ... maximum: 9.31 GiB ... MergeSortingTransform`, about 24 wasted jobs before "GAVE-UP". The ingest lane runner was built differently:
  - **Polling:** `GET /api/v2/activity/activityLog?taskId=<id>&rowLimit=20`, matched on runId. A run is done at state 1, or state 2 with 0 failed rows.
  - **Retries:** at most 3, only when errorMsg matches a transient pattern: Premature EOF, agent disconnection, TOO_MANY_SIMULTANEOUS, SOCKET_TIMEOUT, 502/503/504, "job not found on agent", "DTM process terminated", MEMORY_LIMIT, Code: 241.
  - **Concurrency:** at most 3 heavy items at once.
  - **State:** JSON written via temp file + replace, so the runner can be killed and restarted safely.

  The lane runner counts a memory error as transient (another lane may have held the memory); the backfill showed that the same Code 241 on the same scope three times in a row is deterministic.
- **Fix / do this:** Retry only transient signatures (SSL peer, connection refused, Premature EOF after a proxy fix, a one-off memory error). Never retry data or permission errors (Code 497, Code 469). On a repeated memory-cap error, change the run (shard, settings) instead of repeating it. Don't edit the manifest or the state file while the runner is running.
- **KB:** L-CDI-205, L-CDI-287, L-METHOD-136

### PD-P1-146 A backfill driver should adopt a run already in flight
- **Date:** 2026-11-01
- **Context:** `backfill_v3/v4/v5` national MDM drivers
- **Lesson:** Drivers took a running match run id as an argument and waited on it ("(adopted)") instead of starting a duplicate; lane A ran match per state group, lane B ran golden plus publish for each group as soon as its match landed. Re-running a group only rewrote the same record ids at a newer version.
- **Fix / do this:** Make drivers idempotent, able to adopt in-flight runs, with one heavy run per lane.
- **KB:** L-CDI-102

### PD-P1-147 Address-verification sweeps used most of the monthly job budget
- **Date:** 2026-11-12
- **Context:** `<p>_r7_av_verify_mt` and `mt_<p>_av_cert_s1..s4`
- **Lesson:** About 2,180 verification runs since 11-08 at about 4,800 addresses each, 728 jobs on 11-11 alone, against an org cap of about 10,000 jobs a month shared with other demos. A taskflow of N tasks counts N+1 jobs.
- **Fix / do this:** Budget jobs per lane before starting a sweep; verify in big batches; put a quota breaker in every starter.
- **KB:** L-CDI-131, L-IPU-041, L-IPU-043

### PD-P1-148 No pushdown to ClickHouse: IDMC moved 1,100-18,000 rows/s where SQL did 124,000-660,000
- **Date:** 2026-11-12
- **Context:** Measured from ClickHouse query_log, 11-01 to 11-12
- **Lesson:** IDMC standardization wrote 383M rows in 5.8 h (1,372 rows per INSERT, about 18,000 rows/s across tasks); merge routing 29.7M in 7.4 h at the 200-row default batch (about 1,100 rows/s). SQL built the matching map (2.0B rows) in 50.5 min and survivorship (1.09B) in 147 min. Every row leaves ClickHouse over JDBC and comes back because full pushdown is proven only inside one warehouse family.
- **Fix / do this:** Do not plan full national rebuilds through mappings on ClickHouse; process only changed rows, or test pushdown once on a copy of one task.
- **KB:** L-CDI-043, L-CDI-202, L-CDI-203

### PD-P1-149 Per-state mapping copies multiply jobs and reruns
- **Date:** 2026-11-12
- **Context:** Folder 04 Property Master
- **Lesson:** 123 mappings and 123 tasks were created per state (`<p>_r7_route_<st>`, `m_<p>_r7_dq_<st>`, `m_<p>_onemaster_<st>_*`); Texas standardization ran about 11 times (197M rows written for 17.9M properties). Each run is one job against the monthly cap.
- **Fix / do this:** One mapping per step with state and shard parameters (about 51x fewer jobs), or archive the copies when the step is finished.
- **KB:** L-CDI-265, L-CDI-272

### PD-P1-150 Tuned writer settings were not carried into new mappings
- **Date:** 2026-11-12
- **Context:** 11-07/08 Act 3 pilot and routing mappings
- **Lesson:** After the 11-01 fix (batch 10-20k, bigger DTM buffers) took inserts to 2,100-10,000 rows, the later pilot and routing mappings still wrote 200-307 rows per INSERT because they were built with defaults.
- **Fix / do this:** Put the tuned task session properties and writer batch size into the generator's defaults so every new mapping inherits them.
- **KB:** L-CDI-262

### PD-P1-151 Unattended runs: a linear taskflow plus a gate mapping, not a Decision step
- **Date:** 2026-11-12
- **Context:** Plan to make the master run without Claude sessions
- **Lesson:** Advanced taskflows with a Decision cannot be published headless; linear taskflows and v2 schedules can. A check mapping that fails the run replaces the Decision.
- **Fix / do this:** Build a linear taskflow whose gate mapping fails on a broken check, then bind a native schedule.
- **KB:** L-CDI-069, L-CDI-070, L-CDI-073, L-CDI-193
- **Status:** overturns the taskflow-Decision design in PD-P1-131

### PD-P1-152 Learn a connector's mapping shape from one working export, and diff the generated IMF against it before import
- **Date:** 2026-10-04 / 2026-11-03
- **Context:** PG source and PG Insert target shapes; trim-to-Oracle task (`<oracle task>`, connection `<oracle connection>`)
- **Lesson:** A read-only v3 export of a proven demo-app mapping served as the reference for the PG shapes. The generated source and target matched it with 0 key or value differences (only precisions differed), and rebuilds kept the mapping GUID (guid.txt), so an OVERWRITE re-import stays possible. mapgen knows only BigQuery, PostgreSQL, JDBC V2, Flat File and Salesforce (`KIND_BY_CONNECTOR` in `resolve.py`); Oracle resolves to unknown. The plan there: find a mapping that already writes to the connection (`GET /public/core/v3/objects/<conn id>/references?refType=usedBy`) or ask for a throwaway 2-node UI mapping, v3-export it, and copy `typeSystem`, object path, field `nativeType` and createTarget attributes.
- **Fix / do this:** Export one proven mapping per adapter, diff the generated IMF against it by key set, then import. Keep the GUID stable across rebuilds and a diff of every mapgen change. Never guess a new connector's shape.
- **KB:** L-CDI-145, L-METHOD-129, L-MIG-034; shape diff new

### PD-P1-153 Before building on a file and an Oracle target: test, read the header, check the real table name
- **Date:** 2026-11-03
- **Context:** Same Oracle task
- **Lesson:** Steps that worked elsewhere: resolve ids by name, test both connections on the runtime (`GET /api/v2/connection/test/<id>`), read file columns with `GET /api/v2/connection/source/<conn id>/field/<file>`. Oracle uppercases unquoted names, so a created table may not be called what the mapping said. Fallback only with approval: a JDBC V2 connection with the Oracle driver shipped under `ext/connectors/thirdparty/informatica.jdbc_v2/common`.
- **Fix / do this:** Verify with activity-log state 1, success rows = file rows, and a sample row; write down every object created and how to undo it.
- **KB:** L-CONN-014, L-CONN-049

### PD-P1-154 The landing table is wide and mostly Nullable: plan port types from the DDL
- **Date:** 2026-11-01
- **Context:** `<target_db>.property_master` (369 columns)
- **Lesson:** The one shared table has 249 Nullable, 62 LowCardinality, 4 Array and 3 DateTime64 columns plus lineage columns (`idmc_mapping_id`, `idmc_task_id`, `idmc_run_id`, `dq_status`, `dq_score`, `serving_eligible`, `field_lineage_json`). Fill-rate checks must treat '', '{}' and '[]' as empty and skip MATERIALIZED/ALIAS columns.
- **Fix / do this:** Generate ports and fill-rate SQL from `system.columns`, per type family.
- **KB:** new

### PD-P1-155 A connector-less ingest engine: config-only sources, raw landing, governance in sidecar columns
- **Date:** 2026-08-01
- **Context:** The property app ingest platform (`av-ingest` on the data host)
- **Lesson:** One generic engine reads `ingest-sources.yaml` (hot-reloaded every 10 s; a malformed edit keeps the last good registry, a bad source block is skipped and logged) and lands every record verbatim in a ClickHouse bronze table with `_source_system`, `_source_uri`, `_entity`, `_business_key`, `_dq_status`, `_dq_reasons`, `_record_hash`, `_batch_id`. Adding a governed source is a YAML edit with no redeploy.
- **Fix / do this:** Keep per-source logic declarative; secrets come from env vars, never the YAML.
- **KB:** new

### PD-P1-156 On a shared 8 GB box, run the ingest JVM capped and single-threaded
- **Date:** 2026-08-01
- **Context:** Ingest runtime co-located with ClickHouse, MongoDB and the IDMC agent
- **Lesson:** The service runs under Camel JBang (`camel run *.java`, no Maven build, which risked OOM on the box) with `mem_limit 512m`, `memswap_limit 1g`, `cpus 0.5` and one scheduler consumer, so sources run one after another. Route errors are handled per source so the timer never dies.
- **Fix / do this:** Cap every co-located service's memory and CPU; prefer sequential scheduling over parallel lanes on a shared host.
- **KB:** L-AGENT-052

### PD-P1-157 Retire dropped files only after the batch lands; ownership matters
- **Date:** 2026-08-01
- **Context:** File-drop sources (`listing_property`, `property_dropzone`)
- **Lesson:** Files are renamed `.done` only after a successful insert, so a failure never loses data and a re-drop is dedup-safe. The container runs as uid 1500, so drop files must be `1500:1500` and the folder writable by it. A file dropped for a disabled source just sits there. Each partner gets an isolated subfolder so sources do not consume each other's files.
- **Fix / do this:** chown drops to the container uid, use one subfolder per source, enable the source before dropping.
- **KB:** L-ENV-104

### PD-P1-158 One provider can need two ingest paths
- **Date:** 2026-08-01
- **Context:** A listings provider's research CSVs and home-detail pages
- **Lesson:** Wide monthly research CSVs (300+ columns, up to about 26k regions) are the wrong shape for a JSON engine in a 512 MB JVM, so they load ClickHouse-native and stay declared but `enabled: false` for governance visibility. Home-detail pages are HTML with an embedded `__NEXT_DATA__`/`ld+json` record, extracted to NDJSON and dropped. Per-property AVM data is not in the free CSVs; it needs the gated vendor API.
- **Fix / do this:** Pick the ingest path by data shape; declare disabled sources so the registry still shows them.
- **KB:** new

### PD-P1-159 Fail-safe declarative DQ on ingest: never drop a record, never fail good data on a config typo
- **Date:** 2026-08-01
- **Context:** `DQEngine` in the ingest platform
- **Lesson:** Rule types `not_null`, `regex` (unanchored), `range`, `allowed_values`; severity fail holds a record out of golden, warn only annotates. An unknown rule type or malformed regex counts as pass; a non-numeric value under range is a real violation; a non-JSON payload lands marked `payload:not-json`. Failing records still land and show in `dead_letter` with every violated check. A deliberate all-null test row failed all 6 fail rules and appeared in dead_letter.
- **Fix / do this:** Land everything, stamp the verdict, and prove the gate with a seeded failing record.
- **KB:** L-DQ-060

### PD-P1-160 A schedule edited to Daily kept firing hourly
- **Date:** 2026-10-04
- **Context:** demo-app cadence trim: <evidence_hourly> / <landing_every3h>
- **Lesson:** `GET /api/v2/schedule` showed interval=Daily, frequency=1, yet the runs kept coming hourly and every 3 h. An external REST starter (a lane controller) was launching them, so re-applying "Daily" fixes nothing.
- **Fix / do this:** Before trimming cadence, group the runs by `runContextType` and `startedBy`, then cut the cadence where the runs really start.
- **KB:** L-IPU-061

### PD-P1-161 Headless CDI end to end on the shared agent: one job
- **Date:** 2026-10-04
- **Context:** <p>_cdi_probe_m_dq_parity
- **Lesson:** The generator produced a mapping of 8 transformations and 7 links: PG source → EXP flags → AGG counts → EXP run stamp (SYSTIMESTAMP once, in a VARIABLE port) → 2 row EXPs → 2 PG Insert targets. The run sequence:
  1. v3 import (REUSE) → SUCCESSFUL.
  2. `POST /api/v2/mttask` {@type mtTask, name, mappingId, runtimeEnvironmentId}.
  3. FRS `/frs/api/v1/MoveEntities` into the folder.
  4. `POST /api/v2/job` {taskId, taskType MTT}.
  5. Poll `activityLog?taskId=..&rowLimit=1` until endTime is set.

  The run took 8 s and ended in state 1.
- **Fix / do this:** Reuse this sequence for probe and parity tasks. Only the run counts as a job; create, import and move do not.
- **KB:** L-CDI-033, L-CDI-037, L-CDI-016, L-CDI-056

### PD-P1-162 Give each lane its own v3 project and folder, never Default
- **Date:** 2026-10-04
- **Context:** The app's Explore project, folder <p>_cdi_probe
- **Lesson:** `POST /public/core/v3/projects` followed by `/projects/<id>/folders`, created idempotently and read back, kept the property app objects apart from the demo app's. Undo is a folder delete.
- **Fix / do this:** Create the project and folder idempotently, cache their ids, and move tasks in with MoveEntities.
- **KB:** L-CDI-055

### PD-P1-163 CDI REG_MATCH and NULL handling matched PostgreSQL on edge cases
- **Date:** 2026-10-04
- **Context:** parity rules on 20 synthetic MA rows
- **Lesson:** `REG_MATCH(zip,'^[0-9]{5}(-?[0-9]{4})?$')` gave the same results as PostgreSQL `~` on a leading space, 6 digits, ZIP+4, 'O2108' and ''. `NOT year_built BETWEEN 1600 AND 2026` with IIF/ISNULL matched on NULL and on 1599, 2027, 0, -5 and 9999. Both rules matched exactly (7/20 and 4/20). Because only totals were written, two row-level errors that cancel each other out cannot be ruled out.
- **Fix / do this:** Build parity probes on synthetic edge-case rows. Add row-level output if cancelling errors matter.
- **KB:** new

### PD-P1-164 BigQuery CSV loads reject date-only TIMESTAMP values and float artifacts in NUMERIC
- **Date:** 2026-10-04
- **Context:** Loading a 50,110-row × 186-column TSV export into BigQuery
- **Lesson:** The first load failed with "too many errors" (100/100). TIMESTAMP columns rejected date-only values. NUMERIC (scale 9) rejected float artifacts such as 58.674594559562735, which affected 49,461 sample_weight values. Postgres had silently rounded the same values on COPY.
- **Fix / do this:** Append " 00:00:00" to date-only values, and round NUMERIC to the source scale (half-up, fixed-point text). Validate, then compare sums and NULL/'' counts with the source.
- **KB:** new (related L-CDI-159)

### PD-P1-165 A v2 schedule edit or rebind doesn't change the scheduler's trigger
- **Date:** 2026-10-04
- **Context:** The demo app evidence workflow and the 3-hourly landing workflow
- **Lesson:** Both schedules read Daily/1 in v2 and v3 from 09-30, yet SCHEDULER kept starting runs hourly and every 3 h under the old schedule names. Rebinding the workflows to new daily schedules read back OK (only scheduleId differed). Run 130 still fired at 08:10:01Z with scheduleName <evidence_hourly>.
- **Fix / do this:** Verify every schedule change in the activity log at the next boundary (runContextType, scheduleName, startTime). A read-back is not proof.
- **KB:** new (refines L-METHOD-040, L-IPU-061; L-CDI-195)

### PD-P1-166 endTime / endTimeUTC did not stop a stale trigger
- **Date:** 2026-10-04
- **Context:** Both old schedules ended at 08:25Z (read back OK in v2 and v3)
- **Lesson:** Runs 131 (09:10:02Z) and 132 (10:10:02Z) still started from SCHEDULER, and the landing workflow fired at 10:10Z. Ending a schedule with endTime did not stop this kind of stale trigger.
- **Fix / do this:** Don't count an end time as a stop. Watch the next two slots.
- **KB:** L-CDI-076 (does not hold here: dispute candidate)

### PD-P1-167 A v3 schedule PATCH to disabled returns V3API_007
- **Date:** 2026-10-04
- **Context:** Trying to disable the two old schedules
- **Lesson:** `PATCH /public/core/v3/schedule/<v3id>` with {"status":"disabled"} returned 400 V3API_007, and so did a full object without the read-only fields. The status stayed enabled.
- **Fix / do this:** Don't plan on a v3 disable. Unbind, `DELETE /api/v2/schedule/<id>` once nothing is bound, or park it through the UI route.
- **KB:** L-CDI-076

### PD-P1-168 Admin UI has no schedule Disable: park it by moving the start into the far future
- **Date:** 2026-10-04
- **Context:** Demo-app fix UI steps (shared-host Playwright)
- **Lesson:** The UI blocks a direct disable:
  - The row menu has only Permission, Delete and Edit, and the edit form has no status field.
  - Save stays disabled until something changes.
  - A schedule whose end time has passed cannot be saved ("Cannot schedule when no possible valid time...").

  What worked: Starts 10/04/2036, Repeat Indefinitely, a tagged description. The UI then sends `PUT /scheduler-service/api/v2/Schedules('<v3id>')` (204). Whether this kills the stale trigger was not proven.
- **Fix / do this:** Park a schedule through the UI's own save path, keep the before-JSON as the undo, and confirm in the activity log at the next slot.
- **KB:** new

### PD-P1-169 How a v3 schedule id relates to the v2 id
- **Date:** 2026-10-04
- **Context:** Reading schedules on both APIs
- **Lesson:** The v3 id is the 22-character org uuid followed by the v2 id with its 6-character org prefix removed (for example <orgUuid> + <v2 id minus its 6-char org prefix>). A v3 GET with the v2 id returns 404.
- **Fix / do this:** Derive the v3 id from the org uuid. Always read and write the *UTC time fields.
- **KB:** L-AUTH-014, L-CDI-063, L-CDI-073 (id mapping: new)

### PD-P1-170 Builder scripts re-create the old cadence
- **Date:** 2026-10-04
- **Context:** mk_evidence.py and landing_native.py (two copies each)
- **Lesson:** The builders still named the hourly and 3-hourly schedules, so re-running them would have rebound the workflows to the old cadence.
- **Fix / do this:** After any schedule change, patch every copy of the builder with exact-match edits, back them up, parse-check them and diff the copies.
- **KB:** new (related L-CDI-079)

### PD-P1-171 Schedule cutover risks: overlapping first slots and an untested rollback
- **Date:** 2026-10-04
- **Context:** New daily schedules at 00:10Z and 01:10Z
- **Lesson:** The new first slots coincided with slots of the surviving stale triggers, so the workflows could start twice in the same minute. The rollback POSTed objects without endTime, and a v2 POST that leaves out a key may keep the stored value.
- **Fix / do this:** Stop the old trigger before the new first fire, or offset the new slot. Send explicit nulls for endTime and endTimeUTC in rollbacks.
- **KB:** new

### PD-P1-172 Stopping jobs does not stop their triggers: inventory every starter and schedule, and back up the workflow before unbinding
- **Date:** 2026-11-01 / 2026-11-12
- **Context:** two address-verification workflows still firing every 45 and 30 min after the build was "turned off"; the 11-12 recommended pause of address verification until migrations finish
- **Lesson:** Both schedules were enabled with no end time. The workflows they drove lived in project `Default`, not the audited project, and a schedule had been renamed (the log says `_20min`, the schedule is now `_30min`). On 11-12 a proper pause meant: stop `the external driver script` (no cron or timer; launched by a session) and the unlocated starter of `<p>_r7_av_verify_mt`, disable `sch_<p>_address_45min`, `sch_<p>_verifier_diagnostic` and `sch_<p>_cloud_window_30min`, let in-flight runs finish, then note it on the tracker. It was not done, because it changes other sessions' work and needs the owner's word.
- **Fix / do this:** Inventory every starter and schedule before calling a lane paused. GET the workflow, log the full body as a backup, then POST the workflow with `scheduleId: null`. At cutover, search `Default` and every task detail for bound schedules.
- **KB:** L-CDI-075, L-CDI-077, L-METHOD-135

### PD-P1-173 One mapping, N lane tasks, with per-run SQL passed through an agent parameter file
- **Date:** 2026-11-01
- **Context:** m_<p>_ingest_capture (12 lanes), m_<p>_ml_capture (2 lanes) and reference capture: 870 lane starts
- **Lesson:**
  - The source query is the in-out parameter `$$SRC_SQL` (STRING, precision 262144, retention NEVER), with a harmless `WHERE 0` default.
  - Each lane task is a clone with its own `parameterFileName`.
  - The runner installs the item's one-line `$$SRC_SQL=` file into `<agent>/apps/Data_Integration_Server/data/userparameters/` over SSH, then starts the job.
  - Recreating a task after the mapping gained the parameter returned 403 `REPO_19001` twice before it saved. Long SQL defaults cause that error.
- **Fix / do this:** Keep in-out defaults short, and put the real SQL in per-lane parameter files. Clone lanes by GET mttask, strip id/frsGuid/times/owner/schedule and `parameters[].id`, POST under a new name, then MoveEntities.
- **KB:** L-CDI-285, L-CDI-022, L-METHOD-136

### PD-P1-174 A mapping task keeps its own copy of the fixed target object
- **Date:** 2026-11-01
- **Context:** Retargeting a mapping that already had lane tasks
- **Lesson:** `GET /api/v2/mttask/<id>` lists each non-parameterized target in `parameters[]` (type TARGET) with `targetObject` '<schema>/TABLE/<table>' and its connection, copied at task creation. Changing the mapping's target means updating or recreating every task. An OVERWRITE import can fail while deploying those changes.
- **Fix / do this:** Fix target objects before cloning lanes, or parameterize the target.
- **KB:** L-CDI-271

### PD-P1-175 Lossless capture SQL: row JSON, sha256 identity, chunks, streaming
- **Date:** 2026-11-01
- **Context:** build/capture_sql.py, the source of m_<p>_ingest_capture
- **Lesson:**
  - **Row mode:** `toValidUTF8(formatRowNoNewline('JSONEachRow', *))`. id = sha256 of the JSON, split into 8,000-code-point chunks by ARRAY JOIN. No GROUP BY, so it is safe on a live server.
  - **Duplicates:** exact duplicates share one record. Reconcile compares `count()` with `uniqExact(hash)`.
  - **Property-pack mode:** one record per (table, property_id) holding sorted JSONL, duplicates kept.
  - **Settings:** `output_format_json_escape_forward_slashes=0`, `max_block_size=8192`, `max_threads=4`, a memory cap, `max_execution_time=0`, `http_send_timeout=send_timeout=3600`.
- **Fix / do this:** Shard big tables by `cityHash64(property_id) % N` on a key that is never NULL. IDMC adds lineage and DQ.
- **KB:** new (related L-MIG-093, L-CDI-286)

### PD-P1-176 Bring ML files and Mongo documents through IDMC by staging them where the source can read
- **Date:** 2026-11-01
- **Context:** m_<p>_ml_capture into model_registry
- **Lesson:**
  - **Model files:** copied into ClickHouse user_files (`<p>_ml_files/<md5>.bin`) and read with `file()`. The md5 is the identity. Rows are base64 chunks, with `max_block_size=1`, `max_threads=1`.
  - **Mongo:** `mongoexport --jsonFormat=canonical --sort {_id:1}` to JSONL, stored as 1,000-character chunks per document.
  - **Proof:** `md5(base64Decode(chunks in order))` per file and sha256 per document.
  - **Untested:** whether a JDBC V2 string carries 25 MB base64 chunks.
- **Fix / do this:** Stage non-database sources as files the source engine can read. Make the hash the record id and verify by reassembling.
- **KB:** new (related L-CDI-296)

### PD-P1-177 JDBC stream failures (Premature EOF, agent disconnection) leave partial loads
- **Date:** 2026-11-01
- **Context:** Old-build failures: agent disconnection 134, Premature EOF 30, Code 202 10
- **Lesson:** A 42.65M-row load in natural order died with Premature EOF and left an uneven gap. The resume shards then left holes: parity 1 was not covered, shard 15 had no task, and three shards never got a final retry. Premature EOF often means a reader stall longer than ClickHouse's 30 s http_send_timeout.
- **Fix / do this:** Size each work item to a resumable shard listed in a manifest. Retry transport errors, and check every shard against distinct source keys.
- **KB:** L-CDI-267, L-CDI-287

### PD-P1-178 A Dynamic Mapping Task is v3 type BATCH_MAPPING, read on the pod host without /saas
- **Date:** 2026-11-01
- **Context:** idmc_capabilities probe (DMT as an ingest lever)
- **Lesson:** v3 types `DMAPPINGTASK` and `DMT` return count 0, the same as a bogus type; the real type is `BATCH_MAPPING`. `GET https://<pod>.<domain>/batch-mapping/api/v1/dynamictask/<id>` returns 200, a bogus id returns 500 CMN_001, and adding `/saas` gives 404. DMT create by POST, and whether DMT sub-jobs count toward the job cap, are untested.
- **Fix / do this:** Clone an exported BATCH_MAPPING. Measure how sub-jobs are billed before relying on DMTs to cut job counts.
- **KB:** L-CDI-289

### PD-P1-179 JDBC V2 on ClickHouse: no pushdown, partitioning only in advanced mode, no DBMI
- **Date:** 2026-11-01
- **Context:** Capability matrix for the ClickHouse-to-ClickHouse move
- **Lesson:**
  - **Pushdown:** none (`optimizationPlan NONE`).
  - **Partitioning:** advanced mode only, and Elastic was not enabled.
  - **DBMI:** JDBC V2 is not a DBMI connector.
  - **Post-SQL:** an `INSERT...SELECT` run as Post-SQL bypasses the pipeline and its lineage.
  - **Advanced taskflows:** made by API, they can't be published, and the job API rejects them (UI_13430).
- **Fix / do this:** Get parallelism from lane tasks and the DTM pool. Do heavy shaping in the source SQL. Orchestrate with linear v2 workflows (`POST /api/v2/workflow`).
- **KB:** L-CDI-070, L-CDI-069, L-CONN-030 (pushdown/partitioning: new)

### PD-P1-180 Bypass a stalling generator deploy with a direct timed build and v3 import
- **Date:** 2026-11-01
- **Context:** build/<p>_import.py
- **Lesson:** The generator's deploy path (lock plus source control) stalled. A direct compile → package → v3 import script was reliable: it prints the seconds per step and exits non-zero unless the import is SUCCESSFUL. The task is created separately, and every field is read back (for example `parameterFileName`).
- **Fix / do this:** Keep a minimal timed import path next to the generator.
- **KB:** new

### PD-P1-181 CDQ rule specs on ClickHouse through a JDBC V2 mapping, proven against SQL
- **Date:** 2026-10-29
- **Context:** `m_<p>_gold_dq` / `mt_<p>_gold_dq`
- **Lesson:** The mapping runs 8 CDQ rule specs plus 8 range checks on gold and appends one row per state per run to `<idmc_gold_db>.dq_gold_scorecard` (views `v_dq_gold_scorecard`, `v_dq_gold_latest`). The 1% sample (1,009,410 rows) ran in 90 s and matched an independent SQL check. That day, direct REST profiling of ClickHouse still hung; on 11-02 cloning a working JDBC V2 profile body fixed it.
- **Fix / do this:** Schedule the mapping daily after the existing gold DQ, and use the scorecard as an extra, independent publication gate.
- **KB:** L-DQ-117, L-DQ-128

### PD-P1-182 Collecting is not delivering: measure verified output in the table customers read
- **Date:** 2026-10-09
- **Context:** source-to-gold audit
- **Lesson:** 30 public feeds collected 1,457,869 records, but only 5 had property delivery contracts. 199,361 of 199,372 verified facts came from one recovery job; the new scheduler contributed none. Old writers updated `<legacy_db>.property_master` while serving read `<gold_db>`, so a "successful" job could leave serving unchanged. Labels such as "MLS sold" are not proof of a feed.
- **Fix / do this:** Report fetched, accepted or held, unique properties, fields filled and sale events added, each separately. Confirm values on the real read path (`v_property_current`, search, backend).
- **KB:** new

### PD-P1-183 One controlled publisher is the only gold writer, with proof re-read, intents and receipts
- **Date:** 2026-10-09
- **Context:** gold_system publisher.py / sale_publisher.py
- **Lesson:** Connectors emit evidence and proposals and never rewrite a served property. The publisher:
  1. Re-reads the exact silver proof and re-checks freshness.
  2. Takes the gold lock, then the heavy lock.
  3. Writes before-images and intents.
  4. Applies only approved changes.
  5. Verifies the values and the search index.
  6. Writes receipts.

  On restart it can tell a completed write from an unwritten intent and from a conflicting partial write. Replaying the first Florida input proposed zero writes.
- **Fix / do this:** Advance the checkpoint only after verification. Fill only by source rank (cama > crawl > listing > model), and never overwrite newer conflicting values. Roll back field by field from the receipts. A CLI run without `--apply` still records a run, so use the read-only `preview.py`.
- **KB:** L-ENV-118 (publisher protocol: new)

### PD-P1-184 Bounded batches: halve an oversized block instead of raising caps
- **Date:** 2026-10-09
- **Context:** gold-market publisher, Virginia
- **Lesson:** A 5,000-row identity block exceeded the fixed read cap. The publisher halved it to 2,500 and advanced only through those rows. Queries stay at 2 threads, 2 GB and 90 s. Exhausted states log a heartbeat instead of taking the next state's turn.
- **Fix / do this:** Halve without skipping the remainder, and keep the limits as they are.
- **KB:** new

## Profiling & data quality

### PD-P1-185 Profile runs and CDGC jobs are not in the v2 activity log: count them where they run
- **Date:** 2026-10-03
- **Context:** The property-app job-budget guard (M1 / budget guard, rule 6)
- **Lesson:** `GET /api/v2/activity/activityLog` returned only MTT, WORKFLOW and MAPPING rows (3,700 rows: MTT 3,491 / WORKFLOW 180 / MAPPING 29) and no PROFILE rows, although the 17:40Z s_profiling run on the prod DB host did happen. So "0 property-app jobs" was only what the log could see. CDGC scans and DQ-capability runs appear only in the data360 observable jobs list. Rule-spec previews do show up, as `PreviewMapping_RULE_SPECIFICATION` MAPPING rows. MCP/CLAIRE calls appear only in your own log.
- **Fix / do this:** Keep a ledger with separate sources: DI jobs and previews from activityLog by object name; profile runs from the dqprofile service (`GET /profile/<id>` lastRunKey and runDetail) or jls-di JobLogEntries with `assetType eq 'PROFILE'`; CDGC jobs from `data360/observable/api/v1/jobs` filtered by catalog-source id; MCP/CLAIRE calls from your own log. Otherwise the counts will be badly low.
- **KB:** L-IPU-055, L-DQ-106, L-DQ-159

### PD-P1-186 lastRunKey moves only when a run finishes: probe lastRunKey+1 to see runs in flight
- **Date:** 2026-10-04
- **Context:** guard profile reader, which reported "<profile_ID> never ran"
- **Lesson:** lastRunKey advances only when a run completes. A RUNNING / QUEUED / stuck run sits at `runDetail/<profileId>/<lastRunKey+1>` (run 1 when lastRunKey is null): `GET runDetail/<id>/1` returned 200 with status RUNNING (started 17:41:26Z, 181 columns, ALL_ROWS) while the profile still had no lastRunKey. A loop over 1..lastRunKey never sees such a run, which made the stuck run that thrashed the host invisible to the guard. A 404 with PROFILE_SVC_00005 at that key means no run there. The guard probes up to 3 keys.
- **Fix / do this:** Keep the job id returned by `POST /profile/<id>/execute`. Read runDetail per key up to lastRunKey and probe lastRunKey+1.. (or JobLogEntries) for in-flight runs, and count a queued run with no startTime at probe time. Escalate a run stuck in RUNNING, because it can block editing or recreating the profile.
- **KB:** L-DQ-150, L-DQ-096, L-DQ-106

### PD-P1-187 A run-history row can stay RUNNING after its job FAILED: decide "ended" from GET /job/<jobId> with a terminal-status allowlist
- **Date:** 2026-10-04
- **Context:** <profile_ID> run 1, job <jobId>, stopped 10-03 18:39Z, after which the agent shut down; budget guard orphan patch (v1.2 denylist versus v1.3 allowlist)
- **Lesson:** `GET /runDetail/<profileId>/1` stayed RUNNING with endTime null from 10-03 17:41Z for more than 15 h, while `GET /job/<jobId>` returned FAILED "User requested stop." (18:39:19Z), runningJobs was [] and the job log said FAILED. Step errors included "DTM process killed ... agent is shutdown" and "Agent ... not active". The agent shut down before the row was finalized; the UI run list hides the orphan row, and no route edits it. The first guard patch (v1.2) treated everything outside RUNNING/QUEUED/STOPPING as ended, which turned RESUMING, SUSPENDED, PAUSED, WAITING, ABORTING, SCHEDULED and CANCEL_PENDING into "not in flight", and its 9/9 tests never covered an unknown status. The UI's own map: INITIALIZED, QUEUED, RUNNING and STOPPING are active; SUCCESS, WARNING, FAILED, COMPLETED and STOPPED are ended.
- **Fix / do this:** Treat a run as ended only when `GET <pod>-dqprofile/profiling-service/api/v1/job/<jobId>` answers 200 with a status in JOB_TERMINAL = COMPLETED SUCCESS WARNING FAILED STOPPED CANCELLED ABORTED. Anything else (an unknown status, no jobId, a failed read) counts as in flight and blocking; test unknown statuses explicitly. Count an orphan row once at its weight. To clear the row, delete or recreate the profile (needs a GO), restoring from the v3 export.
- **KB:** L-DQ-106, L-DQ-150

### PD-P1-188 Stop a profiling job headless with POST profiling-service/api/v1/job/stop; the run-list route needs the UI's body
- **Date:** 2026-10-04
- **Context:** guard STUCK warning (runs older than 2 h); looking for a way to cancel a stuck profile (routes read from the UI bundle)
- **Lesson:** Stop is `POST <pod>-dqprofile/profiling-service/api/v1/job/stop` with {jobId, jobType:"PROFILING_PC"}. The UI offers it only for QUEUED, RUNNING and INITIALIZED jobs; a FAILED job offers only Resume. The run list is `POST /runDetail/<id>/filter?pageNo=0&size=N&sortBy=runKey&sortOrder=DESC` with body {"purgeQueryType":"EXCEPT_LAST_N_RUNS","exceptLastNRun":-1}; any other body gives 400 PROFILE_SVC_00093. The earlier claim "the REST API has no cancel" was wrong.
- **Fix / do this:** When a run is stuck for more than 2 h, print the job status and this stop route for a person to act on. Don't replay stop on a FAILED job while the agent is off, because it can stick in STOPPING. Keep the per-key runDetail reads, since the filter hides orphan rows.
- **KB:** L-DQ-106, L-DQ-019

### PD-P1-189 POST runDetail/<id>/filter hides orphan rows: keep the per-key reads
- **Date:** 2026-10-04
- **Context:** guard run-history reader
- **Lesson:** The filter route needs the UI's purge-dialog body and hides orphan rows, so the guard reads `GET /runDetail/<profileId>/<runKey>` one key at a time (startTime ms, status, rowsProcessed, numberOfColumns, numberOfRules, jobId) and caches the runs it has seen.
- **Fix / do this:** Read run history per key, not through the filter route.
- **KB:** new

### PD-P1-190 The dqprofile host takes IDS-SESSION-ID, and the profile list may come in several shapes
- **Date:** 2026-10-04
- **Context:** guard and gate profile reads
- **Lesson:** The host is derived from serverUrl (`https://<pod>-dqprofile.<domain>/profiling-service/api/v1`, for example <pod>-dqprofile) and takes the v2 session in IDS-SESSION-ID. `GET /profile?limit=200` returned either a list or an object with profiles/content/items, so the readers accept every shape and treat any other body as a read error.
- **Fix / do this:** Derive the pod host from serverUrl, use a large limit, and validate the body shape.
- **KB:** L-DQ-155, L-AUTH-025

### PD-P1-191 Data profiles cannot be moved (FRS_108): recreate them in the target project after a v3 backup
- **Date:** 2026-10-03
- **Context:** <profile_ID> / <profile_MA> sitting in the demo app's own folder
- **Lesson:** The two profiles had been created in the live demo's folder and could not be moved (FRS_108). They were recreated in the app's Explore project, with a v3 package backup taken first.
- **Fix / do this:** Create profiles in the right project from the start. To relocate one, take a v3 backup and recreate it. Note that the KB disputes whether FRS MoveEntities works.
- **KB:** L-DQ-029, L-DQ-124
- **Status:** superseded by PD-P1-133 (on 11-02 FRS MoveEntities moved profiles too; FRS_108 remained only on 3 orphan profile shells)

### PD-P1-192 IDMC cannot sample for you on most connectors: build the sample upstream and profile All Rows
- **Date:** 2026-10-03
- **Context:** sampling spec: native sampling options per connector (CDP October 2025 guide, pp. 72-73)
- **Lesson:**
  - BigQuery V2, Flat File, S3, ADLS and GCS offer All Rows only.
  - JDBC V2, PostgreSQL, Oracle, SQL Server and Salesforce offer All Rows and First N.
  - Random N exists only on Redshift V2, Synapse and Snowflake.

  "First N" on Postgres reads physical order, which is load order (one town or county).
- **Fix / do this:** Materialize a deterministic, stratified sample table with open-source tools, then profile it with Run on = All rows.
- **KB:** L-DQ-099, L-DQ-102

### PD-P1-193 Profile fan-out math: above 100M rows Data Profiling splits one subtask per column, so refuse runs above 100k rows or about 50-60 columns
- **Date:** 2026-10-03
- **Context:** property_master (109-120M rows, 181-191 columns); profile-shape tripwire T4
- **Lesson:** Above 100,000,000 rows (the Min Rows for Split per Column default), Data Profiling creates one subtask per column, about 184 subtasks (181+ jobs) per run for the universe, against about 7 for a sample. At or below that it creates one subtask per 50 columns+rules, plus 3 fixed subtasks. Value-frequency pairs default to 500 (maximum 10,000), and memory is capped at 512 MB per mapping.
- **Fix / do this:** Profile samples of 100k rows or fewer. Refuse in the guard any run with more than 100,000 rows, more than 50-60 columns, more than 60 rules or more than 8 subtasks. On small agents, set profileAdvProps maxColumnsPerMapping to 25.
- **KB:** L-DQ-098, L-DQ-103

### PD-P1-194 Profile settings for a sample table that keep jobs low and CLAIRE insights valid
- **Date:** 2026-10-03
- **Context:** s1 profile configuration (SAMPLING_SPEC §7)
- **Lesson:** The settings: one source table per profile, built and sampled upstream; All rows, because the table itself is the sample and First N follows load order; CLAIRE capabilities on; no filter, never changed between runs (Top Pattern Stability needs the same filter); Drilldown off on scheduled runs, because drilldown and queries run as extra jobs; Max Columns per Mapping 50; Max Memory per Mapping 512 MB. Value frequencies default to 500 pairs (max 10,000); MA uses 2,000 because zip and city each have more than 500 values. Keep rule occurrences at 60 or fewer (vendor max 200), because each rule output also counts toward the 50-column split. No IDMC schedule: a controller calls `POST /profile/<id>/execute` after the load and quota gates.
- **Fix / do this:** Start from these settings when you create a profile over REST by cloning a working profile body.
- **KB:** L-DQ-032, L-DQ-098, L-DQ-102, L-DQ-103

### PD-P1-195 CLAIRE profile Insights: the headless read, a stable sample, and the run history each kind needs
- **Date:** 2026-10-03
- **Context:** PRN panel design; capturing CLAIRE output for the rule registry
- **Lesson:** Insights are read at `GET <pod>-dqprofile/metric-store/api/v1/odata/Profiles('<uuid>')/Insights`. Completeness Variation and Distinct Variation use the truncated mean of the last 5 runs and need at least 1 prior run. Distribution Shift needs 4 or more runs. MinMax Variance ignores sources under 1,000 rows. Top Pattern Stability needs the same filter on both runs. A sample that churns between refreshes makes these insights measure the sampling, not the data. Approving an Insight creates `rs_<col>_<insightType>_<n>`, but no REST approve route is known.
- **Fix / do this:** Keep sample membership stable across refreshes (a stable PRN keeps the rows the same) and run the same sample profile 2-4 times on different days. Treat Insights as advisory steward text, not registry rules.
- **KB:** L-DQ-019 (read route); the run-history needs are new

### PD-P1-196 Stage and profile types: avoid int4 and char(n) (PROFILE_MDL_00006), and profile the CDE columns through a casting view
- **Date:** 2026-10-03
- **Context:** stage DDL for profiling; the 181-column property_master stage
- **Lesson:** int4 and char(n) columns give PROFILE_MDL_00006, and json, enum and array columns are skipped. The stage used varchar(n) with lengths from name rules (2 state, 16 zip/fips, 64 ids, 255 address, 1000 joined), giving NSTRING; numeric(p,0) for integers and numeric(10,7) / (28,2) / (28,6) for floats (NaN/Inf to NULL), giving DECIMAL; and timestamp loaded from ISO text, giving TOOLKIT_DATETIME. double precision, int8 and date were avoided as untested. Overlong values are never truncated: the run stops and the column is widened, because a changed precision means a profile field update.
- **Fix / do this:** Use varchar/numeric/timestamp for stage tables that IDMC will profile, and profile 20-40 CDE columns through a casting view.
- **KB:** L-DQ-022

### PD-P1-197 Column precision limits and the UI pre-selection
- **Date:** 2026-10-03
- **Context:** Data Profiling field selection
- **Lesson:** Strings may be 0-4000 characters (the UI pre-selects only ≤ 150) and numerics ≤ 38 digits (the UI pre-selects ≤ 15). Value frequencies are truncated above 255 characters. The REST builder lists fields explicitly, so the UI pre-selection does not apply, but tight varchars keep DTM row buffers small.
- **Fix / do this:** List profileable fields explicitly over REST (columnKey from 10001) and leave out the sampling-metadata columns.
- **KB:** new

### PD-P1-198 Read profile results from metric-store OData Columns and Insights
- **Date:** 2026-10-03
- **Context:** CLAIRE capture into claire_rule_recs
- **Lesson:** Results are read from metric-store OData `Profiles('<id>')/Columns` and `/Insights`, and CLAIRE rules through `POST profiling-service/Configuration/autoAssignRules`. The 18 CLAIRE-sourced recommendations from <profile_MA> insights were captured verbatim as `proposed`.
- **Fix / do this:** Treat Insights as advisory text until an approve route exists. Store them verbatim with their evidence.
- **KB:** L-DQ-151

### PD-P1-199 CLAIRE automatic rule association (autoAssignRules) needs a licence, a bundle project and an agent config file
- **Date:** 2026-10-03
- **Context:** sampling spec §7; found `POST profiling-service/Configuration/autoAssignRules`
- **Lesson:** It matches bundle rules to columns by name, and it needs three things: the DataQualityClaireRule licence; a `CloudDataQuality_Bundles` project holding the copied bundle; and `<agent>/apps/Data_Integration_Server/data/profiling/AutoRuleAssignmentConfig/<connection_type>AutoAssignRulesConfig.json` (or the Default file). Its default connection types are Oracle, Flat File, ODBC and S3 V2, so Postgres and BigQuery need `PostgreSQLAutoAssignRulesConfig.json` or `DefaultAutoAssignRulesConfig.json`. No agent restart is needed. The request body is undocumented.
- **Fix / do this:** Check the licence and the bundle project read-only first, and put the config file on the agent (only the shared agent) before you expect auto-assigned rules. Keep stage column names identical to gold so the rules line up. It is lower value than Insights or CLAIRE GPT.
- **KB:** new

### PD-P1-200 Do not toggle the org-wide "Disable Data Value Storage" in a shared org: mask upstream instead
- **Date:** 2026-10-03
- **Context:** privacy for profiles
- **Lesson:** The switch applies to the whole org, so it would also change the live demo. Hashing and exclusion before staging already cover privacy.
- **Fix / do this:** Mask PII upstream rather than changing org-wide storage switches.
- **KB:** L-DQ-157

### PD-P1-201 Profiling copies values to Informatica's cloud metric store: mask and exclude PII and licensed fields before staging
- **Date:** 2026-10-03
- **Context:** PII register posture; a sample that included MLS and listing fields
- **Lesson:** A CDP profile, and a CDGC scan with profiling, store value frequencies, patterns and top values in IDMC's cloud metric store, and the same goes for CLAIRE and DQ-agent uploads. Masking after staging is too late for any profile that already ran. The stage template had been exporting `listing_agent` and `brokerage` raw, and two profiles ran on them (fill probably 0%, but unmeasured for MA). MLS and listing data may carry licensing limits as well as privacy ones.
- **Fix / do this:** Mask in the export (in ClickHouse) before any row leaves the DB host. Profile an explicit column allowlist: drop MLS/listing columns and JSON blobs, and keyed-hash agent and brokerage names. Run a leak-gate SQL before every profile.
- **KB:** L-DQ-157

### PD-P1-202 Run a pre-profile leak gate as read-only SQL on the stage
- **Date:** 2026-10-03
- **Context:** PII leak gate G1-G3, dq candidate cand_pu_no_raw_pii_in_stage
- **Lesson:** G1: no column names in information_schema matching owner/mail/grantor/grantee/care_of/taxpayer/buyer/seller/email/phone (expect 0). G2: masked columns hold only `^[0-9a-f]{64}$` hashes. G3: measure how many rows have non-empty agent/brokerage values. The readiness gate also checks that the shared host sample has zero raw name columns.
- **Fix / do this:** If the gate fails, do not run the profile.
- **KB:** new

### PD-P1-203 Translate IDMC rules into SQL/dbt deterministically: anything UNMAPPED or unparsed goes to needs_review
- **Date:** 2026-10-03
- **Context:** The infa_rule_to_sql.py translator prototype
- **Lesson:** The prototype could not tokenize negative literals (`>= -180` raised ValueError). Unmapped functions (IS_NUMBER, TO_INTEGER, IS_DATE, SUBSTR, IIF, DECODE) rendered as `/* UNMAPPED */ NULL` but were still marked translated; that SQL is valid and fails every row. It also mapped only inputs[0], and the 10 basic-mode specs were unsupported. It was proven on 6/6 advanced demo-app specs; the property app coverage was untested. Still to add: unary minus, arithmetic, date/number functions, and a basic-mode mapper plus a dictionary export. Parity tests must pin the semantics of REG_MATCH anchoring, IS_SPACES(''), IN case-sensitivity, and ClickHouse '' vs NULL.
- **Fix / do this:** Make any UNMAPPED marker or parse error set status `needs_review`, never `translated`. Claim only what was tested: check each translation against the spec's own testData arrays and prove it by a 0-row parity diff on the same sample.
- **KB:** L-DQ-104 (read spec logic); translator gaps = new

### PD-P1-204 Translation parity and representativeness are two separate alarms
- **Date:** 2026-10-03
- **Context:** rules2dbt spec §7
- **Lesson:** Parity runs the dbt rule on the exact sample IDMC profiled (unweighted) and expects 0 rows of difference. A mismatch sets PARITY_MISMATCH and keeps the rule at `accepted`. Representativeness compares the full-estate (census) pass rate with the weighted sample estimate, and a failure means restage the sample, not repair the data.
- **Fix / do this:** Keep separate status values and repair lanes for the two (translator vs sampling).
- **KB:** L-CDI-138

### PD-P1-205 Drift alarms need multiple-testing control, design weights, and an exact binomial for rare failures
- **Date:** 2026-10-03
- **Context:** drift alarm comparing the IDMC sample score with the dbt pass rate
- **Lesson:** With about 11 rules x 51 states = 561 comparisons, 95% intervals would give about 28-50 false alarms per run, and IDMC's scores are unweighted over a stratified, oversampled sample. So DRIFT fires at z = 3.29 in one run, or z = 1.96 in two consecutive runs. When the expected failures λ = n_eff·(1−p) < 10, use the exact binomial (Clopper-Pearson) test instead. Worked example: MA latlon (16 fails in 2.52M) with n_eff ≈ 35k is OK at 0-3 sample failures and DRIFT at 4 or more; the normal rule would flag at 2. STALE_SAMPLE is checked first: more than 5% changed rows since staging, or a sample older than 30 days.
- **Fix / do this:** Use Wilson intervals with Kish effective n when λ ≥ 10 and exact tails below that (or Benjamini-Hochberg), check staleness before drift, and show the weighted estimate, labelled as such.
- **KB:** new

### PD-P1-206 IDMC's profile statistics are unweighted: report bias, take KPIs from the full-estate run
- **Date:** 2026-10-03
- **Context:** stratified sample weights
- **Lesson:** Floor-boosted strata are over-represented in IDMC's numbers. Weights 1/rate are stored per row, so dbt can compute weighted (Hájek) estimates, and the Kish design effect is reported per state. IDMC is used for understanding and rule discovery. The KPI numbers come from dbt over the full estate.
- **Fix / do this:** Never quote an IDMC sample percentage as the estate KPI.
- **KB:** new

### PD-P1-207 Interim rule acceptance until parity is readable: a Claude steward reviews, never the owner
- **Date:** 2026-10-03
- **Context:** accept policy (b)
- **Lesson:** A rule is accepted when three things hold: it translates deterministically; its sample pass rate is ≥ 90% or it maps to a known repair lane; and it is not already covered by gold_dq (linked via `covered_by`). Every acceptance is reversible with "reverse KEY". The first acceptance wave rides the batched OK.
- **Fix / do this:** Write explicit accept criteria and keep acceptance reversible.
- **KB:** new

### PD-P1-208 CLAIRE rule generation and publish/accept are UI-only: run them in a Playwright harness with a publish guard
- **Date:** 2026-10-03
- **Context:** CLAIRE rules (decision 17); cards C3/C8 had been marked fully headless
- **Lesson:** CLAIRE GPT chat has no public REST API, and generate-and-publish has been proven only through the UI. A stray free-text reply can publish. The MCP rule_generation tool only drafts, and generation leaves DICTIONARY objects in CDQ even before anything is published. The plan: generation runs first, from a policy file built from the glossary's rule_hooks, then recommend/accept, naming the columns. Both steps run through the shared host Playwright harness, which stops at Publish/Accept prompts.
- **Fix / do this:** Mark these steps as workarounds, use a publish guard, name the columns explicitly, and count their browser logins against the lockout budget. After every batch, audit the RULE_SPECIFICATION and DICTIONARY objects over v3, and move CLAIRE-generated specs out of the `CLAIRE/CLAIRE` folder by v3 export/import (or document them).
- **KB:** L-UI-030, L-DQ-010, L-DQ-079, L-MCP-079, L-MCP-096, L-MCP-097, L-MCP-099

### PD-P1-209 CLAIRE and the DQ-agent MCP tools can write and start jobs: classify them by side effect, not by name
- **Date:** 2026-10-03
- **Context:** MCP/CLAIRE write tools; the CLAIRE budget (≤20/day)
- **Lesson:** The DQ agent's data_quality_rule_recommendation "recommends and applies" the rules it recommends, and cleansing uploads files, so both are writes. CLAIRE GPT can itself "run data profiling" or "run data quality", which starts jobs outside the controller. The egress limits that held were ≤2,000 rows × 50 columns × 1 MB and ≤5 uploads a day. Recommendation was treated as a write that needs the batched OK, and used on the sample only.
- **Fix / do this:** Classify MCP tools by their side effects, not their names. Keep exploration prompts free of run and publish wording, log any run CLAIRE starts, and treat recommendation and generation as writes that need an OK.
- **KB:** L-MCP-120, L-DQ-071, L-DQ-081

### PD-P1-210 After any rule accept, check that no DQ_Capability schedule references the guest's rule occurrences
- **Date:** 2026-10-03
- **Context:** CDGC catalog source + RuleInstances
- **Lesson:** Catalog Data Quality can create org schedules (DQ_Capability_Schedule_*) that would run the guest's rules unattended and burn the cap.
- **Fix / do this:** Keep DQ automation off on the source, and after each accept list the schedules.
- **KB:** L-CDGC-152

### PD-P1-211 Limits for CLAIRE GPT and DQ-agent uploads
- **Date:** 2026-10-03
- **Context:** plan v3 §3 other limits
- **Lesson:** The limits used: CLAIRE GPT ≤ 20 prompts/day; DQ-agent uploads ≤ 2,000 masked rows x 50 columns x 1 MB, logged as egress; CLAIRE GPT file profiling ≤ 25 MB and ≤ 10,000 rows x 50 columns. CLAIRE design-time use was free until 2027-01-31, but profiling runs still bill.
- **Fix / do this:** Keep an egress ledger for uploads and cap prompts per day.
- **KB:** L-MCP-120, L-DQ-081, L-MCP-116

### PD-P1-212 Flow the scale results back into IDMC as a catalogued table, because lineage writes and DQ-score import don't exist
- **Date:** 2026-10-03
- **Context:** flow-back dq_scale_summary
- **Lesson:** Lineage writes are a silent no-op and there is no DQ-score import API. So the table `dq_scale_summary` (rule x estate x state pass %) goes into the shared host sample DB and is catalogued with the sample, and IDMC shows the scale pass rate next to its own sample score.
- **Fix / do this:** Publish external results as a table in a cataloged source.
- **KB:** L-DQ-050

### PD-P1-213 A profile's SQL override must stay under 4,000 characters: split wide tables at 3,900 characters or 100 columns
- **Date:** 2026-11-04
- **Context:** 17 profiles `p_<p>_prof5_<table>[_g1..g7]` on the 5 production tables (property_master 588 / 576 columns)
- **Lesson:** The override is stored in a 4,000-character column, and a longer one fails the create with 500 PROFILE_SVC_00004. The profiler groups columns until `SELECT ... + tail` would pass 3,900 characters or 100 columns (`runtimeOptions.profileAdvProps.maxColumnsPerMapping` = 100), which gives 7 profiles each for gold and staging.
- **Fix / do this:** Generate overrides in code and split them by length and column count before create. Skip a table whose single column already overflows. Keep profile names to 90 characters or fewer (use a hash suffix).
- **KB:** L-DQ-133, L-DQ-103

### PD-P1-214 A JDBC V2 ClickHouse profile sees only the connection's schema, real table and column names, and native types
- **Date:** 2026-11-04 / 2026-11-05
- **Context:** profiling every ClickHouse table on both servers (chprof.py)
- **Lesson:** Before a profile reads any rows, three checks apply:
  - **Schema:** `sourcePath '<connection schema>/TABLE'` resolves only the connection's schema. Any other database fails with "[<db>] was not found", even when the SQL override names it; the override names the real db.table.
  - **Names:** `source.name` must be a real table ("Object(s) [<t>] not found") and every field a real column ("Invalid operation field name in CCI Metadata Client"), so aliases must equal real column names. Pointing at an anchor table while the override reads another table fails.
  - **Types:** recognised types must come back native. DateTime cast to text gives "String cannot be cast to java.sql.Timestamp", Int64 cast to text gives "should be a of type [java.lang.Number]", and a bare Date gives "LocalDate cannot be cast to java.sql.Timestamp".

  The job itself often shows only "Data too long for column error_msg". The real error is in the agent's Data_Integration_Server tomcat log (CCIMetadataResource.createDataOperation).
- **Fix / do this:**
  - Pass through bare: Int8-32/Float/Decimal as DOUBLE, Int64+ as BIGINT, DateTime/DateTime64 native (timestamp(29,9)); String, FixedString, UUID, Enum and IPv4/6 as NSTRING varchar(1000).
  - Convert: Date with `toDateTime(col)` (TOOLKIT_DATETIME), Date32 with `toDateTime64(col,0)`, Bool with `toUInt8` (as DOUBLE).
  - Stringify only Array, Map, Tuple and other types with `left(toString(col),1000)`. Skip AggregateFunction columns.
  - Build the fields from system.columns with this map, and keep every alias equal to the real column name. The override may still sample (PREWHERE / LIMIT / SETTINGS).
- **KB:** L-DQ-134 (supersedes the 10-29 view in L-CONN-089 / L-DQ-119), L-DQ-128
- **Status:** overturns PD-P1-089 (the 10-03 JDBC_V2_ERROR_205 verdict and the Postgres-stage workaround)

### PD-P1-215 Create profiles over REST by cloning a body that has already run on the same connection, and keep a name -> id ledger
- **Date:** 2026-11-04
- **Context:** 315 legacy + 15 work-table profiles created headless (chprof create, profiles.py)
- **Lesson:** Start from a JDBC V2 profile body that already ran on the same connection.
  - Remove `id`, `profileKey`, `version`, `frsId`, `createdBy*`, `updatedBy*`, `createTime`, `updateTime`, `lastRunKey`, `orgId`, `runtimeOptions.id` and `source.id`.
  - Set `name`, `connectionId`, `frsProjectId`, `frsFolderId`, `source.properties = {dataSourceType: TOOLKIT_CCI, sourcePath: '<db>/TABLE'}`, `advancedOptions["SQL Override"]`, `fields`, and one `profileableFields` entry per field (appliedBy USER, fieldType DATASOURCEFIELD, columnKey 10001+i).
  - The description (max 1,000 chars) records the sample, the PII exclusions and "no copy tables".

  POST `<profiling base>/profile` does not always return the id, and the list GET ignores offset.
- **Fix / do this:** Keep one known-good template body per connector and generate every other profile from it. If the id is missing, find the profile by name before creating anything else, and stop if it can't be found. Record name → id in `chprof_created_ids.json`, use a large list limit, and log in again every 25 creates or 50 reads.
- **KB:** L-DQ-128, L-DQ-155

### PD-P1-216 Bind rule specs to profiles headless inside the profile body with a full PUT, and keep the before-bodies
- **Date:** 2026-11-02 / 2026-11-04
- **Context:** 53 bindings on 4 profiles (11-02); 218 checks on 17 profiles (11-04, profiles.py bind)
- **Lesson:** The body needs one `source.rules` block per spec (name, frsId, outFields Output string(100)). Each column binding is a MAPPLETFIELD with `ruleType RULE_SPECIFICATION`, a fresh `assignmentIdentifier` (uuid4 hex), `inputFieldMappings` and `outputFieldMappings` with columnKey 40000+n. Delete the old MAPPLETFIELDs before rebinding. The body is saved with a full PUT and read back. Before-bodies go to `backup/before_<name>.json`, so undo = PUT them back. The plan capped each profile at about 200 rule occurrences.
- **Fix / do this:** Back up the body once, PUT the full body, read it back and count the MAPPLETFIELDs and rules, then run. Keep the binding plan in a file (`bind_plan.py`).
- **KB:** L-DQ-023, L-DQ-088 (superseded: binding is not UI-only)

### PD-P1-217 Read profile and rule results from the metric-store OData, not from the UI
- **Date:** 2026-11-02 / 2026-11-04
- **Context:** `idmc_rule_results.py`, `ms_read.py`, chprof read
- **Lesson:** The profile list is `GET {profiling}/profile?limit=200`, and `GET /profile/{id}` gives `lastRunKey`. Read `https://<pod>-dqprofile.<domain>/metric-store/api/v1/odata/Profiles('<id>')/Columns?$top=200&$skip=n`, paging until fewer than 200 come back, and `/Insights?$top=500`. Rule outputs are the columns with columnKey ≥ 40000, and their VALID/INVALID counts per profile run are in the value frequencies. After a re-run, values from earlier runs also come back. Scores on 11-02: property 80.1, ml 24.5, sources 90.1, dictionary 93.8.
- **Fix / do this:** Read the output column's ValueFrequencies for the run you executed: use the highest runKey, and keep only value entries whose totalRows equals the column's current totalRows. Retry metric-store GETs up to 3 times.
- **KB:** L-DQ-123, L-DQ-151, L-DQ-155
- **Status:** overturns PD-P1-291 (exact per-rule counts are readable from the metric store)

### PD-P1-218 Cross-check IDMC rule scores with independent SQL on the same fixed sample
- **Date:** 2026-11-04
- **Context:** proof of the 218 checks (crosscheck.sql)
- **Lesson:** 10/10 gold pass rates recomputed in ClickHouse SQL on the same `cityHash64(property_id) % 64 = 0` FINAL sample matched IDMC to 0.01 point. 4 staging checks matched only within 0.2 point, because the table kept receiving rows between the two reads. The 10-29 gold DQ mapping matched ClickHouse in 866 of 867 state x check cells.
- **Fix / do this:** Profile a deterministic sample that cannot move between reads (or snapshot it), recompute a few rules in SQL with the identical predicate, and explain every mismatch.
- **KB:** L-DQ-147

### PD-P1-219 Rule specs have no create verb (405): clone a same-type template through a v3 migration package, two attempts at most
- **Date:** 2026-10-29 / 2026-11-04
- **Context:** av_rs_build.py (`rs_<p>_*`) and <p>_rs_build.py (40 new `rs_<p>_*` rule specifications)
- **Lesson:** Each spec is built from a same-type template (`email_not_null_and_not_empty_check`):
  1. Export the template read-only.
  2. Set a fresh 22-character GUID, name, description, DIMENSION, input field type and advanced script.
  3. Give it fresh rulebuilder ids (`'U:'+base64url(UUIDv1)`, 22 characters), with references following.
  4. Re-hash with SHA-256. The exportPackage.chksum keys use Java-properties escaping, so a space is written `\ `.
  5. Upload multipart (`checksumValid` must be true), then import with REUSE ("Project: Reuse existing object; RULE_SPECIFICATION: Create object").

  All 40 `rs_<p>_*` specs imported on the first attempt.
- **Fix / do this:**
  - Build one package per missing spec. Allow at most 2 import attempts per spec and stop at the first spec that fails twice; no blind retries. Lint identifiers, quotes and logic offline before import.
  - Read back via FRS `Documents('<id>')?$expand=nativeData`, PATCH the description if needed, and verify with `extensionPoint getDescription`.
  - Imports drop tags, so re-tag with TagObjects and read the tag back.
  - Run no previews, runs or schedules, and use one shared login.
- **KB:** L-DQ-010, L-DQ-094, L-DQ-109, L-CDI-030, L-MIG-008, L-MIG-016

### PD-P1-220 Read every new rule spec back: script, input, dimension, description
- **Date:** 2026-11-04
- **Context:** Rule spec build verification
- **Lesson:** After import, an FRS read-back checked the script, input port, DIMENSION and description of all 40 specs. All were OK with documentState VALID. The description is PATCHed when it is wrong.
- **Fix / do this:** Verify each created asset field by field, and store the check results in the build state.
- **KB:** L-DQ-094, L-DQ-109, L-METHOD-030

### PD-P1-221 Rule-spec design that scores raw and gold fairly: validity rules pass blanks, and one "value present" rule judges emptiness
- **Date:** 2026-11-04
- **Context:** 60 rule specs / 218 checks on raw (staging) and gold (the pattern of an earlier build)
- **Lesson:**
  - Every rule answers VALID or INVALID. Format, range and list rules answer VALID for an empty value; required fields carry `rs_<p>_not_blank`, `rs_<p>_value_present` or `rs_<p>_json_present`. This keeps raw and gold comparable and stops one missing value from failing many rules.
  - Closed lists come from the project's `data_dictionary` enum_value entries.
  - The same specs bind to staging (raw) and gold.
  - Hard rules are held to 99% on served rows; completeness of optional facts is reported, not gated.
  - Existing specs from other folders are reused, not copied (8 `rs_<p>_*`).
- **Fix / do this:** Keep completeness rules separate from validity rules in every rule set. Bind one spec set to raw and gold and publish a raw-vs-gold table.
- **KB:** L-DQ-154, L-DQ-140

### PD-P1-222 Closed lists come from the data dictionary, and a list rule that fails massively often means the dictionary is incomplete
- **Date:** 2026-11-04
- **Context:** list rules (record kind, stage, status, entity level, ownership form, ...), including `rs_<p>_entity_resolution` and `rs_<p>_zip5`
- **Lesson:** Lists were taken from the `enum_value` entries of `<target_db>.data_dictionary`, so the dictionary is the reference and an unlisted value fails (case-sensitive). This showed that the `entity_resolution_status` values `provisional_parcel`, `provisional_address`, `source_property_id` and `matched_*` were missing from the dictionary (fail 50.5% of gold, 37.4% of staging). Separately, `av_postal_code` held ZIP+4 text on 51.5% of gold rows, even though `av_zip4` already held the +4.
- **Fix / do this:** Generate list rules from the dictionary, not from observed values. Before blaming the data, check whether the dictionary is incomplete: add or map the missing values, and fix whichever side is wrong.
- **KB:** L-DQ-153, L-DQ-122 (related)

### PD-P1-223 Bind the same rules to raw and gold to show what mastering changed
- **Date:** 2026-11-04
- **Context:** property_master_staging vs property_master
- **Lesson:** Same rule, same column. Better in gold: state 93.4 -> 100 %, coordinates 99.8 -> 100 %, source rights 58.7 -> 73.2 %. Worse in gold, because of the held provisional rows: identity 62.6 -> 49.5 %, lineage 51.5 -> 23.1 %, payload hash 95.9 -> 0 %, av_postal_code 93.8 -> 48.4 %.
- **Fix / do this:** Report raw vs gold per rule. A drop in gold points at the mastering step.
- **KB:** L-DQ-154

### PD-P1-224 Cross-field and cross-table rules cannot run inside a profile
- **Date:** 2026-11-04
- **Context:** checks such as "a unit has a parent building", "the source id exists in sources", "assessed = building + land", "one row per property"
- **Lesson:** A profile binds a one-input rule to one column. Rules that need two columns or another table cannot be bound; they belong in a scoring mapping (the "score raw, clean and gold" pattern from an earlier build), which also writes `dq_score` back.
- **Fix / do this:** Split the rule catalog into profile rules and scoring-mapping rules up front.
- **KB:** new (related L-DQ-117)

### PD-P1-225 "passed" on every row with no dq_score is a stamp: the pipeline's own proof columns measured nothing
- **Date:** 2026-11-02 / 2026-11-04
- **Context:** property_master gold, check P-K05; IDMC findings on the target project gold and staging
- **Lesson:**
  - `dq_status = 'passed'` was set on all 101,369,803 gold rows while `dq_score` was empty on all of them. That one check cost 3.28 points and made "rows with no hard failure" 0%.
  - `record_payload_sha256` on 100% of gold rows was the SHA-256 of an empty string (`e3b0c442...b855`).
  - `idmc_mapping_id` / `idmc_task_id` on 76.9% of gold rows named `native:...` SQL steps.
  - 72.1% of dictionary rows carried a `<org>17PENDING00000` placeholder.
- **Fix / do this:** Compute `dq_score` / `dq_issue_codes` from the rule specs in the mastering mapping, or set `dq_status` only when a score exists, and bind a rule to the score column itself. Make the sha256 rule reject the empty-string hash, use an IDMC-object-id rule that accepts only a real 20-character id, and move the native steps into IDMC mappings.
- **KB:** L-DQ-121, L-DQ-122, L-DQ-136, L-DQ-146, L-DQ-152, L-CDI-295

### PD-P1-226 A payload hash of the empty string proves nothing
- **Date:** 2026-11-04
- **Context:** `record_payload_sha256` on gold (100 % of rows) and staging (4.1 %)
- **Lesson:** The column held `e3b0c442...b855`, the SHA-256 of an empty string, which passes a format check.
- **Fix / do this:** The hash rule (`rs_<p>_sha256`) requires 64 lower-case hex characters and rejects the empty-string hash. Hash the record's real content.
- **KB:** L-DQ-146

### PD-P1-227 Lineage stamps checked as data: native SQL steps and a PENDING placeholder
- **Date:** 2026-11-04
- **Context:** `rs_<p>_idmc_object_id` on 8 lineage columns
- **Lesson:** A rule that requires a real 20-character IDMC id found `native:...` SQL steps on 76.9 % of gold rows and 48.5 % of staging rows, and the placeholder `<org>17PENDING00000` on 72.1 % of dictionary rows.
- **Fix / do this:** Validate lineage columns with `^[0-9A-Z]{20}$` and reject "PENDING". Move the native steps into mappings or record their real ids.
- **KB:** L-CDI-295

### PD-P1-228 Define each postal-code column's format before writing its rule
- **Date:** 2026-11-04
- **Context:** `av_postal_code` vs `rs_<p>_zip5`
- **Lesson:** The AV output column held ZIP+4 text (`77327-1234`) on 51.5 % of gold rows and failed the 5-digit rule, while the +4 part was already in `av_zip4`.
- **Fix / do this:** Decide per column (5-digit or ZIP+4) in the dictionary, then pick the rule.
- **KB:** L-DQ-156

### PD-P1-229 The CLAIRE-generated state-code rule rejects DC
- **Date:** 2026-10-29
- **Context:** `m_<p>_gold_dq` (8 CDQ rule specs + 8 range checks on gold), 1% sample: 866 of 867 state × check cells matched SQL
- **Lesson:** The one IDMC/SQL mismatch (2,121 sample rows) was a gap in the rule: the DC rows failed only because the CLAIRE-generated state-code rule leaves out DC. `rs_<p>_state_code` (50 states + DC, upper case) replaced it.
- **Fix / do this:** Review CLAIRE-generated rules against the domain before using them: read a generated rule's allowed list before national use, and add DC (and territories if present).
- **KB:** L-DQ-118

### PD-P1-230 Property-data rule catalog: the ranges and placeholders that worked
- **Date:** 2026-11-04
- **Context:** 60 rule specs for property, sources, dictionary and models
- **Lesson:** Ranges used:
  - beds/baths 0-40, rooms 1-100, stories 1-120
  - living area 100-5,000,000 sf; lot 50 sf to 1,000,000 acres
  - year built 1700-2027 (the upper bound needs a yearly review)
  - sale price $1,000-$500M (below that = nominal deed)
  - latitude 17.5-71.5; longitude -179.9 to -64.5 (0 is invalid)
  - state FIPS 01-78; tract 11, block group 12, block 15 digits
  - timestamps from 2000 (the 1970 and 1900 defaults are invalid); event dates from 1800, excluding 1900-01-01, 1901-01-01 and 1970-01-01
  - address placeholders are invalid: 0, NO SITUS, UNKNOWN, VACANT LAND, N/A, TBD

  City is a sort-key column, so a failing city goes to a re-key queue and is never edited in place.
- **Fix / do this:** Reuse this catalog. Write each rule's description in plain English, with what VALID and INVALID mean.
- **KB:** new

### PD-P1-231 Thresholds: 99 % on hard rules for served gold; optional facts are reported, not gated
- **Date:** 2026-11-04
- **Context:** An earlier build's "raw to gold at least 99 % perfect" bar, applied here
- **Lesson:** Of 218 checks, 171 meet 99 %, 9 are close (95-99 %) and 38 need a fix. Completeness of beds, baths and year built depends on the asset class, so it is reported, not gated. Missing is not dirty.
- **Fix / do this:** Gate hard rules (state, ZIP, keys, identity, lineage) at 99 % on serving rows, and track coverage separately.
- **KB:** L-DQ-140

### PD-P1-232 A re-runnable evaluator: weighted check pass rates, points to 100, diff against the previous run
- **Date:** 2026-11-02
- **Context:** `dqdg_eval.py` scorecard for the 4 tables
- **Lesson:** Score = weighted mean of check pass rates (hard x2, soft x1, info not scored). Each check shows its "points to 100", so fixes can be ranked. Each run writes `evaluations/<UTC>.json` and `DQ-DG Scorecard - latest.md` and compares with the previous run. Baseline: property 88.0, sources 93.5, dictionary 81.3, model_registry 22.2. Sources went from 93.5 to 95.6 after its mastering run.
- **Fix / do this:** Keep a read-only evaluator, rank work by points and re-score after each fix. Then move the same checks into IDMC so that IDMC owns the number.
- **KB:** new

### PD-P1-233 An evaluator run scoped to one table printed governance checks as failures
- **Date:** 2026-11-02
- **Context:** `evaluations/2026-11-02T1553Z_sources.md`
- **Lesson:** The partial run (sources only) showed finished_table `?`, DG 9, and FAIL on governance checks that had passed at 15:05 (dictionary definitions, profile exists). Those inputs were not loaded in a scoped run.
- **Fix / do this:** In a scoped run, print governance checks as "not evaluated" instead of FAIL. Compare DG only between full runs.
- **KB:** L-METHOD-042

### PD-P1-234 Keep PII, raw JSON blobs and backup tables out of every scan and profile
- **Date:** 2026-10-03 / 2026-11-04
- **Context:** exclusion list for IDMC and OpenMetadata; legacy server profiling
- **Lesson:** Profiles store values and patterns in IDMC's cloud metric store, and blobs are expensive: extra_json is 65 GiB uncompressed, about 48% of property_master, and backup, undo and snapshot tables add about 24 GiB more. On the legacy server 402 columns were left out:
  - the PII register's columns
  - name patterns: owner, mailing, grantor/grantee, buyer/seller, taxpayer, contact, phone, agent, brokerage, tenant, ...
  - blob names: json, payload, raw, document, response, notes, comments

  Each profile's description states how many columns were left out.
- **Fix / do this:** Filter columns by a PII register plus name regexes before create. Exclude the tables `%__pre_do_final_%`, `%_bak%`, `%_undo%`, `w34_snap_%`, `tmp_%` and the scratch DBs, and the columns `*_json`, address_aliases, geo_features, permits, for_sale and estimate_signals. Never stage owner or mailing data.
- **KB:** L-DQ-157

### PD-P1-235 Profile a live production ClickHouse off-peak, one profile at a time, from another host, with a load guard and per-query caps
- **Date:** 2026-11-04
- **Context:** 289 legacy `<legacy_db>` tables (315 profiles) queued off-peak
- **Lesson:** The Secure Agent on the new database VM reads the legacy server over the network as a read-only user, so no profiling engine runs on the website's host. Profiles run one at a time from 02:00 to 13:00Z and skip while load1 > 8 (or the second load reading > 40). Override SETTINGS on legacy: `max_threads = 1, max_memory_usage = 2 GB, max_execution_time = 1200, priority = 10`. On the new server: `max_threads = 2`, 4 GB, 3,600 s.
- **Fix / do this:** Use a window, a load guard and caps inside the override: `chprof.py run --window 02-13 --maxload 8 --parallel 1`. Stop after 5 failures in a row, and log every job to a runs ledger so the run can resume.
- **KB:** L-DQ-158

### PD-P1-236 Sample big ClickHouse tables in the override by granule or by id hash
- **Date:** 2026-11-04
- **Context:** Profiles of tables with 1.5B-2.7B rows
- **Lesson:** JDBC profiling offers only First N rows, so the sample is built in the override:
  - tables up to 100,000 rows: read all rows
  - MergeTree tables: every N-th granule (`intDiv(_part_offset, 8192) % N = 0`), capped at 100,000 rows
  - other engines: LIMIT 100,000
  - gold: `cityHash64(property_id) % 64 = 0` with FINAL (3.19M rows)
  - staging: 1/2048 of granules
  - model_registry: all model rows + 1/4096 of snapshots and chunks
- **Fix / do this:** Choose a deterministic sample per table so that reruns and SQL cross-checks see the same rows.
- **KB:** L-DQ-102, L-CDI-296

### PD-P1-237 FINAL on the rebuilt gold table needed a 12 GB memory cap, and the profile job shows only "Premature EOF"
- **Date:** 2026-11-04
- **Context:** gold profiles `p_<p>_prof5_property_master_*` after the 203.9M-row rebuild
- **Lesson:** With the 4 GB `max_memory_usage` cap the FINAL sample in the override failed with code 241 (memory limit); 12 GB worked. The profile job does not report this: it shows "Premature EOF", and the cause is only in `system.query_log`.
- **Fix / do this:** Size `max_memory_usage` in the override for FINAL at the table's current size, and re-check it after each rebuild. When a profile fails, read `system.query_log` (ExceptionWhileProcessing, exception_code 241).
- **KB:** L-DQ-148

### PD-P1-238 Inventory the server from its system tables before "profile everything", and skip what cannot or need not be profiled
- **Date:** 2026-11-04
- **Context:** "Profile everything in ClickHouse": chprof inventory/plan on the new and legacy servers
- **Lesson:** Read `system.tables`, `system.columns` and `system.parts` once to get engines, row counts and types. Not profiled: 709 views and materialized views (and `.inner` storage), 109 empty tables, 8 dictionaries, external or streaming engines (Kafka, S3, URL, MySQL, PostgreSQL, Distributed, Merge, Buffer, Iceberg, ...) and aggregate-state columns. 924 tables needed a connection per database, and 289 were queued. Tables of up to 100k rows are read whole; bigger MergeTree tables use `PREWHERE intDiv(_part_offset, 8192) % N = 0` with a 100k LIMIT, and other engines LIMIT 100k. The production samples were fixed: gold at 1/64 by property_id hash with FINAL, staging at 1/2048 of granules.
- **Fix / do this:** Run inventory, then plan (it writes a skipped list with a reason for each object and a status CSV per object), then create, then run. Price the run in profiles and jobs against the cap first.
- **KB:** L-DQ-159, L-DQ-099 (granule sampling: new detail)

### PD-P1-239 Profile in place through a sample query instead of building copy tables
- **Date:** 2026-11-02 / 2026-11-04
- **Context:** Profiling copies in the work area
- **Lesson:** An earlier lane built a 67 GB full copy (`dq_t_pu_obs_dates`), and its profile never ran. The 11-04 round read every table in place through the override. For huge tables the end state keeps only a small stratified sample per table (`dq_s_*`).
- **Fix / do this:** Try the override sample first. Build a sample table only when the connector forces it.
- **KB:** L-DQ-102

### PD-P1-240 A direct-profiling wall from 10-29 was solved by 11-04
- **Date:** 2026-10-29 -> 2026-11-04
- **Context:** IDMC Data Profiling of ClickHouse
- **Lesson:** On 10-29 the REST profile create against ClickHouse hung, and profiling worked only on a PostgreSQL sample path. By 11-04, cloning a working JDBC V2 body with real columns and native types had profiled the 5 production tables and more than 330 others.
- **Fix / do this:** Date every wall, and re-test it when the approach changes.
- **KB:** L-CONN-089 (disputed), L-DQ-128, L-METHOD-035
- **Status:** overturns PD-P1-089 and the 10-29 "REST profiling of ClickHouse hangs" note in PD-P1-181

### PD-P1-241 Address verification had verified the wrong population
- **Date:** 2026-11-01
- **Context:** Before the Property MDM rebuild
- **Lesson:** 2.4M "verified" addresses were NAD address points (`source-unresolved:*`), and 0 Massachusetts property addresses had been verified.
- **Fix / do this:** Check which population a verification step reads before reporting its coverage. Drive verification from the current situs address of each source property that is not yet verified (input SHA-256 fingerprint).
- **KB:** L-DQ-144

### PD-P1-242 What counts as "verified" for a property, a unit and a land parcel
- **Date:** 2026-11-01
- **Context:** Result interpretation in `m_<p>_mdm_10_verify_address`
- **Lesson:** verified = premise verified (ProcessStatus V/C/A, ResultQuality 4-6). Quality 6 also sets `address_delivery_confirmed`. A unit counts as verified only when quality 6 returns the same sub-building token. Land parcels that do not verify but have a parcel id and coordinates become `nonpostal`, with the assessor observation as evidence, and the serving gate accepts them (134,272 in MA). MA results: 86.5 % verified, 3.3 % unit not confirmed, 9.9 % failed (mostly land).
- **Fix / do this:** Encode these codes in the Expression after the Verifier, and classify failures before fixing them.
- **KB:** L-DQ-120, L-DQ-129

### PD-P1-243 A DQ gate that measures the legacy table says nothing about what customers see
- **Date:** 2026-10-29
- **Context:** universe gate (universe_dq), state parity, dq_checks.py, coverage marts
- **Lesson:** All of them read legacy `<legacy_db>.property_master` (109.07M ids), while customers read `<gold_db>.property_master` (100.84M). The two disagree: 15.6M ids exist only in legacy, 7.39M only in gold, and shared ids drift up to 4.9% on fields. About 15 legacy crons write a table customers never see, so a gate PASS or FAIL said nothing certain about the product.
- **Fix / do this:** Point the gates at served gold, run old and new side by side for 3 days with a `source_table` tag, then switch. Retire the legacy writers one cron at a time.
- **KB:** L-DQ-136

### PD-P1-244 19 states failed the duplicate gate after a key-changing city repair: a missing flag, not bad data
- **Date:** 2026-10-29
- **Context:** shared-address sibling parcels after the 10-23/24 county-as-city fix; 19 states failing the universe gate since 10-23
- **Lesson:** A house and a vacant lot at one address (one source, distinct parcels) now shared the gate key. The gate exempts a group only when `dq_shared_address = 1`, and its re-assert re-flagged only ids that were already adjudicated. So the failing groups went from 25 (MA) to 33,247 in 20 states (131,880 rows), and reverting the cities gave 0 groups. Only 2 groups were true repeats, and the dry-run totals matched the gate exactly (33,247 = 33,245 eligible + 2 true repeats).
- **Fix / do this:** Re-run the dependent flags after a key-changing repair instead of reverting it, using the proven earlier rule (one source AND distinct parcels). Dry-run the counts first and make them equal the gate's own counts, apply to one state first, keep a before-image plus an adjudication row per group, and leave repeated (source, parcel) groups for review.
- **KB:** L-DQ-138, L-DQ-135

### PD-P1-245 A silver DQ status that passes every row is not a gate
- **Date:** 2026-10-29
- **Context:** `<silver_db>.public_property_candidate` (30.1M rows) and its delivery decisions
- **Lesson:** Every silver candidate had `dq_status = PASS`, so records were held only at the publisher. Delivery decisions: 11.19M held, 10.92M no-change, 77,702 promoted, 7,150 conflicts; gold got 797,671 field writes from only 12 sources.
- **Fix / do this:** Run the gold check set (ranges, ZIP, state, class, numeric validity) at silver as well, so holds happen before the publisher.
- **KB:** L-DQ-143

### PD-P1-246 "Clean gold" = 22 pass/fail checks, certified after 7 green nights, and gating publication
- **Date:** 2026-10-29
- **Context:** Clean-gold definition
- **Lesson:** The definition has 5 structure checks, 16 data checks and 6 gate/process checks. Examples of data failures: impossible living area 23,778, lot under 50 sf 180,384, placeholder sale dates 229,334. Gold passed 1 check, and only SD and WY passed every data check. The rules that go with it:
  - the publisher refuses a state whose latest scorecard row fails or is older than 30 h
  - alert when a check goes from 0 to above 0, or rises more than 1 % day over day
  - a new rule ships with a test that makes the gate fail
  - coverage is tracked, not gated
- **Fix / do this:** Keep one nightly scorecard table (51 rows a night), with IDMC CDQ rules running the same checks as the independent view.
- **KB:** L-DQ-137, L-METHOD-047

### PD-P1-247 Every gold change is a frozen diff with a judged sample
- **Date:** 2026-10-29
- **Context:** Gold cleanup process
- **Lesson:** The sequence:
  1. plan into a diff table
  2. judge a 30-row sample per rule
  3. apply with a partition backup that exists only during the swap
  4. verify and write a receipt
  5. drop the backup after 7 stable days

  The field-level undo ledger is kept for 90 days. Gold repairs change ML inputs, so they land between ML gates and the ML owner is told.
- **Fix / do this:** Let IDMC plan and score the diff, and apply it through the tested cleanup flow, state by state.
- **KB:** new

### PD-P1-248 Conflicting sale observations go to a review table, not a delete
- **Date:** 2026-10-29
- **Context:** `<legacy_db>.sale_history`
- **Lesson:** The table had 0 exact duplicate rows but 6,406 keys (property, date, source) with two different prices. These are conflicting observations, not copies.
- **Fix / do this:** Build a review table with both prices and their evidence. Prefer the price with recorder/deed evidence, else the later ingest. Set `training_eligible = 0` until the key is resolved.
- **KB:** new

### PD-P1-249 The live address method: cloud Address Verification REST in Certified mode, called from a Java transformation
- **Date:** 2026-11-03
- **Context:** `m_<p>_av_cert_s1..s4` / `mt_<p>_av_cert_s1..s4` in `<project>/03 Address Verification`
- **Lesson:** Each mapping is a straight line: ClickHouse custom SQL → rule specification `rs_<p>_required_text` on property_id → Java `JAVA_AV_CERTIFIED` → Expression → append to `property_master` as record_kind 'address', publication '<p>-av-certified-v1' (131 columns plus the full response JSON). The Java step buffers 1,000 addresses (the API maximum), POSTs `https://idmc-api.<region>.informaticacloud.com/dataquality/addressverification/api/v1/process` with Mode Certified, Countries [USA], enrichments CountrySpecific + Global + Geocoding Rooftop/ArrivalPoint, retries up to 5 times with backoff, renews the token on a 401, and fails the run when the output count does not equal the input count. Runs took 1-8 min for 5k-155k addresses.
- **Fix / do this:** Reuse this shape for bulk certified verification; parse about 75 fields (CASS/DPV with footnotes, RDI, ZIP+4, carrier route, geocodes, FIPS, census tract/block group, CBSA/MSA, time zone, result quality, match %).
- **KB:** L-DQ-132, L-DQ-125
- **Status:** overturns PD-P1-296 (12 addresses per call and "keep native Verifier as the single path")

### PD-P1-250 Why cloud Certified and not the on-agent Verifier: the agent's reference data has no CASS
- **Date:** 2026-11-03
- **Context:** Choice of address verification path
- **Lesson:** The agent's USA reference data (`apps/Data_Integration_Server/data/avdata/FileSetA`: VRF/BIA plus ENR GST/GRT/GAP/EN1) has no CASS files; only the cloud service in Certified mode returns CASS, DPV and RDI (its responses list VRF/BIA + CASS C02-C07 + ENR EN1/GAP/GRT in `ResultInfo.DataFilesUsed`). The cloud service is metered per address (licence AV_IDMC_IPU).
- **Fix / do this:** Pick the method by what it returns; read `DataFilesUsed` in a real response; check the org's AV entitlement first.
- **KB:** L-DQ-125, L-AGENT-116

### PD-P1-251 The cloud service never returns the Standard street-level geocode, and says nothing
- **Date:** 2026-11-03
- **Context:** Geocode enrichment; fallback `m_<p>_av_standard_geocode` / `vfr_<p>_geocode_standard`
- **Lesson:** Standard geocoding is requested, no file is used, nothing comes back and there is no error. Unknown enrichment flags are also ignored silently, and Batch mode returns the same geocodes without the CASS block. The planned fallback (local Verifier with the GST file, only for addresses where rooftop and arrival point both came back NothingFound, writing `<work_db>.av_standard_geocode_fix`) did not return Standard geocodes yet as of 11-02.
- **Fix / do this:** Verify each requested enrichment in the response rather than trusting the request; budget a separate on-agent path for Standard geocodes.
- **KB:** L-DQ-125, L-DQ-130

### PD-P1-252 Clean address input before paying for verification
- **Date:** 2026-11-03
- **Context:** Source SQL of the certified shards
- **Lesson:** The source picks each property's best current address with argMaxIf (trusted, non-legacy sources first, then newest), trims and upper-cases, strips a trailing state/ZIP from the street line, expands ST RT → STATE ROUTE and ST HWY → STATE HIGHWAY, blanks placeholders (NO ADDRESS, NONE, UNKNOWN, UNASSIGNED, N/A), blanks a city equal to the state, cuts ZIP to 5 digits and skips rows with neither street nor ZIP, then emits one input JSON per record (`SourceID`, `AddressElements` Country/SubBuilding/Locality/AdministrativeDivision/PostalCode, `PreformattedData.PostalDeliveryAddressLines`).
- **Fix / do this:** Do this prep in the Expression or SQL before any paid call.
- **KB:** L-DQ-129

### PD-P1-253 Read "premise found, unit not confirmed" as verified; expect most to verify
- **Date:** 2026-11-03
- **Context:** Results on about 100M US property addresses
- **Lesson:** ProcessStatus V/C/A with ResultQuality 6 = delivery point confirmed; 4-5 = valid premise without its unit (typical for apartments). Counting ResultQuality >= 4 with DPV D or S as "verified, unit unconfirmed" removed about 36% of the "failures". The other large failure groups: street with no house number, house number given but street not found, placeholders.
- **Fix / do this:** Classify failures before fixing them; route no-house-number and placeholder rows to review or a geocode-by-location path instead of paid Certified calls.
- **KB:** L-DQ-129, L-DQ-120

### PD-P1-254 Track sweep progress by "already has a result for this input", never by deletable control rows
- **Date:** 2026-11-01 / 2026-11-03
- **Context:** both AV pipelines read their keyset cursor from the latest run_manifest row; the skip join in the certified shards and in `m_<p>_mdm_10_verify_address`
- **Lesson:** A lightweight delete of all run_manifest rows (10-31 20:42Z) reset both cursors to the first key, so both pipelines repeated metered verification and 343,388 properties got more than one native assessment. The fixed shard SQL skips properties that already have a Certified result unless the first 3 ZIP digits or the house number changed. The MDM verifier skips `(property_id, input_fingerprint)` pairs already written, with the fingerprint = SHA-256 of line|unit|city|state|zip.
- **Fix / do this:** Make the result table itself the progress record, keyed by an input fingerprint: select work by "this fingerprint has no result for this reference version".
- **KB:** L-CDI-283

### PD-P1-255 Store verification results as separate rows with full provenance and the raw response
- **Date:** 2026-11-03
- **Context:** `address_verification_*` / `av_*` columns in `property_master`
- **Lesson:** Results are appended as their own 'address' rows and never overwrite source values. Each carries provider, mode, verified-at time, IDMC mapping/task/run ids, the full response JSON and its SHA-256, because many returned fields exist only in the JSON.
- **Fix / do this:** Keep results append-only and keep the whole response.
- **KB:** L-DQ-132

### PD-P1-256 Cap memory in the shard SQL: unbounded runs hit ClickHouse Code 241
- **Date:** 2026-11-03
- **Context:** Certified shards on the shared new-server ClickHouse
- **Lesson:** 2 of about 70 runs (11-03 02:40-04:31Z) failed with "memory limit exceeded ... 72 GiB" (Code 241). The recipe for a new org adds `SETTINGS max_threads=4, max_memory_usage=6000000000` and limits each run to one state plus one hash slice `cityHash64(id) % N = k`.
- **Fix / do this:** Bound every shard query by state, slice and a memory cap.
- **KB:** L-CDI-292, L-CDI-286

### PD-P1-257 The AV token lives in a tmpfs file on the agent, so the call has no lineage
- **Date:** 2026-11-03
- **Context:** Auth for `JAVA_AV_CERTIFIED`
- **Lesson:** The Java step reads a short-lived Bearer token (about 5 minutes) from a `/dev/shm/...token` file in the agent container (2 lines: expiry, token); a helper on the agent host logs in and renews it with at least 300 s validity, and the Java step runs it on a 401. No IDMC connection holds this credential, so the call does not show in lineage.
- **Fix / do this:** Keep the token out of mappings, logs and chat; ask before installing helpers on a shared agent; document the lineage gap.
- **KB:** L-DQ-132 (lineage gap new)

### PD-P1-258 An external runner rewrites the mapping SQL before every run: do not edit while it runs
- **Date:** 2026-11-03
- **Context:** `the external driver script` driving the certified shards
- **Lesson:** The runner writes the state, slice and run id into each mapping's SQL (re-importing it) before every run, so hand edits are overwritten and an IDMC export alone cannot reproduce a run. Mapping descriptions still said "CA slice 3/18" while the SQL had moved on.
- **Fix / do this:** Keep the runner and its query templates with the export; for a fresh build, pass state and slice as in-out parameters instead.
- **KB:** L-CDI-294, L-METHOD-136

### PD-P1-259 Verify each address once: the sweep was paying again for known results
- **Date:** 2026-11-12
- **Context:** Golden master address coverage
- **Lesson:** 99.9% of the golden master's addresses were already IDMC-verified (87.8M Certified, 2.1M verifier, 1.7M suggestion, 55k not IDMC), yet about 391k already-verified properties were paid again, and results landed on ids still being re-keyed. The recommended reset keeps the ~98M paid results and verifies only properties with no result or a changed address, in big batches.
- **Fix / do this:** Run verification against the stable golden id set once, then incrementally for new or changed addresses.
- **KB:** L-CDI-283, L-IPU-062

### PD-P1-260 The on-agent CDQ address path gives postal results only and runs about 160 addresses/s by default
- **Date:** 2026-11-01 / 2026-11-03
- **Context:** `m_<p>_mdm_10_verify_address` (Cleanse `cls_<p>_address_text` + Verifier `vfr_<p>_address_verify_status`) on agent <dq-re>
- **Lesson:**
  - **Location:** AV runs inside Data_Integration_Server (not on the Hosted Agent).
  - **Reference data:** `data/avdata/FileSetA` (USA, 5 `*.MD6` files, about 4.09 GB; a `*.MD` search misses them).
  - **Licence:** `data/avLicenseFile/AV_IDMC_IPU.LIC`, fetched on every start. AV is IPU-metered.
  - **Config:** engine 1.9.0 / AV 6.9.0, NumFunctionServers=1, preload 0 MB, MaxMemory 8192.
  - **Result:** ZIP+4 and county, but no CASS and no geocodes unless those outputs are configured. Single-threaded with no preload it ran about 160 addresses/s (10.4 min per 100K); one DTM ran Cleanse + Verifier at about 550-580 addresses/s on MA. AV error -12000 "insufficient memory ... preload" means memory or preload settings.
- **Fix / do this:** Check the reference files and the licence before building. Raise NumFunctionServers and preload, lift the 24 GiB / 10 CPU container limit, and run disjoint key ranges in parallel. Deduplicate inputs by fingerprint first (2,874,420 were unique out of 3,238,035).
- **KB:** L-AGENT-116, L-DQ-120, L-DQ-130, L-IPU-062

### PD-P1-261 Without agent reference data, use the managed MCP for small volumes only
- **Date:** 2026-11-03
- **Context:** Choosing a method in another org
- **Lesson:** The managed MCP tool `dqverifyaddress` verifies one address per call; mapgen has no Java node, so the Certified REST call must be built outside mapgen or tested through the MCP.
- **Fix / do this:** Ask the owner before choosing; use the MCP for tests and small sets, the Certified Java step for bulk.
- **KB:** L-DQ-016

### PD-P1-262 Interpret Verifier codes in an Expression into verified / secondary_unverified / failed / unresolved
- **Date:** 2026-11-01
- **Context:** `EXP_INTERPRET_VERIFICATION` in `m_<p>_mdm_10_verify_address`
- **Lesson:** Primary verified = first letter of `Verification_Status_Code` in V/A/C and `Result_Quality` 4-6; delivery point = quality 6. A unit counts as verified only when quality is 6 and the normalized input unit (APT/UNIT/STE/... prefix removed, non-alphanumerics stripped) equals `Sub_Building_1`; the sub-building match/result statuses may be blank because Batch mode can leave them empty. Code I = failed, anything else = unresolved. MA: 2,503,090 situs addresses, 86.5% verified, 3.3% unit unconfirmed, 9.9% failed.
- **Fix / do this:** Reuse this rule set; do not require the sub-building status outputs.
- **KB:** L-DQ-120, L-CDI-266

### PD-P1-263 Certify land parcels as non-postal instead of failing them
- **Date:** 2026-11-01
- **Context:** MA golden certification
- **Lesson:** Most "failed" MA addresses were land parcels with no postal address. 134,272 were certified non-postal with the assessor parcel record and coordinates as existence evidence.
- **Fix / do this:** Give properties with no deliverable address their own certification rule rather than a failed status.
- **KB:** L-MDM-076

### PD-P1-264 A required-id rule specification as a fail-fast gate
- **Date:** 2026-11-03
- **Context:** `rs_<p>_required_text` on property_id in every certified shard
- **Lesson:** A row with no id aborts the run before any paid call, so a broken source query cannot write anonymous results.
- **Fix / do this:** Put a required-key rule specification before the expensive step.
- **KB:** L-DQ-132

### PD-P1-265 CLAIRE flagged ZIP+4 stored in a 5-digit ZIP column
- **Date:** 2026-11-04
- **Context:** 11-04 profiling round (17 profiles, 1,290 columns, one profile at 101M rows)
- **Lesson:** CLAIRE's Column Length Deviation insight flagged `av_postal_code` holding ZIP+4 (51.6% of rows); the same round found 73 insights on the gold table and 19 columns more than half empty.
- **Fix / do this:** Read CLAIRE insights as defect leads, then add a cleanse to 5 digits and a rule that keeps it there.
- **KB:** L-DQ-128

### PD-P1-266 ClickHouse profiling works through JDBC V2, but the catalog cannot scan ClickHouse
- **Date:** 2026-11-12
- **Context:** DQ scoring of the master
- **Lesson:** Profiles with rules bound run on ClickHouse through the JDBC V2 connector (up to 101M rows), but there is no native catalog scan, so scores live in IDMC and in the tables; catalog-side DQ goes through the profile route.
- **Fix / do this:** Plan ClickHouse DQ as profiles plus table columns, not catalog scans.
- **KB:** L-DQ-128, L-CONN-089

### PD-P1-267 Cleanse and Deduplicate run only on a Secure Agent, per row
- **Date:** 2026-11-12
- **Context:** Plans for unit recovery and residual duplicates (~86k)
- **Lesson:** Cleanse, Verifier and Deduplicate run in the agent's engine (not on the Hosted Agent and not through pushdown); the largest proven Deduplicate run was 720k rows. They add correctness, not speed.
- **Fix / do this:** Run them on changed records only, on a sized Secure Agent.
- **KB:** L-CDI-279, L-DQ-127

### PD-P1-268 A local profiler on a small box: full vs sampled, memory caps and a memory floor
- **Date:** 2026-08-01
- **Context:** The property app data dictionary KB over 465 ClickHouse tables on a 7.8 GB host
- **Lesson:** Tables up to 1M rows are aggregated whole (`max_threads=2, max_memory_usage=1.2 GB, max_execution_time=120`); larger ones are sampled (`rand()%97`, LIMIT 50,000, one thread, 700 MB, `max_block_size=16384`); 0-row tables are listed and never queried. The runner skips a query when free memory is below a floor and retries memory-aborted tables once at a tighter sample, recording the rest as partial.
- **Fix / do this:** Give every profiling query a memory cap so ClickHouse aborts gracefully instead of the kernel OOM-killer taking the server.
- **KB:** L-DQ-159 (local profiler new)

### PD-P1-269 Profile a schemaless store by sampling documents, not one findOne
- **Date:** 2026-08-01
- **Context:** The property app MongoDB (the app database)
- **Lesson:** Field frequency and BSON types come from a `$sample` of 300 documents per collection plus `estimatedDocumentCount`; a single document lies about the schema. Several collections were empty (for example `account_invitations`, `auth_sessions`, `field_policy_bindings`).
- **Fix / do this:** Sample per collection and record field coverage percentages.
- **KB:** new

### PD-P1-270 No Data Profiling profile had been proven on a BigQuery V2 connection
- **Date:** 2026-10-03
- **Context:** Planned per-table BigQuery profiles with CLAIRE Insights
- **Lesson:** Every profile in the org ran on PostgreSQL. The proven REST create clones a known-good profile on the same connection type. The vendor's BigQuery fix calls for -Xmx4096m, but the shared agent ran 2048m. BigQuery V2 profiles support All Rows only, so the sample has to be a materialized ≤100k-row table.
- **Fix / do this:** Spike one profile cloned from a UI-created template, and size the DTM heap first. Use one profiling path per table so nothing is profiled twice.
- **KB:** L-DQ-019, L-DQ-102, L-AGENT-112, L-CDGC-184

### PD-P1-271 Keep a profile at or under 200 rule occurrences
- **Date:** 2026-10-03
- **Context:** Profile and rule budget
- **Lesson:** Above 200 rule occurrences per profile, the scorecard publish times out.
- **Fix / do this:** Plan about 60 rules per profile or fewer. Split by table or state, and reuse one spec across columns.
- **KB:** L-DQ-032

### PD-P1-272 Profiling REST: list, read, execute; a profile that has never run has no results
- **Date:** 2026-10-03
- **Context:** <profile_ID> / <profile_MA>
- **Lesson:** The routes are under `<pod>-dqprofile.dm-us.informaticacloud.com/profiling-service/api/v1`:
  - `GET profile?limit=200` lists profiles.
  - `GET profile/<uuid>` shows fields, samplingType, the CLAIRE flags, runtimeEnvironmentId and lastRunKey (null means it never ran).
  - `GET runDetail/<id>/filter` on a never-run profile returns 400 PROFILE_SVC_00093.
  - `POST profile/<uuid>/execute` runs it. <profile_MA> (33,277 rows × 181 cols) COMPLETED in 203 s.
- **Fix / do this:** Check lastRunKey before reading results. Execute only once the row count is bounded.
- **KB:** L-DQ-019

### PD-P1-273 CLAIRE GPT recommend: name the columns, and put the RE in both scope groups for DQ scores
- **Date:** 2026-10-03
- **Context:** demo-app precedent copied for the property app
- **Lesson:** With unnamed columns, 7 of 12 rules bound to the wrong columns, and the score fell from 73.04% to 63.68% until the misbound instances were deleted. Accepting creates `DQREC_<column>_<dimension>_<rule>`. Scores come from the catalog capability "Data Quality". That needs the RE in both the Data Profiling and the Data Quality scope groups, and scores arrive in 15-25 min. `datamanagementorchestrator.orchestrate` gives the UI's answers headless in 28-80 s.
- **Fix / do this:** Name the CDE columns from a live DESCRIBE. Pin the conversation, and never re-accept live in a demo.
- **KB:** L-MCP-086, L-CDGC-143, L-CDGC-144, L-DQ-097, L-MCP-111

### PD-P1-274 For a new domain, generate rules first and recommend second
- **Date:** 2026-10-04
- **Context:** Plan v3 decision 17: the property app property columns in an org that had only demo-app rules
- **Lesson:** Recommendation only matches specs already in the repository, so for a new domain it returns "No matching data quality rules were found". Generation from a one-sentence prompt or a policy file (one rule per line) produces a real CDQ RULE_SPECIFICATION in project CLAIRE in about 4-7 min. It is visible via `GET /public/core/v3/objects?q=type=='RULE_SPECIFICATION'`. Generate and accept are UI-only.
- **Fix / do this:** Build the policy file from the glossary rule_hooks. Generate, then recommend and accept on named columns. Move generated specs out of the shared CLAIRE project with a v3 export and import.
- **KB:** L-MCP-079, L-MCP-098, L-MCP-099, L-MCP-089

### PD-P1-275 DQ-agent MCP mechanics, and which of its tools write
- **Date:** 2026-10-03
- **Context:** The CLAIRE DQ agent as a source of rules
- **Lesson:** Calls nest a JSON-RPC tools/call. Poll `get_skill_execution_updates` from cursor "0" every ~1.5 s, for up to about 15 min. The tools behave differently:
  - `data_quality_rule_recommendation` needs a catalogued asset and pauses on HUMAN_PROBE; answer `{prompt:'yes', conversation_id, deferred:true}`. It applies what it recommends, so it is a write.
  - `rule_generation` only drafts.
  - `cleansing` uploads the file to Informatica's cloud.

  Angle brackets in prompts give error -32602.
- **Fix / do this:** Treat recommendation as a write under an approval, and run it on the sample only. Uploads: at most 5 a day, each at most 2,000 rows × 50 cols × 1 MB, masked and logged.
- **KB:** L-DQ-071, L-DQ-079, L-DQ-080, L-DQ-081, L-MCP-112

### PD-P1-276 Rule specs translate deterministically from the v3 export, but some semantics are unpinned
- **Date:** 2026-10-03
- **Context:** Prototype infa_rule_to_sql.py on 19 local rule specs
- **Lesson:** The logic is two JSON strings deep: `nativeData.documentBlob` → `ruleModel`. Advanced specs hold `alternateDefinition.script` (IF/ELSEIF with ISNULL, LENGTH, IS_SPACES, REG_MATCH, IN). Basic specs hold the `topRuleFamily.statements` tree. Advanced specs were rendered as `upper(CASE…END) IN ('VALID','TRUE','1','YES','OK')`, with REG_MATCH anchored `^(?:p)$` and no lookaround (RE2). Still unverified: IS_SPACES(''), IN case sensitivity, and ClickHouse '' vs NULL.
- **Fix / do this:** Claim only the coverage you have tested. Build the basic-mode mapper and a dictionary export before counting a rule as translated.
- **KB:** L-DQ-104

### PD-P1-277 A SHA-256 PRN is a sample key that works the same in every engine
- **Date:** 2026-10-03
- **Context:** Sample s1
- **Lesson:** cityHash64 exists only in ClickHouse and FARM_FINGERPRINT only in BigQuery. `prn32`, the first 4 bytes of SHA-256('s1:' + id) read big-endian, can be computed in ClickHouse, BigQuery and Postgres, so the same keys stay in the sample on every refresh. ClickHouse reinterpretAsUInt32 reads little-endian, so reverse the bytes. Changing the hash format (for example 16 hex vs 64 hex) breaks parity.
- **Fix / do this:** Keep a test-vector TSV (empty, padded, non-ASCII and long keys), and make every engine reproduce it before first use.
- **KB:** L-DQ-099

### PD-P1-278 Stratify the sample: a few towns in hash order is not representative
- **Date:** 2026-10-03
- **Context:** Interim stage pu_ma
- **Lesson:** pu_ma held 33,277 rows from 8 towns taken in cityHash64 order, so it did not represent the state. property_master has no SAMPLE BY.
- **Fix / do this:** Stratify by state → town → asset_class_v2, with at least 30 rows per town and 200 per class, and store the weights. MA budget: 50k rows (±0.44 pp). National: 10 large states × 10k plus 40 × 5k, in one union table with a state column.
- **KB:** new

### PD-P1-279 Samples go stale while other lanes rewrite the source
- **Date:** 2026-10-03
- **Context:** property_master during the probe
- **Lesson:** The ID partition grew from 98,115 to 137,019 rows in about 4 h, and an INSERT was running during the probe.
- **Fix / do this:** Record max(ingested_at) and the snapshot time with every sample, swap atomically, and re-stage before CLAIRE reruns. Run a STALE_SAMPLE check before any drift alarm.
- **KB:** new (related L-DQ-147)

### PD-P1-280 Rules must be dialect-neutral to run across estates
- **Date:** 2026-10-03
- **Context:** dq_claire supported only ClickHouse predicate and unique rules
- **Lesson:** rule_expr was hand-written ClickHouse SQL using FINAL, ifNull(toUInt8) and ARRAY JOIN. BigQuery has no FINAL, and dbt-postgres was not installed anywhere.
- **Fix / do this:** Use a typed rule spec (not_null, regex, in_set, range, length, unique_key, cross_field, reference_fk, freshness), rendered through `adapter.dispatch`. Validate BigQuery with a 0-byte dry run and Postgres with EXPLAIN. Replace FINAL with a `QUALIFY ROW_NUMBER() ... = 1` view. Set maximum_bytes_billed in every BigQuery profile.
- **KB:** new (L-ENV-041 for the byte cap)

### PD-P1-281 Don't build a second DQ engine; link rules to existing checks with covered_by
- **Date:** 2026-10-03
- **Context:** gold_dq vs CLAIRE rules
- **Lesson:** gold_dq already ran 13 value checks, 11 freshness checks and a volume check per state. Two engines on the same defect give two verdicts and two repair queues.
- **Fix / do this:** CLAIRE/dbt handle row-level column rules and gold_dq handles aggregates. Add `covered_by` (for example `gold_dq:bad_year`) so the generator skips covered rules. Accept a rule only if it translates deterministically, passes parity, has a sample pass rate of at least 90%, and is not already covered.
- **KB:** new

### PD-P1-282 autoAssignRules returns 0 suggestions while the org has no published rule specs
- **Date:** 2026-10-03
- **Context:** <profile_MA> (33,277 × 39, 203 s)
- **Lesson:** CLAIRE produced 18 insights (17 Number Value Distribution, 1 Completeness). `autoAssignRules` returned 200 with 0 suggestions because no published rule specs existed. Rules derived from insights are not CLAIRE rules, and 2 of them failed their own thresholds (30.4% vs 1%, 0.96% vs 0.5%).
- **Fix / do this:** Publish rule specs before expecting auto-assignment. Send rules derived from insights to a reviewer, and tune their thresholds before accepting them.
- **KB:** new

### PD-P1-283 ClickHouse toDateTime() clamps pre-1970 dates when staging for a profile
- **Date:** 2026-10-03
- **Context:** stage and sample DDL generation
- **Lesson:** `toDateTime()` clamps pre-1970 sale dates to 1970. A length overrun should stop the run rather than truncate, because changing a precision forces a profile field update.
- **Fix / do this:** Export dates as ISO text into Postgres `timestamp`. Generate the DDL and the IDMC field list from the live DESCRIBE.
- **KB:** L-DQ-022 (types); date clamp new

### PD-P1-284 Rule translator: portable regex, NULL counts as fail, never NOT IN
- **Date:** 2026-10-03
- **Context:** rules2dbt SPEC (one registry, many compilers)
- **Lesson:** Store each rule once as kind + params, and compile every dialect from that; never translate one dialect's SQL into another. Regex rules:
  - Use a portable subset: no backslashes (escape with `[.]`), no `\d`, `\w` or `(?i)`.
  - ClickHouse unescapes `\\`, BigQuery needs `r''`, and Postgres keeps the text literal.

  A NULL check result counts as a fail. reference_fk uses NOT EXISTS, never NOT IN, because NOT IN breaks on NULLs. Anything the translator cannot map becomes needs_review.
- **Fix / do this:** Validate examples_pass and examples_fail as literal SELECTs on all three engines before accepting a rule.
- **KB:** L-DQ-100 (related); new

### PD-P1-285 BigQuery DQ cost shape: one scan per partition, a byte cap and a dry run
- **Date:** 2026-10-03
- **Context:** rules2dbt COST_GUARDS
- **Lesson:** Shape M (one scan returning rows_checked and rows_failed per partition) avoids a second count query. A per-state loop on a table with no pruning column rescans each column 51 times, about $6 a pass instead of $0.12. LIMIT never reduces bytes billed. BigQuery cannot partition on STRING.
- **Fix / do this:**
  - Partition with `RANGE_BUCKET(state_fips…)` and use `CLUSTER BY state, property_id`.
  - Set `maximum_bytes_billed` (1-5 GB) on every query.
  - Dry-run every compiled test, and abort if the total exceeds the run budget.
- **KB:** L-ENV-041 (related); new

### PD-P1-286 dbt resolves a local package's macros only when they are namespaced
- **Date:** 2026-10-04
- **Context:** dq_estates with local package dq_rules
- **Lesson:** `dbt compile` failed 3 times (Compilation Error in the dq_pack tests). A root-project test does not resolve bare package macros. Once every call was written `dq_rules.<macro>`, compile passed on clickhouse, postgres and bigquery.
- **Fix / do this:** Namespace every macro call inside a local package.
- **KB:** new

### PD-P1-287 Validate dbt with no database contact, in its own venv
- **Date:** 2026-10-04
- **Context:** dq_estates on another VM
- **Lesson:** netguard.py ran dbt deps, parse and compile with every non-loopback connection refused (0 attempts). sqlglot then parsed all 21 compiled tests. Pins that resolved: dbt-core 1.12.5, dbt-adapters 1.24.5, dbt-clickhouse 1.9.3, dbt-bigquery 1.8.3, dbt-postgres 1.11.0. dbt-postgres 1.11.0 was the only version compatible with adapters 1.24.
- **Fix / do this:** Prove offline first, in a separate venv. Label every query "compiled, never executed" until it actually runs.
- **KB:** new

### PD-P1-288 Don't duplicate DQ scans or bind rules to tables that can't support them
- **Date:** 2026-10-04
- **Context:** dq_estates vs dq_claire; universe_events
- **Lesson:** dq_claire already ran the 11 baseline rules daily, so scheduling the same pack would repeat the FINAL scan. universe_events has no state partition and no `source` column, so its two rules were retired.
- **Fix / do this:** Before binding rules to an estate, check overlap with existing runners and check the real columns and partitions in system.columns.
- **KB:** new

### PD-P1-289 BigQuery bills at least 10 MiB per query, so dbt tests add up
- **Date:** 2026-10-04
- **Context:** dq_estates BigQuery run on 4 <corp> marts
- **Lesson:** Dry-runs estimated at most 153 KB per query, yet every measure query billed 10,485,760 bytes. 10 measures plus 10 tests came to 200 MiB.
- **Fix / do this:** Dry-run every compiled test and refuse the whole run if any one exceeds the cap. Set maximum_bytes_billed, and budget at least 10 MiB per test.
- **KB:** new

### PD-P1-290 Profile runs are in the jls-di JobLogEntries: filter by assetId, not by name
- **Date:** 2026-10-04
- **Context:** <profile_ID> run 1
- **Lesson:** `GET <pod>/jls-di/api/v1/Orgs('<orgUuid>')/JobLogEntries?$filter=assetType eq 'PROFILE'` works with the v2 session in IDS-SESSION-ID. One full run is 3 entries, including the Outlier and Insight sub-jobs. assetName is "<profile> - run - N", so `assetName eq '<profile>'` returns 0. assetId is the profiling jobId, and extraData.jobParams = {jobId, jobType PROFILING_PC}.
- **Fix / do this:** Filter on assetId (the jobId), or use startswith on the name. Count profile runs for the budget from this read.
- **KB:** L-DQ-106, L-IPU-055 (assetName format: new)

### PD-P1-291 IDMC gives no per-rule profile counts: store "not measured" as NULL
- **Date:** 2026-10-04
- **Context:** dq_rule_spec idmc_sample_n / idmc_sample_failed
- **Lesson:** 7 rules whose columns were missing from the profiled slice were stored as n=33277, failed=0. That reads as a measured zero and would corrupt parity.
- **Fix / do this:** Make these columns Nullable, DEFAULT NULL, meaning "not measured". Count each rule with SQL on the exact table IDMC profiled.
- **KB:** L-DQ-100, L-DQ-031 (NULL point: new)
- **Status:** superseded by PD-P1-217 for the claim that IDMC gives no per-rule counts (exact VALID/INVALID counts are readable from the metric store); the NULL-for-not-measured rule stands

### PD-P1-292 Rule hashes over JSON text: 2 and 2.0 hash differently
- **Date:** 2026-10-04
- **Context:** rule_hash in --static vs --live mode
- **Lesson:** static_rules_v1.json stored threshold_pct as integers while the registry hashed floats. Three baseline rules got a different sha1, which causes false version bumps and missed parity joins.
- **Fix / do this:** Normalise numeric types before hashing, then prove the static, live and stored hashes agree (29/29).
- **KB:** new

### PD-P1-293 Bounds derived from a sample: check representativeness, drift and calendar windows
- **Date:** 2026-10-04
- **Context:** 29 rules derived from an 8-town profiled slice (33,277 rows)
- **Lesson:** Bounds came from p0.1/p99.9 fences, rounded outward, and several failed on wider data:
  - On full data tax_rate_range passed only 66.85%, because the slice missed the largest city and commercial properties.
  - 609,075 rows carry a nominal sale of $100 or less.
  - Gold had changed since staging.
  - Narrowing tax_year to toYear(now())..+1 would fail almost every row from 2027-01-01.
  - On the 50,110-row stratified sample, 10 of 29 rules failed.
- **Fix / do this:** Derive bounds on a stratified sample that includes the hard segments. Restage a stale copy or mark it stale. Keep a ±1 year window for year rules. Accept a rule only after parity on the real sample.
- **KB:** new

### PD-P1-294 Parity on a database copy with no dbt login: compile offline, run read-only
- **Date:** 2026-10-04
- **Context:** Estate pg_stage_av_s1 (parity_of: clickhouse)
- **Lesson:** Tests were compiled offline (netguard: 0 connections). The compiled SQL then ran inside the container with `PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=60000'`. Parity joins on rule_id + rule_hash. An independent cross-check SQL built from the registry's own translator matched 29/29.
- **Fix / do this:** Keep compile separate from run, force read-only at the session level, and cross-check with a second translator.
- **KB:** new

### PD-P1-295 A rule spec used as an ABORT guard is not DQ: store outcomes and build a promotion gate
- **Date:** 2026-11-01
- **Context:** The old build's 03 Data Quality folder
- **Lesson:** What the folder actually did:
  - `rs_<p>_required_text` was used 316 times, mostly as `IIF(Output!='VALID', ABORT(...))`.
  - The cleanse asset was used by 0 mappings. There were 0 profiles, scorecards or match assets.
  - Results were tokens in `dq_message`; `dq_issue_codes` was empty and `dq_score` was NULL.
  - Every mapping hard-coded `dq_status='held'`, so none of the 154.7M rows could ever be promoted.
- **Fix / do this:** Write rule-spec outputs to `dq_issue_codes` and `dq_score`, and write failing rows as `dq_issue` records. Add a gate mapping that sets passed/eligible from those outputs.
- **KB:** L-DQ-143, L-DQ-004, L-CDI-112

### PD-P1-296 Cloud AV from a Java transformation: 12 addresses per call, a token from outside IDMC, no added coverage
- **Date:** 2026-11-01
- **Context:** wf_<p>_cloud_address_window, every 30 min
- **Lesson:** A CDI Java transformation POSTed 12 addresses per call to `idmc-api.dm-us.../dataquality/addressverification/api/v1/process`, where the API accepts 1,000. The Bearer token was read from /dev/shm and minted by a separate helper on the agent disk, so no IDMC connection held it and no lineage showed it. Results: 0 cloud-only properties, no geocodes, 68% unresolved (native AV: 0.02%).
- **Fix / do this:** Keep native Verifier batch as the single path. If cloud AV stays, send 1,000 addresses per call and handle a renewable token inside IDMC.
- **KB:** L-DQ-015, L-DQ-132
- **Status:** superseded by PD-P1-249 (from 11-03 cloud Certified AV, 1,000 addresses per call, became the live method instead of the native Verifier batch)

### PD-P1-297 Test rule-spec logic offline first: REG_MATCH is a full match, IN is case-sensitive
- **Date:** 2026-10-29
- **Context:** `local_eval` in the rule-spec builders
- **Lesson:** A Python mirror of each advanced script, run with test values, catches logic slips before import. It also checks identifiers and quotes against the keyword set (IF/THEN/ELSE/ELSEIF/ENDIF/AND/OR/NOT/Output) and the function set (ISNULL, LENGTH, IS_SPACES, REG_MATCH, IN, LOWER, UPPER, LTRIM, RTRIM, SUBSTR, INSTR). The mirror must copy CDQ semantics: REG_MATCH matches the whole value, and IN is case-sensitive.
- **Fix / do this:** Run `plan` (offline checks plus an IDMC census) before `build --execute`.
- **KB:** new (related L-DQ-104)

### PD-P1-298 Placeholder dates and nominal prices: prove a burst per source before nulling
- **Date:** 2026-10-25
- **Context:** cleanup v2 rules (v1 sampled only 30 rows per rule)
- **Lesson:** v1 nulled real 1936/1938 MA deeds and missed 1970-01-01 placeholders (TN/SC/PA).
  - A Jan-1 date before 1950 is a placeholder only where a (source, year) burst is proven: at least 20 rows and at least 10x the busiest other month start.
  - Month-precision sources never qualify.
  - One state GIS source's prices are real.
  - Hits over 100k sf were all real non-dwellings.
  - Bed or bath counts above 30 are building totals: flag them, don't null them.
  - Control characters in parcel_id aborted a state's import.
- **Fix / do this:** Sample 30 hits per rule before writing it. Choose flag or fix from the evidence, and cap fixes per field.
- **KB:** new

### PD-P1-299 Audit label provenance and fan-out before training
- **Date:** 2026-10-24
- **Context:** ML LESSONS §2, dq/events_bulk_deeds
- **Lesson:**
  - 13 source families never set arm's-length flags, so 15 states had zero corpus.
  - Bulk deeds (103,720 groups, 841,050 sales sharing date and price) are portfolio sales.
  - Wrong-state rows, plat dates and assessments reached training. Fixes included deleting 253,620 mis-tagged FL/CT rows, re-dating 185,766 TN sales and NULLing 288,370 OH flags.
- **Fix / do this:** Check provenance per source family. Never build a (state, date, price) fan-out key. Keep validity separate from training eligibility, and back up before deleting.
- **KB:** new

## MDM & golden records

### PD-P2-001 Property MDM plan: a single-source track first, then a dual-source track with one UI match/merge
- **Date:** 2026-08-03
- **Context:** MDM SaaS Property entity in a second org, by REST push (not executed)
- **Lesson:** Track A: Idaho single source (about 98,115 rows, 1:1, fuzzy matching off). Track B: Nantucket (9,105 rows) dual-source, then one manual UI match + merge (the first real MDM record-processing IPU). About 6-8 UI clicks (model, publish, source systems) unblock everything else. Guardrails: curated subset only, the second org only, no headless spend.
- **Fix / do this:** Prove MDM 1:1 before fuzzy matching. Count the UI clicks that gate headless work.
- **KB:** L-MDM-053

### PD-P2-002 Survivorship and canonical duplicates on the ClickHouse golden record
- **Date:** 2026-10-03
- **Context:** glossary entries 06 / 07
- **Lesson:** Inside ReplacingMergeTree the newest ingested version wins. The golden view keeps the latest DQ-passing whole row (argMax, no cross-source mixing). MA dedupe keeps the survivor with more filled fields, fill-only, with an undo row and an alias. Legitimate shared addresses are flagged dq_shared_address = 1, not deleted. A fix helper re-derived its own predicate once and over-selected 2M rows.
- **Fix / do this:** Build any dedupe fix FROM the gate view, never from a re-derived predicate.
- **KB:** new

### PD-P2-003 Master in this order: registries, then definitions, then models, then the big entity
- **Date:** 2026-11-02
- **Context:** 4-table mastering plan (sources R, data_dictionary D, <model_registry> V, <property_table> M+E)
- **Lesson:** Each table gets an archetype: R registry, D definition, V versioned asset, M entity, E events. Order follows the FKs: sources first (FK target of `source_{1,2,3}_id`), then the dictionary (it holds the vocabularies and rule ids), then <model_registry> (it links to a property publication), and the property table last. Each table pilots one scope, runs gates G1-G9, then fans out.
- **Fix / do this:** Classify each table by archetype, master the FK targets first, and gate every table on G1 (key unique), G4 (duplicates), G7 (orphans) and G9 (dictionary in both directions) before fan-out.
- **KB:** new

### PD-P2-004 A registry's "duplicates" were its grain: dataset x state
- **Date:** 2026-11-02
- **Context:** `sources` (1,790 rows)
- **Lesson:** There were 70 same-domain groups (1,459 rows) and 27 same-name groups (841 rows), but EPA Walkability, FEMA USA Structures and similar datasets repeat once per state. Only 6 groups / 12 rows were true duplicates (same name + scope), and even those turned out to be distinct feeds sharing a name. The fix was names, not merges.
- **Fix / do this:** Find the grain before matching, and disambiguate names before merging anything.
- **KB:** L-MDM-077

### PD-P2-005 Add a registry's hierarchy as columns, and resolve placeholder FKs through an alias table
- **Date:** 2026-11-02
- **Context:** sources hierarchy and the `unresolved` FK
- **Lesson:** `provider_id` and `dataset_id` are added to every row, so a feed rolls up to dataset and then provider without new tables. 220,827 finished property rows had `source_1_id = 'unresolved'`, and 11,327 had a `source_2_id` that is not in sources. An existing `source_alias` table (5,902 labels -> source_id) is the route to resolve them, with the remainder sent to a steward list.
- **Fix / do this:** Count a placeholder FK as an orphan in G7, resolve it through the alias map, and fold the alias table into `sources.aliases` at the end.
- **KB:** new

### PD-P2-006 One model, three id schemes: build the alias crosswalk before mastering a versioned registry
- **Date:** 2026-11-02
- **Context:** `<model_registry>` (1.31B rows, 8 record kinds)
- **Lesson:** The same models appeared under three id schemes:
  - model_version used `state_model:<ST>`, `avm-blend` and captured table names (2,445 capture rows stamped as versions)
  - artifacts used file names, and 258 of 284 matched no version
  - evaluations used legacy table names, and none of 40 matched

  54 keys held more than one row because the scope sat in record_id, not in the key (`avm-blend/current` held 3 rows).
- **Fix / do this:** Map file names to models with rules (`<ST>.asof-YYYY-MM-DD.joblib` -> `state_model:<ST>` / `asof-...`). Re-key captured rows as evidence, put the scope into the key (`avm-blend:MA:condo`), keep one champion per family and scope, and split sentence statuses into a decision code plus a description.
- **KB:** L-MDM-078

### PD-P2-007 Two overlapping golden builds give one entity several golden rows
- **Date:** 2026-11-02
- **Context:** property observations table
- **Lesson:** `<prefix>-mdm-property-master-v1` (MA 4.70M rows for 2.18M ids) and `<prefix>-gold-v2` (MA 1.25M, NJ 1.10M) both lived beside the separately built finished table.
- **Fix / do this:** Make the finished table the only golden. Mark older publications superseded (`record_stage = 'gold_superseded'` or `is_deleted = 1`, which needs an owner GO), and make incremental publish write the finished table, not a third golden.
- **KB:** L-MDM-079

### PD-P2-008 Triage same-address masters into house+lot, true duplicate or condo without unit
- **Date:** 2026-11-02
- **Context:** G4 on the finished property table (MA 151 groups / 302 rows, CT 212 / 424)
- **Lesson:** The sampled pairs were the same address with different parcels: either a house plus its lot, or a genuine duplicate.
- **Fix / do this:** Handle each group by type:
  - house + lot: keep both masters and add a `same_site` relationship
  - true duplicate: a merge override (loser -> winner) in a table the match step reads first; the loser id stays as an alias
  - condo without a unit: a hold code
- **KB:** L-MDM-076

### PD-P2-009 Property MDM in CDI: verify, match, golden, publish as 4 parameterized mappings
- **Date:** 2026-11-01
- **Context:** `m_<prefix>_mdm_10/20/30/40` + `wf_<prefix>_mdm_property_master`
- **Lesson:** The steps:
  - 10: Cleanse + Verifier
  - 20: match keys + variable ports -> cross-reference (`identity_alias`, confirmed or merged)
  - 30: XREF join -> sorted Aggregator survivorship -> qualified sale event -> unit-in-building hierarchy -> 3 rule specs -> certification -> Router to the steward queue `dq_issue`
  - 40: publish one `run_manifest` per state plus `*`

  Every row carries `publication_id = <prefix>-mdm-property-master-v1`. MA result: 2,519,596 observations -> 2,516,176 masters, 2,167,667 (86.1 %) serving-eligible, average DQ score 97.7 (86.9 before verification), 0 hard-rule failures.
- **Fix / do this:** Use this chain as the template for an entity built in CDI (the same shape as the C360 pipeline), with the linear taskflow stopping on error.
- **KB:** L-MDM-075, L-CDI-263

### PD-P2-010 Survivorship by attribute group in one sorted Aggregator: companions come from the same observation
- **Date:** 2026-11-01
- **Context:** `m_<prefix>_mdm_30_golden_record` (`AGG_SURVIVORSHIP`)
- **Lesson:** Location (address, city, ZIP, unit), geo (lat/long, tract), classification and valuation (assessed, building, land, tax year) each survive as a group from one observation: the most recent non-null. Physical attributes survive one by one. Observations are read ordered by master id, newest first; the Aggregator is grouped by master id with `inputSorted=true` plus advanced `Sorted Input=true`, and each attribute is `FIRST(value, NOT ISNULL(value))`, with companion fields anchored to the same condition and `FIRST(record_id, <anchor>)` for field lineage. `field_lineage_json` names the winning observation per group. 2.5M masters from 2.5M observations took 13-38 minutes, including rule specifications and three targets.
- **Fix / do this:** Group attributes that must agree, use FIRST with a condition per attribute group, record per-group lineage, and name every output port distinctly.
- **KB:** L-CDI-263

### PD-P2-011 The last sale comes from the latest qualified sale event, not the property record
- **Date:** 2026-11-01
- **Context:** Golden-record sale fields
- **Lesson:** The most recent arm's-length sale of at least $1,000 that is not future-dated beats the record's own last sale. 1,477,789 MA masters got a qualified sale and 113,194 nominal $1-type last sales were corrected. When no qualified sale exists, the record's sale is kept and flagged `LAST_SALE_NOMINAL` (498,529, still served).
- **Fix / do this:** Survive event-derived summaries from canonical events, and flag nominal values instead of dropping them.
- **KB:** new

### PD-P2-012 Build the condo unit -> building hierarchy from postal verification, not from inferred memberships
- **Date:** 2026-11-01
- **Context:** Hierarchy in the golden mapping; serving gate for condo units
- **Lesson:** Inferred memberships (same address, `inferred_review` status) do not satisfy a gate that needs a confirmed parent, so the captured legacy memberships stay as evidence only. When verification confirms the unit (quality 6 and the same sub-building token), the building id = `'building:' || md5(verified premise without unit | zip5)`, and a confirmed `unit_in_building` relationship row is written from a third Router group; unconfirmed units are held. MA: 167,528 inferred memberships, 113,902 confirmable, 115,852 units in 13,140 buildings confirmed in the published build.
- **Fix / do this:** Serve a condo unit only when its building relationship is confirmed (`CONDO_PARENT_UNCONFIRMED` otherwise). Test the premise rule in SQL first (`hier_test.sql`), then move it into the mapping.
- **KB:** L-MDM-076

### PD-P2-013 The serving-eligible gate, a dq_score from 8 checks, and CHECK constraints that enforce the same gate
- **Date:** 2026-11-01
- **Context:** Golden-record certification
- **Lesson:** A record is serving-eligible only when:
  - no hard rule fails (state, ZIP format, address present)
  - The class is mastered
  - The address is verified (for units: the unit is verified)
  - a condo's building is confirmed

  `dq_score` 0-100 = 8 equal checks, and each gap is a code in `dq_message`. The table's CHECK constraints enforce the same gates.
- **Fix / do this:** Compute eligibility and score inside the mapping, and back them with table constraints so a bad writer cannot bypass them.
- **KB:** new

### PD-P2-014 Publish a golden set only when the counts reconcile, and gate consumers on gold_committed
- **Date:** 2026-11-01
- **Context:** `m_<prefix>_mdm_40_publish` (07 Reconciliation)
- **Lesson:** Per state and for `*`, the publish mapping compares mastered ids expected from the cross-reference (XREF) with the golden records written, merged, certified, held and failed, plus issue counts. It writes one run_manifest row per state plus one `*` row, and marks `gold_committed` only when every master has exactly one golden record (MA 2,516,176 = 2,516,176). Consumers read only committed publications: `record_kind = 'property_state' AND record_stage = 'gold' AND publication_id = ... AND serving_eligible = 1` FINAL.
- **Fix / do this:** End every mastering run with a reconcile step that decides publication, and gate every consumer on the latest run_manifest of the publication being `gold_committed`.
- **KB:** new

### PD-P2-015 Parity on single-observation masters proves survivorship lost nothing
- **Date:** 2026-11-01
- **Context:** `parity_ma.sql`
- **Lesson:** For the 2,512,767 MA masters with one observation, golden vs bronze showed 0 differences in beds, baths, living area, year built, assessed value, class, address and parcel (argMax by version, null-safe comparisons).
- **Fix / do this:** Compare a slice whose expected answer is known (single source) field by field before trusting multi-source results.
- **KB:** L-METHOD-053, L-CDI-140, L-MDM-082

### PD-P2-016 A golden-table rebuild silently doubled the rows with held provisional identities
- **Date:** 2026-11-04
- **Context:** <property_table> rebuild, 11-03 22:12Z to 11-04 18:19Z (101.4M -> 203.9M rows)
- **Lesson:** 50.5 % of rows were provisional identities (provisional_address 21.9 %, provisional_parcel 21.2 %, source_property_id 7.3 %). The serving gate held, so none of them became serving- or ML-eligible, but every mastering rule fell to about 49-52 % and they dragged the gold score to 90.3 % overall.
- **Fix / do this:** After every rebuild, compare the row count and the identity-status mix with the previous build. Keep consumers gated on `serving_eligible = 1`. Decide whether to master the held rows or move them out before re-profiling.
- **KB:** L-MDM-083

### PD-P2-017 property_id is heterogeneous and opaque: never parse it
- **Date:** 2026-08-03
- **Context:** MDM business-entity key design
- **Lesson:** In MA the id is a bare 24-hex ObjectId surrogate. In assessor states it is `<STATE>-<countyFips>-<parcelId>[#disambiguator]` (ID: 5,089 `#`). A single PK-format validator breaks one shape or the other.
- **Fix / do this:** Treat the key as an exact-match string, take state, county and parcel from their own columns, and attach no regex to the key.
- **KB:** L-MDM-046

### PD-P2-018 Mongo _id is a BSON ObjectId: convert it to hex before joining
- **Date:** 2026-08-03
- **Context:** Mongo `<legacy_db>.<property_table>` (2,515,303 MA docs) vs ClickHouse
- **Lesson:** `$type:string` count = 0, so a naive string == ObjectId compare matches nothing. hex(`_id`) == ClickHouse `property_id` for MA, 1:1 in both directions. Mongo also has no `county_fips`.
- **Fix / do this:** Use `$addFields:{propertyId:{$toString:'$_id'}}` in the extract. Compute county subsets on the ClickHouse side, then key into Mongo.
- **KB:** new

### PD-P2-019 The two "sources" were a byte-identical mirror: survivorship would fire nothing
- **Date:** 2026-08-03
- **Context:** ClickHouse vs MongoDB for a 2-source MDM demo
- **Lesson:** 800 shared MA properties diffed across 22 fields showed zero divergence, and so did 300 more on values. Mongo's "enrichment" field `bedsEst` was byte-identical to CH `beds_est`. A 26-agent adversarial review proved the v1 design premise false (20/20 findings verified). The only genuinely Mongo-only content was nested (`geoFeatures`, `permits`, `saleHistory`).
- **Fix / do this:** Audit actual divergence before designing survivorship. Call a mirror demo "mechanics" (2 -> 1 golden, ranking applied), and never stage a synthetic seeded conflict as proof.
- **KB:** L-MDM-082, L-MDM-045

### PD-P2-020 Two per-source field maps, sentinel defaults nulled, and a one-row canary
- **Date:** 2026-08-03
- **Context:** MDM ingest bodies
- **Lesson:** The sources were asymmetric: `assetClassV2` and `assetClassGroup` were CH-only, Mongo had `assetClass`, and `livingAreaSf` was 99.5 % filled in Mongo vs 85.8 % in CH. Sentinel defaults (`asset_class_v2 = 'unknown'`, `asset_class_group = 'other'`) must become null on extract. A mistyped key is silently dropped inside a 201, and there is no schema-list verb.
- **Fix / do this:** Keep one field map per source. Map Float64 -> Double, ints -> Integer, Date32 -> Date, DateTime64 -> Date Time (ms), money -> Decimal, and county_fips as a String with its leading zeros. POST one real row and read it back field by field before any bulk run.
- **KB:** L-MDM-046, L-MDM-019

### PD-P2-021 Match deterministically on the business key: a fuzzy address rule would collapse 34,875 parcel groups
- **Date:** 2026-08-03
- **Context:** Property match model design
- **Lesson:** The v1 secondary rule (addressNorm + zip + city / SSA-NAME3) collides on 34,875 distinct MA parcel groups (unit 99.96 % empty). The largest group is 306 Nantucket parcels sharing one degenerate address. SSA-NAME3 populations are person/org identity models with no parcel population.
- **Fix / do this:** Use one exact rule on `propertyId`, no fuzzy rule. Inspect the candidate pairs before merge.
- **KB:** L-MDM-044

### PD-P2-022 MDM SaaS headless/UI split: run time is headless; design, deploy, jobs and steward decisions are UI
- **Date:** 2026-08-03
- **Context:** 49-step Property MDM runbook (27 headless, 17 UI, 4 hybrid, 1 design gate)
- **Lesson:** Headless: login + JWT, record ingest (bare flat body, `trustScore` as a STRING -> 201), read by known id, R360 search (`POST /rdm-service/external/v1/search` = 400, so the verb exists), metering. UI only: BE/field/key authoring, Publish, source-system registration (`.../sourceSystems` 404), match and survivorship authoring, match and merge job runs (`.../jobs` 404 on both verbs), steward adjudication. `entity/{be}/search` is GET 404 / POST 405, so golden uniqueness and lists need the UI or MCP.
- **Fix / do this:** Put the ~6-8 UI clicks on one checklist (Modeler vs Console), and automate everything after them.
- **KB:** L-MDM-004, L-MDM-005, L-MDM-016, L-MDM-028

### PD-P2-023 Source updates go to entity-xref; trustScore in the body is not the survivorship policy
- **Date:** 2026-08-03
- **Context:** MDM ingest semantics
- **Lesson:** Writing source data to the golden `entity` corrupts it, so updates go to `entity-xref`. The ingest `trustScore` is at best a per-field seed, and it is unproven that survivorship honors it. BVT and source ranking are authored in the Modeler. entity-xref PUT/PATCH remain unproven.
- **Fix / do this:** Author ranking and trust in the model, and validate the winners visually in the Console's Source Records tab.
- **KB:** L-MDM-023, L-MDM-038, L-MDM-039

### PD-P2-024 Pin the consolidation field and value on the first live golden read
- **Date:** 2026-08-03
- **Context:** Reconcile poll design
- **Lesson:** The token `MATCH_INDEXED` was used with opposite meanings across design stages (pre-merge source index vs post-merge golden), and the real values are likely `CONSOLIDATED` / `UNMERGED`. An unpinned poll never ends or reports success on the un-merged state. Gating on `probe_runtime() == 'DEPLOYED'` tests deployment, not match completion, and `/data360/ingress/api/v1/jobs` 404s on both verbs.
- **Fix / do this:** Dump the raw golden JSON once (`--pin-dump`) and store the real key and value as a constant used by every gate.
- **KB:** new

### PD-P2-025 Size MDM pilots under the step-queueing thresholds; queued is normal
- **Date:** 2026-08-03
- **Context:** Pilot county choice
- **Lesson:** Match-key generation queues above 5k rows and index-for-search above 10k (transform above 100k, load above 1k). Nantucket (9,105) stays under the index threshold, while Middlesex (432,665) is 4.3x the 100k CSV cap. Other caps: CSV 100k rows / 100 MB, search/export 10,000, reports 500 rows / 100 total, ingress jobs queue above 25 per pod or 5 per org, address verification 1,000 per call. Match results expire 4 days after release, and a missed window repeats the run. 526,605 MA rows had NULL county_fips and could not be put in any county subset.
- **Fix / do this:** Pick a pilot slice from these caps, and schedule the UI match/merge re-run within the 4-day window.
- **KB:** L-MDM-034, L-MDM-035

### PD-P2-026 No server-side count: reconcile MDM ingest by a client tally plus by-id reads
- **Date:** 2026-08-03
- **Context:** Track A validation (~98,115 Idaho rows)
- **Lesson:** No count or list verb exists, so ingest is reconciled from the client's submitted/ok/fail counters against the extract count, plus spot reads by id. A clean pass over 0 rows means nothing. The expected result (~98,115 1:1 xrefs, zero consolidations, single source) is stated up front.
- **Fix / do this:** Fail the gate when the count is 0 or differs from the extract. Write down the expected outcome before running so a correct "nothing merged" is not read as failure.
- **KB:** L-MDM-028, L-MDM-045

### PD-P2-027 Steward inbox needs a role and a support ticket
- **Date:** 2026-08-03
- **Context:** Steward queue in C360
- **Lesson:** Adjudication needs the Customer 360 Data Steward (or MDM Admin) role plus Informatica GCS enabling the task inbox and ticket manager (preview in April 2026). Tasks expire after 365 days and are deleted 3 days later. Reads are headless; decisions are UI.
- **Fix / do this:** Open the ticket early and budget its lead time.
- **KB:** new

### PD-P2-028 MDM is the wrong tool for a 100M-row estate: cap it at a curated subset, route the estate to the warehouse and the catalog
- **Date:** 2026-08-03 / 2026-10-03
- **Context:** ~99-109M-row / ~1.2B-cell property estate; limits review
- **Lesson:** MDM search and export stop at 10,000 per query, CSV import is limited to 100 MB or 100,000 rows, reports show 500 rows, and jobs queue above 25 per pod or 5 per org. MDM is licensed by records, outside the IPU pool, and the record cost was unknown, so a 98.8M-golden national MDM number is neither achievable nor priced.
- **Fix / do this:** Keep MDM out of the sample-first phase. Later, master only a business-relevant subset (properties linked to accounts and deals, or a 2-state pilot). Keep the estate in ClickHouse for serving, and catalog it in CDGC.
- **KB:** L-MDM-056, L-MDM-034

### PD-P2-029 Two property universes that disagree: retire legacy rather than merge it
- **Date:** 2026-10-29
- **Context:** Legacy `<legacy_db>.<property_table>` (109.07M ids) vs gold (100.84M)
- **Lesson:** 15.6M ids were legacy-only (OH 36 % of the state, NC 36 %) and 7.39M gold-only. Fields drifted up to ~5 % on shared ids, and downstream tables keyed on legacy ids pointed at nothing in gold (<property_link_table> 10.9 %). About 15 legacy crons still wrote a table customers do not see.
- **Fix / do this:** Classify legacy-only ids read-only first (held candidates, never promoted, re-keyed). Then make a product decision per state, write only through the publisher, and retire legacy writers one cron at a time.
- **KB:** new

### PD-P2-030 Never re-key, a shared address is not a merge, and corrections must conserve rows
- **Date:** 2026-10-29
- **Context:** Gold write and repair rules from the pipeline runbooks (notes_for_change_plan DL-04/51/52)
- **Lesson:** State, city, address_norm and property_id are copied unchanged so that ReplacingMergeTree replaces the version. A shared address is not a merge, and probabilistic matches go only to a review queue. Fill-only by source rank (cama > crawl > listing > model); zero or unknown -> NULL; models never become observed facts. Corrections are a scoped `ALTER ... UPDATE` (`mutations_sync=2`) or a REPLACE PARTITION from a backup next to the table. The undo is written before the run (for example a `joinGet` undo table per state), and rows outside the target are asserted unchanged. A plain re-INSERT duplicates, so it is never used.
- **Fix / do this:** Keep keys stable, and route a key change through a re-key queue. After every promote or repair, run the same saved query per state partition before and after, to show non-target rows are unchanged.
- **KB:** L-METHOD-013

### PD-P2-031 Dictionary mastering: reconcile in both directions, one severity scale, one definition per rule id
- **Date:** 2026-11-02
- **Context:** data_dictionary (1.68M raw / 1.50M current)
- **Lesson:** Every live column was defined. 10 definitions had no live column, and 5 of them match nothing live or planned. Severity had 5 spellings (hard 41, error 170, soft 2, info 613, transform 2). 5 rule ids were defined 2-7 times. 59 groups (41,830 rows) repeated the same legacy -> target mapping. 26,858 mappings were unresolved and 34,781 only proposed.
- **Fix / do this:**
  - map severities to hard/soft/info in the load mapping, not by hand
  - keep one definition per rule id
  - collapse repeated mappings, carrying the value count
  - close `unresolved` in bulk by the legacy table's status (`retired_with_table`)
  - verify `proposed` by sampled value comparisons
  - tombstone orphan definitions (version + 1, needs a GO)
- **KB:** L-MDM-080, L-DQ-122

### PD-P2-032 Events: one canonical sale per conflict group, and incremental runs on changed fingerprints only
- **Date:** 2026-11-02
- **Context:** Property events in staging and incremental mastering
- **Lesson:** The finished table's sales, assessments and valuations must come from canonical events only (`sale_canonical = 1` per `sale_conflict_group_id`). Unknown-date and zero-value events are kept with a precision code. New observations flow through mdm_10 -> 20 -> 30 -> 40 for changed fingerprints only.
- **Fix / do this:** Key incremental work on an input fingerprint, and publish into the finished table.
- **KB:** new

### PD-P2-033 A safe deterministic property match key
- **Date:** 2026-11-01
- **Context:** `m_<prefix>_mdm_20_match_merge` (R1 source identity, R2 same physical property)
- **Lesson:** Same parcel is not same property (condos share a parcel; some feeds reuse parcel numbers across counties), and same address is not same property. The automatic merge key is state + ZIP5 + normalized parcel + normalized address + unit + class (lowest id survives), assigned with variable ports over warehouse-sorted input, writing one cross-reference row per observation. If the warehouse and the Expression normalize differently, a group is only split, never merged wrongly. On MA, 36,153 shared-address groups and 44,907 shared-parcel groups were all kept apart.
- **Fix / do this:** Merge automatically only on the full key; send the rest to review.
- **KB:** L-MDM-075

### PD-P2-034 Shard the golden read by hash: external sort alone still hit the memory cap
- **Date:** 2026-11-01
- **Context:** National golden records by state group
- **Lesson:** Group runs of 6-9M wide rows failed every try with "Query memory limit exceeded ... 9.31 GiB ... While executing MergeSortingTransform" even with `max_bytes_before_external_sort` at 2 GB, because the merge of spilled runs holds a block per run. `max_block_size=8192` plus `prefer_external_sort_block_bytes=4194304` brought a 7.4M-row read to an 8.5 GB peak; the robust fix was `p_shard` k/N with `cityHash64(property_id) % N = k` in every CTE (sharding on the master id). Final golden SQL settings: grace_hash join with 16 initial buckets, external group by 2 GB, external sort 1 GB, max_memory_usage 12 GB, 8 threads.
- **Fix / do this:** Shard big sorted reads on the master id; hash a non-null column, not `*`.
- **KB:** L-CDI-272, L-CDI-286

### PD-P2-035 Run national mastering in state groups of 6-9M observations
- **Date:** 2026-11-01
- **Context:** `backfill_v3/v4/v5`
- **Lesson:** Groups (TX, FL, CA, NY+OH, NJ+TN+MD, NC+GA+IN+PA+CT+MN, IL+WA+..., then 23 small states) bounded ClickHouse memory and the work lost to a failure; match runs of 6.2-9.5M rows completed per group, while golden needed hash shards on top.
- **Fix / do this:** Size groups by observation count, not by number of states.
- **KB:** L-CDI-272

### PD-P2-036 One golden owner: four builds in 12 days left a broken table behind
- **Date:** 2026-11-12
- **Context:** Property master history 11-01 to 11-12
- **Lesson:** The cutover chain into <property_table> (to 11-05), `m_<prefix>_mdm_*` (11-01), the phase-3 one-master pilots (11-07/08) and the SQL golden_master (11-09 on) all built the master; the old 302 GB table stayed broken and a CRM job still copied from it (~6.9k inserts a day).
- **Fix / do this:** One owner per golden scope; evolve one pipeline; repoint every reader before retiring the old table.
- **KB:** L-MDM-079

### PD-P2-037 Full rebuilds while under 1% changes: make mastering incremental
- **Date:** 2026-11-12
- **Context:** golden_master rebuilds
- **Lesson:** About 1.8B rows a day were rewritten across golden_master, golden_id_map, r8 and r9 (about 4 h of ClickHouse time) while only 850,912 rows (0.93%) changed per build. At IDMC's measured 1,100-18,000 rows/s, 1% of rows takes 1-13 minutes.
- **Fix / do this:** After the first load, run matching and survivorship only on changed input fingerprints.
- **KB:** L-CDI-093

### PD-P2-038 IDMC decides, SQL folds: the hybrid that keeps mastering in IDMC
- **Date:** 2026-11-12
- **Context:** Recommendation for the master
- **Lesson:** Rules, matching, survivorship and DQ run as transformations on changed records, write a scalar staging batch, then a short Post SQL merge folds it into the replacing table. Preconditions: incremental input, one parameterized mapping per step, tuned write settings, fixed AV job burn, a linear taskflow with a failing gate. Prove it on one state's changed records against the SQL result before replacing anything.
- **Fix / do this:** Compare IDMC and SQL winners for the same state before switching.
- **KB:** L-CDI-273

### PD-P2-039 IDMC merge decisions computed but never used
- **Date:** 2026-11-12
- **Context:** `r7_routed_*` and `r7_review_queue`
- **Lesson:** 29.7M IDMC merge decisions and a 3.56M-row review queue were read only by ad-hoc SELECTs while SQL re-derived duplicates with its own rules (golden_id_map, r7_exact_dups). IDMC's standardized facts (r7_dq2_*) and address verification were used. That left two rule sets for one decision.
- **Fix / do this:** Make the IDMC decisions the merge input, or retire the IDMC step.
- **KB:** new

### PD-P2-040 Standardized addresses never reached the match keys
- **Date:** 2026-11-12
- **Context:** Provisional rows in <property_table>
- **Lesson:** `address_canonical` and `address_norm` were blank on every provisional row, 49% of the old table stayed provisional, and about 17-19M likely duplicates were unmatched (12.85M provisional_address rows matched a confirmed row exactly by state+address).
- **Fix / do this:** Match only on standardized keys and fail the run when a match key is blank.
- **KB:** new

### PD-P2-041 The serving gate held, except for a 7-row leak
- **Date:** 2026-11-12
- **Context:** serving_eligible in the old table
- **Lesson:** Unconfirmed rows were not served apart from 7 provisional_address rows in SD (written by `native:m_<prefix>_tbl_0788_SD` on 11-03 09:41Z with the address unverified).
- **Fix / do this:** Make "nothing served unverified" an exact gate check in the run, not a later audit.
- **KB:** L-DQ-136

### PD-P2-042 Gates measured but not enforced
- **Date:** 2026-11-12
- **Context:** National go-live
- **Lesson:** Checks G1-G9 were written, but New Jersey (about 3M properties) never entered the master, 7 unverified rows were served, and the 'passed' stamp went unchallenged, because no gate stopped a publish.
- **Fix / do this:** Run a check mapping that fails the run (one row per property, every state present, nothing served unverified, no duplicate addresses, hard DQ rules) before any publish.
- **KB:** L-DQ-132, L-DQ-136

### PD-P2-043 Measure matching against a truth set before scaling
- **Date:** 2026-11-07
- **Context:** SD identity pilot `m_<prefix>_onemaster_sd_identity_native`
- **Lesson:** 235,734 rows became 169,916 properties with 0 wrong merges on 939 checked pairs and 1 wrong merge on a 381-pair county-GIS truth set; native quality rules reproduced the earlier run exactly.
- **Fix / do this:** Keep a truth set and skeptic pair checks per scope.
- **KB:** L-METHOD-046

### PD-P2-044 Protect the rows mastering reads, and keep live DQ assets out of Archive
- **Date:** 2026-11-01
- **Context:** Coordination between the MDM lane and the consolidation lane
- **Lesson:** Match and golden read `record_kind='property_state' AND record_stage='bronze'` (63.7M rows); the MDM session asked the capture owner to keep them or announce a replacement. Older DQ assets (`rs_<prefix>_us_state`, `rs_<prefix>_us_zip`, `rs_<prefix>_required_text`, `cls_<prefix>_address_text`, `vfr_<prefix>_address_verify_status`) were live inputs and had to stay in 02 Data Quality, not Archive (ids survive a move either way).
- **Fix / do this:** Publish each pipeline's input contract and asset dependencies before another lane archives or replaces them.
- **KB:** L-MIG-034

### PD-P2-045 Write gold v2 into a work table before the swap
- **Date:** 2026-11-01
- **Context:** Gold v2 (every old-gold column, history, hierarchy, DQ, verified address)
- **Lesson:** The plan was to build into `<work_db>.<property_table>_gold` with the delivered table's DDL through a connection bound to `<work_db>`, then rename in the swap phase, never touching `<prod_db>.<property_table>` during the build. No paid geocode or CASS add-on was enabled without the owner.
- **Fix / do this:** Build replacements beside the live table and swap atomically.
- **KB:** L-ENV-106

### PD-P2-046 Per-state go-live needs a recorded reason for every switch and rollback
- **Date:** 2026-11-12
- **Context:** Pages switched onto golden_master
- **Lesson:** WY, AK, HI, SD and MT went live per `golden.mode`. DE, ME and NH switched 02:53-03:14Z with every check passing and were rolled back 03:24-03:25Z (fingerprints restored exactly) with no reason recorded. Decisions existed only in `/var/log/phase3-g5-switch.log`, with no tracker claim.
- **Fix / do this:** Keep per-state GO plus undo, but write each decision and its reason on the tracker.
- **KB:** new

### PD-P2-047 Turn judgement holds into rule specifications
- **Date:** 2026-11-12
- **Context:** WY hold on federal-estimate square footage (58,828 pages)
- **Lesson:** A manual "owner decides" hold on estimate-only living area could be a rule (`rs_<prefix>om_*_source_backed_native`) so survivorship is consistent across states.
- **Fix / do this:** Encode recurring judgement calls as rule specifications that gate serving.
- **KB:** new

### PD-P2-048 Link ML model versions to the master publication
- **Date:** 2026-11-12
- **Context:** <model_registry>
- **Lesson:** 0 of 2,887 model versions were linked to a publication id, so no model can be traced to the master it trained on.
- **Fix / do this:** Record the publication id with every model version as a step after each build.
- **KB:** new

### PD-P2-049 A mapping-based MDM works at state scale; it broke on the way to national
- **Date:** 2026-11-12
- **Context:** Review of the home-grown MDM
- **Lesson:** MA (2,519,596 records to 2,516,176 masters, 0 differences on single-source masters, 2,167,667 serving, average DQ 97.7) and SD proved the pieces. National failed on design: full rebuilds, no pushdown, default write settings, per-state copies, logic in SQL text, session orchestration and no job budget. Calling the SQL fold "IDMC MDM" is wrong in a customer conversation.
- **Fix / do this:** Pilot one scope, measure rows/s, jobs and memory, then fan out; keep rules as transformations.
- **KB:** L-MDM-081, L-MDM-052, L-DQ-004

### PD-P2-050 Listing and sale semantics: absence is not a sale; identities need corroboration
- **Date:** 2026-10-09
- **Context:** market and sale contracts
- **Lesson:** Rules in the contracts:
  - Disappearing from a feed or a partial crawl never means sold or off-market.
  - A closed sale closes a listing only for the same listing URL and MLS id, with a source observation at least as new and at most 48 h old.
  - New sales carry `arms_length=NULL`, `training_eligible=0`.
  - The first contract accepts only exact, unique single-family identities with a valid ZIP and coordinates within 100 m.
  - Never create a property from a listing id or a nearby point. Preserve leading zeros, hyphens and unit tokens.
- **Fix / do this:** Encode these rules in versioned contracts with tests, and keep ambiguous matches in a replayable hold queue.
- **KB:** new

### PD-P2-301 Name the golden master fully and give it one owner
- **Date:** 2026-11-12
- **Context:** the national property master built in SQL beside the match map
- **Lesson:** The live master is `<work_db>.golden_master`, with its match map `golden_id_map` in the same database, built in straight SQL (matching via the match map and an exact-duplicate table). At about 92M properties across 50 of 51 states, one owner session moves pages onto it state by state behind a mode switch, and the old master table is left alone rather than rebuilt in parallel.
- **Fix / do this:** Always refer to the master as `<database>.<table>` in docs and lessons; record its single owner; never start a second master build beside it.
- **KB:** new

## Catalog & governance

### PD-P2-051 First catalog scan = Metadata Extraction only, behind an asset tripwire, with automation off; profile once the asset list is clean
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** CDGC source <sample>_pg (V3 decision 21), cloned from the host-app sources
- **Lesson:** The templates were the host-app sources: GET `/ccgf-catalog-source-management/api/v1/datasources/<id>`, then a multipart POST. Their defaults can create DQ schedules and rule-occurrence work, and can pull in unwanted assets, so the source was created with Run Rule Occurrence Frequency = false and Data Quality Automation = false. The first run was Metadata Extraction only: `POST /data360/executable/v1/catalogsource/<id>` with {"capabilityNames":["Metadata Extraction"]} ran 7 min 18 s with 4 tasks (Test Connection, Extraction, Metadata Extraction, Bulk Ingestion), polled with `observable/v1/jobs/<id>?expandChildren=TASK-HIERARCHY`, and counted as 1 metered job. Profiling, classification and DQ ran only after the asset list showed only <sample_db> tables. Other settings: asset tripwire 2,000, Metadata Change Option = Delete, classification auto-accept threshold set at creation, an include filter covering the sample only, one scan at a time. The scan completed with 426 assets (include <sample_db>/public only) and 132 term links.
- **Fix / do this:** Create sources with automation off, scan metadata first, check that only the intended schema arrived against the tripwire, then add capabilities.
- **KB:** L-CDGC-152, L-CDGC-028, L-CDGC-035, L-CDGC-021, L-CDGC-027, L-CDGC-061, L-CDGC-034, L-CDGC-037, L-CDGC-103

### PD-P2-052 CLAIRE classifications stay "generated" unless auto-accept is set, and the threshold can't be set over REST: set it in MCC before the first run, exact matches only
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** Sample PII classification, gate G6 / G6a (PII classes on the register columns)
- **Lesson:** CLAIRE-generated classifications have no public REST bulk-accept route. Accepting them needs the Data Classification auto-accept threshold plus a rescan. The 10-03 plan assumed the threshold could go in the source body; on 10-04 the PostgreSQL Data Classification type configuration had no option groups, and the capability layer offers only "Data Classification Inference Type", so the threshold is a UI step. Promoting non-exact CLAIRE classes corrupts governance. On a masked sample, an empty PII class list is the expected result.
- **Fix / do this:** Set the threshold in the MCC capability config (Playwright) at source creation, before the first classification run, to exact built-in matches only. Gate on "zero HIGH-sensitivity columns" as a leak check, and keep the PII register as the system of record.
- **KB:** L-CDGC-061, L-CDGC-062; REST gap new

### PD-P2-053 Apply a built-in classification headless with PATCH dataClassification, after checking the class exists
- **Date:** 2026-10-03
- **Context:** PII register §3
- **Lesson:** The call is `PATCH .../data360/content/v1/assets/<columnIdentity>?scheme=internal` with segment `dataClassification`. Only built-in classes that exist in the org can be applied. Proven in the org: `Email` and `Phone Number USA`. Confirm any other class with an ES term search on `core.classType = core.DataElementClassification`. A hashed column is no longer a name, so give it no class.
- **Fix / do this:** Verify the class exists, then PATCH it.
- **KB:** L-CDGC-060, L-CDGC-079

### PD-P2-054 DAM policy authoring is walled: enforce privacy with DB-side masking and pushdown views
- **Date:** 2026-10-03
- **Context:** PII enforcement
- **Lesson:** Data Access Management policy authoring had no REST API on the probed orgs.
- **Fix / do this:** Enforce privacy in the warehouse (masking in the export, pushdown views), not with an IDMC policy.
- **KB:** L-CDGC-067

### PD-P2-055 A second business in a shared org needs its own glossary domain with explicit text, and a regression check on the host's prompts
- **Date:** 2026-10-03
- **Context:** DOM-14 "<Platform> — Property Data Foundation" (45 terms) next to the host app's DOM-13 in the org
- **Lesson:** Governance is org-scoped, and CLAIRE GPT answers from the domain and term descriptions. The host-app glossary in the same org was tuned to answer 18/18 questions. The property-platform domain description says plainly that it is a separate business, and no term name collides with the host app's, so property questions do not bleed into host-app answers and vice versa. The glossary load created 45 terms (Published) with a registry keyed by term_id, not by BT number, since BT numbers differ per org. CLAIRE's index takes hours to catch up after content changes.
- **Fix / do this:** Give each business its own domain, project, source and prefixes, with a description that states what the domain is and is not. Re-run the host's CLAIRE prompt set after each catalog change, once the index has caught up, and freeze catalog changes for 24 h before a demo.
- **KB:** L-CDGC-072, L-CDGC-050, L-MCP-062, L-CDGC-009

### PD-P2-056 The glossary is fully headless except stewards and bulk classification accept: create terms, link them after the first scan, keep a RACI
- **Date:** 2026-10-03
- **Context:** Glossary load, domain "<Platform> — Property Data Foundation" (45 terms)
- **Lesson:** The glossary steps:
  - **Domain:** `POST idmc-api/data360/content/v1/assets` with core.classType Domain returns DOM-<n>.
  - **Term:** a BusinessTerm with parent.core.identity returns BT-<n>, already Published.
  - **Links and classifications:** links use the PATCH "glossary" segment, after the first scan (gate: ≥ 40 links); classifications use "dataClassification".
  - **Ids:** resolve them by externalId search.

  CLAIRE GPT cannot create terms. Stakeholder (steward/owner) assignment has no REST write, and the Data Owner / Data Steward roles must exist in Administrator first, or the picker is empty. Bulk classification accept needs the auto-accept threshold plus a rescan. The 9-role RACI stays the store of record.
- **Fix / do this:** Drive the build from an idempotent registry with an undo file. Link terms after the first scan. Keep steward roles as a table in code and assign them in the UI once the roles exist.
- **KB:** L-CDGC-050, L-CDGC-051, L-CDGC-052, L-CDGC-053, L-CDGC-056, L-CDGC-060, L-CDGC-061, L-CDGC-066

### PD-P2-057 Count terms in a domain by ES classType plus parentLocation
- **Date:** 2026-10-04
- **Context:** gate G6a
- **Lesson:** POST `data360/search/api/v1/search?knowledgeQuery=*&segments=all` with header X-INFA-SEARCH-LANGUAGE: elasticsearch and a term query on core.classType (`com.infa.ccgf.models.governance.Domain` / `.BusinessTerm`). Match the domain by core.name, then keep terms whose `__meta.parentLocation` = `CDGC://<domain core.identity>`. Count assets per source with a term query on `core.origin` = the source id.
- **Fix / do this:** Use ES term queries, page in steps of 200, and set a cap.
- **KB:** L-CDGC-073, L-CDGC-079

### PD-P2-058 Read catalog sources and scan jobs from ccgf datasources and observable jobs
- **Date:** 2026-10-04
- **Context:** guard and gate CDGC reads
- **Lesson:** Sources: `GET cdgc-api.<domain>/ccgf-catalog-source-management/api/v1/datasources?offset=0&limit=100` (and `/datasources/<id>`). Jobs: `GET idmc-api.<domain>/data360/observable/api/v1/jobs?limit=100&offset=N`. A job belongs to a source when its name starts with the source name or its input/output properties carry the source id. The CDGC job history reaches further back than the activity log, and showed 1-4 CDGC jobs a day through September.
- **Fix / do this:** Filter jobs by source id or name, and stop paging after about 32 days.
- **KB:** L-CDGC-037

### PD-P2-059 How to cancel catalog scans and profiles, and what has no headless route
- **Date:** 2026-10-03
- **Context:** Plan v3 limits; tripwires "scan > 90 min → stop" and "PSI/OOM → stop profile"
- **Lesson:** On 10-03 no REST scan cancel was known, so the plan bounded scans with a 90 min / 2,000 asset tripwire; a stuck scan locked the source (406 on rerun). A catalog-job cancel was found later, which overturns the "no REST cancel" belief: `POST cdgc-api.<domain>/ccgf-orchestration-management-api-server/api/v1/jobs/<jobId>/operations/cancel`. Profiling has no REST cancel; only killing pmdtm on the host stops a run. runDetail returns 400 PROFILE_SVC_00093 for subtask reads.
- **Fix / do this:** Use the ccgf orchestration cancel for catalog jobs, and keep the tripwire anyway as a pre-run refusal. Size runs so that "cannot stop once started" is acceptable for profiles, and keep an owner-run procedure for killing pmdtm and cleaning up.
- **KB:** L-CDGC-040 (superseded), L-CDGC-221

### PD-P2-060 A BigQuery catalog scan needs bigquery.jobs.create in the connection's project: the scanner runs INFORMATION_SCHEMA SQL as jobs there
- **Date:** 2026-10-04
- **Context:** CDGC source <sample>_bq on dataset <other-project>.<sample_ds> (scan a2dee7dd); the service account had dataset READER only
- **Lesson:** The BigQuery scanner runs its metadata SQL as query jobs in the connection's Project ID: `region-US`.INFORMATION_SCHEMA.SCHEMATA plus unqualified `<dataset>`.INFORMATION_SCHEMA.*. With dataset READER only, the connection test still passed (1.1 s) and v2 browse returned 200 []. The scan FAILED after about 2 min with "Scan finished with abnormal exit status. Reason: No input was processed". The real 403 ("does not have bigquery.jobs.create permission") appears only in `Metadata_Foundation_Agent/data/workspaces/<source>-*/logs/`. Dataset READER grants datasets.list, tables.list and tabledata.list, but not jobs.create, so those calls succeeding proves nothing about scanning. A working copy in the connection's own project (the connection's own project) scanned fine: scan 4b9c9900 COMPLETED with 11 assets.
- **Fix / do this:** Before scanning, dry-run one query whose job runs in the dataset's project; a 403 means you will hit this wall. Grant roles/bigquery.jobUser plus project-level metadata read there, or keep the dataset in the project where the connection's key can create jobs.
- **KB:** L-CDGC-154 (disputed), L-CDGC-182, L-CONN-016, L-CONN-034
- **Status:** partly superseded by PD-P2-266: only the dataset-in-another-project form was scanned; the include-filter form (connection in its own project, `<other-project>.<ds>.*`) was never tested, so "cross-project fails in every form" is unproven.

### PD-P2-061 Each BigQuery catalog scan bills about 346 MiB of INFORMATION_SCHEMA even for a 10-row dataset
- **Date:** 2026-10-04
- **Context:** Catalog source <sample>_bq; fallback scan of <own-project>.<sample_ds>
- **Lesson:** One scan ran 11 INFORMATION_SCHEMA jobs in 8 s and billed 362,807,296 bytes (`region-US`.TABLE_STORAGE alone was 176 MiB). The lane reported "0 bytes" because it looked only at the gateway query. The cost scales with the project's metadata, not the dataset's size, so scans were limited to 4 a month.
- **Fix / do this:** After each scan, sum total_bytes_billed from the connection service account's job list (jobs?minCreationTime=...). Budget BigQuery metadata scans by count, not by data size, and avoid frequent rescan schedules.
- **KB:** L-CDGC-155

### PD-P2-062 Choose the CLAIRE GPT sample store by what the Data Gateway can read: BigQuery only, and it picks the first connection whose key it can open
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** CLAIRE GPT "Query the data" scope; synthetic BigQuery sample
- **Lesson:** The Data Gateway reads BigQuery V2. It refuses PostgreSQL, and ClickHouse is not listed, so a Postgres sample cannot be queried. It runs only on one agent (the off-prod tooling agent). Its limits are a 100 rows × 100 cols preview, a 60 s query timeout and a 30 min cache. Answers take 30-200 s, and named-table search misses about 1 in 6. Catalog, glossary, profiling, rules, scores and trust prompts all work on a Postgres sample. The CDI-key-form connection <APP>_BQ_SAMPLE could not be opened by the gateway, so the query ran on the host-app connection <HOST_APP>_BQ_DBMI instead. MCP data_explore "How many rows are in <prefix>_synth_probe?" answered 10 in 33 s. Under the "no BigQuery for property-platform data" rule, only synthetic data (10 rows, tables expiring after 30 days) was allowed there.
- **Fix / do this:** Decide the sample's store by what the gateway reads before building the sample. Without BigQuery, drop "Query the data" from the scope and demo the read-only prompts instead. Check which connection actually served each query.
- **KB:** L-MCP-121, L-MCP-125, L-MCP-060, L-MCP-114, L-MCP-061, L-AGENT-051, L-MCP-103, L-AGENT-097

### PD-P2-063 Prove a BigQuery dataset exists or is gone with 404-vs-403 name probes, a made-up control name and a full listing
- **Date:** 2026-10-03
- **Context:** BigQuery <legacy_ds> and siblings (deleted 09-10); verifying the deletion
- **Lesson:** Earlier specs assumed a BigQuery copy existed, but it had been deleted. Even an identity with no BigQuery rights gets "Not found" (404) for a missing dataset and "Access Denied" (403) for an existing one from `bq show`. A made-up control name proved the probe tells the two apart. Absence was verified at 22:29Z by these name probes plus a full listing of the project's datasets.
- **Fix / do this:** Before you design on an assumed dataset, prove that it exists or that it is absent. Always include a control name, and confirm with a privileged datasets.list when possible.
- **KB:** L-ENV-041

### PD-P2-064 Keep the guest's assets out of the host's catalog includes, and re-run the host's prompt set after each change
- **Date:** 2026-10-03
- **Context:** Explore project of the property platform, `<host_app>_idmc_cdi` include, gate G14
- **Lesson:** The property platform objects use the `<prefix>_` prefix and the tag `<app>`, and are kept out of the host-app IICS include filter. After any property-platform catalog change, the host-app CLAIRE prompt set must still answer the same way (G14).
- **Fix / do this:** Isolate the guest by project, prefix and include filter. Baseline the host's prompts before the first scan.
- **KB:** new

### PD-P2-065 Lineage: view lineage on the sample in IDMC, full-estate lineage in OpenMetadata
- **Date:** 2026-10-03
- **Context:** decision 23
- **Lesson:** IICS lineage was skipped because there is no CDI except the parity task. OpenMetadata covers ClickHouse (no IDMC connector) through the daily provenance crawl plus the dbt manifest. The estate PII tags (G6b) come from the register CSV, not mirrored from IDMC.
- **Fix / do this:** Split governance between tools by what each can reach.
- **KB:** new

### PD-P2-066 An unsalted hash of an owner name is not pseudonymization
- **Date:** 2026-10-03
- **Context:** PII register F6
- **Lesson:** Names are low-entropy, and a dictionary built from public owner rolls reverses a plain SHA-256.
- **Fix / do this:** Use a keyed hash with a secret salt held outside IDMC, or better, do not stage the field at all.
- **KB:** new

### PD-P2-067 Masking rule set M0-M6 and an explicit allowlist export
- **Date:** 2026-10-03
- **Context:** PII register §4
- **Lesson:** M0 exclude; M1 presence flag; M2 keyed hash; M3 generalize; M4 keep public-record columns; M5 extract allowlisted JSON keys only; M6 never stage app or identity stores (Keycloak, IAM, MCP, app DBs, Mongo app collections). The export must be an explicit column allowlist, never SELECT *, so a new column stays out until it is classified.
- **Fix / do this:** Default to exclusion and register every column before it is staged.
- **KB:** new

### PD-P2-068 Connections to personal-data stores: metadata only, never profiling or classification sampling
- **Date:** 2026-10-03
- **Context:** <APP>_PG_MCP (mcp_audit 1,229 rows), <APP>_PG_APP
- **Lesson:** If such stores are ever cataloged, it must be metadata only, with no Data Profiling and no Data Classification sampling. Here the connections were deleted.
- **Fix / do this:** Never point a profiling-enabled scan at an identity or app store.
- **KB:** new

### PD-P2-069 Automated PII classifiers miss columns: keep a register CSV as the record and inspect new tables
- **Date:** 2026-10-03
- **Context:** pii_columns.csv (183 rows)
- **Lesson:** An earlier KB register listed 47 columns, but 110 more owner/mailing columns in raw county tables had been tagged "Free text"/"Address" (for example OWNERNAME, MAILNME1, FullOwnerAddress). New tables need a DESCRIBE before they are trusted.
- **Fix / do this:** Treat the CSV register as authoritative and mark uninspected tables VERIFY (treat as HIGH).
- **KB:** new

### PD-P2-070 Governance score per table: 11 checks beyond DQ
- **Date:** 2026-11-02
- **Context:** DG part of the evaluator (DG 36-55 at baseline)
- **Lesson:** The checks: every column defined in the dictionary, sensitivity classified (more than one access tier), columns with a testable rule, source mappings resolved, IDMC profile exists / covers the table / has rules bound and run, CDGC rule occurrences, glossary term, dataset with lineage via CDI, and a relational scan of the table. The usual misses were sensitivity tiers, rule occurrences and the relational scan.
- **Fix / do this:** Bind rules on profiles, publish CDGC rule occurrences (contentv2 publish + dataQuality/sync), and run a relational catalog scan of the tables themselves.
- **KB:** L-CDGC-161

### PD-P2-071 CDGC lineage shows "SQL blob -> table" when logic lives in the Source query
- **Date:** 2026-11-02
- **Context:** Why the mastering mappings were rebuilt
- **Lesson:** With survivorship inside a SQL Source and much of the finish run as SQL in work tables (`u_stage`, `u_slots`, `u_val`), IDMC profiled and moved the data but did not clean it. The catalog showed no transformation-level lineage.
- **Fix / do this:** Make each fixing step a visible transformation, so that CDGC lineage and CLAIRE can see it.
- **KB:** L-MDM-081, L-CDI-293

### PD-P2-072 One door into gold: named writer logins and an alert on any other writer
- **Date:** 2026-10-29
- **Context:** Gold write control
- **Lesson:** Gold was written by the publisher and by the shared admin `default`.
- **Fix / do this:** Grant writes only to `<app>_gold_publisher` and one named `gold_repair` login, and make `default` read-only on gold. Check `query_log` nightly for gold writes by any other login (filter on query_kind and the target table, because tables[] also lists the tables a query reads).
- **KB:** L-ENV-118, L-ENV-116

### PD-P2-073 Turn a proven pilot into a KB blueprint with synthetic tables and gates
- **Date:** 2026-11-02
- **Context:** Making the mastering method re-creatable
- **Lesson:** After the pilots pass, the same specs (with placeholders), one tiny synthetic table per archetype with planted duplicates, the gates and the expected results go into a KB blueprint (`demos/table-mastering/`). A reader can then rebuild and check the process in their own org.
- **Fix / do this:** Ship the method as specs + sample data + gates + expected results, and never with deployment ids.
- **KB:** new

### PD-P2-074 SQL steps are invisible to lineage; measure how much is IDMC-built
- **Date:** 2026-11-12
- **Context:** golden_master provenance
- **Lesson:** 81% of old gold rows were stamped by 'native:' SQL steps and the national master was straight SQL, so the catalog shows none of it. Lineage stamps can be checked as data: a rule that accepts only a real 20-character IDMC object id.
- **Fix / do this:** Stamp IDMC ids on every row an IDMC step writes and score the share of IDMC-built rows.
- **KB:** L-CDI-295

### PD-P2-075 Catalog-source creation and accepting CLAIRE classifications were UI steps
- **Date:** 2026-08-01
- **Context:** Plan to catalog the DigitalOcean data stores
- **Lesson:** Creating a catalog source per datastore and accepting CLAIRE-suggested classifications had no REST verb; the scan run and its results were REST-readable. A 202/201 on scan start means submitted, not completed.
- **Fix / do this:** Poll per-item status after a scan start; plan one UI step for the source definition.
- **KB:** L-METHOD-037
- **Status:** superseded by PD-P2-105 for catalog-source creation (sources were later created over REST by multipart POST to ccgf-catalog-source-management, see also PD-P2-085); accepting CLAIRE classifications is still a UI step (PD-P2-052).

### PD-P2-076 Price catalog scans and profiling before pointing them at big tables
- **Date:** 2026-08-01
- **Context:** CDGC on the 385M-row property-platform warehouse
- **Lesson:** Scans and profiling bill IPUs, and an unthrottled multi-engine run had OOM-killed ClickHouse on the 7.8 GB box; IDMC's scanner has no memory guard of its own.
- **Fix / do this:** Scope the first scan to the curated core (~25 tables), run off-peak with row limits, and get spend sign-off.
- **KB:** L-DQ-159, L-AGENT-052

### PD-P2-077 A cloned catalog source schedules hidden DQ jobs
- **Date:** 2026-10-03
- **Context:** Plan to clone <host_app>_bq into a property-platform catalog source
- **Lesson:** The host-app source body sets "Run Rule Occurrence Frequency: true" and "Data Quality Automation: true, Apply on all Data Elements". The org also has auto-generated DQ_Capability_Schedule_Daily/Weekly/Monthly schedules. An unchanged clone would run rule occurrences on IDMC-side schedules that never appear in the activity log, and would attach rules to every element.
- **Fix / do this:** Create the clone with Rule Occurrence Frequency=false and DQ Automation=false, and make the first run Metadata Extraction only. After each accept, check that no DQ_Capability schedule references the new rules.
- **KB:** L-CDGC-152

### PD-P2-078 A cloned string precision of 50 breaks parity with dbt
- **Date:** 2026-10-03
- **Context:** Cloning the <host_app>_bq typeCapabilities
- **Lesson:** "Maximum Precision of String Fields = 50" is set in both the DQ and the Profiling scope groups. Length and regex rules on longer strings (for example address_norm) would then evaluate 50-character prefixes in IDMC but full strings in dbt.
- **Fix / do this:** Set the precision to at least the longest sampled string (255-4000), and copy the full scope groups when cloning.
- **KB:** L-CDGC-216 (field required); truncation parity risk = new

### PD-P2-079 Metadata Change Option = Delete plus a table swap deletes assets and their links
- **Date:** 2026-10-03
- **Context:** Planned atomic swap of the sample tables
- **Lesson:** With Delete set, a scan that runs mid-swap, or a swap that renames the table, deletes the catalog asset together with its RuleInstances and glossary links.
- **Fix / do this:** Refresh with CREATE OR REPLACE or WRITE_TRUNCATE so the table keeps its identity, and have the guard refuse a scan while a swap is in progress.
- **KB:** L-CDGC-028 (setting); swap hazard = new

### PD-P2-080 CLAIRE goes blind after scans, and duplicate assets confuse it
- **Date:** 2026-10-03
- **Context:** Adding a property-platform catalog source to an org with live host-app CLAIRE prompts
- **Lesson:** A rescanned source cannot be answered for hours, and CLAIRE is blind while a scan runs. Duplicate assets confuse its answers (7 "curated-members" assets already existed). A mis-scoped include filter would duplicate the host-app assets.
- **Fix / do this:** Wait 2-3 h after a scan before CLAIRE steps, and re-run the host-app regression prompts after every catalog addition. Scope include filters tightly and set the asset tripwire near the expected count.
- **KB:** L-CDGC-090, L-MCP-103

### PD-P2-081 Plan where profiles and specs live before you create them
- **Date:** 2026-10-03
- **Context:** DQ_<PREFIX>_* profiles sat in the host app's shared folder (119 objects)
- **Lesson:** FRS MoveEntities does move profiles (FRS_108 marks orphan documents left by failed creates). Placement still matters, because a catalog source that includes the shared DI project mixes property-platform objects into the other app's lineage and cleanup scripts.
- **Fix / do this:** Before creating profiles, create an app Explore project with a tag and the <prefix>_ prefix, keep it out of the other app's IICS include, and move CLAIRE-published specs out of the shared CLAIRE project.
- **KB:** L-DQ-029 (disputed), L-DQ-124

### PD-P2-082 Lineage needs views or an IICS source, not plain table loads
- **Date:** 2026-10-03
- **Context:** The property platform sample loaded as plain Parquet tables
- **Lesson:** Plain table loads produce no lineage in CDGC. A database scan derives lineage only from view SQL with Lineage Discovery on, or from CDI mappings through an IICS source.
- **Fix / do this:** Load one base table and expose the sample and summary tables as views. Enable Lineage Discovery, and gate on at least 2 hops via MCP get_asset_details.
- **KB:** L-CDGC-087, L-MCP-107

### PD-P2-083 Re-derive table and schema names from the live DDL
- **Date:** 2026-10-04
- **Context:** Tooling-VM DB built as public.pu_s1_ma while the DDL still ran CREATE SCHEMA <sample_db>
- **Lesson:** The stale DDL would have created the table in another schema, which the `public.*` include filter would miss without any error. The demo prompts also used a table name that does not exist (pu_sample_ma).
- **Fix / do this:** After building, re-derive table, schema and connection names from the live DDL and the catalog source, then align cards and prompts to them.
- **KB:** new

### PD-P2-084 The OpenMetadata ingestion SDK minor must match the server minor
- **Date:** 2026-10-03
- **Context:** Reusing the IDMC→OpenMetadata loader built for OM 1.13 against OM 1.5.11
- **Lesson:** The loader pins openmetadata-ingestion==1.13.*, so it does not work as-is against OM 1.5.11. The bot JWT had never been obtained, and the ingestion container does not mount the dbt folder.
- **Fix / do this:** Re-pin to 1.5.x in an isolated venv. Get the bot JWT from the pipeline configs inside the ingestion container, and copy manifest.json and run_results.json into it each run.
- **KB:** new

### PD-P2-085 Headless routes the plan could rely on
- **Date:** 2026-10-03
- **Context:** Tech-feasibility "SOUND" checks
- **Lesson:** These routes were proven to work:
  - CDGC typeCapabilities, with the RE in both the DQ and the Profiling scope groups;
  - catalog-source create by multipart POST and update by multipart PUT;
  - RuleInstances found by class search;
  - TechnicalRuleReference = frsId;
  - v3 export of RULE_SPECIFICATION;
  - glossary content through data360/content/v1/assets plus a glossary-segment PATCH;
  - `POST /profile/<id>/execute`.
- **Fix / do this:** Build on these routes, and label everything else "untested" until a spike passes.
- **KB:** L-CDGC-143, L-CDGC-020, L-CDGC-144, L-CDGC-145, L-DQ-094, L-DQ-010, L-DQ-011, L-DQ-019

### PD-P2-086 Regenerate glossary content when the staging design changes
- **Date:** 2026-10-03
- **Context:** Glossary draft still described the old Postgres-stage sample, with 131 links using PG-stage external IDs
- **Lesson:** CLAIRE answers from glossary descriptions, so stale text produces wrong answers. Link external IDs depend on the catalog source's format.
- **Fix / do this:** Before loading, re-render the domain text, the terms and the link plan in the target source's external-ID format.
- **KB:** L-CDGC-072

### PD-P2-087 ClickHouse cannot be a CDGC catalog source, and its wire-protocol fallbacks are weak
- **Date:** 2026-10-03
- **Context:** Catalog design
- **Lesson:** ClickHouse has no native scanner. JDBC-based scans end COMPLETED WITH ERRORS and drop constraints and FKs. The MySQL wire protocol (port 9004) would need a config change and a restart on the prod host. The Postgres wire protocol (9005) lacks pg_catalog.
- **Fix / do this:** Catalog a Postgres or BigQuery sample in IDMC. Use OpenMetadata, with a read-only user, for the full ClickHouse estate.
- **KB:** L-CONN-030, L-CDGC-023, L-CDGC-024, L-CONN-057; wire-protocol part new

### PD-P2-088 Default privileges expose scratch tables to the catalog scan
- **Date:** 2026-10-04
- **Context:** Tooling-VM sample DB before the <sample>_pg scan
- **Lesson:** Default privileges gave the read-only IDMC role SELECT on the synthetic table public.pu_s1_ma_synth, so the catalog would have listed it.
- **Fix / do this:** Before profiling or classification scans, REVOKE SELECT on scratch and synthetic tables (or fix the default privileges). Then check that the asset list shows only the sample.
- **KB:** new

### PD-P2-089 CDGC concurrency and API limits that shape scan windows
- **Date:** 2026-10-03
- **Context:** Limits lane
- **Lesson:** Each source allows one job at a time; a second start gets 406 "Job is in progress". Every scan is IPU-metered. Search totals stop at 10,000 (`gte`), and the catalog was already over 10,000 assets. Asset and search walks hit 429, so pace them at 0.8-4 s.
- **Fix / do this:** Walk the APIs sequentially. Watch scan state through `data360/observable/api/v1/jobs`. Stop a scan at more than 90 min or more than 2,000 app assets. Freeze rescans for 2 h before a demo.
- **KB:** L-CDGC-013, L-CDGC-040, L-CDGC-090, L-CDGC-158, L-CDGC-103

### PD-P2-090 CDGC write-backs: lineage writes are no-ops, so catalog a results table instead
- **Date:** 2026-10-03
- **Context:** Flowing dbt scale results back into the catalog
- **Lesson:** `/data360/lineage/*` returned 404 on 25+ variants. ccgf-contentv2 publish of data-flow edges returned 207 with items:[], so nothing was written. There is no DQ-score import API. A catalogued results table shows only metadata from its last scan and never merges into the DQ score. A rescan can blank curated descriptions.
- **Fix / do this:** Write `dq_scale_summary` into the sample DB and catalog it, worded as "a queryable table; the DQ score covers the sample only". Re-apply description PATCHes after each rescan.
- **KB:** L-CDGC-085, L-CDGC-065, L-CDGC-054, L-CDGC-055, L-CDGC-016, L-DQ-031, L-MCP-058

### PD-P2-091 Existing lineage sources and MCP servers already cover new assets
- **Date:** 2026-10-03
- **Context:** The property platform lineage path
- **Lesson:** IICS source <host_app>_idmc_cdi already includes the host app's DI project, but its stitching filter lists only the host app's sources. The managed MCP search_metadata and get_asset_details cover any catalogued asset after its next scan.
- **Fix / do this:** Add no new MCP server or tool connection. Add the app's source to the stitching filter only if IICS lineage is wanted. Gate: a read-only MCP call returns the app's assets.
- **KB:** L-CDGC-085

### PD-P2-092 Split PII governance: IDMC classifies the sample, the open-source catalog tags the estate
- **Date:** 2026-10-04
- **Context:** Gates G6a/G6b
- **Lesson:** IDMC only ever sees the masked sample, so its classifications cannot govern the full estate.
- **Fix / do this:** G6a checks the accepted built-in classes on the sample's quasi-identifiers, with zero HIGH columns. G6b checks OpenMetadata tags taken from `pii_columns.csv` (183 rows, the system of record), not mirrored from IDMC.
- **KB:** new

### PD-P2-093 Use the open-source catalog for the full estate, and copy dbt artifacts into it
- **Date:** 2026-10-03
- **Context:** OpenMetadata 1.5.11, daily crawl cron
- **Lesson:** OpenMetadata catalogued 5 ClickHouse schemas daily, and its runtime grew from 233 s to 2,216 s. It skipped <idmc_db> and <prefix>_milestones and had no dbt ingestion, because the container does not mount the dbt folder. Grafana had no ClickHouse datasource.
- **Fix / do this:** Add the missing schemas to schemaFilterPattern. Copy manifest.json and run_results.json into the container on each run. Add the ClickHouse Grafana plugin under a batched approval, since it needs a restart.
- **KB:** new

### PD-P2-094 Every content write spawns a Content Publish Task system job
- **Date:** 2026-10-04
- **Context:** glossary and link writes counted against the job budget
- **Lesson:** 46 writes (1 domain + 45 terms) produced 46 "Content Publish Task" SYSTEM_JOBs, all COMPLETED. They run at author time and use no IPU, and they are not known to count toward the DI job cap.
- **Fix / do this:** Count them separately from the lane's budget.
- **KB:** L-CDGC-153, L-CDGC-173, L-CDGC-174

### PD-P2-095 About half of core.origin search hits are relationship docs with no classType
- **Date:** 2026-10-04
- **Context:** asset check after the scan
- **Lesson:** 426 hits split into 208 real assets (resource, database, schema, 3 tables, 199 columns, 3 PKs) and 218 relationship docs with a null classType.
- **Fix / do this:** Count by classType and drop null-class docs before comparing with expected table and column counts.
- **KB:** L-CDGC-158, L-CDGC-169 (related); new

### PD-P2-096 Link terms to columns by externalId, re-point stale paths, log misses
- **Date:** 2026-10-04
- **Context:** 132 links on pu_s1_ma
- **Lesson:** An ES `terms` query on core.externalId (`<csId>://db/public/table/col~…Column`) resolves each column, then `PATCH …/assets/<id>?scheme=internal` applies the glossary segment. The plan still pointed at the old table pu_ma and had to be re-pointed. One link was missing because dq_flags is not a column. A "remove" PATCH is unproven, so undo is manual in MCC.
- **Fix / do this:** Log a status per pair (linked, missing-asset, error), skip finished pairs on re-runs, and read back a sample.
- **KB:** L-CDGC-056, L-CDGC-057

### PD-P2-097 What can and can't be undone over CDGC REST
- **Date:** 2026-10-04
- **Context:** Undo plan for the glossary and catalog load
- **Lesson:** CDGC undo limits:
  - DELETE on a Published term can report success while the term stays; rename it "(retired)" instead.
  - REST DELETE of a catalog source only purges metadata. Deleting the definition, cancelling a scan, and assigning stewards are UI-only.
  - Glossary content does not travel in a v3 package.
- **Fix / do this:** Write writes.jsonl with an undo for each write before making it. Plan the UI-only undo steps up front.
- **KB:** L-CDGC-059, L-CDGC-047, L-CDGC-040, L-CDGC-071, L-CDGC-066

### PD-P2-098 A catalog-source PUT needs the id in the body; save a GET first as the undo
- **Date:** 2026-10-04
- **Context:** Updating the filters of <sample>_bq
- **Lesson:** `PUT .../ccgf-catalog-source-management/api/v1/datasources/<id>` without `id` in the body returned 400 "dataSource id in request path and body do not match". With `id` set, it returned 200 and the read-back diff was empty.
- **Fix / do this:** Always set body.id to the path id. GET and save the source before every PUT, and diff the read-back.
- **KB:** L-CDGC-202

### PD-P2-099 REST DELETE of a catalog source only purges; delete the definition in MCC
- **Date:** 2026-10-04
- **Context:** Undo plan for <sample>_bq
- **Lesson:** `DELETE .../datasources/<id>` starts a metadata purge job. The definition itself can only be deleted in MCC > Catalog Sources. The connection can be deleted only after the source is gone.
- **Fix / do this:** Undo in this order: REST purge, then the MCC delete, then `DELETE /api/v2/connection/<id>`.
- **KB:** L-CDGC-047, L-CLEAN-015

### PD-P2-100 Clone a catalog source with DQ automation off and the RE in all three places
- **Date:** 2026-10-04
- **Context:** BigQuery source built from the shape of the host app's <host_app>_bq
- **Lesson:** The body set Run Rule Occurrence Frequency=false and Data Quality Automation=false, and put the RE in global Runtime Settings, the Data Profiling Scope and the Data Quality Scope. A guard asserted that no host-app id had leaked into the body and that the RE appeared exactly 3 times. `GET /type/Google BigQuery/capability/<cap>/configuration` lists the available options; none of them sets billing or adds another project.
- **Fix / do this:** When cloning, change the name, filters and connection, turn off DQ automation and RRO, check for leaked ids, and diff the read-back.
- **KB:** L-CDGC-152, L-CDGC-143, L-CDGC-187

### PD-P2-101 "Query the data" headless through MCP data_explore
- **Date:** 2026-10-04
- **Context:** CLAIRE "Query the data" on <prefix>_synth_probe
- **Lesson:** Call dataexplorationagent.data_explore with prompt, name and an external_id of the form `<sourceId>://<project>/<dataset>/<table>~com.infa.odin.models.relational.Table`. It submits and then you poll get_skill_execution_updates (poll_interval_ms 1000). It answered 2 min after the first scan finished, taking 28-33 s. The generated SQL ended in LIMIT 100, and a COUNT(*) billed 0 bytes. Results are in payload.data with viewType DataExploreResult.
- **Fix / do this:** Read the external_id from the asset list. Before each call, check that activityMonitor is empty, at least 8 GB is free and load is under 4. Prove the answer with the gateway log and the BigQuery job list.
- **KB:** L-MCP-125, L-MCP-114, L-MCP-044, L-MCP-121

### PD-P2-102 OpenMetadata returns column tags only when asked for them
- **Date:** 2026-10-04
- **Context:** Checking 176 "<Platform> PII" labels
- **Lesson:** GET with fields=columns returned no tags, which suggested 0 labels. With fields=columns,tags, all 17 tagged columns showed.
- **Fix / do this:** Always include tags in fields when verifying classifications.
- **KB:** new

### PD-P2-103 Load curated dictionary content as a staged file, not SQL literals
- **Date:** 2026-11-01
- **Context:** m_<prefix>_dictionary_load in 06 Data Dictionary
- **Lesson:** The dictionary is generated as a CSV (UTF-8, standard quoting, no newlines inside values) and staged on the agent. It is read through a new flat-file connection, <APP>_FILES. The target is ReplacingMergeTree(dictionary_version), and superseded entries are retired as version-100 rows with `is_deleted=1`. Reads without FINAL or argMax counted 6,880 entries twice.
- **Fix / do this:** Use the file pattern so the content is data CDGC can see. Always query version-collapsed rows.
- **KB:** new

### PD-P2-104 The generic JDBC catalog source has no Lineage Discovery
- **Date:** 2026-11-01
- **Context:** Cataloguing the new ClickHouse in CDGC
- **Lesson:** For JDBC, `.../type/JDBC/capability/<cap>/configuration` returned 200 for Metadata Extraction, Profiling, DQ, Classification, Relationship Discovery and Glossary Association. Lineage Discovery returned 404 "capability configuration does not exist". A bogus capability returns 400, so the 404 means the capability is not offered. None of the 42 catalog sources covered ClickHouse.
- **Fix / do this:** Get lineage from an IICS catalog source on the CDI project, plus curated `core.DataSetDataFlow` / `DirectionalDataFlow` edges generated from the dictionary.
- **KB:** L-CDGC-234, L-CDGC-179

### PD-P2-105 A new IDMC project needs its own IICS catalog source, and a cloned source's encrypted password fails
- **Date:** 2026-11-01
- **Context:** The existing IICS source filtered only the old `<app>` project
- **Lesson:**
  - **Create:** `<app>_idmc_cdi` was created by multipart POST to `ccgf-catalog-source-management/api/v1/datasources`, cloned with read-only fields dropped.
  - **Password:** The clone's encrypted password failed Test Connection. Credentials had to be re-set by a PUT whose JSON repeats the id.
  - **Scan:** `POST /data360/executable/v1/catalogsource/<id>` returns a jobId.
  - **Auth:** JWT from `identity-service/api/v1/jwt/Token?client_id=cdlg_app`, refreshed after about 18 min.
  - **Overturns:** The 08-01 belief that creating a catalog source has no REST verb (PD-P2-075).
- **Fix / do this:** Re-supply credentials on any cloned catalog source before the scan.
- **KB:** L-CDGC-187, L-CDGC-029, L-CDGC-002 (encrypted-password detail: new)

### PD-P2-106 Generate the CDGC glossary from the dictionary, idempotent and reversible
- **Date:** 2026-11-01
- **Context:** build/cdgc_glossary.py (44 creates)
- **Lesson:** One Domain plus BusinessTerms for the 3 tables, record kinds, stages and migration concepts, created through `POST {idmc-api}/data360/content/v1/assets`. A local registry of created identities lets `--undo` delete them with `DELETE .../assets/<id>?scheme=internal`.
- **Fix / do this:** Drive glossary content from the curated dictionary, and keep a registry so the load can be undone.
- **KB:** L-CDGC-051, L-CDGC-052

### PD-P2-107 Keep PII and raw JSON blobs out of profiles: their values land in IDMC's cloud metric store
- **Date:** 2026-11-04
- **Context:** legacy profiling: 402 columns left out
- **Lesson:** Columns were left out on three grounds:
  - The PII register (`pii_columns.csv`);
  - a name regex for owner, mailing, grantor/grantee, buyer/seller, taxpayer, name, email, phone, agent and brokerage;
  - raw JSON or payload columns and Map/Tuple/JSON types, which may embed owner data.
- **Fix / do this:** Apply the exclusions in the plan step, before create, and write the excluded-column count into each profile's description.
- **KB:** L-DQ-157

### PD-P2-108 Dead columns: mark deprecated in comments, drop only after grepping every consumer
- **Date:** 2026-10-29
- **Context:** Gold <property_table>: 75 of 191 columns are all-null, empty or constant
- **Lesson:** `asset_class_v3` and `class_group_v3` were empty on all 100,983,261 rows. Across the scope: 162 all-null, 78 all-empty and 217 constant columns. Missing values are not dirty values, so completeness is reported separately.
- **Fix / do this:** Flag the columns in the dictionary and in column comments now. Drop one only after grepping the backend, the MCP and the public builders for its name.
- **KB:** L-DQ-140 (drop procedure: new)

## ClickHouse / databases

### PD-P2-109 ReplacingMergeTree: read FINAL one partition at a time, with merge-safe settings and the filter after the merge
- **Date:** 2026-10-03 / 2026-10-25
- **Context:** <property_table> (ReplacingMergeTree(ingested_at), PARTITION BY state); sample export and DQ packs; gold cleanup, label flows, backend clickhouse_store
- **Lesson:** The MA partition held 6,077,694 raw rows against about 2.52M FINAL rows (about 2.4 versions per row). An unscoped national FINAL takes minutes, and a 32M-row FINAL scan trips the server-wide memory tracker whenever anything else is resident (both the 4-thread and the 2-thread-plus-spill variants failed with MEMORY_LIMIT_EXCEEDED). `do_not_merge_across_partitions_select_final=1` is safe only when the partition key is part of the sorting-key prefix (here, state); check `system.tables`. Keep `optimize_move_to_prewhere_if_final=0` so non-key filters apply after the merge: EXPLAIN showed the WHERE clause runs after the FINAL merge, with no PREWHERE. FINAL dedups on the sorting key (state, city, address_norm, property_id), not on property_id, so a property whose address changed keeps two rows; that is a real DQ finding. Under ReplacingMergeTree(ingested_at), max(ts) for freshness can be read without FINAL. Large MA backtests needed a 3 GB cap.
- **Fix / do this:** Take the partition list from parts metadata, run one state per query, and retry once, with `SETTINGS do_not_merge_across_partitions_select_final=1, max_block_size=8192, optimize_move_to_prewhere_if_final=0`, max_final_threads 2, max_threads 2, max_memory_usage 4e9, max_execution_time 900 and a log_comment. Have the generator check partition_key and sorting_key per table and leave the setting off where they don't line up. Allow FINAL only when the query is bounded by state or city.
- **KB:** L-ENV-107, L-ENV-106 (PREWHERE/FINAL setting: new)

### PD-P2-110 Settings for heavy ClickHouse reads: flock, thread/memory caps, log_comment
- **Date:** 2026-10-03
- **Context:** stage_s1.sh and dq_claire
- **Lesson:** Every heavy query ran under `flock /run/lock/<app>_heavy.lock` with max_threads=2, max_final_threads=2, max_memory_usage=4e9, max_execution_time 900-1800, and `log_comment='<job>:<state>:<step>'`. Cost was read back from system.query_log by log_comment (the MA FINAL sample took about 12.5 s). The dq_claire validator rejects `settings` inside rule SQL, so settings go in the profile's custom_settings.
- **Fix / do this:** Tag every query with log_comment and budget by query-seconds and read bytes.
- **KB:** new

### PD-P2-111 Secrets put in ClickHouse SQL leak to the logs: never pass a salt by SET or HTTP parameter
- **Date:** 2026-10-04
- **Context:** Keyed-hash salt for the listing_agent / brokerage columns in the sample export
- **Lesson:** A salt passed with SET or as an HTTP parameter lands in system.query_log, text_log and the server log. EXPLAIN actions=1 showed it constant-folded 15 times into expression names, so any exception would log it. A self-test using an all-constant query does not exercise this path. The plan first moved from SET to an HTTP POST parameter; the final v3 build exported the person-name columns as NULL table-wide instead of hashing them, because the salt could still leak through the logs.
- **Fix / do this:** Keep secrets out of warehouse SQL entirely: hash outside the warehouse, in the exporter, or drop or NULL a field you don't need. Test with the real export SQL and a dummy salt, and restrict who can read query_log.
- **KB:** L-ENV-078, L-ENV-110

### PD-P2-112 A portable SHA-256 PRN gives the same sample in ClickHouse, BigQuery and Postgres
- **Date:** 2026-10-03
- **Context:** s1 sample membership
- **Lesson:** prn32 = first 4 bytes, big-endian, of SHA-256('<sample>-s1:' + property_id). In sample when prn32 < threshold. ClickHouse needs `reverse(...)`, because reinterpretAsUInt32 reads little-endian. BigQuery: CAST('0x'||first 8 hex AS INT64). Postgres: ('x'||lpad(hex8,16,'0'))::bit(64)::bigint. The rejected alternatives: cityHash64 (ClickHouse-only), the SAMPLE clause (needs SAMPLE BY in the DDL), ORDER BY rand() (not reproducible), and an 8-town cluster slice (misses about 343 of 351 towns' formats). The SQL forms were only emulated in Python on 10 test vectors.
- **Fix / do this:** Each engine must reproduce the test vectors before first use. Recompute the PRN after load and require 0 mismatches. Change the salt prefix (<sample>-s2:) to draw a new sample.
- **KB:** L-DQ-099

### PD-P2-113 Stratified Poisson allocation with floors: 50,000 MA rows covered all 12,970 strata
- **Date:** 2026-10-04
- **Context:** s1 MA sample (50,110 rows)
- **Lesson:** rate = max(core, town floor of 30 rows, class floor of 200 rows), with floors scaled down if they would use more than 60% of the budget. The 50,000 budget is expected rows, and predicted = realized in all 12,970 strata. 30 rows per town catches a defect hitting 10% of a town with 95.8% probability; 200 rows per class detects a 1.5% defect. Rates are frozen per sample_version.
- **Fix / do this:** Stratify on the dimension that drives DQ variation (here, the assessor town) and store weights per row.
- **KB:** new

### PD-P2-114 Stage the sample from one snapshot: count pass, export pass, conservation check, atomic swap
- **Date:** 2026-10-04
- **Context:** stage_s1.sh (first run 10-04 07:30Z)
- **Lesson:** The PRN needs every id in the partition, so each refresh runs one FINAL count pass plus one FINAL export pass into an immutable snapshot. Postgres is loaded from the same snapshot via clickhouse-local (TSV, ISO dates, NaN→NULL; no second gold read). Before the swap: count, sum(prn32), distinct ids and PRN recomputed in PG must all match. Never use `toDateTime()`, which clamps pre-1970 dates to 1970.
- **Fix / do this:** Load into `_new`, verify, then swap `_prev`/current in one transaction, GRANT, and ANALYZE. Undo = swap back.
- **KB:** L-CDI-137

### PD-P2-115 A host-local flock cannot be taken from another host: run host-locked jobs on the host
- **Date:** 2026-10-03
- **Context:** stage_s1.sh and /run/lock/<app>_heavy.lock on the DB host, Airflow DAGs on the platform VM
- **Lesson:** The heavy-job lock is a flock on the DB host that root crons hold for up to 1h11m, and Airflow (0 Connections) runs on another VM, so a DAG there cannot take it. The export script therefore runs on the DB host, triggered over IAP. The dbt runners on the platform VM need a cross-host lease.
- **Fix / do this:** Put the lock where the work runs: run the staging script on the DB host (systemd timer) so it takes the flock itself, and let the remote DAG only trigger it, wait, and load the result. Otherwise build a cross-host lease.
- **KB:** L-METHOD-019 (single-writer); host-local lock = new

### PD-P2-116 Choose DB-host work windows from Prometheus load history; on a busy host the gate rarely opens
- **Date:** 2026-10-04
- **Context:** The DB host export windows (decision 12); MA export attempts 01:31-01:45Z
- **Lesson:** Windows are hours whose 7-day p95 of node_load1 is under the gate. They exclude 02:30-06:05Z (backups, the heavy-lock source measure) and 09:40-12:20Z (DQ DAGs). The gate is avg_over_time(node_load1[15m]) < 8 and no holder of the heavy lock. In practice all 6 MA attempts were refused, either because the lock was held or the 15-min load was 8.1-10.6. Over 4 days of 5-min slots, the best hours passed the gate only 25-33 % of the time. The look-ahead was raised from 20 to 35 min because the count and the export can each take 900 s. A refusal exits 75 (busy maps to SKIPPED).
- **Fix / do this:** Use measured load series and known cron windows rather than guessing a quiet hour. Pick run hours from 7 days of Prometheus `avg_over_time(node_load1[15m])` and retry within them.
- **KB:** new

### PD-P2-117 Extend a peer-owned ReplacingMergeTree registry with a side table, not ALTER
- **Date:** 2026-10-03
- **Context:** Rule registry <idmc_db>.claire_rule_recs (owned by another lane) + dq_rule_spec
- **Lesson:** The registry tool (claire_recs.py) re-inserts only its fixed column list on every set/accept/reject. Because the registry is a ReplacingMergeTree, any added columns would silently reset to defaults on the next review action. Its CHECK constraints also limit the source and rule_type values and require two-part table names, and inserts with new values failed with Code 469 on c_status. A side table keyed 1:1 on rule_id, plus a view, survives every tool unchanged.
- **Fix / do this:** Leave a table another lane owns unchanged. Put new fields in a side table you own (dq_rule_spec) and join them in a canonical view.
- **KB:** new

### PD-P2-118 Write one canonical rule form (kind + params) and compile it per dialect, with a portable regex subset
- **Date:** 2026-10-03
- **Context:** rules2dbt kinds and dispatch macros
- **Lesson:** The kinds: not_null, regex, in_set, range, length, unique_key, cross_field, reference_fk, freshness, custom_sql. NULL counts as a fail. Regexes avoid backslashes (use [.] and [0-9]) because ClickHouse, BigQuery and Postgres treat escapes differently; case-insensitivity goes in a param, never (?i). Use NOT EXISTS for reference checks on BQ/PG, never NOT IN (the NULL trap). Every result row carries rule_hash/rule_version.
- **Fix / do this:** Compile with adapter.dispatch macros and check example vectors on every engine.
- **KB:** new

### PD-P2-119 dbt at scale on ClickHouse: compile all rules for one (table, state) into one FINAL pass with countIf per rule, with guards and a pool
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** dq_claire (another lane's DQ project) and gold_dq at scale
- **Lesson:** One test per rule × state means 51 × (rules+1) FINAL scans, about 1,100 a day, at 4.6-18.2 s each: MA took about 115 s for 11 tests on 2.52M rows, so national would take more than 80 min, and gold_dq once took 15,411 s. One scan instead returns checked and failed counts for every rule. It runs as user idmc_dq (4 GB / 2 threads) in the Airflow pool db_heavy. The existing guard required LoadAverage1 ≤ 12 and fewer than 3 queries running over 30 s, retrying for up to 120 min, with exit 99 meaning SKIPPED; there were 3 separate lock mechanisms, and gold_dq ran with no guard.
- **Fix / do this:** Batch rules into a single FINAL query per (table, state) partition that returns countIf per rule. Use an Airflow pool `db_heavy` = 1 on every heavy DAG. Budget query-seconds and read-bytes by log_comment.
- **KB:** new

### PD-P2-120 BigQuery rule runs: dry-run every test, cap bytes, never loop per state
- **Date:** 2026-10-03
- **Context:** dq_estates bigquery target
- **Lesson:** Dry-run each compiled test (free; record the bytes). Set maximum_bytes_billed (1 GB per run; a query over the cap fails unbilled). Without a pruning column, run once nationally with GROUP BY state, because a per-state loop rescans the column 51 times. BigQuery cannot partition on STRING, so use RANGE_BUCKET on state_fips.
- **Fix / do this:** Use the "Shape M" measure query (rows_checked + rows_failed from one scan).
- **KB:** L-ENV-041

### PD-P2-121 Postgres DQ role with server-side read-only limits, plus keeping passwords out of logs
- **Date:** 2026-10-03
- **Context:** dbt-postgres target; tooling-VM sample Postgres and registry reads
- **Lesson:** Role-level `ALTER ROLE ... SET statement_timeout='60s', lock_timeout='2s', default_transaction_read_only=on, idle_in_transaction_session_timeout='60s', max_parallel_workers_per_gather=0`. The client cannot bypass role settings. `PGOPTIONS` in the task env adds a second layer that reaches dbt-postgres through libpq. Setup scripts pass passwords to psql on stdin only, and `log_min_error_statement=panic` stops a failed statement's text, and any password in it, from reaching the server log. dbt-postgres was installed nowhere, so it goes in a new venv, pinned first in a scratch venv and never added to the production project's venv.
- **Fix / do this:** Enforce "findings, never writes" through grants and server-side role settings, not good behaviour. Keep secrets on stdin and use the error-statement logging guard.
- **KB:** L-METHOD-001 (related); new

### PD-P2-122 Put ClickHouse caps in settings-profile constraints, and know the DQ user's blind spots (system.parts byte columns)
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** ClickHouse user idmc_dq (users.d/idmc_dq.xml on the DB host)
- **Lesson:** The profile's constraints (max 4e9 memory, 2 threads, 900 s) cannot be raised by a client. Reads of system.parts byte columns return ACCESS_DENIED for idmc_dq, while system.columns and system.tables are readable.
- **Fix / do this:** Enforce caps as profile constraints, not client settings. Size tables from system.columns and system.tables.
- **KB:** new

### PD-P2-123 ReplacingMergeTree holds unmerged versions: readers without FINAL double-count
- **Date:** 2026-10-29
- **Context:** ClickHouse 360 profile of legacy, gold, silver and bronze tables
- **Lesson:** Versions that collapse only under FINAL:
  - legacy <property_table>: 1.59M extra rows;
  - gold: 141,768;
  - market_indexes: about 7.5 %;
  - bronze national_sale_observation: about 23 %;
  - ma_cama_parcel: 12 %.

  The listings-feed gate kept failing on dup_versions.
- **Fix / do this:** Read with FINAL scoped to one partition. Collapse with a per-partition `OPTIMIZE ... FINAL` outside the backup window and while no writer runs.
- **KB:** L-ENV-107

### PD-P2-124 readonly=1 rejects every SETTINGS clause; read-only sessions need readonly=2
- **Date:** 2026-10-04 / 2026-10-29
- **Context:** stage_s1.sh chq() helper; grafana_ro login; dry-run counts on the DB host
- **Lesson:** readonly=1 refuses every settings change, including log_comment, so queries with SETTINGS clauses fail: `SETTINGS max_bytes_before_external_group_by = ...` failed with Code 164 "Cannot modify ... setting in readonly mode". One diagnostic query_log read had run with readonly 0. The measurement helper uses `--readonly=2`.
- **Fix / do this:** Send every read-only diagnostic that needs per-query caps with readonly=2, or set the comment at client or session level.
- **KB:** L-ENV-112

### PD-P2-125 Pre-flight checks before any heavy ClickHouse write on a shared host: windows, locks, disk, mutations, one partition at 4 GB / 2 threads
- **Date:** 2026-10-29
- **Context:** Change-plan rules on the DB host; cleanup / labels / zos runners
- **Lesson:** Refuse the write when any of these holds:
  - inside 03:00-07:00Z (backup; `<app>-heavy-window` must exit 0, it exits 3 inside) or 02:00-07:30Z (ML);
  - an ML gate is running, or a pub2 build is running;
  - free disk is below 40-60 GiB (45 GiB in the change plan), or MemoryTracking is at or above 7 GiB;
  - code 241 appeared in the last hour;
  - there are unfinished mutations, or a peer wrote or ALTERed the target in the last 30 min.

  Lock order is always the gold writer lock, then the heavy lock. One state partition at a time, at most 3-4 GB and 2-4 threads per statement, no global FINAL or whole-table IN subqueries. Gold measurements (~10 min per query) used 4 GB / 2 threads.
- **Fix / do this:** Put these checks inside the script so it refuses on its own, and re-check them after the lock wait and again right before the swap. Never raise limits or bypass locks to force a load.
- **KB:** L-CDI-292, L-METHOD-019, L-ENV-109 (guard list: new)

### PD-P2-126 groupArray over an 11M-row state blew the 4 GB cap: count first, then expand only the duplicate keys
- **Date:** 2026-10-29
- **Context:** Shared-address dry run
- **Lesson:** A single pass with groupArray over every address of a big state exceeded the per-query cap. Two passes worked: a cheap count of duplicate keys, then `IN (...)` only for those groups.
- **Fix / do this:** Split heavy group queries into a key-finding pass and a detail pass.
- **KB:** new

### PD-P2-127 Swap the finished table in with one atomic RENAME
- **Date:** 2026-11-02
- **Context:** `<property_table>_gold` -> `<property_table>`, the old table -> `<property_table>_staging`
- **Lesson:** One RENAME with a ready undo makes the swap instant (about 5 min with checks). Post-swap steps (22 AV columns + dictionary entries, dq_score, FK linking) wait for it.
- **Fix / do this:** Build into a separate table, prove it, then RENAME. Never truncate-then-insert the served table.
- **KB:** L-ENV-106

### PD-P2-128 Restructure 29 databases into 6 by moving tables, sequenced by readers and writers, and leave a view at the old name
- **Date:** 2026-10-29
- **Context:** 29 databases -> 6 (layout.py)
- **Lesson:** The six databases are bronze, silver, gold, site, ml and ops. About 800 code files name the six databases that stay, so names are kept and tables move. Kept tables were mapped by database, and legacy tables by name: sale_history and market_indexes go to gold, DQ histories to ops, <property_link_table> to silver; legacy <property_table> retires after the gates read gold. The script checks for name clashes, and each move is sequenced by counting the writers per table. In Atomic databases `RENAME TABLE` is instant. The steps: pause the writer, rename, repoint the gold view and the writer, resume, compare counts, and keep a read-only view at the old name for 14 days. The L1 phase moves 17 tables (7.6 GB), with generated SQL, undo and the writers to repoint.
- **Fix / do this:** Build the layout CSV from the inventory plus the writes log before moving anything, keep the database names stable, generate the move SQL and its undo, and rehearse on a scratch copy before the GO.
- **KB:** L-ENV-117 (related L-MIG-088)

### PD-P2-129 Keep the work database minimal: only IDMC staging and profiling samples
- **Date:** 2026-11-02
- **Context:** `<work_db>` (49 tables)
- **Lesson:** The work database held cutover scaffolding (14 `u_*`, ~240 GB), profiling copies (71 GB), compatibility views, undo copies and dead tests. Views in a work database are a hidden dependency for the site. The target is 6 tables: 3 staging tables (needed for the Array/Map writer or merges) and 3 stratified samples. Dead tables were moved to `<archive_db>` by RENAME (reversible) before any delete.
- **Fix / do this:** Give every work table a purpose and a verdict. Let the site read production tables directly, and delete only after acceptance and a GO.
- **KB:** new

### PD-P2-130 Deterministic sampling for comparisons: the same id-hash bucket on both sides
- **Date:** 2026-10-29
- **Context:** Legacy vs gold drift analysis
- **Lesson:** `cityHash64(property_id) % 20 = 3` (5 % of ids) was applied to both tables in every comparison. Tables over 20M rows were profiled on a deterministic ~10M-row set of whole parts, with exact totals from system.parts. The profiler was serial, resumable, capped at 4 GB / 2 threads, paused while load1 > 12, and stopped by a STOP file.
- **Fix / do this:** Sample by key hash so both sides cover the same entities; take totals from system tables.
- **KB:** L-METHOD-053

### PD-P2-131 Find unused tables from query_log, archive them in the backup's format, verify, then drop
- **Date:** 2026-10-29
- **Context:** Storage hygiene (200 of 867 tables archivable, disk 91 % full); change plan step `02_archive_then_drop_scratch.sh`, `10_backups.sh`
- **Lesson:** A table is an archive candidate when it has not been read in 14 days (backup exports and the OpenMetadata crawler excluded), no view references it, and it has not been written in 7 days. 200 tables / 35.9 GB qualified; 667 / 164.5 GB were still used by recent repairs. Each table goes to GCS as `<db>.<table>.schema.sql` (SHOW CREATE) and `.native.gz` (`SELECT * FORMAT Native | gzip -1`), with a `manifest.tsv` row (table, rows, bytes, sha256 of the gz). This matches the nightly backup's format, so restore is identical (`clickhouse-client < schema.sql; gsutil cat ... | gunzip | INSERT FORMAT Native`). The drop is a separate GO (`DROP=1`), and only tables whose archive decodes to the same row count are dropped.
- **Fix / do this:** Re-run the candidate builder right before acting, so a table read since then drops out. Archive needs no GO; drop does. Keep the restore commands in the script header.
- **KB:** L-METHOD-048, L-ENV-116 (related L-ENV-114)

### PD-P2-132 Wrap docker exec clickhouse-client with stdin from /dev/null
- **Date:** 2026-10-29
- **Context:** Shell helpers in the change-plan scripts
- **Lesson:** The helper `ch()` runs `docker exec -i ... clickhouse-client ... < /dev/null` so that it does not swallow the stdin of a surrounding `while read` loop.
- **Fix / do this:** Redirect stdin in every `docker exec -i` wrapper used inside loops.
- **KB:** L-ENV-115

### PD-P2-133 Every ad-hoc query on a co-located box must carry max_memory_usage
- **Date:** 2026-08-01
- **Context:** The data droplet (8 GB, ClickHouse + Mongo + IDMC agent, 1.25B-row warehouse)
- **Lesson:** An unthrottled query OOM-killed ClickHouse on this box. Health checks start with `SET max_memory_usage = 1500000000`.
- **Fix / do this:** Cap every verification query; size the host before enabling more services.
- **KB:** L-AGENT-052, L-AGENT-109

### PD-P2-134 Content-hash dedup with ReplacingMergeTree, and count with uniqExact
- **Date:** 2026-08-01
- **Context:** Ingest bronze tables `<bronze_db>.ext_<source>`
- **Lesson:** Landing tables are `ReplacingMergeTree(_ingested_at) ORDER BY (_source_id, _business_key, _record_hash)` with `_record_hash = sha256(source_id + payload)`, so a re-drop collapses to one row, but only after background merges. The scorecard uses `uniqExact(_record_hash)` instead of `count()` to stay exact while duplicate parts are unmerged.
- **Fix / do this:** Count distinct keys, or read with FINAL, on replacing tables.
- **KB:** L-ENV-107

### PD-P2-135 Golden "latest passing record wins" with argMax over a tuple
- **Date:** 2026-08-01
- **Context:** `<ingest_db>.golden`
- **Lesson:** `argMax((payload, _source_system, _source_id, _source_uri, _record_hash), _ingested_at) ... WHERE _dq_status='pass' AND _business_key != '' GROUP BY _entity, _business_key` keeps every winning field from the same source row (no mixing fields across rows); two sources with the same entity and key merge into one golden row.
- **Fix / do this:** Use a tuple argMax when the winner's fields must come from one row.
- **KB:** new

### PD-P2-136 merge('db', '^ext_') views pick up new landing tables with no new SQL
- **Date:** 2026-08-01
- **Context:** `bronze_all`, `golden`, `lineage`, `dq_scorecard`, `dead_letter`
- **Lesson:** The governance views read every table matching `^ext_` at query time, so a new source is included automatically; the anchor excludes the `_ext_ingest_log` run log. Views are read-time and reversible with DROP VIEW.
- **Fix / do this:** Name landing tables with a fixed prefix and keep operational tables outside it.
- **KB:** new

### PD-P2-137 View column names differ from the bronze sidecars
- **Date:** 2026-08-01
- **Context:** Querying golden, lineage, dead_letter and silver views
- **Lesson:** Bronze uses `_entity` and `_business_key`; the views expose `entity` and `business_key`; `silver.property` keys on `property_key` and `silver.geo_place` on `place_key`; the run log has `started_at`/`finished_at`/`source_id`. Underscore names on a view return UNKNOWN_IDENTIFIER.
- **Fix / do this:** Check `DESCRIBE` of a view before writing checks against it.
- **KB:** new

### PD-P2-138 Two business keys for one entity create ghost duplicates in a typed view
- **Date:** 2026-08-01
- **Context:** `silver.property` fed by `provider_property` (`/provider_id`) and `property_dropzone` (`/parcel_id`)
- **Lesson:** golden groups by (entity, business_key), so one real property could produce two golden rows; a parcel-keyed record that carried a provider id showed up in the provider-named typed view as a near-empty duplicate.
- **Fix / do this:** Ingest each provider through its own keyed source; add cross-source identity (provider id to parcel_id) as an explicit xref, never by letting two schemas collide in one view.
- **KB:** new

### PD-P2-139 Land JSON over ClickHouse HTTP with additive, idempotent DDL
- **Date:** 2026-08-01
- **Context:** `ClickHouseSink` in the ingest platform
- **Lesson:** The sink runs `CREATE TABLE IF NOT EXISTS` plus `ADD COLUMN IF NOT EXISTS` for governance columns, and inserts each batch with `FORMAT JSONEachRow` over port 8123, with no JDBC driver. Additive-only DDL was adopted after earlier classification work had to learn it the hard way.
- **Fix / do this:** Never drop or mutate the production warehouse from a pipeline; add columns, tables and views only.
- **KB:** new

### PD-P2-140 Extract view definitions with ClickHouse doing the JSON escaping
- **Date:** 2026-08-01
- **Context:** Lineage for the property-platform KB
- **Lesson:** `system.tables.create_table_query ... FORMAT JSONEachRow` emits one JSON line per view, avoids fragile shell quoting, and reads only metadata.
- **Fix / do this:** Use system tables and JSONEachRow for metadata exports.
- **KB:** new

### PD-P2-141 Read a raw JSON payload with formatRowNoNewline, and hash it honestly
- **Date:** 2026-10-31
- **Context:** Bronze capture source SQL
- **Lesson:** The capture builds `raw_payload_json` with `formatRowNoNewline('JSONEachRow', *)` and `record_payload_sha256 = lower(hex(SHA256(raw_payload_json)))`. Derived MDM rows instead carried the SHA-256 of '' as a placeholder, which later looked like a valid fingerprint on 100% of rows.
- **Fix / do this:** Beware same-named aliases leaking into `*`; leave a derived row's payload hash empty or labeled rather than using the empty-string hash.
- **KB:** L-CDI-270, L-DQ-146

### PD-P2-142 Postgres read-only roles keep PUBLIC defaults on the other databases
- **Date:** 2026-10-04
- **Context:** Tooling-VM sample Postgres roles idmc_ro_<prefix> and <prefix>_loader
- **Lesson:** The role was read-only only inside <sample_db>. It could still CONNECT to postgres and template1 and create TEMP tables there.
- **Fix / do this:** Run `REVOKE CONNECT, TEMP ON DATABASE postgres, template1 FROM PUBLIC`, grant per role, and verify with has_database_privilege.
- **KB:** new

### PD-P2-143 Report every deviation from the sampling spec
- **Date:** 2026-10-04
- **Context:** stage_s1.sh versus SAMPLING_SPEC §8 (MA)
- **Lesson:** Five deviations from the spec went unreported:
  - arrays were dropped instead of flattened to _n/_joined;
  - The hash was a 64-hex digest, not the specified 16-hex;
  - The export was TSV over HTTP, not Parquet;
  - The export ran as the default user without readonly=2;
  - 8 columns that are empty table-wide were still profiled.
- **Fix / do this:** List each deviation in the report, and run exports as a readonly=2 user. Treat any change of hash format as a parity break.
- **KB:** L-DQ-099 (PRN portability)

### PD-P2-144 Grafana plugins and dbt venvs inside containers
- **Date:** 2026-10-03
- **Context:** Adding a ClickHouse Grafana plugin and a dbt-postgres venv on the platform VM
- **Lesson:** Changing GF_INSTALL_PLUGINS recreates the shared Grafana container and needs egress to grafana.com. A venv created inside a container is lost when the container is recreated.
- **Fix / do this:** Use an existing datasource, or pre-stage the plugin zip in the plugins volume. Put venvs on a bind mount, pin versions that work with dbt-adapters 1.24.x, and gate on `dbt debug`.
- **KB:** L-ENV-094 (partial); rest = new

### PD-P2-145 Memory caps on the DB host summed above its RAM, and the kernel killed ClickHouse
- **Date:** 2026-10-03
- **Context:** DB host (31.3 GiB RAM, no swap)
- **Lesson:** The configured caps added up to about 33 GiB against 31.3 GiB of RAM: ClickHouse 16 GiB, Postgres shared_buffers 6+4 GiB, agent 4 GiB, Neo4j 2 GiB, mongod 1.2 GB. The kernel killed clickhouse-server at 05:59:54Z (anon-rss 17.1 GB). Root cause: max_server_memory was 28.2 GiB with no per-query cap, while IDMC JVMs and about 10 heavy sessions ran. The fix was a 16 GiB server cap, a 10 GiB per-query cap, and spill at 6 GiB.
- **Fix / do this:** Before adding an agent, sum every configured cap against RAM. Right-size shared_buffers (about 1 GiB for about 180 MB of data). Fleet rule: 4 GB and 2 threads per query, no stacked FINAL, back off when load is above 20.
- **KB:** L-AGENT-052 (related); specifics new

### PD-P2-146 Make the registry writer's status vocabulary match the CHECK constraint
- **Date:** 2026-10-03
- **Context:** <idmc_db>.claire_rule_recs
- **Lesson:** An insert by idmc_dq failed with Code 469 "Constraint c_status ... is violated". A rule could quietly fail to arrive.
- **Fix / do this:** Align the writer's status values with the CHECK constraint. Alert on Code 469 in query_log.
- **KB:** new

### PD-P2-147 FINAL exports over whole partitions don't scale: slice by primary key or pin partitions
- **Date:** 2026-10-03
- **Context:** stage_pu.sh vs stage_pu_ma_towns.sh
- **Lesson:** <property_table> is a ReplacingMergeTree(ingested_at), PARTITION BY state, ORDER BY (state, city, address_norm, property_id), with no SAMPLE BY. Per-state FINAL exports read whole partitions; the 29 partitions of 1M+ rows (91.4% of rows) queued on a heavy lock held for 1h11m. A city-list slice read 285,311 rows in 5.6 s. A hash-PRN filter cannot skip data by the sort key. FINAL with optimize_move_to_prewhere_if_final=0 reads every exported column first, so each refresh read all 51 partitions twice.
- **Fix / do this:** Slice by primary key where the method allows it. For the PRN sample, run one partition-pinned FINAL count pass plus one export pass with these settings: `do_not_merge_across_partitions_select_final=1`, max_threads 2, max_memory_usage 4e9, a log_comment, all under the heavy flock. Record the cost from query_log.
- **KB:** L-ENV-107 (related)

### PD-P2-148 Per-user ClickHouse caps for IDMC users
- **Date:** 2026-10-03
- **Context:** Users idmc and idmc_dq
- **Lesson:** The caps were set as max constraints:
  - **idmc:** max_threads 2, max_memory_usage 6e9, max_execution_time 3600.
  - **idmc_dq:** 4e9 memory and 900 s, 2 concurrent queries, `do_not_merge_across_partitions_select_final=1`, and writes only to <idmc_db>.

  IDMC users accounted for less than 0.1% of a day's 55 query-hours.
- **Fix / do this:** Give every IDMC and dbt user a capped settings profile with max constraints. Tag queries with log_comment and keep a daily budget.
- **KB:** L-CDI-292 (related)

### PD-P2-149 Spot all-empty ClickHouse columns by their compressed size
- **Date:** 2026-10-04
- **Context:** pu_s1_ma column plan
- **Lesson:** Seven columns, including listing_agent, brokerage and permits, were each exactly 1,100,322 compressed bytes. That size is the null map alone, so the columns are empty across the whole table.
- **Fix / do this:** Treat identical per-column compressed sizes as a cheap hint that the columns are empty, then confirm with a capped countIf.
- **KB:** new

### PD-P2-150 An isolated sample Postgres for IDMC on a shared host
- **Date:** 2026-10-04
- **Context:** The sample-pg container (postgres:16-alpine) on the tooling VM
- **Lesson:** The container listens on loopback port 5439 only, with 1 GB and 1 CPU. Every TCP login uses SCRAM, and the password comes from POSTGRES_PASSWORD_FILE (0600). There is an owner role, plus a read-only IDMC role with default privileges. Checks passed 12/12, including rejecting a bad password. The host's /data was 93% full, so disk needs watching.
- **Fix / do this:** Use this pattern to give IDMC a copy that is not the production estate.
- **KB:** new

### PD-P2-151 A BigQuery row access policy hides dry-run byte estimates
- **Date:** 2026-10-04
- **Context:** Table pu_s1_ma with policy <prefix>_idmc_only
- **Lesson:** With a row access policy on the table, a jobs.query dryRun returns no totalBytesProcessed (-1 or None). The jobs.insert dryRun shows only rowLevelSecurityStatistics, and finished jobs report null for processed and billed bytes. A control table without a policy dry-ran normally.
- **Fix / do this:** Estimate bytes from the schema (NUMERIC 16 B, TIMESTAMP 8 B, STRING 2 B + length), and always set maximumBytesBilled (for example 10 MiB) on the query.
- **KB:** new

### PD-P2-152 ClickHouse 25.3: GRANT ALL ON db.* also adds admin-type grant rows
- **Date:** 2026-10-04
- **Context:** Trimming ClickHouse user idmc's grants (users.d XML)
- **Lesson:** `GRANT ALL ON <idmc_db>.*` expanded to TABLE ENGINE, CREATE/ALTER/DROP USER/ROLE, SET DEFINER and NAMED COLLECTION ADMIN rows. Listing database-level privileges explicitly cut SHOW GRANTS from 12 rows to 7. users.d reloads without a restart. The XML and its backup were 0644, so the password_sha256_hex was world-readable.
- **Fix / do this:** List privileges explicitly, then check SHOW GRANTS and text_log. Keep users.d files at 0600.
- **KB:** new

### PD-P2-153 Revoking database grants breaks INVOKER views (Code 497)
- **Date:** 2026-10-04
- **Context:** After revoking idmc's bronze/gov grants
- **Lesson:** Views without an SQL SECURITY clause run as INVOKER (default_normal_view_sql_security=INVOKER). Six views in databases idmc kept, for example <idmc_db>.dq_repair_queue, now return 497 ACCESS_DENIED for idmc and grafana_ro. The grant rows still looked unchanged, so "rights unchanged" was wrong.
- **Fix / do this:** Before revoking, list the views that read the revoked DBs (system.tables create_table_query), probe each as the user with LIMIT 0, and record what breaks.
- **KB:** new

### PD-P2-154 ReplacingMergeTree merges away the "previous version" an undo relies on
- **Date:** 2026-10-04
- **Context:** Undo for claire_rule_recs after 18 `bin/dq recs set` rewrites
- **Lesson:** The planned undo was "revert to the previous version", but background merges had already dropped the old versions. cmd_revert reported "nothing to revert to (single version)".
- **Fix / do this:** Save the old rows before rewriting a replacing table. Build the undo as explicit "set back" commands, checked by a shlex round-trip.
- **KB:** L-ENV-107 (undo aspect: new)

### PD-P2-155 Validate ClickHouse predicates without reading data: EXPLAIN on an empty partition
- **Date:** 2026-10-04
- **Context:** 56 rule predicates of the registry-rules lane
- **Lesson:** EXPLAIN PLAN with the partition pinned to a missing value (state 'ZZ') validated all 56 predicates in 281 EXPLAINs, with 0 failures and no data read. The one real pass then ran under the heavy lock and a load15 < 8 gate, with these limits:
  - pinned to the MA partition, with FINAL;
  - readonly=1, 2 threads, 4 GB.

  It took 9.9 s, read 1.30 GiB and peaked at 352 MiB.
- **Fix / do this:** EXPLAIN every generated predicate first, then run one capped, partition-pinned pass tagged with a log_comment.
- **KB:** new

### PD-P2-156 ClickHouse view column types follow the table
- **Date:** 2026-10-04
- **Context:** dq_rules_canonical after MODIFY COLUMN to Nullable
- **Lesson:** The view kept the old types, so it had to be recreated after the ALTER.
- **Fix / do this:** Recreate dependent views after a type change. Back up SHOW CREATE and every row version first.
- **KB:** new

### PD-P2-157 Narrow a database user's networks from the client addresses actually seen
- **Date:** 2026-10-04
- **Context:** The app's own user: networks narrowed from ::/0 to loopback plus the private ranges
- **Lesson:** Seven days of query_log client addresses showed the only callers. After the change there were 0 auth failures and 750 queries from the expected hosts in 50 s, and the app and MCP health checks returned 200. `displaySecretsInShowAndSelect` has no effect while the server setting is 0.
- **Fix / do this:** Read query_log first, change one file with a backup, then check text_log and the app health right away.
- **KB:** new

### PD-P2-158 Grafana ClickHouse plugin: timeout margin and version pin
- **Date:** 2026-10-04
- **Context:** "<Platform> ClickHouse (DQ)" datasource on Grafana 11.3.1
- **Lesson:** queryTimeout must be at least 5 s below the user's max_execution_time, because clickhouse-go sends the remaining deadline + 5 s (25 s was used against 30 s). Plugin 4.15.0+ needs Grafana 11.6 or later, so 4.14.0 is the newest that runs on 11.3. Unpinned plugins in GF_INSTALL_PLUGINS upgrade on every restart: bigquery-datasource jumped to 3.4.2, which does not support 11.3.
- **Fix / do this:** Pin every plugin and check grafanaDependency in the versions API. After a restart, health-check every datasource.
- **KB:** L-ENV-094 (related); new

### PD-P2-159 ClickHouse MATERIALIZED columns are not short-circuited on INSERT
- **Date:** 2026-11-01
- **Context:** Insert CPU on <property_table> was the bottleneck of every writer lane
- **Lesson:** `if(record_kind='<k>', <empty>, <heavy array expr>)` evaluates the heavy branch for every inserted row, and `short_circuit_function_evaluation='force_enable'` does not help. Four completeness columns took 11.4 s of a 15 s insert of 40,000 rows. The same expression in a SELECT is lazy: 0.16 s vs 2.8 s.
- **Fix / do this:** Keep heavy derivations out of MATERIALIZED columns on high-volume tables.
- **KB:** L-CDI-268

### PD-P2-160 A ClickHouse Join-engine table cannot be a source: read its persisted .bin
- **Date:** 2026-11-01
- **Context:** fmt_ma_street_zip / fmt_ma_geo_zip lookups (no MergeTree base)
- **Lesson:** SELECT on `Join(ANY, LEFT, k1, k2)` fails with Code 121 UNSUPPORTED_JOIN_KEYS, and `joinGetOrNull` over a key source misses keys. Reading the persisted file works: row counts match total_rows.
- **Fix / do this:** Find `system.tables.data_paths`, run `clickhouse compressor --decompress` on the `.bin`, place it in user_files, and read it with `file('<dir>/x.native','Native','<structure>')`. Use that snapshot in both capture and reconcile.
- **KB:** L-CDI-269

### PD-P2-161 Row-hash SQL can quietly hash an alias instead of a column
- **Date:** 2026-11-01
- **Context:** Reconciliation checksums
- **Lesson:** In `SELECT SHA256(formatRowNoNewline('JSONEachRow', *)) AS h, count() AS n ... GROUP BY h`, a table column named `n` resolves to the alias. The count matched but the checksum differed, with no error. Byte-exact digests in the verifier use `formatRow`, because `formatRowNoNewline` drops a byte in binary formats.
- **Fix / do this:** Build the row JSON in an innermost subquery over the bare table, using aliases no table uses (`__<prefix>_*`), and aggregate one level up.
- **KB:** L-CDI-270 (formatRow part: new)

### PD-P2-162 Delta pass: ship the target's key set to the source and anti-join
- **Date:** 2026-11-01
- **Context:** build/delta_capture.py for live legacy tables
- **Lesson:** The captured unit keys are exported from the target as RowBinary UInt64 and copied to the legacy server's `user_files/<prefix>_delta/<name>.bin`. Each capture item is re-emitted as `delta/<item>`, keeping only units NOT IN that set, and runs through the same IDMC lanes, which append.
- **Fix / do this:** Use this instead of a full recapture after a writer freeze, then re-run reconcile.
- **KB:** new (related L-CDI-092)

### PD-P2-163 Reading a live legacy server: stream, cap each query, limit heavy lanes
- **Date:** 2026-11-01
- **Context:** The old DB-host ClickHouse serves the website
- **Lesson:** GROUP BY pack lanes drove the old server to its 64 GB memory limit and were stopped. From 07:55Z the rule was streaming SQL only, with at most 3 heavy GROUP BY jobs. All lanes used one dedicated reader login, so one KILL stops them all.
- **Fix / do this:** Put max_memory_usage and max_threads inside every lane's source query. Default to streaming row mode and cap heavy items in the runner.
- **KB:** L-MIG-093, L-CDI-292

### PD-P2-164 The target's max_concurrent_queries=32 is shared by loads, AV and DQ
- **Date:** 2026-11-01
- **Context:** Runs failing with Code 202 "Too many simultaneous queries"
- **Lesson:** The new ClickHouse had `max_concurrent_queries=32`; the old one had 1000. Resume shards, lineage, event_gap runs and a scheduled AV run all died on it at 1.4-1.8M rows. Every lane and every AV and DQ step is a query.
- **Fix / do this:** Budget the target's concurrency across all pipelines, or raise the limit. Treat Code 202 as a retryable capacity error.
- **KB:** L-CDI-287, L-CDI-292

### PD-P2-165 In a ReplacingMergeTree the sort key decides what a rerun does, and it can drop real rows
- **Date:** 2026-11-01
- **Context:** <property_table> ORDER BY (record_kind, property_id, record_id, publication_id); <model_registry>
- **Lesson:** Three ways the sort key bit:
  - publication_id was in the ORDER BY, so every rerun kept another copy (sale: 129.1M rows for 58.7M ids).
  - A record_id that left out `recorded_at` collapsed two decisions into one row.
  - Merges shrank property_state from 65.7M to 63.7M while it was being measured.
- **Fix / do this:** Make the sort key exactly the record identity, never the run or publication. Compare distinct key sets plus payload sha256, not count(). Read with FINAL.
- **KB:** new

### PD-P2-166 A lightweight delete hid 49.5M loaded rows, recoverable only until merges
- **Date:** 2026-11-01
- **Context:** `DELETE ... lightweight_deletes_sync=0` on source_record/run_manifest/dq_issue (10-31 20:42:58Z)
- **Lesson:** source_record had 50.06M physical rows but only 507,919 visible. The masked rows were readable with `SETTINGS apply_deleted_mask=0`, and `system.mutations` showed the delete. A later delete had already been purged. Auditors reported the masked tables as "0 rows loaded".
- **Fix / do this:** Check for masked rows before calling data missing. Copy them out, with approval, before merges purge them. Don't run cleanup deletes against a lossless target.
- **KB:** L-MIG-089

### PD-P2-167 Target changes made during a load: constraints added mid-load, fsync left off
- **Date:** 2026-11-01
- **Context:** DDL history on the new ClickHouse
- **Lesson:** Four CHECK constraints added at 23:35Z rejected rows that had loaded fine earlier (Code 469). The rows loaded before them were never checked. A temporary async-insert profile was dropped after 8 min, but `fsync_after_insert=0` and `fsync_part_directory=0` stayed on two tables.
- **Fix / do this:** Freeze the target's DDL during loads and check rules in a later DQ pass. Keep a revert line for every temporary setting, and audit table settings after the load.
- **KB:** L-MIG-090, L-ENV-121

### PD-P2-168 Prove duplicates and subsets cheaply with cityHash64 sums, sharded under the memory cap
- **Date:** 2026-11-01
- **Context:** Must-migrate decisions for 2,003 legacy objects
- **Lesson:**
  - **Exact duplicate:** same row count, same column set and equal `sum(cityHash64(toString(tuple(cols))))`.
  - **Subset:** an anti-join returns 0 (a 1% sample for huge tables).
  - **Memory:** 4 of these queries hit a 2 GB cap and needed `cityHash64(id) % 16` shards.
  - **Look-alikes:** pairs with equal row counts often differed in content, and several earlier "retire_ok" calls were wrong.
- **Fix / do this:** Never mark a table redundant without a hash proof.
- **KB:** new

### PD-P2-169 A background merge committed after an undo REPLACE PARTITION, leaving old and restored rows both active
- **Date:** 2026-10-25
- **Context:** junk-city rehearsal; safe_replace.sh now wraps the ZIP, condo-class and sale-flag runners
- **Lesson:** Gold's writer lock serialises writers but does not stop ClickHouse background merges. A merge already in flight can commit after the swap.
- **Fix / do this:** For each state-scoped REPLACE:
  1. `SYSTEM STOP MERGES <target>`.
  2. Wait up to 10 min for `system.merges` to drain. No proof of drain means no swap.
  3. Replace.
  4. `SYSTEM START MERGES` in a trap that also fires on failure or TERM, and log the recovery command if the restart fails.
- **KB:** new

### PD-P2-170 Copies into Replacing tables need optimize_on_insert = 0, and backups must never merge
- **Date:** 2026-10-25
- **Context:** gcl_sql.py / npf_sql.py corrected-copy inserts; gl-zos staging
- **Lesson:** A Replacing engine collapses same-key versions within an insert block, so the copy loses versions and its row-count check fails. Backup or staging tables that merge are no longer exact copies.
- **Fix / do this:** INSERT copies with `optimize_on_insert = 0` (max_threads 2, max_insert_threads 1, small blocks). Make backups plain MergeTree, or STOP MERGES on them. Take hard-link partition backups.
- **KB:** new

### PD-P2-171 With tied version values, insert order decides what FINAL shows
- **Date:** 2026-10-25
- **Context:** test_adversarial_clickhouse `test_tied_versions_cannot_change_visible_untouched_fields`
- **Lesson:** With the same key and version but different beds, FINAL keeps the last row inserted. A copy that inserts in a different order silently changes fields nobody touched.
- **Fix / do this:** Verify every copy with a FINAL hash of the untouched columns plus a full-row fingerprint against the backup. Refuse the swap if they differ.
- **KB:** new

### PD-P2-172 ClickHouse v25.3.14.14: nested-subquery mutations hang, and untyped UNION literals give "Block structure mismatch"
- **Date:** 2026-10-25
- **Context:** er_apply undo-merges, er_clusters insert
- **Lesson:** An `ALTER .. DELETE` whose WHERE nested subqueries hung its background task. Untyped literals across branches (0 vs `toUInt16(..)`) failed with "Block structure mismatch".
- **Fix / do this:** Materialise keys first and use single-level subqueries with `mutations_sync = 2`. Type and alias every branch of a generated INSERT ... SELECT.
- **KB:** new

### PD-P2-173 NULL-aware keys and multiset undo for plain MergeTree
- **Date:** 2026-10-25
- **Context:** er_apply v2.1, sale_history undo
- **Lesson:** Comparing nullable prices directly lets an unknown price duplicate a canonical sale or collide with a real `-1`. In plain MergeTree identical rows are distinct occurrences, so an anti-join undo loses multiplicity.
- **Fix / do this:** Compare nullable keys with `tuple(price)`. Number duplicates with `row_number() OVER (PARTITION BY formatRowNoNewline('RowBinary', *))` and restore by multiset count. Verify against both missing and surplus occurrences.
- **KB:** new (related L-CDI-286)

### PD-P2-174 Decide undo on the active-parts hash, not on count/max/id fingerprints
- **Date:** 2026-10-25
- **Context:** <app>-gl-zos.sh v2
- **Lesson:** A count | max(ingested_at) | id-hash fingerprint cannot see a writer that keeps `ingested_at` unchanged.
- **Fix / do this:** Gate the fast undo on the partition's active parts (`hash_of_all_files` in `system.parts`) plus a write stamp. Refuse it if the stamp moved, if `max(ingested_at)` passed `swap_at`, or if the fingerprint differs from `fp_after`; otherwise fall back to the surgical undo.
- **KB:** new

### PD-P2-175 Change a state partition through a staged copy, not a whole-partition rewrite
- **Date:** 2026-10-25
- **Context:** ZIP-other-state repair v1 → v2
- **Lesson:** v1 rewrote whole partitions: about 18 GiB of new parts for 32 states, against a 60 GiB free-disk floor.
- **Fix / do this:** Hard-link the partition into a staging table and run `ALTER UPDATE` on staging only. Write Gold only with `REPLACE PARTITION`, then read back. Make the job idempotent and resumable, with a `log_comment` on every statement.
- **KB:** new (related L-ENV-106)

### PD-P2-176 Freeze a row-level diff, apply only cells still equal to it, keep two undos
- **Date:** 2026-10-25
- **Context:** <app>-gold-cleanup.sh v2
- **Lesson:** `plan` freezes a diff table (`gcl_<st>_<tag>_diff`: property_id, rule, column, action, old, new). `run` applies only cells whose live value still equals `old`; other cells are HELD, and rows gone from Gold are GONE.
  - Caps: fix rules ≤ 5% of a field, held ≤ 1%, merges ≤ 0.5%.
  - Merges run before fields.
  - A newer identity run holds merges until the state is re-planned.
- **Fix / do this:** Two undos: fast = REPLACE PARTITION from the backup; surgical = re-insert old values with `now()`, keeping newer values from other lanes. Write receipts to `<gov_db>.gold_cleanup_runs` and add a kill-switch file. Keep `_diff` tables 90 days and `_bak` 7 stable days.
- **KB:** new (related L-DQ-135, L-CDI-135)

### PD-P2-177 Conflicting sale observations go to a review table, not a delete
- **Date:** 2026-10-29
- **Context:** `<legacy_db>.sale_history` (plain MergeTree)
- **Lesson:** There were no exact duplicate rows, but 6,406 (property, date, source) keys carried two different prices.
- **Fix / do this:** Create `<gov_db>.sale_conflict_review` with both prices and their evidence. Prefer the recorder/deed price, otherwise the later ingest, and set `training_eligible = 0` until resolved.
- **KB:** new

### PD-P2-178 FINAL scans on the request path: persist a shared snapshot with a lease
- **Date:** 2026-10-03
- **Context:** backend clickhouse_store (coverage page, market heat)
- **Lesson:** Every gunicorn worker rescanned the universe every 5 min on its own clock: 51 per-state FINAL passes, about 1,300 s of ClickHouse time per 15 min. Loading 3.3M national `market_heat` rows into one dict spiked RSS by about 3 GB and OOM-killed a worker.
- **Fix / do this:** Persist the snapshot in ClickHouse (max age 45 min) and allow one recompute at a time through a 20-minute lease row. Load only the ZIPs the corpus references.
- **KB:** L-METHOD-133 (lease/per-ZIP: new)

### PD-P2-179 Typeahead serving table: narrow ORDER BY, rebuilt per state and swapped
- **Date:** 2026-10-29
- **Context:** `universe_address_index`
- **Lesson:** A narrow ReplacingMergeTree `ORDER BY (address_norm, state, city, property_id)` turns `LIKE 'prefix%'` into a granule-range read instead of a 40M-row scan. It is rebuilt nightly per state via staging and EXCHANGE TABLES.
- **Fix / do this:** Build into staging and EXCHANGE. Never truncate and insert in place.
- **KB:** L-ENV-106

### PD-P2-180 A shared 16 GiB ClickHouse: per-statement caps, and re-run arms that OOM inside a gate
- **Date:** 2026-10-24
- **Context:** gate202 addendum, ML LESSONS §5
- **Lesson:** The server-total limit (16 GiB) is shared across sessions. An ml16 refresh hit OOM, and the pub2 nightly runs uncappable single statements of up to 8.5 GB. Simultaneous heavy jobs caused a production outage. An OOM inside one arm of a comparison is noise the verdict can't see.
- **Fix / do this:** Cap each statement at 3 GiB or less and 4 threads or fewer, and isolate heavy jobs (`docker run --rm --cpus 2 --memory 6g`). Re-run, once and with all arms back-to-back, any state whose log shows MEMORY_LIMIT_EXCEEDED or Code 241. If it fails again, exclude it with the reason. Don't hold the heavy lock while waiting.
- **KB:** new (related L-CDI-292, L-ENV-109)

### PD-P2-181 Read-only native ClickHouse capture: allow-listed SQL, verified caps, no retries
- **Date:** 2026-10-24
- **Context:** native_capture.py (graph input capture)
- **Lesson:** Every query must match an exact approved SQL hash, and callers cannot override the caps. The client enforces `readonly=2`, 2 threads, 4 GB, 280 s execution, a 300 s transport timeout and zero query retries. A `getSetting` probe verifies the effective caps before any input is read. The capture runs in a one-shot container (1 CPU, 6 GiB, read-only root) under the heavy lock, and credentials never enter receipts.
- **Fix / do this:** Before a sensitive read, verify the effective settings on the server, not just the ones you requested.
- **KB:** new (related L-ENV-112)

## Storage & backups

### PD-P2-182 Keep the masked sample as an immutable snapshot of record, archived, never deleted
- **Date:** 2026-10-04
- **Context:** s1 snapshot 20261004T073032Z
- **Lesson:** Snapshots are kept 2 per state and older ones are archived, never deleted. The tooling-VM copy of record is a tsv.gz, and refresh steps are written next to it. The GCP→Azure copy (about 45 MB, about $0.01 egress) was treated as spend that needs a request and a separate confirm.
- **Fix / do this:** Snapshot before load, keep the copy of record with a README, and treat cross-cloud copies as spend.
- **KB:** new

### PD-P2-183 Back up a profile or connection with a v3 export before you recreate or delete it; connection exports mask passwords
- **Date:** 2026-10-04
- **Context:** DQ_<PREFIX>_PU_ID profile backup zip; connection backup zip <prefix>_conn_backup_20261004.zip
- **Lesson:** Both recreations and deletions were preceded by v3 export zips kept on the laptop. A v3 export of the PROFILE without dependencies succeeded (18,029 B, 6 entries) and did not count as a job run. This conflicts with a later KB note where PROFILE exports failed with MigrationSvc_086. The note "profiles cannot move (FRS_108)" is superseded: FRS_108 only marks orphan profile documents. Each connection.json in a connection package has the password replaced by 8 asterisks, so a restore needs the passwords re-entered and creates new ids. The lane's secret scan reported 0 password fields because it read the nested SYS/*.Connection.zip entries as compressed bytes. The only copy of the backup was on the laptop, outside the synced folders.
- **Fix / do this:** Export, then change. Also save the `GET /profile/<id>` body as a second backup. Unzip nested entries before scanning for secrets, record where the passwords live for a restore, and store the backup in a synced, private location.
- **KB:** L-DQ-025, L-DQ-124, L-DQ-029 (disputed), L-CONN-064, L-CONN-007 (nested-zip scan: new)

### PD-P2-184 Deploy a guard to a second host byte-identical, with backups and a lock-protected swap
- **Date:** 2026-10-04
- **Context:** guard 1.3 rollout to the tooling VM
- **Lesson:** The .py and .json are copies of the laptop master, checked by sha256sum. Only `<prefix>_idmc_guard.host.json` differs per host, and it must never sit next to the laptop master, because it switches the session provider. Updates back up `<file>.bak-<lane>-<UTC>` and swap under the cron's flock. Undo = remove the one tagged crontab line, the symlink, and rename the folder (keeping the ledger).
- **Fix / do this:** Keep one master, put host-only keys in a host file, take backups, swap under the lock, and write the undo.
- **KB:** new

### PD-P2-185 The nightly backup covered 2 of 6 databases, failed every night, and copied backup tables: gold was never backed up
- **Date:** 2026-10-29
- **Context:** `/opt/<db-host>_clickhouse_backup_v2.sh`; backup inventory
- **Lesson:** It exported only `<legacy_db>` and `<gov_db>`, so gold, silver, bronze, site and ML had no cloud copy. It re-uploaded 176 GB of in-database `_bak` tables every night and exited 1 on 5 dictionaries (`dict_tiger_*`, `dict_<city>_neighborhood_*`), so its alert was always red. Cloud sets were 8 x ~180 GB because unchanged tables were copied, not referenced.
- **Fix / do this:** Back up every database you keep (set the DB list to all six). Exclude `(_bak|backup|_snap_|__pre_|_prev$|scratch|test)`, export dictionaries as schema only, carry unchanged objects by reference, then run a restore drill of gold into scratch, weekly.
- **KB:** L-ENV-113

### PD-P2-186 In-database repair backups pile up: keep the oldest copy per table-state as the baseline, drop the rest
- **Date:** 2026-10-29
- **Context:** ClickHouse disk (534 GB used, 91 % full); classify.py / backup_verdicts
- **Lesson:** Each repair lane copied the partitions it touched (`cfx_*_bak`, `w34_snap_*`, `gl_*_bak_v3_*`, `gcl_*_bak`, `__pre_do_final_20260928`), and nobody dropped them: 190.5 GB of repair copies held 464 copies of 150 table-state pairs (cityfix 291 tables; TX had 6 passes). There were also 31.8 GB of site `_prev/_next` copies and 26.9 GB of test databases. Verdicts:
  - 314 newer copies (123.8 GB): drop.
  - 167 oldest copies (64.0 GB): export as the baseline (Coldline, 90 days), then drop.
  - 141 test or rehearsal copies (26.9 GB): drop.
  - 8 site rollback copies (31.8 GB): drop after verification.
  - 49 (2.6 GB): review.
  - 93 still in use (7.1 GB): keep.

  The target of about 265 GB used is reached by keeping two cloud backups and no standing copies.
- **Fix / do this:** Classify each backup by name regex (source table, state, lane) plus query_log reads and writes. Keep two off-server backups only: the nightly backup and one frozen baseline. Give every backup an owner, and drop it after about 7 stable days. A repair takes a partition backup only for the minutes of its swap and keeps a small field-level undo ledger for 90 days.
- **KB:** L-ENV-114

### PD-P2-187 Guards before any drop: unchanged since inventory, unread for 7 days, no view, outside the window
- **Date:** 2026-10-29
- **Context:** Backup consolidation drops
- **Lesson:** Before any drop, a table must:
  - still exist, with metadata time equal to the frozen list
  - have no SELECT by anyone except `default` in 7 days
  - not be referenced by any view
  - have a verified export receipt (baseline class)
  - be dropped outside 03:00-07:00Z with load1 < 16

  A table failing any check is skipped, never forced.
- **Fix / do this:** Freeze the verdict list, re-check every guard per table at drop time, and write a receipt per table.
- **KB:** L-METHOD-048

### PD-P2-188 Fix backup coverage before dropping the stacked copies
- **Date:** 2026-10-29
- **Context:** Phase order of the clean-gold path
- **Lesson:** Until gold was in the nightly cloud backup, the stacked repair copies were the only spare copy of pre-repair gold. So B3/B4 (drops) depend on B1 (nightly scope) being green. Copies become droppable 7 days after the last repair pass (cityfix 10-31, zip/nominal/condo 11-02).
- **Fix / do this:** Order: backup coverage -> baseline export -> drops; take stable dates from the last pass.
- **KB:** L-ENV-105

### PD-P2-189 Backups have one shape: a janitor, a scratch database and a weekly restore drill
- **Date:** 2026-10-29
- **Context:** Keeping storage clean
- **Lesson:** The steady-state rules:
  - a janitor drops any unregistered `_bak` / `_snap_` / `__pre_` / scratch table older than 7 days
  - only `scratch` accepts ad-hoc tables, and it is emptied nightly
  - `CREATE DATABASE` is admin-only
  - every week, restore a gold partition from the cloud into scratch and check the row count
- **Fix / do this:** Put the janitor and the drill on a schedule, and review backup alerts weekly.
- **KB:** new

### PD-P2-190 POSTGRES_DB in the container env is not the list of databases
- **Date:** 2026-09-07
- **Context:** Postgres dumps for the four apps' backups
- **Lesson:** The real databases had other names; the env names were empty placeholders.
- **Fix / do this:** Enumerate `select datname from pg_database where not datistemplate and datname!='postgres'` and dump each.
- **KB:** new

### PD-P2-191 Neo4j Community can only dump offline
- **Date:** 2026-09-07
- **Context:** Neo4j backup of a second app
- **Lesson:** Stop the container, run a one-off container on the bind-mounted data with `--user root` and a writable backup dir, and restart inside a `trap ... EXIT` so it always comes back. It is kept out of the daily cron because it means downtime.
- **Fix / do this:** Refresh Neo4j dumps in a maintenance window only.
- **KB:** new

### PD-P2-192 Nested .git folders become submodule pointers in a filesystem capture
- **Date:** 2026-09-07
- **Context:** `av-capture.sh` box captures to git
- **Lesson:** A captured tree with nested `.git` dirs commits gitlinks and loses the files; the script renames them `_git_history_snapshot`. It also skips files over 100 MB and data dirs (covered by DigitalOcean volume snapshots) and records them in `SKIPPED.txt`.
- **Fix / do this:** Neutralize nested repos before committing a capture; list what was excluded and where it is restored from.
- **KB:** new

### PD-P2-193 az run-command and SAS tokens: base64 everything
- **Date:** 2026-09-07
- **Context:** Pushing DB dumps to Azure Blob from VMs
- **Lesson:** `az vm run-command --scripts` on Windows mangles spaces, so the on-box script is sent base64 and run as `echo${IFS}<b64>|base64${IFS}-d|bash` (with `${IFS}` single-quoted). A SAS embedded raw in a quoted string splits on `&` and uploads fail with 409/auth errors; pass it base64 and decode on the box. A single Put-Blob works up to 5000 MiB with that SAS version, so azcopy was not needed.
- **Fix / do this:** Base64 the script and the SAS; background long jobs on the box with `setsid` and poll.
- **KB:** L-ENV-073, L-ENV-007, L-ENV-003

### PD-P2-194 The app droplets accept SSH only from one corporate range
- **Date:** 2026-09-07
- **Context:** DigitalOcean app / data / ci droplets
- **Lesson:** Besides the DO cloud firewall, an on-host ufw allows SSH only from the corporate proxy range (`<ip>/24`), so SSH works only from that network. A DO API token can manage firewalls and snapshots but cannot open a shell.
- **Fix / do this:** Test SSH with a short timeout first; a timeout means the wrong network, not the wrong key.
- **KB:** L-ENV-011

### PD-P2-195 Backup layout: code in git, databases in Blob, ClickHouse by snapshot
- **Date:** 2026-09-07
- **Context:** Interim backups of the four apps until the GCP cutover
- **Lesson:** Code and config per box went on `vm/<host>` branches with a `live-final` restore pointer and a RESTORE.md map on main, mirrored to GitLab and SHA-checked. Postgres dumps run daily (03:40 cron) into a private Blob container with a 90-day lifecycle. ClickHouse was skipped (moving to BigQuery) and is covered by DO volume snapshots. If a cron stops, backups age out in 90 days.
- **Fix / do this:** Verify with a 4 x (GitHub / GitLab / Blob under 48 h / snapshot) PASS/GAP matrix; remove the crons and SAS files at cutover.
- **KB:** L-ENV-038

### PD-P2-196 Captures contain secrets: wipe staging, keep repos private, rotate what passed through chat
- **Date:** 2026-09-07
- **Context:** Box captures and handoff
- **Lesson:** Captures deliberately include `.env` files and certs; the script wipes its staging dir. Tokens shared in chat (DO token, GitHub PAT) and cleartext GitLab PATs in on-box git remotes had to be rotated; the baked container-scoped SAS is revoked by rotating the storage keys.
- **Fix / do this:** Use short-lived tokens, keep backup repos private, never leave tokens in git remote URLs.
- **KB:** L-ENV-043, L-METHOD-088

### PD-P2-197 BigQuery dataset ACLs: set the full list when you create the dataset
- **Date:** 2026-10-03
- **Context:** Creating <sample_db> with the platform SA
- **Lesson:** The SA had datasets.create but not datasets.update or delete, so a wrong ACL could not be fixed and the dataset could not be rolled back. Passing access entries on insert drops the default creator-OWNER entry. A GCS-staged `bq load` failed because storage.objects.create was denied.
- **Fix / do this:** Set the full ACL at create time, with the creator SA explicitly as OWNER. Load Parquet with a local-file load job. Use a default table expiration and write the rollback as "drop tables".
- **KB:** new

### PD-P2-198 A container's RAM limit is not its swap limit
- **Date:** 2026-10-04
- **Context:** The sample-pg container container on the tooling VM (8 of 15 GB swap already used)
- **Lesson:** `--memory 1g` left MemorySwap at 2 GB, so the container could use another 1 GB of swap. It also had no PIDs limit.
- **Fix / do this:** Set `--memory-swap` equal to `--memory` and add `--pids-limit` on shared hosts.
- **KB:** new

### PD-P2-199 When your own identity lacks rights, read metadata as the VM's service account over IAP
- **Date:** 2026-10-03
- **Context:** The operator identity had no BigQuery permissions
- **Lesson:** testIamPermissions showed the operator identity held only compute get/list, IAP tunnel and actAs. The platform VM's SA had datasets.create, jobs.create and table rights.
- **Fix / do this:** Run `gcloud compute ssh <vm> --tunnel-through-iap`, then use python with the metadata token. Use `__TABLES__` metadata queries (0 bytes billed). Put your own maximum_bytes_billed on every query; 50 MB blocked a 328 MB TABLE_STORAGE query. Clean up /tmp afterwards.
- **KB:** L-ENV-008, L-ENV-009; the metadata-token route is new

### PD-P2-200 BigQuery's default quota is not a spend cap
- **Date:** 2026-10-03
- **Context:** The shared-services BigQuery project
- **Lesson:** QueryUsagePerDay was at its 200 TiB/day default (about $1,250/day possible), with no per-user limit. A custom quota needs serviceusage.quotas.update, which no SA had.
- **Fix / do this:** Set maximum_bytes_billed in every dbt-bigquery profile and a default table expiration on sample datasets. Leave the custom quota as an owner step.
- **KB:** L-ENV-041

### PD-P2-201 A secret in a container's env can be read by anyone with docker inspect
- **Date:** 2026-10-03
- **Context:** airflow-scheduler on the platform VM
- **Lesson:** A Postgres role credential (<redacted>) sat in plaintext in the compose environment. The lane's first redaction filter missed it because it matched key names only.
- **Fix / do this:** Move the secret to an env_file with mode 0600 or a secrets backend, then rotate it. Redact by value, not only by key name.
- **KB:** L-METHOD-087 (related)

### PD-P2-202 Default table expiration leaves the empty BigQuery dataset behind
- **Date:** 2026-10-04
- **Context:** Sample datasets with defaultTableExpirationMs = 30 days
- **Lesson:** Expiration removes only the tables. The empty dataset stays until someone deletes it.
- **Fix / do this:** Track the dataset delete (`DELETE .../datasets/<ds>?deleteContents=true`) as its own undo step.
- **KB:** new

### PD-P2-203 Deleting a sensitive file: check by metadata only, and make old backups fail closed
- **Date:** 2026-10-04
- **Context:** Deleting an obsolete salt file on the DB host
- **Lesson:** Before the delete, the lane checked:
  - no live script referenced the file;
  - no process had it open;
  - no heavy-lock holder was active;
  - The file was read only with stat (64 B, 0400).

  Three older backups still name the path, so a restore of the pre-fix script now fails closed, which is intended. An earlier statement that "snap/ is empty" was stale by the time it was posted.
- **Fix / do this:** Re-list a directory right before stating anything about it. Back up the README first. Confirm the delete with `test -e`.
- **KB:** new (related L-ENV-078)

### PD-P2-204 Lossless table retirement and consolidation on ClickHouse
- **Date:** 2026-10-30
- **Context:** GitLab ops snapshot: table-retirement, table-consolidation (213 tables into 9 shared tables + a manifest), history-preservation
- **Lesson:**
  - **Retire:**
    1. Freeze the exact parts.
    2. Upload a content-addressed GCS object under a hold.
    3. Download it and restore into an isolated container.
    4. Compare parts, masks and checksums, and run CHECK TABLE.
    5. Quarantine-rename the table, then DROP it.
  - **Consolidate:** typed shared tables with compatibility views under the original names.
  - **Full-row digest:** spill after 32 MB with 1,024-row blocks, inside a 750 MB, 1-thread cap.
  - **Retention:** at least 14 days of observation and 90 days of archive. A passing date is never permission to purge.
- **Fix / do this:** Use the retirement gate that binds the proof files by SHA-256.
- **KB:** L-MIG-088 (related); new

### PD-P2-205 The new target host had no real backup
- **Date:** 2026-11-01
- **Context:** The new target VM holds the only copy of the migrated data
- **Lesson:** There was no backup timer. The single 85 GB local backup sat on the same disk and was never restore-tested. The backup worker asserted exactly 2 user tables, so it broke once <model_registry> was added. The backup user also lacked the BACKUP grant on the new table.
- **Fix / do this:** Schedule off-VM backups and restore-test them. Make backup workers discover their table set, and grant on new tables when they are added.
- **KB:** L-ENV-123

### PD-P2-206 A wide "one table for everything" design used about 11x the bytes per row
- **Date:** 2026-11-01
- **Context:** <property_table> at 256.76 GiB for 440.67M rows
- **Lesson:** The new table used about 626 B/row against about 54 B/row in the legacy estate. The remaining load projected to 2.08-2.83 TiB, against 2.46 TiB free.
- **Fix / do this:** Measure bytes per row per record kind from the first batches (system.parts) and project the full load before going on.
- **KB:** L-MIG-092

### PD-P2-207 Evidence storage: fixed caps, holds instead of deletion, immutable batched archives
- **Date:** 2026-10-09
- **Context:** gold_system ARCHITECTURE / RUNBOOK
- **Lesson:** The pilot safeguards are a 10 GiB (later 20 GiB) raw/history ceiling, 200 MiB headroom, a 40 GiB free-disk reserve and a 2 GiB/day transfer cap. They are not a capacity plan. Hitting a cap holds the work and keeps the evidence; there is no TTL deletion.
- **Fix / do this:** Batch small records into compressed, immutable GCS objects with hashes and manifests. Advance cursors only after the evidence is durable. Never silently raise a limit or delete evidence.
- **KB:** new

## Method & process

### PD-P2-208 Learn in IDMC on a masked sample, enforce at scale in open source
- **Date:** 2026-10-03
- **Context:** The property platform IDMC plan v3 core idea and decision
- **Lesson:** IDMC compute on the production DB host caused the earlier saturation incident, and the job cap is shared with the live host-app demo. So IDMC catalogs, profiles and gets CLAIRE rules on a 50,000-row masked sample through the off-prod agent. dbt/Airflow then run the accepted rules on all 6.08M MA rows (and later all 51 states and other estates). The prod-host agent is retired and the PII-capable connections are unbound. Runs on sample copies are labelled "dialect parity", never "scale". A shared contract table joins the two sides.
- **Fix / do this:** Under a job cap, use IDMC for understanding on small, stable, masked samples, keep volume work outside it, and flow results back to IDMC as summaries.
- **KB:** new

### PD-P2-209 The pre-run check fails closed and has explicit exit codes
- **Date:** 2026-10-04
- **Context:** <prefix>_idmc_guard.py check
- **Lesson:** Exit 0 = allowed, 3 = blocked, 2 = usage, 4 = source read failed, 5 = login blocked. `check` exits 3 whenever any source read failed, also in a cached status, an offline status or an unexpected exception. A usage error in check exits 3. The remote laptop check needs remote exit 0 AND an ALLOWED line; a hop error, ssh 255 or a timeout = 3. Proven: --jobs 1 exit 0 in 6 s, --jobs 9999 exit 3.
- **Fix / do this:** Call `check --jobs N` before any IDMC job. Block on exit 3. Prove the pause with one refused test run (simulated org 8,100 → exit 3).
- **KB:** L-IPU-059

### PD-P2-210 Day-cap overrides: one UTC date, with a reason, never on the month or hour caps
- **Date:** 2026-10-04
- **Context:** Guard 1.3 day_cap_overrides (phase 2 of the budget work)
- **Lesson:** On 2026-10-04 the day cap was raised from 20 to 45 to front-load the first IDMC cycle before the org reached the 8,000 pause: day_cap_overrides {"2026-10-04": {"cap":45, "reason":...}}. The override applies on that UTC date only; check uses its own date's cap and status prints the override when it applies. A malformed entry is ignored, so the base cap applies. Month and hour caps are never overridden.
- **Fix / do this:** Put temporary budget raises in config as dated, reasoned entries, each tied to the card that approved it, rather than editing the base cap. Test the boundaries (40+5 allowed, 41+5 blocked, other dates ignored).
- **KB:** new

### PD-P2-211 A cron monitor should push only on a change and must never break the cron line
- **Date:** 2026-10-04
- **Context:** <prefix>_idmc_guard_watch.py
- **Lesson:** The monitor reports FAILING when the ledger exit code is non-zero, the status is missing or more than 40 min old, read errors were recorded, or a login block exists. It sends one push after 2 failing runs in a row and one on recovery. A failed push keeps the old state, so it retries. It always exits 0 and never prints the topic.
- **Fix / do this:** Make monitors change-triggered with a debounce, and wrap the cron in flock and timeouts.
- **KB:** L-AGENT-029

### PD-P2-212 "100% ready" = a read-only gate script with numbered, measurable gates, non-zero exits and 3 clean runs
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** <prefix>_idmc_gate.py G1-G19 (22 checks); earlier readiness gates G1-G12 and card C7 "Prove ready", closed in Sprint 1
- **Lesson:** In the first plan some gates were not measurable or not under the app's control, whole deliverables had no gate, and the final proof could only turn green in later sprints. The gate script fixed that: each gate returns GREEN/AMBER/RED/UNKNOWN with numbers, and an exception becomes UNKNOWN, never green. Exit 0 = all green, 1 = amber left, 2 = red or unknown left. The ClickHouse reads are skipped when the host's load1 ≥ 15 and are time-limited to 20 s. The first run: 7 green, 3 amber, 12 red. "Done" = all green in 3 consecutive daily runs.
- **Fix / do this:** Write the gate script first (sprint 1), give every deliverable a gate, judge progress by the script, not by claims, and end with an "all green in 3 consecutive daily runs" card.
- **KB:** L-METHOD-023

### PD-P2-213 Plan by adversarial review: v1 → v3 found 5 blockers and 46 majors; mark every step not yet run UNTESTED
- **Date:** 2026-10-04
- **Context:** Plan v3 process (v2 → v3: 4 critics)
- **Lesson:** 8 discovery lanes, 4 design lanes and 4 critics produced v3. The critics changed the store, the budget, the counting method, agent retirement and the parity route, and overturned several earlier assumptions (a BigQuery copy existing, hashing salts being safe). v3's decisions override earlier drafts, and every step nobody has run is marked UNTESTED.
- **Fix / do this:** Run refute-only critics before publishing a plan, record the decisions in one authoritative file that overrides the plan, tag untested steps, and qualify headline claims.
- **KB:** L-METHOD-046, L-METHOD-023

### PD-P2-214 One batched approval message for the owner; spend needs a request and a separate confirm; trims to another lane go to that lane
- **Date:** 2026-10-04
- **Context:** Plan v3 §6 (0 owner cards); approval list for the owner
- **Lesson:** All asks went into one message: egress spend, prod config changes, MCP write tools, the first scheduled cross-estate run, a Grafana plugin restart, an optional reversal (default no), and the pending vendor question. Spend items need a request followed by a separate confirm. A host-app cadence trim had been put on the platform's list, but it belongs to the host-app lane.
- **Fix / do this:** Send one message with numbered one-line items, and keep spend confirmation as its own step. A trim to another lane goes as one evidence comment on that lane's card. When a decision narrows an older rule, say so.
- **KB:** L-IPU-020

### PD-P2-215 Front-load the first IDMC cycle when the runway is short; if the cap hits, freeze IDMC but keep the OSS side running
- **Date:** 2026-10-04
- **Context:** Plan v3 runway rule 9
- **Lesson:** The reset window is unknown. If it is anchored on the 25th or rolls, the cap could arrive around Oct 6-7 instead of Oct 12-13. The cycle (scan + MA profile + CLAIRE generation/recommend + one DQ capability run + parity run) was therefore planned to finish by Oct 8. If the org reaches 8,000 first, property-platform IDMC work freezes until the reset, and dbt/Airflow keep going.
- **Fix / do this:** Put the IDMC-dependent steps first and keep a degraded mode that doesn't use IDMC.
- **KB:** L-IPU-058, L-IPU-054

### PD-P2-216 Demo freeze: no IDMC changes from 2 h before a demo, pinned prompts with fallbacks, and a read-only smoke check
- **Date:** 2026-10-03 / 2026-10-04
- **Context:** The property platform IDMC demo run-of-show
- **Lesson:** Live accepts or scans during a demo risk accidental publishes, and CLAIRE is blind while a source scans. So: no property-platform scans, profile runs, rule accepts or catalog edits from 2 h before a demo until it ends. The pinned conversations exist before the demo, and the read-only smoke test checks: last scan < 35 days, 45 terms, ≥ 40 links, RuleInstances with a score, results < 26 h, and gate exit 0. Rule recommendations are shown from pinned answers, never re-accepted live.
- **Fix / do this:** Use a freeze, pinned prompts with fallbacks (≥ 6 of 8 passing twice) and a smoke script.
- **KB:** L-METHOD-075

### PD-P2-217 Coordinate with peer sessions through claims and card comments, and give owned objects a do-not-touch list
- **Date:** 2026-10-03
- **Context:** plan v3 §9
- **Lesson:** The plan lists, with their owners, the objects others own: the dq_claire project, the stage DB (no writes until confirmed free), the agent window paths (claim them before an override), host-app folders, schedules and glossary. A cross-project "blocked_by" never clears, so cross-project waits are written as text.
- **Fix / do this:** Re-check ownership before writing near peer objects. Hand off with one comment, not peer messages.
- **KB:** L-AUTH-054

### PD-P2-218 A hash-ordered town slice is a cluster sample, not a random one
- **Date:** 2026-10-03
- **Context:** interim stage pu_ma (33,277 rows, 8 towns)
- **Lesson:** Taking the first 8 towns in cityHash64(city) order was cheap (5.6 s, 4.7% of the partition read), but it biased completeness numbers and pulled in 3 typo towns by chance. The typo towns were a real spelling-drift finding.
- **Fix / do this:** Keep such slices as smoke tests only, and quote any number from them with the caveat.
- **KB:** new

### PD-P2-219 Never pipe stdin through gcloud compute ssh on Windows: deliver scripts with scp
- **Date:** 2026-10-03
- **Context:** gate run_gcp/run_tooling helpers; staging script delivery
- **Lesson:** The helpers write an LF-ending temp script, `gcloud compute scp` it (via an apps-VM hop for the tooling VM), run it, then delete it. The guard's subprocess hop sets stdin=DEVNULL. Passwords go to docker exec by env var name, never in argv.
- **Fix / do this:** Use scp + run, and give gcloud no stdin.
- **KB:** L-ENV-002, L-ENV-001

### PD-P2-220 Rule hooks in the glossary: candidate rules need profiling before thresholds
- **Date:** 2026-10-03
- **Context:** glossary §5 rule catalog (11 baseline + 32 candidates)
- **Lesson:** Candidates are drafted from the data dictionary and live measurements (for example 86,059 MA rows with an embedded unit and 7,853 with ZIP '00000'). They are marked "profile" until measured. CLAIRE's recommendations take precedence when they cover the same check. Zero-as-unknown values (living area, lot size, beds) need positive-value rules.
- **Fix / do this:** Profile before you fix a threshold, and link each term to its rules.
- **KB:** new

### PD-P2-221 IDMC never writes gold; route failures to repair lanes by estate
- **Date:** 2026-10-03
- **Context:** rules2dbt §8 failure routing
- **Lesson:** A FAIL on gold goes to the gold repair queue. A FAIL on a copy where gold passes goes to sync (re-sync from gold, never patch the copy). App DBs go to the app owner. PARITY_MISMATCH goes to the translator. DRIFT/STALE go to sampling. INVALID/ERROR go to the rule owner. SKIPPED means the guard did its job.
- **Fix / do this:** Enforce the routing through grants. Each DQ identity writes only its results schema.
- **KB:** new

### PD-P2-222 Pick estates by data, not by engine: copies of one sample are a parity check, and every exclusion needs a written reason
- **Date:** 2026-10-03
- **Context:** Plan v3 §11; G10 "dbt across different estates" (CH gold, BQ sample, PG stage)
- **Lesson:** The BigQuery and Postgres "estates" were loaded from the same ClickHouse snapshot, while the real other estates got no decision. The corrected list: gold <property_table>; gold side tables; bronze/silver before promotion; the Postgres source registry; the Mongo twin (land it in ClickHouse, or exclude it with a written reason); Neo4j out of scope (written down); BigQuery marts for generic rule families only.
- **Fix / do this:** Label copy runs "dialect parity on the sample". List every store with its rule kinds and engine, and give an explicit reason for each exclusion.
- **KB:** new

### PD-P2-223 Plan read-only, size each fix by a dry run, and wait for a one-word GO
- **Date:** 2026-10-29 / 2026-11-02
- **Context:** ClickHouse change plan, mastering plan, storage plan
- **Lesson:** Every step lists what it changes, its dry-run size, its script (dry run by default; `APPLY=1` or `--execute` to act), its undo and the GO it needs (`GO 01`, `GO 02 drop`, `GO B1`, ...). Steps that touch what the site reads (tombstones, renames, archive moves, deletes) are marked GO. Applying starts with one state, then the rest.
- **Fix / do this:** Make every write-capable script dry-run by default, and apply to one partition before the rest.
- **KB:** L-METHOD-013, L-METHOD-065

### PD-P2-224 Work inside the lease holder's lane on a shared database
- **Date:** 2026-11-02
- **Context:** One session held the lease on the new project's databases and IDMC project
- **Lesson:** Every write ran inside that lane or after a hand-over, and requests went as comments on the card. Work that did not touch the table being gated (dictionary, <model_registry>) could start in parallel. A peer's claim being reaped left the AV runner without an owner, which was flagged as a risk.
- **Fix / do this:** Check the lease before writing, coordinate on the card, and split paths that do not overlap.
- **KB:** L-METHOD-062, L-METHOD-063

### PD-P2-225 Plan backward from "ready" with a critical path and named owners
- **Date:** 2026-11-03
- **Context:** Reverse timeline to "the 5 tables are ready" (~06:00Z)
- **Lesson:** The path: eligibility gate, state by state, smallest first (~80 s per small state, big states slower) -> proofs -> swap -> Certified AV for the remaining 2.27M -> proof run. Without the AV step the tables are ready at ~05:15Z, with those properties flagged. "Ready" was defined per table, separately from the traffic cutover.
- **Fix / do this:** Define the finish line per table, list every step with owner, duration and status, and name the risks (big-state slowdown, an unowned runner).
- **KB:** new

### PD-P2-226 Before-images and undo for every IDMC asset edit
- **Date:** 2026-11-01 / 2026-11-04
- **Context:** Task property, profile and folder changes
- **Lesson:** The pattern used for each kind of edit:
  - `taskprops.py` saves `task_backup_<id>.json` before POSTing session properties
  - profile edits keep `before_<name>.json`
  - moves log from/to to `moves_log.jsonl`
  - sources rewrites keep `sources_pre_master_20261102`
- **Fix / do this:** Save the full prior body or rows before every write, and write the undo next to it.
- **KB:** L-METHOD-013, L-METHOD-022, L-METHOD-016

### PD-P2-227 Reuse a proven builder and change only constants, specs and local tests
- **Date:** 2026-11-02 / 2026-11-04
- **Context:** Rule-spec builder lineage (CRM -> gold cleanup 10-29 -> the new project)
- **Lesson:** The 11-02 and 11-04 rule builders were copies of earlier proven builders in which only the constants, the spec list and the local evaluation changed. They worked the first time.
- **Fix / do this:** Copy a builder that already works and keep its safety behavior (plan / build --execute / verify, the max-attempt rule).
- **KB:** L-METHOD-020

### PD-P2-228 Rename a "pilot" whose correct result is nothing merged
- **Date:** 2026-08-03
- **Context:** Track A (Idaho, single source)
- **Lesson:** The single-source run was renamed a "mechanics rig" so that ~98,115 1:1 xrefs and zero consolidations would read as a PASS, not a letdown. Track A had to be green before Track B started.
- **Fix / do this:** Name runs by what they prove, state the expected result up front, and gate dependent tracks on it.
- **KB:** L-MDM-045, L-METHOD-039

### PD-P2-229 State what a plan does not fix
- **Date:** 2026-10-29
- **Context:** Clean-gold plan
- **Lesson:** The plan lists what it leaves open: identity reconciliation (a product decision), attribute coverage (needs new sources) and listing freshness (source maintenance). This stops anyone assuming storage or cleanup work raises coverage.
- **Fix / do this:** End every plan with a "does not fix" section.
- **KB:** L-METHOD-055

### PD-P2-230 Prove every claim with a run, an export or a count; old docs describe dead designs
- **Date:** 2026-11-03
- **Context:** Address verification handover
- **Lesson:** Older documents describe a 12-addresses-per-call "cloud window" and a 45-minute native pipeline that no longer run. The handover gives its check time and asks the reader to re-check before acting.
- **Fix / do this:** Back each statement with an activity-log entry, a mapping export or a ClickHouse count, and date it.
- **KB:** L-METHOD-046

### PD-P2-231 Stay read-only until you know who owns a lane
- **Date:** 2026-11-03
- **Context:** Shared org, shared runtime, many sessions
- **Lesson:** The rules: check the tracker cards for the lane owner first, touch only the named objects, never restart or reconfigure the agent, never print credentials. In practice another session's runner restarted 12 capture lanes minutes after they were stopped.
- **Fix / do this:** Claim on the tracker, announce what you stop and why, and check after a stop that nothing restarted it.
- **KB:** L-METHOD-060, L-AUTH-054, L-METHOD-135

### PD-P2-232 Do not orchestrate production through chat sessions
- **Date:** 2026-11-12
- **Context:** National go-live ("CODE RED", 11-08)
- **Lesson:** Sessions were reaped after 120 minutes again and again, rebuilds ran from cron and SSH scripts, and steps stalled when a session ended.
- **Fix / do this:** Move recurring work into an IDMC linear taskflow on a schedule; when a lease expires, reassign its open steps explicitly.
- **KB:** L-METHOD-142, L-CDI-069

### PD-P2-233 An alert job with no destination is no alerting
- **Date:** 2026-11-12
- **Context:** `phase3_alerts.py`
- **Lesson:** The alert script ran every 5 minutes, but `DEST` was empty, so launch alerts went only to a log file.
- **Fix / do this:** Test that an alert reaches a person (a Slack webhook is the quick fix) before relying on it.
- **KB:** new

### PD-P2-234 Prototype rules in SQL if you must, but port them before scaling
- **Date:** 2026-11-12
- **Context:** Phase-3 matching and survivorship in `phase3_onemaster.py`
- **Lesson:** The keep-apart arms, unit vetoes and alias chains lived in a unit-tested Python/SQL module where a change took minutes; the IDMC versions stopped at the pilots, so the national master ended up outside IDMC.
- **Fix / do this:** Port each proven rule into the mapping before fanning out.
- **KB:** L-MDM-081

### PD-P2-235 Downstream refreshes on independent clocks race the build
- **Date:** 2026-11-12
- **Context:** Steps after each golden build
- **Lesson:** Sale events (15 min), value decisions (hourly), search projection (30 min), release receipts (5 min), drift (daily) and the crawler tap (10 min) ran on 6 cron clocks, none waiting for the master build.
- **Fix / do this:** Chain downstream steps on the build-finished event (for example a CAI process), in one order.
- **KB:** new

### PD-P2-236 Where CAI fits a mastering program, and where it does not
- **Date:** 2026-11-12
- **Context:** CAI options for the property platform
- **Lesson:** CAI suits go-live approvals, pause/resume switches, event chaining, real-time address lookup (about 0.2-2 s per call) and merge-correction endpoints. It is wrong for bulk work (per-run metering, 10,000-activity limit per run) and for timed runs: a CAI process on the Secure Agent never fired from the CAI scheduler, so timing belongs to a scheduled taskflow. CAI keeps working at the DI job cap, but the jobs it starts still count.
- **Fix / do this:** Use a scheduled taskflow for timing and CAI for events and approvals; test one shell-step call before relying on it.
- **KB:** L-CAI-142, L-CAI-050, L-CAI-084, L-CAI-088, L-CAI-096, L-IPU-041

### PD-P2-237 Mark inferences separately from measured facts
- **Date:** 2026-11-12
- **Context:** Review of why the IDMC master was dropped
- **Lesson:** No written reason for the switch to SQL was found on the server; the review marked which reasons were measured (query_log throughput) and which were inferred (iteration speed, deadline pressure).
- **Fix / do this:** Label every conclusion as measured or inferred and name the evidence.
- **KB:** L-METHOD-046

### PD-P2-238 Write down every object you create and how to undo it
- **Date:** 2026-11-03
- **Context:** Shared-org builds (Oracle test task, MDM pipeline, folder moves)
- **Lesson:** The rule for each build is to list the task, mapping and table created with the undo (delete task, delete mapping, drop table); the MDM session kept `ids.json`, move logs and task backups for the same reason.
- **Fix / do this:** Keep an object ledger with undo steps per run.
- **KB:** L-METHOD-013

### PD-P2-239 Co-owned config: pull and diff first, additive edits only
- **Date:** 2026-08-01
- **Context:** `ingest-sources.yaml` and the ingest README on the droplet
- **Lesson:** Several sessions edit the live config; overwriting it would drop another session's source blocks. The build tree and the droplet copy must be kept in sync.
- **Fix / do this:** Pull and diff the live file before editing; add, never replace.
- **KB:** L-METHOD-071

### PD-P2-240 Rank actions by importance, impact and effort before acting
- **Date:** 2026-11-12
- **Context:** The property platform master action list (29 items)
- **Lesson:** Scoring each action on importance (is launch blocked?), impact and rough effort put small, high-value fixes first (pause the sweeps, a failing check mapping, an alert destination, record pending decisions, repoint the CRM job). Any pause, delete or switch still needed the owner's word.
- **Fix / do this:** Rank before working a long backlog and flag which items need an owner decision.
- **KB:** new

### PD-P2-241 The activity log has no runtime-environment or agent field
- **Date:** 2026-10-03
- **Context:** Budget-tripwire rule T2 tried to filter property-platform jobs by RE <RE id>
- **Lesson:** Activity-log rows carry no runtimeEnvironmentId or agentId, so runs can be attributed only by object name. Once property-platform compute moved to the shared host-app tooling RE, an RE filter could not have separated the two apps anyway.
- **Fix / do this:** Attribute by object-name prefix (<prefix>_ / DQ_<PREFIX>_). Better, log each submission's job id at the moment the guard starts it.
- **KB:** L-IPU-055 (partial); missing RE field = new

### PD-P2-242 The activity log keeps about 3 days and is purged a day at a time
- **Date:** 2026-10-04
- **Context:** Rebuilding the org's October month-to-date job count
- **Lesson:** The log held about 3,700-3,806 rows. Between 01:25Z and 03:21Z on 10-04 the oldest row jumped from 09-29 23:32Z to 09-30 23:36Z and the row count fell to 2,476, so effective retention was about 3.2 days, not the assumed ~4.5. At 550-700 rows a day, month-to-date cannot be rebuilt from the log after a few days.
- **Fix / do this:** Seed a local ledger from a capture right away and snapshot the log at least every 6 h. Never rely on the log alone for month-to-date.
- **KB:** new

### PD-P2-243 Re-measure job pace after a consolidation change
- **Date:** 2026-10-03
- **Context:** Cap projections used Oct 1-3 pace (634-1,345/day) while a sync-consolidation change went live at 20:53Z
- **Lesson:** That change collapsed the Salesforce sync from 11 or 5 jobs per lane run to 1 task. About 680 of the Oct 1-3 jobs (roughly 235 a day) came from the old per-object Salesforce sync tasks, so projections made from the old pace were stale.
- **Fix / do this:** After any lane-consolidation change, re-measure 24 h of pace before asking anyone to change cadence, and name the concrete lever.
- **KB:** new

### PD-P2-244 Check the host's published heavy-job window, don't hard-code one
- **Date:** 2026-10-04
- **Context:** stage_s1.sh refused only hard-coded windows
- **Lesson:** `/etc/<app>/heavy-job-window.conf` reserves 03:00-07:00Z for backups, and `<app>-heavy-window` exits 3 inside that window. The script never called it. The earlier "safe window" of 04:00-06:00Z had no measured basis and was exactly the window of an earlier outage, when ClickHouse was OOM-killed at 05:59:54Z.
- **Fix / do this:** Call the host's window checker in every heavy script. Pick windows from 7 days of Prometheus p95 data.
- **KB:** new

### PD-P2-245 Gate on smoothed load and per-slice pressure
- **Date:** 2026-10-03
- **Context:** Prod DB host gates (load1 < 10 / < 6 / 12 in different places)
- **Lesson:** Instantaneous load1 is spiky, so a single dip can open the gate in the middle of an overload. A host-wide PSI gate set at 20% would almost never open. The plan, the spec and the script each used a different threshold.
- **Fix / do this:** Gate on avg_over_time(node_load1[15m]) plus infaagent.slice pressure, with one value used everywhere.
- **KB:** new

### PD-P2-246 Ask for an OK as the decision it reverses
- **Date:** 2026-10-03
- **Context:** A BigQuery sample after the owner's 09-10 "no BigQuery for the property platform" decision, framed as "$0.05/month"
- **Lesson:** Calling a reversal of a recorded decision a tiny spend OK hides the decision. Request and confirm are two separate approvals.
- **Fix / do this:** Word the OK as the decision it reverses, with bounds and a "declined" branch that names the demo scenes lost. Wait for every lane digest before writing the plan.
- **KB:** new

### PD-P2-247 Claim every path before writing, tag every write, and keep the old text
- **Date:** 2026-10-04
- **Context:** Verifier audit of the tooling-db, budget-guard, cards and plan-docs lanes
- **Lesson:** The audit found five problems:
  - writes landed outside the claimed paths or before the claim (/tmp, env files, ~/.idmc, __pycache__);
  - a scope comment claimed a check before that check could have run;
  - cards were changed with no session tag;
  - `--no-keep-old` overwrote descriptions, leaving the undo pointing at text that was never saved;
  - an undo said "delete".
- **Fix / do this:** Claim every path, including /tmp, env and cache files. Tag each write with the session. Save the old text before overwriting. Make undos archive instead of delete.
- **KB:** L-METHOD-124 (related); rest = new

### PD-P2-248 Python writes can silently change shared files' line endings and bytes
- **Date:** 2026-10-04
- **Context:** add_lessons_1003.py and the published plan file
- **Lesson:** Writing with `newline='\n'` converted 5 shared KB files, including lessons.jsonl, from CRLF to LF, which changed every line. A non-raw string turned `\a` in a Windows path into a BEL byte (0x07).
- **Fix / do this:** Preserve each file's line endings (`newline=''`). Use raw strings or forward slashes for paths, and diff at byte level before publishing.
- **KB:** L-ENV-023 (related)

### PD-P2-249 Re-verify facts live right before publishing a plan
- **Date:** 2026-10-04
- **Context:** Plan facts that the verifiers refuted
- **Lesson:** The plan stated facts that were already wrong:
  - a connection was "on the delete list" but already gone;
  - "0 CLAIRE rules" was wrong (18 proposed rows existed);
  - "0.5 vCPU" was actually 1 vCPU;
  - "/budget ~5,400" was about 6,150.
- **Fix / do this:** Re-read live state just before publishing. Mark numbers taken from the KB or assumed, and recompute the arithmetic.
- **KB:** new

### PD-P2-250 Never ask the owner for demo times
- **Date:** 2026-10-03
- **Context:** Tripwire "never within 40 min of a host-app demo"
- **Lesson:** No headless demo calendar exists, and demos are zero-prep for the owner. The 06:00-09:00Z slot still carries 26-32 host-app jobs a day.
- **Fix / do this:** Use fixed windows with automatic skips when the org's job controller is in a fast mode, host-app lanes are busy, or activityMonitor is non-empty. Alternatively, use a demo marker file the guard can read.
- **KB:** new

### PD-P2-251 Relabel probe rows so they can't pass as parity for a real rule
- **Date:** 2026-10-04
- **Context:** Parity verifier; tooling-VM table public.dq_parity
- **Lesson:** Two probe rows were stored under rule_id claire_ma_year_built_range with bounds 1600-2026. The real rule is 1700..toYear(now())+1, so those rows would read as parity for the wrong rule.
- **Fix / do this:** Run `UPDATE public.dq_parity SET rule_id = 'probe_' || rule_id WHERE source = 'idmc_cdi_probe'`. Never store probes under production rule ids.
- **KB:** new

### PD-P2-252 Check recorded business decisions before designing on a data store
- **Date:** 2026-10-03
- **Context:** Plan v1 put the IDMC sample in BigQuery
- **Lesson:** Memory and KB lines still described <legacy_ds> (110M rows) as present. It had been deleted on 09-10 under the owner's "no BigQuery for the property platform" decision, and a later decision made ClickHouse the only OLAP store, so Plan v1 had to be rewritten.
- **Fix / do this:** Read the decision cards and verify live state before trusting memory or KB claims about stores. Mark stale memory as superseded. Present any exception as an item that defaults to no.
- **KB:** new

### PD-P2-253 Probe a production DB host without leaking secrets or adding load
- **Date:** 2026-10-03
- **Context:** DB-host estate probe (load 17-20.8 on 4 vCPU)
- **Lesson:** The probe stopped above load 20 and read only system tables. It never opened the users.d XML files (they hold password hashes) and took settings from system.users and settings_profile_elements instead. Docker NAT hid the DB clients from `ss`.
- **Fix / do this:** Read client IPs from query_log, pg_stat_activity and currentOp. Print key names only, and leave nothing in /tmp.
- **KB:** L-METHOD-087

### PD-P2-254 Don't change another lane's contract; add a side table and a sibling project
- **Date:** 2026-10-04
- **Context:** claire_rule_recs / dbt_dq_results, owned by another lane
- **Lesson:** A repair lane lost an update when sessions edited stale copies of dq_checks.py.
- **Fix / do this:** Leave owned tables unchanged. Put new fields in the plan-owned `dq_rule_spec` (1:1 on rule_id) behind a canonical view. Write results to new tables and never ALTER another lane's table. Build a sibling dbt project. Fetch, diff, back up and claim before editing shared files.
- **KB:** new

### PD-P2-255 Tracker claims: check before writing, and beat inside the reaper window
- **Date:** 2026-10-03
- **Context:** Two cards shared by several sessions
- **Lesson:** Claims are `[claim:v1 op= key= session= until= paths=]` comments on one shared ledger card. The reaper releases claims that are quiet for 120 min, and it once missed a stale one. The laptop CLI knew only the old LEASE format and showed "lease: none" on live claims. One card had 4 holders in one day.
- **Fix / do this:** Check the card's comments for "claim:" before any write. Claim narrow paths and beat at least every 60 min. Force a claim only from a dead holder, with a note. Hand off in one comment on the owner's card.
- **KB:** L-METHOD-100, L-METHOD-064

### PD-P2-256 The tracker's API rate limit is shared, so budget your calls
- **Date:** 2026-10-03
- **Context:** Tracker landscape sweep
- **Lesson:** The limit is 60 requests/min per key, shared with another service, and 98 of 415 calls got 429. Showing one card reads up to 300 ledger comments, about 4 extra GETs. A cross-project blocked_by never clears.
- **Fix / do this:** Use the snapshot cache, batch reads, and keep each lane to 45 calls or fewer. Write cross-project dependencies as text.
- **KB:** new

### PD-P2-257 Read-only lanes must still disclose every POST they made
- **Date:** 2026-10-03
- **Context:** idmc-org lane
- **Lesson:** A "read-only" inventory still started a metering export job, made CDGC search POSTs and minted a JWT.
- **Fix / do this:** List every non-GET call in the lane's disclosure, and say whether it changed anything.
- **KB:** new

### PD-P2-258 Don't count a layer as ready while its own builds are red
- **Date:** 2026-10-04
- **Context:** <prefix>_idmc_gate.py (G1-G19) vs the existing dbt layer
- **Lesson:** The open-source dbt layer was already red: milestones had 1 fail and 123 skipped, and ma_scoreboard had 140 failures in 7 days.
- **Fix / do this:** The gate script exits non-zero on any red. Ready means all gates green in 3 consecutive daily runs. Report MA and national separately.
- **KB:** new

### PD-P2-259 Keep the central IDMC log and the app README current
- **Date:** 2026-10-03
- **Context:** The central IDMC log had 0 property-platform entries, and the property-platform README was stale (09-29)
- **Lesson:** Later sessions kept assuming nothing for the property platform ran in IDMC, and kept using the wrong org kit.
- **Fix / do this:** Log every IDMC action, with object ids, on the central log and the guard card. Update the app README after each change, and run kb_gate.
- **KB:** new

### PD-P2-260 Job counting that matched the org's own ledger exactly
- **Date:** 2026-10-04
- **Context:** guard vs the org job controller's budget ledger
- **Lesson:** The rule: 1 job per top-level activity-log row, plus 1 per NAMED taskflow child. An MTT's single unnamed entry is its own session, so it does not count again. Daily totals matched the org ledger exactly (1,345 / 634 / 854): 3,806 rows = 4,425 jobs.
- **Fix / do this:** Use this rule for any job-cap accounting.
- **KB:** L-IPU-042, L-IPU-043

### PD-P2-261 Rule-spec previews can't be attributed by name
- **Date:** 2026-10-04
- **Context:** guard attribution
- **Lesson:** All 29 rule-spec previews in the activity log are named PreviewMapping_RULE_SPECIFICATION, whichever app ran them.
- **Fix / do this:** Attribute previews by runtime environment, or log your own previews in your own call log.
- **KB:** L-IPU-055 (related); new

### PD-P2-262 Keep one run-log comment, updated in place, with one named writer per run
- **Date:** 2026-10-04
- **Context:** The guard's run-log comment (one fixed comment id)
- **Lesson:** Separate per-lane comments produced a wrong log. It left out glossary, connection and browse rows, counted 4 browses instead of 5, and called a stuck run "never run". Counting was also inconsistent: one v3 export was counted as a job and three others as 0, and no MCP caller appended its calls.
- **Fix / do this:** Keep one comment, updated in place, with UTC, asset, rows × cols, jobs counted, status and writer. Use one counting rule everywhere (exports and imports are not jobs), and have every MCP caller append to the guard's log.
- **KB:** new

### PD-P2-263 Independent read-only verifiers, then fix lanes with backups
- **Date:** 2026-10-04
- **Context:** verify-*/fix-*/recheck-guard lanes
- **Lesson:** The verifiers found real defects:
  - a salt leak;
  - a profile undercount for runs still in flight;
  - fail-open reads;
  - The wrong unbind route;
  - The timer wording;
  - a DDL target mismatch;
  - reads running with readonly 0;
  - overlap with host-app runs.

  Each fix kept a `.bak-fix-<UTC>` copy and an undo. When the gate agent died mid-write, the session wrote and ran the gate itself.
- **Fix / do this:** Verify every lane independently, fix with backups, then recheck with adversarial tests.
- **KB:** L-METHOD-047 (related); new

### PD-P2-264 Task-tracker traps for app cards
- **Date:** 2026-10-03
- **Context:** scrum skeleton and card creation
- **Lesson:** Traps found on the tracker:
  - The CLI's `new`/`next` drop the importance field, so the card sorts as 999; re-insert it with a helper.
  - A cross-project `blocked_by=<other card>` never clears; write "Waits on:" text instead.
  - `--xid next-v1` creates a second NEXT comment.
  - A card leased by another session gets one comment, with no `--force`.
  - The est-tracker parsed "1h05m" as 5 min.
  - Claude overestimates big tasks: median actual/estimate was 0.56 for 1-4 h tasks and 0.44 above 4 h.
- **Fix / do this:** Follow CHECKLIST.md before posting. Write actual=<minutes>m. Grep card bodies for secrets.
- **KB:** L-METHOD-122 (estimates); tracker traps new

### PD-P2-265 Record secret-hygiene evidence for every lane
- **Date:** 2026-10-04
- **Context:** tooling-db, cdi-probe and verifier scans
- **Lesson:** Passwords were generated with openssl rand, kept only in 0600 files on the host, and passed to psql on stdin. Bodies were redacted before saving. Verifier scans of auth.log, syslog, the journal, /tmp and lane logs found 0 hits. A hex check confirmed the laptop held no copy.
- **Fix / do this:** Scan logs and evidence after every lane, and record the scan in the evidence comment.
- **KB:** L-METHOD-001

### PD-P2-266 Don't record an untested form as a WALL
- **Date:** 2026-10-04
- **Context:** Cross-project form B: connection in the connection's own project with an `<other-project>.<ds>.*` include filter
- **Lesson:** The lane wrote "cross-project = NO in every form", but form B was never scanned: a PUT removed the filter before the only scan ran. The conclusion rested on the scanner's SQL shape alone. The verifier refuted it, and the KB lesson was disputed. It narrows the cross-project scan finding in PD-P2-060.
- **Fix / do this:** Mark a conclusion reached by reasoning only as "likely", never as a wall. Add a dispute note until a real test settles it.
- **KB:** L-CDGC-154 (dispute note)

### PD-P2-267 Read every lazy JS chunk before claiming "no route exists"
- **Date:** 2026-10-04
- **Context:** A refuted "no run-history route" wall claim
- **Lesson:** The lane searched only main.<hash>.js, which has 0 runDetail references. The run-history code is in the webpack lazy chunks (754/848/934/970/990.chunk.js). The bundle's i18n also has "Delete Profile Runs", so a purge route exists.
- **Fix / do this:** Before declaring a wall, load and grep every chunk and the i18n strings, and capture the UI's own XHR calls.
- **KB:** L-UI-002 (chunk aspect: new)

### PD-P2-268 Don't loosen alerts before the fix is proven
- **Date:** 2026-10-04
- **Context:** Data-observability staleness alerts raised from 4 h to 26 h and from 240 to 2400 min
- **Lesson:** The thresholds were raised before the trim was proven, and the trim didn't hold. One raise (1800 to 2400) had no proposal behind it. Phase 2 restored the old values.
- **Fix / do this:** Change alert thresholds only after the cadence change shows in the activity log. Restore them only when the live file differs from its backup in exactly the expected lines.
- **KB:** new

### PD-P2-269 Budget guard on an unknown cap: worst of 4 windows, fail closed
- **Date:** 2026-10-04
- **Context:** <prefix>_idmc_guard 1.1-1.3
- **Lesson:** Org usage is the MAX of: UTC month, Pacific month, since the 25th, rolling 30 days. At 01:27Z these were 2,899 / 2,811 / 6,774 / 6,774, which moved the pause from about 10-10 to about 10-05. The guard exits 3 when blocked, 4 when a read fails and 5 when login is blocked. Each version tightened it:
  - v1.1 fails closed on any read error, partial page, stale or errored cached status, or crash.
  - v1.2 also treats a 200 with an empty or HTML body, or an unknown list shape, as a read error, and a negative `--jobs` cannot relax the caps.
  - 40+ sandbox tests with injected failures passed.
- **Fix / do this:** Every runner calls `check --jobs N` first. Remove windows only once the vendor confirms the reset rule.
- **KB:** L-IPU-059, L-IPU-041, L-METHOD-025, L-METHOD-024, L-AUTH-006

### PD-P2-270 Cron-run state files: per-process tmp names and a stale margin
- **Date:** 2026-10-04
- **Context:** Guard 1.2 race found by the verifier
- **Lesson:** write_json used a fixed "<file>.tmp", and the status max age (30 min) equalled the cron period. A hand check in the ~40 s after the cron fired rebuilt the status alongside cron, and both wrote the same tmp file.
- **Fix / do this:** Use `"%s.tmp.%d" % (path, os.getpid())`, and set the max age above the period (35-40 min).
- **KB:** new

### PD-P2-271 A watcher inside the cron line can't catch a dead cron
- **Date:** 2026-10-04
- **Context:** <prefix>_idmc_guard_watch.py runs as the last step of the cron line
- **Lesson:** The watcher sends one ntfy push after 2 failing runs in a row, but it cannot see cron itself stop. The documented undo (restore the whole crontab) would also revert other lanes' later edits.
- **Fix / do this:** Check the age of the status file from another job or the gate. Undo by deleting only the tagged line ("# <prefix>_idmc_guard <card>").
- **KB:** new

### PD-P2-272 lslocks without sudo can't see root's lock
- **Date:** 2026-10-04
- **Context:** Heavy-lock gate on the production DB host
- **Lesson:** A normal user's lslocks does not show root's <app>_heavy.lock, so a non-root gate reports the lock as free when it isn't.
- **Fix / do this:** Use `sudo lslocks` in every gate.
- **KB:** new

### PD-P2-273 Claims must name the real paths of every write
- **Date:** 2026-10-04
- **Context:** Several lanes on the shared claim ledger
- **Lesson:** Writes were claimed under aliases (users.d#<app>-networks) or not at all: a fallback dataset, tooling-VM scratch, KB files, home-folder tee files, and Windows session files. Because of that, the path-overlap check could not catch collisions, and the estate watcher flagged unclaimed changes.
- **Fix / do this:** Update the claim's paths= before each new write, and cd into the evidence folder before any tee.
- **KB:** new

### PD-P2-274 Quote the approval's own text, and stay inside lane limits
- **Date:** 2026-10-04
- **Context:** bq-sample and oss-surfaces lanes
- **Lesson:** The lanes overstepped their approvals:
  - bq-sample ran 2 scans where 1 was allowed, took 113 min of a 75 min box, and built a fallback dataset it had only been told to record.
  - It also stated a "synthetic only" limit the approval did not contain.
  - The oss lane made OpenMetadata grants that its item did not cover.
- **Fix / do this:** Quote the approval verbatim in the evidence. Record a fallback as NEXT unless it is approved, and report overruns.
- **KB:** new

### PD-P2-275 A synthetic dry run must pass before the real write
- **Date:** 2026-10-04
- **Context:** post_export.sh stage load
- **Lesson:** The synthetic stage test failed (psql rc 75, lock held), yet the real run still targeted the stage. Only the load gate deferred it.
- **Fix / do this:** Make the real run depend on a passing synthetic run against the same target, and test inside a rolled-back transaction.
- **KB:** new

### PD-P2-276 Writing to the shared KB from several sessions: lock, allocate ids at write time, back up, gate
- **Date:** 2026-10-04
- **Context:** add_lessons_1003.py, kb_add_lesson.py, kb_write_p2.py
- **Lesson:** Two lanes added lessons on the same day without recounting the headers. The header counts had already drifted by one, and "**Disputed:**" flags were missed. A safe write:
  1. Take the `.lesson_lock` directory lock (mkdir, retry every 30 s).
  2. Allocate the id as max over md headings and lessons.jsonl, +1, with a duplicate-id assert.
  3. Back up the files you will touch.
  4. Increment the headers and README counts.
  5. Run kb_gate until it reports CLEAN, and check citations.

  Lessons are written generically, with no app names.
- **Fix / do this:** Always go through the locked writer. Dispute lessons rather than delete them.
- **KB:** new

### PD-P2-277 Audit an inherited generated build, then collapse it to a few parameterized mappings
- **Date:** 2026-11-01
- **Context:** The new project. The earlier generated build had 357 mappings, 354 tasks and 149 workflows.
- **Lesson:** Exporting and parsing all 357 mappings turned up only 8 topologies, 52 pattern clusters and 76 logic variants. Most were thin Source>RuleSpec>Expression>Target wrappers. The real logic lived in 16.06M characters of task `$Source$.customQuery` (median 18,799, max 678,789). Run history showed 62/62 full-estate workflows failed and 12/13 bootstrap workflows failed.
- **Fix / do this:** Export everything with v3 export, cluster by mapping shape, and read the full run history. Then redesign as about 7-8 parameterized mappings and 3-4 linear taskflows, with the source lists kept as data in a manifest.
- **KB:** L-MIG-094, L-CDI-293, L-CDI-114, L-CDI-120

### PD-P2-278 A pilot that "became full" may never have run full
- **Date:** 2026-11-01
- **Context:** Coverage audit of bronze loads
- **Lesson:** 22 legacy tables held 64 rows or fewer. Each ran once as a 64-row pilot. Its SQL was later rewritten to read the full table, but the full version showed as NOTRUN inside the bootstrap workflows. Apart from deliberate shards, every partial load was a run that died part-way.
- **Fix / do this:** Judge coverage from each task's run history and the target's distinct key counts, not from its current SQL. Count NOTRUN sub-entries inside workflows.
- **KB:** L-MIG-094 (partial); new detail

### PD-P2-279 If the generator's source is gone, reuse its outputs and take a full backup before rework
- **Date:** 2026-11-01
- **Context:** design_sources audit of the code generator
- **Lesson:** The generator code was nowhere: not on the laptop, the 5 VMs, or any of 45 GitLab repos. What could be reused was the IMF JSON from v3 export, the task SQL, and a full project export (`includeDependencies`) taken before any rework.
- **Fix / do this:** Don't hunt for a missing generator. Keep the full project zip as the rollback point and rebuild with your own generator.
- **KB:** L-MIG-003 (export mechanics); new

### PD-P2-280 Several sessions on one IDMC project need a written ownership split; the IDMC log can't tell them apart
- **Date:** 2026-11-01
- **Context:** COORDINATION.md: three laptop sessions with overlapping directives
- **Lesson:** One session stopped 12 jobs while another created and started an MDM mapping. New folders 01..08 were created next to old 01..04 folders whose numeric prefixes meant different things. IDMC recorded every action under the same user, so the activity log could not attribute anything.
- **Fix / do this:** Write an owner table per folder and asset-name prefix. Never OVERWRITE-import into another session's folder. Keep your own write log.
- **KB:** L-METHOD-135, L-METHOD-061, L-METHOD-072

### PD-P2-281 Write helpers: dry-run by default, log every write with its response
- **Date:** 2026-11-01
- **Context:** <prefix>ops.py / ops_log.jsonl
- **Lesson:** Every IDMC write helper only printed what it would do unless `execute=True` was passed. Each write appended what, when, a request summary and the response to `ops_log.jsonl`. Schedule changes logged the full GET body first, so they could be restored exactly.
- **Fix / do this:** Use this pattern in every headless write tool.
- **KB:** L-METHOD-013, L-METHOD-022

### PD-P2-282 Prove IDMC wrote the data: check the target's query_log for user and client
- **Date:** 2026-11-01
- **Context:** The "all loading through IDMC" rule on the new ClickHouse
- **Lesson:** Real IDMC writes showed user `<app>_idmc` and client ClickHouse-JdbcDriver 0.6.5. The same log exposed loads that bypassed IDMC:
  - all 319,844 <model_registry> rows were loaded by `default` via `INSERT ... SELECT FROM remote()`;
  - 151,640 async inserts were written under a temporary settings profile;
  - 60 direct dictionary inserts hit a CHECK, after which `default` changed the constraint.
- **Fix / do this:** Group target inserts by user, client and query_kind before crediting IDMC. Rebuild non-IDMC loads as mappings, and drop the logins they used.
- **KB:** L-METHOD-043, L-ENV-116

### PD-P2-283 Reconcile a migration inside IDMC, with a "source changed" status
- **Date:** 2026-11-01
- **Context:** m_<prefix>_reconcile in 07 Reconciliation. 116 datasets: 108 reconciled, 5 mismatch_source_changed, 3 mismatch.
- **Lesson:**
  - **Legacy side:** measured read-only per item: rows, units, `sum(cityHash64(x))` mod 2^64, last modification. Run at 2 threads with a 3 GB cap, and staged as a file.
  - **Target side:** SQL from `$$TGT_SQL`. A unit counts only when all its chunks are present (`groupBitmap(chunk)`).
  - **Join and history:** a master-outer joiner keeps every dataset. The run_manifest record_version is the run id.
  - **Status:** `mismatch_source_changed` means the table was written after its capture started.
- **Fix / do this:** Reconcile in batches, read back the statuses, and close source_changed items with a delta pass after the writer freeze.
- **KB:** L-MIG-086

### PD-P2-284 The activity log is a sample: about 1,000 entries and 10 logs per task
- **Date:** 2026-11-01
- **Context:** Counting runs for 354 tasks that started more than 500 jobs a day
- **Lesson:** The log held 1,076 entries (org `maxLogRows` 1000), oldest 10-08, with no working pagination. Each task keeps `maxLogs=10`. Large loads showed only as workflow sub-entries.
- **Fix / do this:** Keep your own run ledger (runner or run_manifest). Treat activity-log counts as lower bounds. Use the target's query_log as the record of what was written.
- **KB:** L-CDI-288, L-CDI-061

### PD-P2-285 Inventory every reader and writer before a sunset; logs alone miss some
- **Date:** 2026-11-01
- **Context:** understand/consumers: 15 active logins and 30 consumer rows on the old ClickHouse
- **Lesson:** Clients were grouped from 7 days of `system.query_log` by login, IP and user-agent, with log_comment naming the jobs. Every host's cron.d, crontabs, systemd timers, Airflow DAGs and container env names (values redacted) were then read. Monthly and yearly jobs show up only in cron and DAG files. The biggest writer was a copy churn of 1.68B rows in 7 days. A "read-only" login held INSERT, ALTER and DROP.
- **Fix / do this:** Combine query_log with host config scans, and read the grants, not just the login names.
- **KB:** L-MIG-041, L-ENV-116

### PD-P2-286 Sunset order for an old database
- **Date:** 2026-11-01
- **Context:** SUNSET_READINESS.md, generated read-only from runner and reconcile state
- **Lesson:**
  1. Let capture and reconcile finish.
  2. Freeze the writers that bypass IDMC, but only once their IDMC replacements exist.
  3. Run a delta pass and a final reconcile, until every dataset is reconciled.
  4. Build the serving layer (read-only logins and views).
  5. Repoint readers.
  6. Take an off-VM backup and a snapshot, stop the database, and keep its disk for 30 days.
  7. Pause the migration schedules and drop the reader logins.
- **Fix / do this:** Generate the readiness report from live state. Get the owner's GO for the writer freeze and the repoint.
- **KB:** L-MIG-091, L-MIG-041

### PD-P2-287 "Everything is in the new tables" needs a scope wider than one engine
- **Date:** 2026-11-01
- **Context:** Completeness critic of the 3-table goal
- **Lesson:** The auditors inventoried only ClickHouse and missed:
  - a 27 GB live Postgres DB, 12 Mongo ML collections and Neo4j;
  - files on disk, GCS archives, and 155 of 251 model files (the r24 production fallback existed on one host only);
  - ClickHouse dictionaries backed by Postgres, which hold 0 rows in ClickHouse.
- **Fix / do this:** Have the owner include or exclude each store explicitly. Inventory model files by md5, and fix a freeze or watermark time.
- **KB:** L-MIG-091

### PD-P2-288 Ask for a scale-up with numbers, impact, the exact command and the undo
- **Date:** 2026-11-01
- **Context:** Capture was CPU-bound on an n2d-standard-32
- **Lesson:** CPU went to ClickHouse inserts (about 9 cores), merges (about 10) and 14 IDMC jobs (about 8). The capture was 3% done after 2 h, which meant 25-35 h more. The optional ask was a 64-vCPU resize for about a day (about $25-35, roughly 1.7x faster). It stated that the VM stop/start would interrupt 14 jobs (retried by the runner) plus a peer session's jobs, and included the gcloud commands and the undo.
- **Fix / do this:** Make spend asks optional, measured and reversible. Name the interruption to peers, and wait for both approvals.
- **KB:** L-ENV-069, L-ENV-124

### PD-P2-289 Archive a superseded build instead of deleting it: loaded rows reference its ids
- **Date:** 2026-11-01
- **Context:** The superseded generated build moved to an Archive folder named "<project> generated build 2026-10-31 (superseded)"
- **Lesson:** Rows in the target carry the old objects' idmc_mapping_id and idmc_task_id, so deleting those objects would orphan the lineage. FRS MoveEntities (`/frs/api/v1/MoveEntities`, at most 25 per call, IDS-SESSION-ID and icSessionId) keeps ids, schedules and history. The emptied folders were then deleted (204).
- **Fix / do this:** Move superseded objects to an Archive project, in a dated and described folder. Delete a folder only once it is empty.
- **KB:** L-CDI-016, L-CLEAN-035

### PD-P2-290 A pgrep-based gate check matched its own ssh command and refused every state
- **Date:** 2026-10-25
- **Context:** gl-zos v1 gate check
- **Lesson:** `pgrep -f national40.sh` matched the checker's own ssh command line, so every state looked busy. A `tail` of the gate log must not count as "gate running". An unreachable apps host should count as busy.
- **Fix / do this:** Match the exact runner invocation (`bash … nationalNN.sh`), the systemd units and the STOP files.
- **KB:** new

### PD-P2-291 One rule text everywhere, a scorer stamped with its own hash, and an A-A drift check
- **Date:** 2026-10-25
- **Context:** gcl_sql.py / scorer_v2
- **Lesson:** Plan, apply and scorer all render from one rule module, and a test fails if the committed scorer differs from the rendered one. Every scorer output starts with the scorer_id and the sha256 of its SQL and Python. The scorer reads one partition per query, with FINAL, readonly 2, 2 GB and 2 threads. Baseline on 10-29: 100.98M rows; candidates `la_range` 23,778, `lot_tiny` 180,384, `av_zero` 10,727, `sale_placeholder` 229,334.
- **Fix / do this:** Run the identical files for BEFORE, the A-A drift check and AFTER.
- **KB:** new (related L-DQ-137)

### PD-P2-292 Test cleanup SQL on a throwaway ClickHouse at the exact production version, plus a scripted fake
- **Date:** 2026-10-25
- **Context:** cleanup tests
- **Lesson:** Production-only failures (hung nested mutations, Block structure mismatch, tied versions) reproduced only on the same server version. Failure branches that are rare on demand (a failed REPLACE, a moved partition, the kill switch, a receipt failure) need a scripted fake client.
- **Fix / do this:**
  - Run `docker run --memory 4g clickhouse/clickhouse-server:<exact production tag> (here vv25.3.14.14)` with the production DDLs.
  - Use `fake_ch.py` for the bash control flow.
  - Evaluate the predicates in SQLite.
  - Rehearse the undo on scratch tables.
- **KB:** new

### PD-P2-293 Score the value the customer is served, paired, as full distributions
- **Date:** 2026-10-24
- **Context:** The platform's ML LESSONS §1
- **Lesson:**
  - Score the served value as of the window start, not an internal blend.
  - Compare candidate and comparator on the same homes, and publish selected, qualified, scored and unscored counts. Requiring every version to score a home drops the hard homes.
  - Report uncapped MAPE, p90, p95, max and signed error, by state × class and price band. A better median hid worse tails twice.
- **Fix / do this:** Every claim names its model, cohort, window, timing, label type, denominators and scope.
- **KB:** new

### PD-P2-294 Pre-register gates and amend them before reading any row
- **Date:** 2026-10-24
- **Context:** PREREG-gate201 / gate202
- **Lesson:** The rules were fixed and timestamped before any row existed: McNemar z > -1.96, a paired bootstrap of 2,000 draws with seed 202, and per-class and per-state (n ≥ 100) checks. Every amendment carries a timestamp and states that no row had been read. Homes already seen while designing the fix were excluded. Rule 6b's 98% bar had the wrong denominator, so the verdict reports both the literal fail (95.0%) and the corrected pass (285/285 reachable).
- **Fix / do this:** Change one thing per arm. Holm-adjust subgroup tests. Treat a spent test set as training data.
- **KB:** new

### PD-P2-295 A data change is a model change: exclude states whose Gold moved inside a gate window
- **Date:** 2026-10-24
- **Context:** A county-as-city fix (375,747 TX rows) and a ZIP fill, both on Gold
- **Lesson:** Filling 4.39M ZIPs moved live NC/VA values with no gate. A Gold rewrite during a gate changes the inputs of one arm but not the other.
- **Fix / do this:** Find each state's swaps in `system.query_log` (REPLACE PARTITION on gold inside its gate window) and exclude those states whole. Run Gold repairs between ML gates and tell the ML owner. Version geography and feature snapshots together with the models.
- **KB:** new

### PD-P2-296 Certification is tied to a code hash; gate runs that wrote none left 98% of valuations low-confidence
- **Date:** 2026-10-24
- **Context:** serving_policy, `backtest_run_summary`
- **Lesson:** A state × class is certified only by a summary row whose `code_hash` equals the serving code (n ≥ 30 SF / 100 condo and 2-4 unit, over-30 ≤ 10%, within 7 days). Gate runs wrote `code_hash ''`, and the cron covered MA only. 2,153 of 2,198 live valuations in 7 days were served low-confidence.
- **Fix / do this:** Make every gate runner write `over30` per class and the real `code_hash`.
- **KB:** new

### PD-P2-297 Knobs must take effect, and exit codes must be read honestly
- **Date:** 2026-10-24
- **Context:** ML LESSONS (ML-L14/28/38/104)
- **Lesson:** For two weeks every "per-state" backtest ran Massachusetts, because the BT_* knobs were not honoured. Three more traps hid failures:
  - reading `rc` from a log line that contained `$(date)`;
  - a pytest exit code masked by `| tail`;
  - assert-only checks, which vanish under `python -O`.
- **Fix / do this:** Print and store the effective knobs, and fail if one is ignored. Capture `rc=$?` on its own line. Make every check raise.
- **KB:** L-ENV-036, L-METHOD-047 (knobs: new)

### PD-P2-298 A release is exact source plus an immutable image plus hashes, built from the live tag
- **Date:** 2026-10-25
- **Context:** RELEASES.md, ML README
- **Lesson:** Live code drifted into VM overlays, and the r24 image's source was never captured. A missing tag is not a deleted image. Retained artifacts with unknown training membership cannot enter a property-disjoint evaluation.
- **Fix / do this:** Build FROM the live image tag, overlay only the changed files, test inside the image, and refuse if the live image moved. Keep the rollback tag. Never retag mutable images or patch a VM copy without Git. Record training membership and cutoff with every artifact.
- **KB:** new (related L-ENV-108)

### PD-P2-299 Evidence integrity: hash and parse one buffer, and test against the real consumer
- **Date:** 2026-10-24
- **Context:** graph_replay postflight / integrity lifecycle
- **Lesson:** Review reproduced a race between hashing a file and reading it again. An adapter's extra status key passed synthetic tests, but the real host rejects any extra field. Two mtime_ns values can fall in the same kernel tick, so matching mtimes don't prove matching bytes. Missing captures must never trigger a second inference run. A stale `.pyc` can run instead of the hashed source.
- **Fix / do this:** Hash and parse one buffer. Test against the real consuming probe. Do full SHA-256 checks at boundaries. Compile from the verified bytes.
- **KB:** new

### PD-P2-300 Diagnostics are read-only, and optional context never breaks a report
- **Date:** 2026-10-25
- **Context:** ML LESSONS §6
- **Lesson:** Probes, coverage and speed agents:
  - never write observations, reports, jobs or tables;
  - never touch production containers;
  - use a private model cache, with cache keys that carry the market.

  Candidate builds train into test storage. One state's failure never stops the others. When a context source fails, the report shows the dated last-known value instead of inventing "now".
- **Fix / do this:** Run checks with `store_results=False`. Label old checkpoints as historical, and keep one current-status entry point.
- **KB:** new
