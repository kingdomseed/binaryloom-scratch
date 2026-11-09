#!/usr/bin/env python3
"""Publish and take down throwaway pages on scratch.binaryloom.io.

Shares are private by default: they open only from a link carrying a secret key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / "live.json"
# Private entries carry only key hashes; the middleware reads this file and hides it.
PRIVATE = ROOT / "private.json"
# Plain keys never enter the deployed tree.
KEYS = Path.home() / ".config" / "binaryloom-scratch" / "keys.json"
RESERVED = {"live.json", "index.html", "scratch.py", "private.json", "functions"}
PROJECT = "binaryloom-scratch"
BASE_URL = "https://scratch.binaryloom.io"


def load_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        sys.exit(f"Error: {path.name} must be a JSON array.\n  python3 scratch.py list")
    return data


def save_list(path: Path, items: list[dict]) -> None:
    path.write_text(json.dumps(items, indent=2) + "\n")


def load_live() -> list[dict]:
    return load_list(LIVE)


def save_live(items: list[dict]) -> None:
    save_list(LIVE, items)


def load_keys() -> dict[str, str]:
    return json.loads(KEYS.read_text()) if KEYS.exists() else {}


def save_keys(keys: dict[str, str]) -> None:
    KEYS.parent.mkdir(parents=True, exist_ok=True)
    KEYS.touch(mode=0o600, exist_ok=True)
    KEYS.chmod(0o600)
    KEYS.write_text(json.dumps(keys, indent=2) + "\n")


def key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def private_url(slug: str, key: str) -> str:
    return f"{BASE_URL}/{slug}/?k={key}"


def find(items: list[dict], slug: str) -> dict | None:
    return next((i for i in items if i.get("slug") == slug), None)


def dest_for(slug: str) -> Path:
    return ROOT / slug


def copy_src(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if src.is_file():
        shutil.copy2(src, dest / "index.html")
        return
    if src.is_dir():
        for item in src.iterdir():
            target = dest / item.name
            if item.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
        if not (dest / "index.html").exists():
            sys.exit(
                f"Error: {src} has no index.html.\n"
                "  python3 scratch.py up --slug NAME --src /path/to/dir-or-index.html"
            )
        return
    sys.exit(f"Error: source not found: {src}")


def cmd_up(args: argparse.Namespace) -> None:
    slug = args.slug.strip("/").strip()
    if not slug or "/" in slug or slug in RESERVED:
        sys.exit(
            "Error: slug must be a single path segment.\n"
            "  python3 scratch.py up --slug character-graph --src ./doc.html --title 'Title'"
        )
    src = Path(args.src).expanduser().resolve()
    if not src.exists():
        sys.exit(f"Error: source not found: {src}")
    public, private = load_live(), load_list(PRIVATE)
    dest = dest_for(slug)
    access = "public" if args.public else "private (key link)"
    if args.dry_run:
        print(f"would copy {src} -> {dest}/")
        print(f"would list {slug} as {access}")
        print(f"url: {BASE_URL}/{slug}/")
        return
    copy_src(src, dest)
    now = date.today().isoformat()
    old = find(public, slug) or find(private, slug) or {}
    entry = {
        "slug": slug,
        "title": args.title or old.get("title") or slug,
        "note": args.note if args.note is not None else old.get("note", ""),
        "added": old.get("added") or now,
    }
    public = [i for i in public if i.get("slug") != slug]
    private = [i for i in private if i.get("slug") != slug]
    keys = load_keys()
    if args.public:
        public.append(entry)
        keys.pop(slug, None)
        url = f"{BASE_URL}/{slug}/"
    else:
        # Re-publishing keeps the existing key so links already sent keep working.
        key = keys.get(slug) or secrets.token_urlsafe(24)
        keys[slug] = key
        private.append({**entry, "keyHash": key_hash(key)})
        url = private_url(slug, key)
    save_live(public)
    save_list(PRIVATE, private)
    save_keys(keys)
    print(f"{'updated' if old else 'published'} {slug} ({access})")
    print(f"url: {url}")
    if args.deploy:
        cmd_deploy(args)


def cmd_down(args: argparse.Namespace) -> None:
    slug = args.slug.strip("/").strip()
    public, private = load_live(), load_list(PRIVATE)
    dest = dest_for(slug)
    exists = find(public, slug) or find(private, slug) or dest.exists()
    if not exists or slug in RESERVED:
        sys.exit(
            f"Error: {slug!r} is not live.\n"
            "  python3 scratch.py list"
        )
    if args.dry_run:
        print(f"would remove {dest}/")
        print(f"would drop {slug} from live.json, private.json and the key file")
        return
    save_live([i for i in public if i.get("slug") != slug])
    save_list(PRIVATE, [i for i in private if i.get("slug") != slug])
    keys = load_keys()
    if keys.pop(slug, None) is not None:
        save_keys(keys)
    if dest.exists():
        shutil.rmtree(dest)
    print(f"taken down {slug}")
    if args.deploy:
        cmd_deploy(args)


def cmd_list(_: argparse.Namespace) -> None:
    public, private = load_live(), load_list(PRIVATE)
    if not public and not private:
        print("0 live")
        return
    for item in public:
        slug = item.get("slug", "")
        print(f"{slug}\tpublic\t{BASE_URL}/{slug}/\t{item.get('title', '')}")
    for item in private:
        slug = item.get("slug", "")
        print(f"{slug}\tprivate\t{BASE_URL}/{slug}/\t{item.get('title', '')}")


def cmd_link(args: argparse.Namespace) -> None:
    slug = args.slug.strip("/").strip()
    if find(load_live(), slug):
        print(f"{BASE_URL}/{slug}/")
        return
    key = load_keys().get(slug)
    if not find(load_list(PRIVATE), slug) or not key:
        sys.exit(f"Error: no private share or key for {slug!r}.\n  python3 scratch.py list")
    print(private_url(slug, key))


def wrangler_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CLOUDFLARE_ACCOUNT_ID", "bb9c6e1c45f208657aed12579feb6e3b")
    # Wrangler OAuth lives in its config file. Do not copy that token into
    # CLOUDFLARE_API_TOKEN — expired or OAuth tokens there fail as API tokens.
    env.pop("CLOUDFLARE_API_TOKEN", None)
    return env


def cmd_deploy(args: argparse.Namespace) -> None:
    if args.dry_run:
        print("would run: npx wrangler pages deploy . --project-name binaryloom-scratch")
        return
    cmd = [
        "npx",
        "--yes",
        "wrangler",
        "pages",
        "deploy",
        str(ROOT),
        "--project-name",
        PROJECT,
        "--branch",
        "main",
        "--commit-dirty=true",
    ]
    result = subprocess.run(cmd, cwd=ROOT, env=wrangler_env())
    if result.returncode != 0:
        sys.exit(result.returncode)
    print(f"index: {BASE_URL}/")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scratch.py",
        description="Put a page up on scratch.binaryloom.io (private key link by default), or take it down.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("up", help="Copy a file or folder onto scratch and list it")
    up.add_argument("--slug", required=True, help="URL path, e.g. character-graph")
    up.add_argument("--src", required=True, help="HTML file or directory with index.html")
    up.add_argument("--title", default="", help="Index title")
    up.add_argument("--note", default=None, help="One-line description")
    up.add_argument(
        "--public",
        action="store_true",
        help="List on the index and open without a key (default: private key link)",
    )
    up.add_argument("--dry-run", action="store_true")
    up.add_argument("--no-deploy", action="store_true")
    up.set_defaults(func=cmd_up, deploy=True)

    down = sub.add_parser("down", help="Remove a live page from scratch")
    down.add_argument("--slug", required=True)
    down.add_argument("--dry-run", action="store_true")
    down.add_argument("--no-deploy", action="store_true")
    down.set_defaults(func=cmd_down, deploy=True)

    listing = sub.add_parser("list", help="Print live slugs and URLs")
    listing.set_defaults(func=cmd_list, dry_run=False)

    link = sub.add_parser("link", help="Print the share link, with its key if private")
    link.add_argument("--slug", required=True)
    link.set_defaults(func=cmd_link, dry_run=False)

    deploy = sub.add_parser("deploy", help="Deploy the current tree to Pages")
    deploy.add_argument("--dry-run", action="store_true")
    deploy.set_defaults(func=cmd_deploy)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "no_deploy", False):
        args.deploy = False
    args.func(args)


if __name__ == "__main__":
    main()
