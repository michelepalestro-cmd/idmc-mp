# IDMC MP: install

Install it as a Claude Code plugin (see the repo README): `/plugin marketplace add michelepalestro-cmd/idmc-mp`, then
`/plugin install idmc-mp@idmc-mp`. Then connect once: run `python kb/check_login.py` from this folder, fill in the
file it creates at `~/.idmc_toolkit/IDMC_LOGIN.txt`, and run it again. Your login stays outside the plugin, so
updates never touch it.
