#!/usr/bin/env python3
"""Publish and take down throwaway pages on scratch.binaryloom.io."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / "live.json"
PROJECT = "binaryloom-scratch"
BASE_URL = "https://scratch.binaryloom.io"


def load_live() -> list[dict]:
    if not LIVE.exists():
        return []
    data = json.loads(LIVE.read_text())
    if not isinstance(data, list):
        sys.exit("Error: live.json must be a JSON array.\n  python3 scratch.py list")
    return data


def save_live(items: list[dict]) -> None:
    LIVE.write_text(json.dumps(items, indent=2) + "\n")


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
    if not slug or "/" in slug or slug in {"live.json", "index.html", "scratch.py"}:
        sys.exit(
            "Error: slug must be a single path segment.\n"
            "  python3 scratch.py up --slug character-graph --src ./doc.html --title 'Title'"
        )
    src = Path(args.src).expanduser().resolve()
    if not src.exists():
        sys.exit(f"Error: source not found: {src}")
    items = load_live()
    dest = dest_for(slug)
    if args.dry_run:
        print(f"would copy {src} -> {dest}/")
        print(f"would write live.json slug={slug}")
        print(f"url: {BASE_URL}/{slug}/")
        return
    copy_src(src, dest)
    entry = find(items, slug)
    now = date.today().isoformat()
    if entry:
        entry["title"] = args.title or entry.get("title") or slug
        if args.note is not None:
            entry["note"] = args.note
        entry["added"] = entry.get("added") or now
        print(f"updated {slug}")
    else:
        items.append(
            {
                "slug": slug,
                "title": args.title or slug,
                "note": args.note or "",
                "added": now,
            }
        )
        print(f"published {slug}")
    save_live(items)
    print(f"url: {BASE_URL}/{slug}/")
    if args.deploy:
        cmd_deploy(args)


def cmd_down(args: argparse.Namespace) -> None:
    slug = args.slug.strip("/").strip()
    items = load_live()
    dest = dest_for(slug)
    exists = find(items, slug) or dest.exists()
    if not exists:
        sys.exit(
            f"Error: {slug!r} is not live.\n"
            "  python3 scratch.py list"
        )
    if args.dry_run:
        print(f"would remove {dest}/")
        print(f"would drop {slug} from live.json")
        return
    items = [i for i in items if i.get("slug") != slug]
    save_live(items)
    if dest.exists():
        shutil.rmtree(dest)
    print(f"taken down {slug}")
    if args.deploy:
        cmd_deploy(args)


def cmd_list(_: argparse.Namespace) -> None:
    items = load_live()
    if not items:
        print("0 live")
        return
    for item in items:
        slug = item.get("slug", "")
        print(f"{slug}\t{BASE_URL}/{slug}/\t{item.get('title', '')}")


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
        description="Put a page up on scratch.binaryloom.io, or take it down.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("up", help="Copy a file or folder onto scratch and list it")
    up.add_argument("--slug", required=True, help="URL path, e.g. character-graph")
    up.add_argument("--src", required=True, help="HTML file or directory with index.html")
    up.add_argument("--title", default="", help="Index title")
    up.add_argument("--note", default=None, help="One-line description")
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
