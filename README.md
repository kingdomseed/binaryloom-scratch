# scratch.binaryloom.io

Temporary shares. Each live item is a folder. Shares are **private by default**: they open only from a link that carries a secret key. Public shares (`--public`) are listed on the index, which is generated from `live.json`.

Agents: load skill `scratch-binaryloom` (do not hand-edit the index, `live.json` or `private.json`).

```text
python3 scratch.py up --slug NAME --src /path/to/index.html --title "Title"            # private key link
python3 scratch.py up --slug NAME --src /path/to/index.html --title "Title" --public   # listed, no key
python3 scratch.py link --slug NAME
python3 scratch.py down --slug NAME
python3 scratch.py list
```

## How private shares work

- `up` makes a random key, keeps it in `~/.config/binaryloom-scratch/keys.json` (mode 600, outside the deployed tree), and writes only its SHA-256 hash to `private.json`.
- `functions/_middleware.js` answers 404 for a private slug unless the request has `?k=KEY` or the cookie it sets. A correct key is swapped for an `HttpOnly` cookie scoped to that slug, and the key is removed from the address bar.
- `private.json` and `functions/` themselves answer 404.
- Re-running `up` on a private slug keeps its key, so links already sent keep working. To revoke a link, `down` the share and put it up again: that makes a new key.
- Anyone holding the link can open the share and forward it. For identity-checked access, put Cloudflare Access in front of the site.

## Examples

```text
python3 scratch.py up \
  --slug character-graph \
  --src "/Users/jasonholt/Broken Empires/character-graph/docs/index.html" \
  --title "Broken Empires — Character Graph" \
  --note "Character creation, races, careers, magic, XP." \
  --public

python3 scratch.py down --slug character-graph
python3 scratch.py up --slug NAME --src ./doc.html --title "Title" --dry-run
python3 scratch.py deploy
```

`--no-deploy` updates the tree without shipping. `up` and `down` deploy unless you pass that.

- Live: https://scratch.binaryloom.io
- Pages project: `binaryloom-scratch`
