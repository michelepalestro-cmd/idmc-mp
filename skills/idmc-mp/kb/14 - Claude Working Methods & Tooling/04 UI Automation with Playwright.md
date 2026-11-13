# UI Automation with Playwright

**Answers:** When is an IDMC step truly UI-only, and how is it automated safely when it is? How do I log in, keep the
session, capture the UI's own API call, settle a chat harness, and keep evidence from a browser run?

**Read when:** a step seems to need the IDMC console; building or debugging a Playwright harness (including a CLAIRE
GPT harness); a page renders blank under automation; an end-to-end story must be proven through an application's UI.

**Key rules:**
- Walk the ladder: REST, a managed MCP tool, a package clone, the UI's own XHR, and only then Playwright (L-UI-001,
  L-UI-002).
- Run Playwright from a server. Behind a transparent enterprise proxy, first try headless Chromium with the Private and
  Local Network Access checks off, and fall back to a host outside the proxy (L-UI-031; L-UI-011 is disputed; L-UI-013).
- Log in once, reuse the storage state inside its window of about 30 minutes, and stop at the first rejected login
  (L-UI-004, L-UI-005).
- Storage states, profiles and XHR captures are credentials: redact login bodies inside the capture hook itself and
  keep the files 0600 (L-UI-006, L-UI-002).
- Every committing click gets a verbatim receipt plus a REST read-back, and end-to-end stories run through every
  channel's real UI (L-UI-010, L-UI-020).
- A chat harness settles only on reply markers: letter-spaced spinner text and the U+2026 ellipsis mean busy, and a
  publish prompt means stop (L-UI-028, L-UI-030).

**Related:** [01 How Claude Reaches and Drives IDMC](<01 How Claude Reaches and Drives IDMC.md>) · [02 Evidence Discipline](<02 Evidence Discipline.md>) · [06 Secrets Hygiene](<06 Secrets Hygiene.md>) · [CLAIRE GPT - Prompting Rules & Patterns](<../09 - CLAIRE & MCP/03 CLAIRE GPT - Prompting Rules & Patterns.md>) · [Lessons: UI Automation](<../13 - Lessons Learned/14 UI Automation.md>)

**Last verified:** 2026-11-03

> **Summary.** Browser automation of the IDMC console is the last resort, used only after REST, managed MCP tools,
> clone-through-package and a capture of the UI's own API call have failed. When it is needed: run Playwright from a
> server (behind a transparent proxy, with the network-access checks off, section 6), reuse one login's storage state
> inside its window, treat state files and captures as credentials, work around
> the SPA quirks, and keep evidence (a screenshot plus page text per step, and a verbatim receipt paired with a REST
> read-back for every committing click).

---

## 1. When is headless truly walled?

Work down this list and stop at the first rung that works (L-UI-001):

1. **REST** on the right host with the right plane header, through the probe toolkit (bogus twin, empty POST,
   Content-Type variants, host sweep). See [02 Evidence Discipline](<02 Evidence Discipline.md>).
2. **A managed MCP tool** from the org's real registry.
3. **A clone through a v3 export/import package** (edit the package, re-hash, import).
4. **Capture the UI's own XHR** for that click and replay it headless (section 8) (L-UI-002).
5. **Drive the UI with Playwright** from a server (behind a proxy, with the section 6 flag set), or hand one precise
   click to a human with a receipt.

Steps that looked UI-only and moved to headless (details in the domain folders): runtime-environment service and
connector selection, MCP OAuth clients, CAI publish and unpublish, ingestion task create/deploy/start, glossary term
writes and catalog-source create, profile create and run, deletes of design objects, new multi-transformation mappings
built as IMF JSON packages, full SQL ELT pushdown on a mapping task (v2 `sessionProperties`, L-CDI-202), lineage
connection assignment (L-CDGC-159), catalog Data Quality rule occurrences (the form's write request, captured once and
replayed over REST: L-CDGC-161, L-UI-032) and intelligent structure models (L-CDI-223).

Still a click in the sources behind this KB:

| Operation | Why it stays UI |
|---|---|
| MDM business-entity model publish / deploy | no route across many host and path shapes |
| MDM match-and-merge job creation | job paths absent; created in the MDM console |
| CLAIRE classification accept | the UI itself offers only Dismiss; many accept paths 404 |
| Steward / owner assignment | no write route found |
| CAI API activate / deactivate | no verb at any path; republishing does not activate |
| CDQ rule logic and console scorecards | rule-builder canvas |
| CDQ dictionary "Convert to API" | one human click before the dictionary API works |
| Catalog-source definition delete | REST delete only purges the metadata |
| MCP tool-connection objects | package import fails; recreate in the designer |
| Publishing API-created advanced taskflows | publish fails for API-created or copied taskflows; use linear taskflows or controller-staged runs |
| Unknown property names (for example a task session property whose key nobody has recorded) | capture once from the UI, then set over REST |

