# scratch.binaryloom.io

Temporary shares on the Cloudflare Pages project `binaryloom-scratch`. Shares are **private by default**: they open only from a link that carries a secret key. Public shares (`--public`) are listed on the index, which reads `live.json`.

Agents: load the `scratch-binaryloom` skill.

This repo holds the tool and the skill. Share folders, `live.json`, `private.json`, and the keys exist only on mac-mini, the one machine that deploys.

```text
python3 scratch.py up --slug NAME --src /path/to/file-or-dir --title "Title"   # private key link
python3 scratch.py up --slug NAME --src /path/to/file-or-dir --public          # listed, no key
python3 scratch.py link --slug NAME
python3 scratch.py check --slug NAME
python3 scratch.py revoke --slug NAME
python3 scratch.py down --slug NAME
python3 scratch.py list
```

## How it works

- A deploy uploads only `index.html`, `404.html`, `live.json`, and the listed share folders, checks both hostnames for the expected status codes, then deletes every older deployment, so removed shares and revoked keys do not survive at old `<id>.binaryloom-scratch.pages.dev` URLs.
- Pages keeps removed files in its edge cache for up to a week, so `functions/_middleware.js` answers 404 for any top-level path that is not currently listed.
- `up` makes a random key for a private share, keeps it in `~/.config/binaryloom-scratch/keys.json` (mode 600), and writes only its SHA-256 hash to `private.json`.
- `functions/_middleware.js` answers 404 for a private slug unless the request has `?k=KEY` or the cookie it sets. A correct key is swapped for an `HttpOnly` cookie scoped to that slug, and the key is removed from the address bar.
- Re-running `up` on a private slug keeps its key. `revoke` replaces it.
- Anyone holding the link can open the share and forward it. For identity-checked access, put Cloudflare Access in front of the site.
