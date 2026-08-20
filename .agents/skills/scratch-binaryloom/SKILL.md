---
name: scratch-binaryloom
description: Publish and take down temporary public pages on scratch.binaryloom.io. Use when the user wants to host, share, throw up, unpublish, or take down a doc, HTML page, mermaid diagram, or other one-off on scratch, binaryloom scratch, or scratch.binaryloom.io.
---

# scratch.binaryloom.io

Temporary public shares for Jason Holt. Index is `live.json`; each live item is a folder. Do not hand-edit the index or deploy around the CLI.

Repo: `~/repos/personal/binaryloom-scratch`  
CLI: `python3 scratch.py` (run from that repo, or pass the full path)  
Live: https://scratch.binaryloom.io  
Fallback: https://binaryloom-scratch.pages.dev  
Pages project: `binaryloom-scratch`

Everything on this host is **public**. Confirm slug + title before `up`. Confirm slug before `down`.

## Before you run anything

Need all of:

1. Repo at `~/repos/personal/binaryloom-scratch` with `scratch.py`
2. `python3` and `npx`
3. Cloudflare Pages auth — `scratch.py deploy` reads `CLOUDFLARE_API_TOKEN` if set, otherwise the wrangler OAuth token in `~/Library/Preferences/.wrangler/config/default.toml`
4. Account `bb9c6e1c45f208657aed12579feb6e3b` (script default)

Probe:

```bash
python3 ~/repos/personal/binaryloom-scratch/scratch.py list
npx --yes wrangler whoami
```

If wrangler is not logged in, stop. Tell the user to run `npx wrangler login` and finish OAuth in **Helium** (never Chrome). Then retry.

`scratch.py --help` / `scratch.py up --help` is the flag source of truth. Do not invent flags.

## Put something up

Source must be an HTML file, or a directory that contains `index.html` (extra assets come along if you pass a directory).

```bash
python3 ~/repos/personal/binaryloom-scratch/scratch.py up \
  --slug SLUG \
  --src /absolute/path/to/index.html \
  --title "Title" \
  --note "One line"
```

- `--slug`: one path segment, lowercase-kebab. Not `live.json`, `index.html`, or `scratch.py`.
- Re-running the same slug overwrites that share (idempotent replace).
- `up` deploys unless `--no-deploy`. `--dry-run` prints the plan only.

Then:

1. Print `https://scratch.binaryloom.io/SLUG/`
2. `curl -sI` that URL and the fallback `https://binaryloom-scratch.pages.dev/SLUG/`
3. If the custom domain does not resolve, give the pages.dev URL and say DNS on this machine may lag

Do not rebuild `index.html` to add a row. The homepage reads `live.json`.

## Take something down

```bash
python3 ~/repos/personal/binaryloom-scratch/scratch.py list
python3 ~/repos/personal/binaryloom-scratch/scratch.py down --slug SLUG
```

If the user says "take it down" without a slug, `list` first. Only skip the ask when one live item matches what they meant.

`down` is public-URL deletion. Requires an explicit slug (from the user or from that list). `--dry-run` if they asked to preview.

## Do not

- Hand-edit `live.json` or `index.html` for listing
- `wrangler pages deploy` except via `scratch.py`
- Publish secrets, private credentials, or anything the user did not ask to make public
- Use Chrome for Cloudflare/wrangler OAuth — Helium only
- Leave a share up because deploy failed; report the failure and the local tree state (`list`)