## 2. Where to run it

- **On a server, in the official container.** `mcr.microsoft.com/playwright/python:<ver>-jammy` with
  `pip install playwright==<same ver>`, `-e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`, `--network host`, Chromium with
  `--no-sandbox`, and a mounted output folder; the Node image runs JS suites on hosts without Node
  (L-UI-013).
- **Behind a transparent enterprise proxy, the flag set first.** From a proxied laptop every heavy IDMC app once painted
  a blank page under automation (L-UI-011). On 2026-10-06 headless Chromium with the Private and Local Network Access
  checks off drove Metadata Command Center, the catalog and the mapping designer from such a laptop (L-UI-031). Try that
  flag set (section 6) before moving the work to a host outside the proxy.
- **Container networking.** Map vhost names with `--add-host` so the browser can resolve them; use `--network host`
  when the app derives its API host from the page origin (L-UI-013).
- **Egress.** A single admin UI session downloads megabytes of SaaS JavaScript; on an egress budget keep UI sessions
  rare and log them (L-METHOD-092).
- **Serially.** One authoring session at a time; parallel sessions collided on shared state files and scratch targets
  (L-UI-009), (L-METHOD-080).

## 3. Login and sessions

- **Recipe.** `https://<domain>.informaticacloud.com/identity-service/home`; wait for `input#username` (or
  `input[name=username]`); fill from env vars; submit with `button:has-text("Log In"):not(:has-text("Single"))` (skips
  the SSO button) or Enter. Some pages are two-step (username, Log In, then password, Log In). The browser lands on
  `https://<pod>.<domain>.informaticacloud.com/cloudshell/showProducts`, and SSO carries to every service host.
  Scripted login works only for a user without MFA (L-UI-003).
- **One rejection stops everything.** If the page is still on the identity service and its text matches
  `locked|not valid|invalid`, exit "LOGIN REJECTED - not retrying"; UI logins count toward the same lockout as REST
  logins (L-UI-004), (L-METHOD-070).
- **Probes never log in.** A probe that only measures rendering reuses a warm state read-only, aborts if bounced to the
  login page, and does not write the state back (L-UI-004).
- **Reuse the state inside its window.** Save `storage_state` after one login and reuse it; the console session lives
  about 30 minutes (JWT iat to exp about 1800 s), and a stale state makes deep links redirect and grids render empty.
  Refresh with one explicit login run before each batch (L-UI-005).

## 4. Storage states and profiles are credentials

A storage state holds the console's cookies, including session JWTs (one held 46 cookies), and a persistent browser
profile cache can hold live session cookies. Keep them 0600, outside repositories, shared folders and the script's own
directory; sequester or delete stale ones; never paste their contents (L-UI-006). Captured network traces
carry `Cookie:` and `Authorization:` headers: keep only method, URL, body shape and status (L-METHOD-088).

## 5. SPA quirks

