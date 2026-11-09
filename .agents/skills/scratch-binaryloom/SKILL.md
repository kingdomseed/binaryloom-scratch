---
name: scratch-binaryloom
description: Publish and take down temporary pages on scratch.binaryloom.io, private by default (secret-key link) or public. Use when the user wants to host, share, throw up, unpublish, or take down a doc, HTML page, mermaid diagram, or other one-off on scratch, binaryloom scratch, or scratch.binaryloom.io.
---

# scratch.binaryloom.io

Temporary shares for Jason Holt. Each live item is a folder. Do not hand-edit `live.json`, `private.json`, or the index, and do not deploy around the CLI.

Repo: `~/repos/personal/binaryloom-scratch`  
CLI: `python3 scratch.py` (run from that repo, or pass the full path)  
Live: https://scratch.binaryloom.io  
Fallback: https://binaryloom-scratch.pages.dev  
Pages project: `binaryloom-scratch`

**Private by default.** A share opens only from a link carrying a secret key (`?k=...`); without it the URL answers 404 and the share is not on the index. `--public` lists it on the index with no key. Anyone holding a private link can open and forward it, so it is not identity-checked; say so when the content is sensitive. Confirm slug + title before `up`, and confirm before using `--public`. Confirm slug before `down`.

## Before you run anything

Need all of:

1. Repo at `~/repos/personal/binaryloom-scratch` with `scratch.py`
2. `python3` and `npx`
3. Cloudflare Pages auth — `scratch.py deploy` uses the wrangler OAuth login (it ignores `CLOUDFLARE_API_TOKEN`)
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
  --note "One line"          # add --public only if the user asked for a public, listed page
```

- `--slug`: one path segment, lowercase-kebab. Not `live.json`, `index.html`, `scratch.py`, `private.json`, or `functions`.
- Re-running the same slug overwrites that share. A private share keeps its key, so sent links keep working.
- `up` deploys unless `--no-deploy`. `--dry-run` prints the plan only.
- The key lives in `~/.config/binaryloom-scratch/keys.json`; only its hash is deployed. `scratch.py link --slug SLUG` prints the link again.

Then:

1. Give the user the link `up` printed (with `?k=` for private shares). Do not paste it anywhere else.
2. Check it: private share without the key must return 404; with the key, 302 then 200 with the cookie. Public share: `curl -sI` the URL and the fallback `https://binaryloom-scratch.pages.dev/SLUG/`.
3. If the custom domain does not resolve, give the pages.dev URL (same `?k=`) and say DNS on this machine may lag.

Do not rebuild `index.html` to add a row. The homepage reads `live.json`, which holds public shares only.

## Take something down

```bash
python3 ~/repos/personal/binaryloom-scratch/scratch.py list
python3 ~/repos/personal/binaryloom-scratch/scratch.py down --slug SLUG
```

If the user says "take it down" without a slug, `list` first. Only skip the ask when one live item matches what they meant.

`down` deletes the share and its key. Requires an explicit slug (from the user or from that list). `--dry-run` if they asked to preview. To revoke a private link but keep the page, `down` then `up` again: that issues a new key.

## Do not

- Hand-edit `live.json`, `private.json`, or `index.html` for listing
- Copy keys into the repo, commits, or chat beyond giving the user their link
- `wrangler pages deploy` except via `scratch.py`
- Publish secrets, private credentials, or anything the user did not ask to share
- Use Chrome for Cloudflare/wrangler OAuth — Helium only
- Leave a share up because deploy failed; report the failure and the local tree state (`list`)
