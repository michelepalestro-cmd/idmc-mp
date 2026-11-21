# Setup and login

**Answers:** How do I install the plugin, connect it to my IDMC org, fix a login that fails, update or remove it, and
keep my password safe?

**Read when:** installing for the first time, a login fails, or before sharing a copy.

**Related:** [Start here](README.md) · [Quick start: your first hour](10-quick-start-your-first-hour-with-idmc-and-claude.md) ·
[Login cheat sheet](../01-login-and-orgs/README.md) · [Setup for git clones and demos](../../toolkit/setup/SETUP.md)

---

## Setup in 3 steps (about 10 minutes)

### Before you start

You need four things. Tick them off:

- [ ] **Claude Code** is installed and opens. ([How to install Claude Code](https://code.claude.com/docs))
- [ ] **Python 3.10 or newer.** To check, open a terminal window and type `python3 --version` (Windows: `py --version`).
      If it says 3.10 or higher, you are fine. If not, install it from [python.org](https://www.python.org/downloads/).
- [ ] **An IDMC user name and password that work on the IDMC sign-in page.**
      If you normally sign in with your company's single sign-on (SSO) button, that will **not** work here:
      ask your IDMC admin for a "native" IDMC user with its own password. A separate service user for Claude is best.
      On a trial you are usually the admin yourself: sign in with SSO, go to Administrator > Users, add a native
      IDMC user and give it a password.
- [ ] **You can sign in to IDMC in your web browser** with that user. (You will copy the address from the browser.)

> **What is a terminal window?** It is the app where you type commands.
> Mac: open **Terminal** (press Cmd+Space, type "Terminal"). Windows: open **PowerShell** (Start menu, type
> "PowerShell"). Linux: open your **Terminal** app.

### Step 1: Install the plugin

Open Claude Code and type these two lines, one at a time, pressing Enter after each:

```
/plugin marketplace add michelepalestro-cmd/informatica-idmc-headless-plugin
```

```
/plugin install informatica-idmc-headless@informatica-idmc-headless
```

Then close Claude Code and open it again.

### Step 2: Give it your IDMC login

In Claude Code, type:

```
/informatica-idmc-headless:connect
```

Claude creates your private login file and shows you a command that ends in `--setup`. Now pick **one** way to fill
it in:

**Way A: let it ask you (easiest).** Copy the `--setup` command Claude showed you, paste it into a **terminal window**
(not into Claude Code) and press Enter. It asks three questions:

1. **The IDMC address.** Sign in to IDMC in your browser. Click the address bar at the top, copy everything, and paste
   it. It looks like `https://usw5.dm-us.informaticacloud.com/cloudUX/home`.
2. **Your IDMC user name.** Exactly what you type on the IDMC sign-in page.
3. **Your password.** You will **not** see anything while you type. That is normal. Press Enter when done.

It saves the file and tries the login once, right there in the terminal. You see `CONNECTED to IDMC` or a message
that says what went wrong (see [If the login doesn't work](#if-the-login-doesnt-work)). Then go back to Claude Code.

**Way B: fill in the file yourself.** Claude also shows you a command that opens the file in a text editor. Fill in the
three lines at the bottom so they look like this example, then save:

```
IDMC_USER=svc_claude
IDMC_PASS=MyS3cretPassw0rd
IDMC_LOGIN_HOST=https://usw5.dm-us.informaticacloud.com/cloudUX/home
```

No quotes, and no spaces around the `=` sign.

> **Never paste your password into the Claude chat.** It only belongs in that file, which stays on your computer in
> your home folder (`~/.idmc_toolkit/IDMC_LOGIN.txt`) and only you can read.

### Step 3: Check that it works

In Claude Code, type `/informatica-idmc-headless:connect` again. When it works you see:

```
CONNECTED to IDMC
  Org name : <your org>
  Org id   : <22 letters and numbers>
  Pod      : <for example usw5>
  User     : <your user>
```

That's it. Try `/informatica-idmc-headless:health-check` next: it looks around your org and changes nothing.

## If the login doesn't work

**Stop after one failed try.** IDMC locks your account after a few wrong logins, and every new try can restart the
lock. The plugin tries only once per run and checks your file on your computer first, so it never wastes a try on an
empty or example value.

| What you see | What it means | What to do |
|---|---|---|
| `Your login is not ready yet` | A line in your file is empty or still has the example in it. Nothing was sent to IDMC. | Fill in the line it names, then run `/informatica-idmc-headless:connect` again. |
| `user name or password is wrong` (`IDS_085` or `UI_10000`) | Most often the **address is for the wrong region**, not a wrong password. | Sign in in your browser and paste that exact address into `IDMC_LOGIN_HOST`. Check the user name is exactly what you type on the sign-in page (it may not be your e-mail). |
| Same, and you sign in with an SSO button | SSO users have no IDMC password. | Ask your IDMC admin for a native IDMC user with a password. On a trial you are the admin: Administrator > Users, add a native user with a password. |
| `account is LOCKED` (`IDS_086`) | Too many wrong logins. | Don't try again. Ask an IDMC admin to unlock you (Administrator > Users > your user > Unlock), or use "Forgot your password?" on the sign-in page. If you are the only admin (a trial), use "Forgot your password?" or open a case with Informatica support. |
| `Logins are paused` (`login BLOCKED`) | The plugin paused itself after a rejected login, to protect your account. No login was sent. | Sign in in the browser to prove the password works. Fix the file: changing the user, the password or the address lifts the pause by itself. If nothing needed to change (for example an admin unlocked you and the password is the same), delete the `.block.json` file the message names, then run `/informatica-idmc-headless:connect` once. |
| `could not reach IDMC` | Internet, VPN or proxy problem. Not your password. | Check your connection or VPN, then try again. |
| `CERTIFICATE_VERIFY_FAILED` | A company network is inspecting secure traffic. | Ask IT for the company certificate file and set `SSL_CERT_FILE` to it. |
| The password must be changed, or it expired | IDMC wants a new password first. | Sign in once in the browser, set the new password, then put it in your file. |

Still stuck? In Claude Code, type `/informatica-idmc-headless:fix-error` and paste the message (never your password).

## Safety

- **Your password stays on your computer**, in `~/.idmc_toolkit/IDMC_LOGIN.txt`, readable only by you. The plugin only
  talks to Informatica's own servers. It sends nothing anywhere else.
- **Writes are dry runs first.** Anything that changes your org shows what it will do, and only runs after it has
  checked it is connected to the org you named (`--expect-org <org id>`).
- **Jobs cost IPUs.** Jobs Claude runs in your org use your subscription, like any job you run yourself.
- Found a security problem? See [SECURITY.md](../../.github/SECURITY.md).

## Update or remove

- **Get updates automatically (recommended):** in Claude Code type `/plugin`, open **Marketplaces**, pick **informatica-idmc-headless**
  and turn on auto-update.
- **Update by hand:** `/plugin marketplace update informatica-idmc-headless`, then `/plugin update informatica-idmc-headless@informatica-idmc-headless`.
- **Remove:** `/plugin uninstall informatica-idmc-headless@informatica-idmc-headless`.

Updates never touch your login or your own lessons: they live in `~/.idmc_toolkit/`, outside the plugin.

## For advanced users

- **Several orgs:** keep one login file per org anywhere outside the plugin, and set `IDMC_CREDS_FILE` to the one you
  want. Its values win over the default file.
- **Run the login check yourself:** `python3 toolkit/check_login.py` from the plugin folder (`--setup`, `--where`,
  `--json`). Windows: `py` instead of `python3`.
- **Working from a git clone, building the demos, or sharing a copy:** see [toolkit/setup/SETUP.md](../../toolkit/setup/SETUP.md).
- **Start here in the knowledge base:** the [Quick Start](10-quick-start-your-first-hour-with-idmc-and-claude.md).