| Symptom | Cause | Fix | Lesson |
|---|---|---|---|
| a deep link (`/explore/<id>`) renders an empty grid | cold SPA state | navigate: Explore, All Projects, click | (L-UI-007) |
| `goto` times out on a page that works | the page never fires `load` | `wait_until="commit"` or `"domcontentloaded"`, then `wait_for_url` and an element wait | (L-UI-007) |
| clicks do nothing | the service-switcher modal intercepts them | close it (`button[aria-label=Close]` or Escape) | (L-UI-007) |
| a selector is not found | the app lives in a frame | search `page.frames`; pick by URL (the CAI shell frame contains `bpmui-cai-app`) | (L-UI-007) |
| a row action is missing | kebab menus appear only on hover; rows are `role=row` | hover the row, then click | (L-UI-007) |
| a dropdown option is not clickable | react-select options are `[class*='-option']`; `role=option` belongs to a background grid; Escape closes the modal | target the react-select class | (L-UI-007) |
| a nested designer renders blank headless | nested SPA bootstrap with a saved state | fresh login, headed browser under `xvfb-run` | (L-UI-007) |
| an expression edit is lost | Escape before commit discards it | `cm.setValue` then `cm.save`, then the enabled OK | (L-UI-008) |
| typing a long query times out | `press_sequentially` default 60 s | `delay=1, timeout=300000`; poll for OK | (L-UI-008) |
| the field-derive spinner never ends and Save is a no-op | a very large custom query on a new mapping | find the auto-persisted `MappingN` over v3 REST and open it by GUID | (L-UI-008) |
| new upstream ports do not reach a create-at-runtime target | the target keeps its derived fields | rename the target to force re-derivation | (L-UI-008) |
| objects show "unsaved changes" after API updates | UI state lags the API | open and save them before a demo | (L-UI-014) |
| a chat harness exits early | busy text matched without its trailing dots | match "Analyzing concepts..." exactly | (L-UI-015) |
| a CLAIRE data prompt is cut before its table arrives (a false FAIL) | the status line ("Checking available connections…") ends in U+2026, one ellipsis character, not three dots | add U+2026 to the busy patterns; re-check earlier "no table" failures for this cause | (L-UI-028) |
| a chat prompt is never sent | `@` opens the mention picker | avoid `@` | (L-UI-015) |
| an exact-text check fails on a correct page | CSS `text-transform` (for example upper-cased headings): `inner_text` returns the rendered text | compare case- and whitespace-insensitively; look at the screenshot before calling it a defect | (L-METHOD-118) |
| free-text arguments arrive split | shell wrappers split on spaces | pass inputs through a JSON file | (L-UI-014) |
| a multi-step catalog picker jumps back to step 1 | the stepper tabs are buttons too: `get_by_role('button', name='Select')` matches the tab 'Select System or Catalog Source' | pass `exact=True`; the last step's button is 'Finish', a parameter-mapping step ends with 'OK'; search inside a picker by clicking its box and typing, then click the row by exact text | (L-UI-032) |
| a radio-button click times out ('input intercepts pointer events') | the input is drawn over its label (for example 'Pick an existing rule') | `check(force=True)` on `input[type=radio][value=...]` | (L-UI-032) |
| the intelligent structure model editor spins forever | in headless Chromium the spinner never clears, for models made in the UI and over REST alike | wait on the 200 response of the service's `openStructureData` request, not on the spinner | (L-UI-033) |

## 6. The proxy / CGNAT blank-page failure

**Symptom.** Login and the launchpad render, but every heavy IDMC micro-frontend (Data Profiling, Administrator)
paints nothing: the title and the JavaScript bundle load, and the DOM body holds 2 nodes and 0 text. The screenshots
are white (L-UI-011).

**Cause.** A transparent enterprise TLS proxy with CGNAT addressing breaks the SPA bootstrap requests for a fresh
automation profile: a worker script 404, a CORS block on the `hdm` host, a DNS failure on another service host, a 503
from a UI service. The user's own browser on the same machine renders fine because it gets the proxy's enterprise
treatment; the automation profile does not.

**Tried and failed (2026-09-20).** Headless, headful, `--disable-web-security`, a real Edge channel on a warm session.
Chromium flags that disable Private/Local Network Access checks (useful when the proxy resolves vendor hosts to 100.64/10
addresses) had helped for a while but were not sufficient (L-UI-027, superseded). Proving it cost about
130-160 MB of egress.

**Disputed (2026-10-06): the flag set that worked (L-UI-031).** From a laptop behind the same kind of proxy, Playwright's
bundled Chromium, headless, with the Local Network Access checks also disabled, plus a saved storage state and at most
one scripted login, rendered and finished work in Metadata Command Center (catalog source pages, lineage
configuration), Data Governance and Catalog (asset pages, the lineage tab, new-asset forms with multi-step pickers) and
the Data Integration mapping designer. Without the flags the console looped on authentication and stayed blank.

```
--no-sandbox
--disable-features=BlockInsecurePrivateNetworkRequests,PrivateNetworkAccessSendPreflights,PrivateNetworkAccessRespectPreflightResults,LocalNetworkAccessChecks,LocalNetworkAccessChecksWarn
```

In the skeleton (section 9) these go into `p.chromium.launch(args=[...])`. Data Profiling and Administrator, the
consoles that went blank in L-UI-011, were not retested, so that verdict is disputed rather than overturned.

**Remedy.** Behind such a proxy, try the flag set above first. If a console still paints nothing, run the automation
from a host outside the proxy (a cloud VM), or hand the click to the user's own browser with a click path and a
receipt.

**Detect it mechanically** instead of trusting screenshots: count DOM elements, text length, buttons and inputs in each
frame; byte-identical screenshot sizes across different pages mean you are photographing a login page
(L-UI-012).

