# state/

Written by the scripts, specific to YOUR org: `ids.json` (every id the build resolved or created), `packages/`
(generated mapping and CAI packages; the CAI one can hold the Connected App secret), `rendered/` (rendered bodies),
`harvest/` (folder files exported from your org), `glossary_registry.json`, `backup/`.
Do not share this folder. `python teardown/teardown.py clean-local` removes the generated files.
