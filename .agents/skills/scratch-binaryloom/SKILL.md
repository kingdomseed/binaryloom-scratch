---
name: scratch-binaryloom
description: Upload, share, verify, revoke, and take down temporary pages and files on scratch.binaryloom.io. Shares are private by default (secret-key link) or public. Use when the user wants to host, share, throw up, unpublish, revoke, or take down a doc, HTML page, mermaid diagram, PDF, image, or other one-off on scratch, binaryloom scratch, or scratch.binaryloom.io.
---

# scratch.binaryloom.io

Temporary shares for Jason Holt, served by the Cloudflare Pages project `binaryloom-scratch` at https://scratch.binaryloom.io (fallback https://binaryloom-scratch.pages.dev). Every action goes through `scratch.py`; never edit `live.json` or `private.json` by hand and never run `wrangler pages` directly.

## Where to run it

Only `mac-mini` publishes. Its checkout at `~/repos/personal/binaryloom-scratch` holds every live share folder, `live.json`, `private.json`, and the keys in `~/.config/binaryloom-scratch/keys.json`. A deploy uploads that tree as the whole site, so a deploy from any other machine would delete every share; the script refuses to deploy anywhere else. This is the one exception to the no-Artwod-on-mac-mini rule.

From another machine, copy the files over and run the script there:

```bash
scp -r /path/to/report mac-mini:/tmp/scratch-SLUG
ssh mac-mini 'python3 ~/repos/personal/binaryloom-scratch/scratch.py up --slug SLUG --src /tmp/scratch-SLUG --title "Title"'
ssh mac-mini 'rm -rf /tmp/scratch-SLUG'
```

If `npx --yes wrangler whoami` on mac-mini says it is not logged in, stop and ask Jason to run `npx wrangler login` there and finish OAuth in Helium (never Chrome). The script ignores `CLOUDFLARE_API_TOKEN`.

`python3 scratch.py --help` and `python3 scratch.py <command> --help` are the source of truth for flags.

## Access

- **Private (default).** The share opens only from a link with `?k=KEY`; without it the URL returns 404 and the share is not on the index. Anyone with the link can open and forward it, so it is not tied to a person. Say so when the content is sensitive.
- **Public (`--public`).** Listed on the index, no key. Use only when Jason asked for a public page.

Confirm the slug and title before `up`, and confirm before `--public`. Never upload secrets, credentials, or anything Jason did not ask to share.

## Upload

```bash
python3 scratch.py up --slug SLUG --src /absolute/path --title "Title" --note "One line"
```

- `--src` is an HTML file (served as the share's page), any other file (served under its own name, `/SLUG/report.pdf`), or a directory with `index.html` (served with its assets).
- `--slug` is one lowercase-kebab path segment that is not a site file (`index.html`, `404.html`, `live.json`, `private.json`, `functions`, `scratch.py`).
- Running `up` again on a slug replaces its contents. A private share keeps its key, so links already sent keep working.
- `up` deploys, verifies, deletes all older deployments, then prints the link. `--dry-run` shows the plan; `--no-deploy` changes only the local tree.

Give Jason the printed link. Do not paste a private link anywhere else, and do not put keys in commits, files, or issues.

## Verify

`up`, `down`, and `revoke` check both hostnames themselves and exit non-zero on any mismatch:

| Share | Expected |
| --- | --- |
| Public | 200 |
| Private, no key | 404 |
| Private, with key | 302 (key swapped for a cookie) |
| Taken down, or an old revoked key | 404 |

Run `python3 scratch.py check --slug SLUG` to repeat the check later. Report the result lines, not just "done". If only the custom domain fails, give the pages.dev link (same `?k=`) and say DNS may lag on this machine. For layout, open the link in a browser as well; a 200 does not prove the page renders.

## Take down

```bash
python3 scratch.py list
python3 scratch.py down --slug SLUG
```

`down` removes the folder, the index entry, and the key, deploys, verifies 404, and deletes every older deployment (each one keeps a permanent `<id>.binaryloom-scratch.pages.dev` URL that would still serve the share). There is no rollback. To publish the share again, Jason's original file is needed.

If Jason says "take it down" without a slug, run `list` and ask, unless exactly one share matches what he meant.

## Revoke a private link

```bash
python3 scratch.py revoke --slug SLUG
```

Replaces the key, deploys, verifies the old link returns 404 and the new one works, and deletes older deployments. Give Jason the new link. `python3 scratch.py link --slug SLUG` prints a current link again.

## When something fails

- Deploy or verification failed: older deployments are left alone. Quote the wrangler error and run `list` to show the local state.
- Deleting old deployments failed: the new deploy is live, but old URLs may still serve removed content. Report the deployment IDs the script printed and rerun `python3 scratch.py deploy`.
- Report FAIL lines as they are. Do not tell Jason a share is gone or private until `check` passes.
