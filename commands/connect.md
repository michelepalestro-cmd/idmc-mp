---
description: Connect Claude to your IDMC org (login file outside the plugin) and prove which org it is
---

Use the informatica-idmc-headless skill. On Windows, use `python` (or `py`) where these steps say `python3`. Goal: the user is connected
to their IDMC org and the org is proven, with at most one login attempt.

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` once. It checks the login file on the computer first
   and only tries to log in when the three values look right.
2. If it just created `~/.idmc_toolkit/IDMC_LOGIN.txt`, or says the login is not ready yet, stop and tell the user, in
   plain words, the two ways to fill it in:
   - **Easiest:** in a terminal window (not in this chat), run the `--setup` command the script printed. It asks for
     the browser address, the user name and the password (hidden while typing), saves them, and tries the login
     once right there in the terminal (it prints CONNECTED or what went wrong). Then they come back here.
   - **Or** open the file with the command the script printed, fill in the 3 lines, save, and run `/informatica-idmc-headless:connect`
     again.
   Ask the user **not** to paste their password into the chat. If they do anyway, do not write it anywhere and never
   repeat it: tell them it is now in the chat history, that they should change it in IDMC, and that they should enter the
   new one with the `--setup` command in a terminal.
3. If it says CONNECTED, report the org name, org id, pod and user from its summary in one short block, and suggest
   `/informatica-idmc-headless:health-check` next.
4. If the login failed, do NOT run it again: wrong logins lock the account. Show the user the "WHAT THIS MEANS" part
   of the output and help them fix the cause it names (wrong region in the address, a single sign-on user with no IDMC
   password, a locked account, a paused login, or a network problem). On a trial the user is usually the only admin:
   point them to "Forgot your password?", a native user they add under Administrator > Users, or Informatica support
   (L-AUTH-037, L-AUTH-045). A paused login with unchanged, correct values needs the `.block.json` file it names
   deleted first. Run it again only after the user says the file is fixed.