## 7. Evidence from the UI

- **One screenshot plus page text per step.** `page.screenshot(full_page=True)` and `page.inner_text("body")`,
  written next to each other, per acceptance criterion (L-UI-014).
- **Receipts for committing clicks.** Record the confirmation text verbatim, the UI path, the REST call it substitutes
  for and a REST read that verifies the change (L-UI-010). Example receipt for agent services: "Changes
  successful. The selected components are enabled for the runtime environment, and all unselected components are
  disabled for the runtime environment.", verified with `GET /api/v2/agent/details/<agentId>`.
- **Capture failure strings too**: failure toasts and silent no-ops look alike in a screenshot.
- **A toast is not completion.** Engines stayed DEPLOYING for 20-45 minutes or more after a service toast; re-read
  before calling the action failed.
- **Never invent a receipt**; a wall with no receipt means nobody has captured it yet.
- **Verify dashboards in a real browser** as well as through their API, and log in through the form; HTTP Basic
  credentials passed to the browser did not log in (L-UI-020).
- **Drive end-to-end stories through every channel's real UI.** A pipeline check that drove the application's APIs
  passed while one channel had no screen for the step at all (and another only redirected), so records that should have
  fed IDMC were never created from that channel. Run each story through each channel's real browser UI (web, mobile
  web, self-service terminals, staff consoles) before trusting downstream counts (L-UI-020).
- **Keep slow verification reads out of timed flows.** Warehouse or database checks of 20-80 s inside a UI flow make
  screens with idle resets (45 s, 3 min) time out the next click; verify at the end of the story (L-UI-020).

## 8. Turn a UI step into REST (capture the XHR)

(L-UI-002)

1. Log in once headless; open the page that holds the control.
2. Record every XHR and fetch to `*.informaticacloud.com`: method, status, URL, request body, the head of the
   response. Drop noise (telemetry, translations, locale files, icons, notification polls). Redact inside the capture
   hook itself, not afterwards: the identity-service login request is captured too, and its body carries the username
   and password in clear. Keep capture logs out of shared folders and transcripts, and rotate the password if an
   unredacted log was shared (L-UI-002).
3. Click the control once.
4. Find the request that changed state; replay it with the session module's headers
   ([01 How Claude Reaches and Drives IDMC](<01 How Claude Reaches and Drives IDMC.md>)); read the object back.
5. Record the route as WORKS with its date, and retire the UI step.

This is how the MCP OAuth-client route and the runtime-environment selections route were found.

## 9. Skeleton flow

