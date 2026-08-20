# scratch.binaryloom.io

Temporary public shares. Index is generated from `live.json`. Each live item is a folder.

Agents: load skill `scratch-binaryloom` (do not hand-edit the index).

```text
python3 scratch.py up --slug NAME --src /path/to/index.html --title "Title"
python3 scratch.py down --slug NAME
python3 scratch.py list
```

## Examples

```text
python3 scratch.py up \
  --slug character-graph \
  --src "/Users/jasonholt/Broken Empires/character-graph/docs/index.html" \
  --title "Broken Empires — Character Graph" \
  --note "Character creation, races, careers, magic, XP."

python3 scratch.py down --slug character-graph
python3 scratch.py up --slug NAME --src ./doc.html --title "Title" --dry-run
python3 scratch.py deploy
```

`--no-deploy` updates the tree without shipping. `up` and `down` deploy unless you pass that.

- Live: https://scratch.binaryloom.io
- Pages project: `binaryloom-scratch`