```python
"""ui_walk.py - skeleton IDMC UI walk: one login, XHR capture, a screenshot and page text per step.
Run on a server; behind a transparent proxy add the section 6 flags to the launch args:
    python ui_walk.py <tag> <url> [<url>...]
Credentials come from the environment (IDMC_USER, IDMC_PASS) and are never printed."""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright

OUT = os.environ.get("UI_OUT", "/work/out")        # mounted output folder
STATE = f"{OUT}/state.json"                         # a credential: 0600, never committed
LOGIN = "https://<domain>.informaticacloud.com/identity-service/home"
SUBMIT = 'button:has-text("Log In"):not(:has-text("Single"))'
NOISE = ("pendo", "translation", "locale", ".svg", "/i18n/", "bellNotification")
tag, urls = sys.argv[1], sys.argv[2:]
os.makedirs(OUT, exist_ok=True)
xhr = []

def on_response(r):
    try:
        if r.request.resource_type not in ("xhr", "fetch") or "informaticacloud.com" not in r.url:
            return
        if any(n in r.url for n in NOISE):
            return
        body = r.request.post_data or ""
        if "identity-service" in r.url or re.search(r"(?i)password|secret|token", body):
            body = "<redacted>"                          # redact at capture time: login bodies carry the password
        xhr.append({"m": r.request.method, "s": r.status, "u": r.url, "req": body[:3000]})
    except Exception:
        pass

def login(page, ctx):
    page.goto(LOGIN, wait_until="domcontentloaded")
    page.wait_for_selector("input#username, input[name=username]", timeout=90000)
    page.fill("input#username, input[name=username]", os.environ["IDMC_USER"])
    if not page.is_visible("input#password, input[name=password]"):     # two-step login page
        page.click(SUBMIT)
        page.wait_for_selector("input#password, input[name=password]", timeout=60000)
    page.fill("input#password, input[name=password]", os.environ["IDMC_PASS"])
    page.click(SUBMIT)
    page.wait_for_load_state("networkidle", timeout=120000)
    text = page.inner_text("body")[:2000]
    if "identity-service" in page.url and re.search(r"(?i)locked|not valid|invalid", text):
        raise SystemExit("LOGIN REJECTED - not retrying")                # counts toward the lockout
    ctx.storage_state(path=STATE)
    os.chmod(STATE, 0o600)

def painted(page):
    return page.evaluate(" => ({nodes: document.body ? document.body.getElementsByTagName('*').length : 0,"
                         " text: document.body ? document.body.innerText.trim.length : 0})")

with sync_playwright as p:
    browser = p.chromium.launch(args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1680, "height": 1050},
                              storage_state=STATE if os.path.exists(STATE) else None)
    ctx.on("response", on_response)
    page = ctx.new_page
    page.set_default_timeout(60000)
    if not os.path.exists(STATE):
        login(page, ctx)
    for i, url in enumerate(urls):
        page.goto(url, wait_until="commit")
        page.wait_for_load_state("domcontentloaded")
        time.sleep(10)                                   # SPAs keep loading after the first paint
        if "identity-service" in page.url:
            raise SystemExit("bounced to login: refresh the state with one explicit login run")
        stats = painted(page)
        page.screenshot(path=f"{OUT}/{tag}_{i}.png", full_page=True)
        with open(f"{OUT}/{tag}_{i}.txt", "w", encoding="utf-8") as f:
            f.write(re.sub(r"\s+", " ", page.inner_text("body")))
        print(i, page.url[:100], stats, flush=True)
        if stats["nodes"] < 10 or stats["text"] == 0:
            print("BLANK PAGE: check the network path before trusting anything", flush=True)
    ctx.storage_state(path=STATE)
    browser.close
with open(f"{OUT}/{tag}_xhr.json", "w") as f:
    json.dump(xhr, f, indent=1)
print(len(xhr), "XHR captured; replay the one behind your click through the REST helper")
```

```bash
# Run it on a server in the official image; credentials pass by NAME (-e VAR), so values never appear in argv
docker run --rm --network host -v "$PWD/out:/work/out" -v "$PWD:/work/app" \
  -e IDMC_USER -e IDMC_PASS -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
  mcr.microsoft.com/playwright/python:<ver>-jammy \
  bash -lc "pip install -q playwright==<ver> && python /work/app/ui_walk.py walk1 '<url-1>' '<url-2>'"
```

Adapt the step loop for actions (click, fill, check) and keep the same guards: one login, rejection stop, blank-page
detection, a screenshot and page text per step, and a REST read-back after anything that should have committed.

## 10. Speed and serialization

- Authoring one mapping plus its task through the designer took about 30-75 minutes, rising with query size; author
  serially, one object per browser session (L-UI-009).
- Create profiles through the UI one per session; the Location picker was flaky; prefer the REST path (L-UI-017).
- A capability walk of agent, CDI, CAI, profiling, catalog and glossary took 8-10 minutes with screenshots
  (L-UI-016).

## 11. Surface recipes

| Surface | Recipe | Lesson |
|---|---|---|
| Mapping designer | CodeMirror `setValue` + `save`, enabled OK, no Escape; long typing with `delay=1, timeout=300000`; adopt a stuck mapping by GUID; rename target to re-derive | (L-UI-008) |
| Mapping designer: a second, similar flow in the same mapping | select the flow's transformations and copy them: the copy keeps its links, edited field precisions and field mappings; rename the copies (each pasted name gets '1' appended), repoint the source settings and order the flows in Flow Run Order; on the copy, changing a Structure Parser's model clears its mapping, links and Passthrough ticks (L-CDI-232) | (L-UI-034), (L-UI-035) |
| Mapping designer traps | choosing a date/time type in the New Field dialog resets the name to 'NewField': rename it afterwards (double-click the field and type); the mapping description strips `<`, `>` and apostrophes, so write them in words; Arrange All puts each flow on its own row; in Target Fields > Edit Metadata a precision commits only when typed and confirmed with Enter, because a pasted value does not commit (L-CDI-227) | (L-UI-035) |
| Data Profiling | reuse state, one profile per session, header checkbox, verify by page text | (L-UI-017) |
| Data Marketplace delivery templates | headed browser; react-select options; field rows `data-testid='field_deliveryType'`, `'field_deliveryFormatIds'`, `'field_deliveryMethodIds'`; text inputs `data-testid='TEXT'` | (L-UI-018) |
| MDM apps | Business 360 Console `https://<pod>-mdm.<domain>.informaticacloud.com/ui-config-app`; Customer 360 `/ui-x360-app/app/c360/`; Multidomain `/ui-x360-app/app/mde`; Reference 360 `/rdm-ui/` | (L-UI-018) |
| Customer 360 search | `div[data-testid='mdm-bui-search-dropdown']`, `button[data-testid='dropdown-button']`, `span#selected-entity`, `input[aria-label='Search input']` | (L-UI-018) |
| Data Integration designer | `https://<pod>.<domain>.informaticacloud.com/diUI/products/integrationDesign/main` | (L-UI-018) |
| Designer Invalid sweep (states no API reports) | open each object at `.../diUI/products/integrationDesign/main/<kind>/<frsId>/read` (`/edit` to change it; kinds `mapping`, `mct`, `linearTaskflow`; a folder at `.../main/explore/<folderId>`) with a saved state, wait 35-45 s for the canvas, read the Valid or Invalid badge and the 'Validation (<n>)' panel (each item's arrow shows the full message, such as a rule specification whose definition changed); log in by filling `#username` and `#password` and clicking the button named exactly 'Log In' (a substring match also hits the SSO button), and stop on the first failed login | (L-UI-036), (L-DQ-126) |
| Advanced-mode (Spark) mapping, CLAIRE PDF source | Discover Structure lists the PDF model but never enables Select (dated 2026-10-26): parse in a standard mapping on a Secure Agent instead | (L-CDI-276) |
| CLAIRE GPT | prompts from JSON, busy-text wait with dots, auto "proceed", 50-110 s per answer, new conversation per prompt; pin good catalog conversations only, because a pinned analytic answer loses its query results | (L-UI-015), (L-MCP-122) |
| CLAIRE GPT settle rule | read only the newest reply; busy = letter-spaced spinner text in the reply's last ~60 non-space characters, or a status ending in U+2026; done = reply markers or 150 s unchanged; never a bare "..." (the input placeholder has one); Enter after every chip or button click | (L-UI-028), (L-UI-028) |
| CLAIRE GPT pins | hover the `chat-nav-link` row; `chat-pin-button`, `chat-edit-button`, `chat-delete-button`, and `chat-unpin-button` on the Pinned tab; read the Pinned titles back | (L-UI-029) |
| Capability walk | the click path per product | (L-UI-016) |
| SaaS setup with no API | `sf org open --url-only` frontdoor, Playwright, verify by SOQL or the Metadata API | (L-UI-019) |
| BI dashboards | form login; real-browser render as well as the API | (L-UI-020) |
| Metadata Command Center, Data Governance and Catalog, mapping designer behind a transparent proxy | headless Chromium with the section 6 flag set, a saved storage state, at most one scripted login | (L-UI-031) |
| Catalog new-asset forms with multi-step pickers (for example a rule occurrence's Primary Data Element: catalog source > data set > data element) | exact button names, 'Finish' on the last step, `check(force=True)` on radio inputs; use the form once to capture its write request, then replay that over REST | (L-UI-032), (L-CDGC-161) |
| Intelligent structure model editor | wait for the `openStructureData` 200, not the spinner | (L-UI-033) |

## 12. Overturned beliefs (kept so nobody re-learns them)

| Belief | Believed | Overturned by |
|---|---|---|
| Playwright is a screenshot tool for IDMC, not an automation path | 2026-07-10 | designer authoring by automation (L-UI-021); was L-UI-022 |
| The first mapping of a new source/target pair must be authored by hand | to 2026-07-06 | a Playwright-authored mapping on 2026-07-07, then IMF JSON import (L-UI-021); was L-UI-023 |
| Log in fresh in each script | 2026-07-06 to 2026-07-08 | reuse the state inside its window; refresh once per batch (L-UI-005); was L-UI-024 |
| Agent service and connector enablement needs a UI bot | July to 2026-09-22 | an MCP tool (09-23) and a REST PUT found by XHR capture (09-28) (L-UI-002); was L-UI-025 |
| CAI publish must be driven through the designer | 2026-07-08 to 2026-07-24 | REST publish on the `-cai` host (L-UI-001); was L-UI-026 |
| Private Network Access flags are enough behind the proxy | 2026-08-18 to 2026-09-13 | blank SPAs under every configuration (L-UI-011); was L-UI-027 |

L-UI-011 itself is disputed since 2026-10-06: with the Local Network Access checks also off, three consoles worked
headless from behind such a proxy (L-UI-031, section 6).
