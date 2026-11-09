#!/usr/bin/env python3
"""Publish and take down throwaway pages on scratch.binaryloom.io.

Shares are private by default: they open only from a link carrying a secret key.
Only mac-mini deploys, because the live share folders and keys exist only there.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / "live.json"
# Private entries carry only key hashes; the middleware reads this file and hides it.
PRIVATE = ROOT / "private.json"
# Plain keys never enter the deployed tree.
KEYS = Path.home() / ".config" / "binaryloom-scratch" / "keys.json"
SITE_FILES = ("index.html", "404.html")
RESERVED = {"live.json", "private.json", "functions", "scratch.py", *SITE_FILES}
PROJECT = "binaryloom-scratch"
BASE_URL = "https://scratch.binaryloom.io"
FALLBACK_URL = "https://binaryloom-scratch.pages.dev"
PUBLISHER = "Jasons-Mac-mini"


def load_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        sys.exit(f"Error: {path.name} must be a JSON array.\n  python3 scratch.py list")
    return data


def save_list(path: Path, items: list[dict]) -> None:
    path.write_text(json.dumps(items, indent=2) + "\n")


def load_keys() -> dict[str, str]:
    return json.loads(KEYS.read_text()) if KEYS.exists() else {}


def save_keys(keys: dict[str, str]) -> None:
    KEYS.parent.mkdir(parents=True, exist_ok=True)
    KEYS.touch(mode=0o600, exist_ok=True)
    KEYS.chmod(0o600)
    KEYS.write_text(json.dumps(keys, indent=2) + "\n")


def key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def share_url(entry: dict, key: str | None = None, base: str = BASE_URL) -> str:
    url = f"{base}/{entry['slug']}/{entry.get('path', '')}"
    return f"{url}?k={key}" if key else url


def find(items: list[dict], slug: str) -> dict | None:
    return next((i for i in items if i.get("slug") == slug), None)


def clean_slug(raw: str) -> str:
    slug = raw.strip("/").strip()
    if not slug or "/" in slug or slug in RESERVED:
        sys.exit(
            "Error: slug must be a single path segment and not a site file.\n"
            "  python3 scratch.py up --slug character-graph --src ./doc.html --title 'Title'"
        )
    return slug


def copy_src(src: Path, dest: Path) -> str:
    """Replace dest with src and return the file path to link inside the share."""
    if dest.exists():
        shutil.rmtree(dest)
    if src.is_dir():
        if not (src / "index.html").exists():
            sys.exit(
                f"Error: {src} has no index.html.\n"
                "  python3 scratch.py up --slug NAME --src /path/to/dir-or-file"
            )
        shutil.copytree(src, dest)
        return ""
    dest.mkdir(parents=True)
    if src.suffix.lower() in {".html", ".htm"}:
        shutil.copy2(src, dest / "index.html")
        return ""
    shutil.copy2(src, dest / src.name)
    return src.name


def status(url: str) -> int:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    request = urllib.request.Request(url, headers={"user-agent": "scratch.py"})
    try:
        with urllib.request.build_opener(NoRedirect).open(
            request, timeout=20
        ) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def verify(checks: list[tuple[str, int]]) -> None:
    """Wait for each URL to answer with its expected status on both hostnames."""
    want = {
        url.replace(BASE_URL, base): code
        for url, code in checks
        for base in (BASE_URL, FALLBACK_URL)
    }
    got: dict[str, int] = {}
    pending = list(want)
    # A new deployment can take over a minute to reach every edge after a
    # large upload.
    for _ in range(36):
        got.update({url: status(url) for url in pending})
        pending = [url for url in pending if got[url] != want[url]]
        if not pending:
            break
        time.sleep(5)
    for url, code in want.items():
        shown = re.sub(r"k=[^&]+", "k=…", url)
        print(
            f"{'ok' if got[url] == code else 'FAIL'}\t{got[url]} (want {code})\t{shown}"
        )
    if pending:
        sys.exit(
            "Error: verification failed; the site does not match the local tree.\n  python3 scratch.py check --slug SLUG"
        )


def live_checks(slug: str) -> list[tuple[str, int]]:
    if entry := find(load_list(LIVE), slug):
        return [(share_url(entry), 200)]
    entry = find(load_list(PRIVATE), slug)
    key = load_keys().get(slug)
    if not entry or not key:
        return [(f"{BASE_URL}/{slug}/", 404)]
    return [(share_url(entry), 404), (share_url(entry, key), 302)]


def cmd_up(args: argparse.Namespace) -> None:
    slug = clean_slug(args.slug)
    src = Path(args.src).expanduser().resolve()
    if not src.exists():
        sys.exit(f"Error: source not found: {src}")
    public, private = load_list(LIVE), load_list(PRIVATE)
    dest = ROOT / slug
    access = "public" if args.public else "private (key link)"
    if args.dry_run:
        print(f"would replace {dest}/ with {src}")
        print(f"would list {slug} as {access}")
        return
    path = copy_src(src, dest)
    old = find(public, slug) or find(private, slug) or {}
    entry = {
        "slug": slug,
        "title": args.title or old.get("title") or slug,
        "note": args.note if args.note is not None else old.get("note", ""),
        "added": old.get("added") or date.today().isoformat(),
    }
    if path:
        entry["path"] = path
    public = [i for i in public if i.get("slug") != slug]
    private = [i for i in private if i.get("slug") != slug]
    keys = load_keys()
    if args.public:
        public.append(entry)
        keys.pop(slug, None)
        url = share_url(entry)
    else:
        # Re-publishing keeps the existing key so links already sent keep working.
        key = keys.get(slug) or secrets.token_urlsafe(24)
        keys[slug] = key
        private.append({**entry, "keyHash": key_hash(key)})
        url = share_url(entry, key)
    save_list(LIVE, public)
    save_list(PRIVATE, private)
    save_keys(keys)
    print(f"{'updated' if old else 'published'} {slug} ({access})")
    if args.deploy:
        cmd_deploy(args, live_checks(slug))
    print(f"url: {url}")


def cmd_down(args: argparse.Namespace) -> None:
    slug = clean_slug(args.slug)
    public, private = load_list(LIVE), load_list(PRIVATE)
    dest = ROOT / slug
    entry = find(public, slug) or find(private, slug)
    if not entry and not dest.exists():
        sys.exit(f"Error: {slug!r} is not live.\n  python3 scratch.py list")
    if args.dry_run:
        print(
            f"would remove {dest}/, its index entry and its key, then delete older deployments"
        )
        return
    keys = load_keys()
    old_key = keys.pop(slug, None)
    save_list(LIVE, [i for i in public if i.get("slug") != slug])
    save_list(PRIVATE, [i for i in private if i.get("slug") != slug])
    save_keys(keys)
    if dest.exists():
        shutil.rmtree(dest)
    print(f"taken down {slug}")
    if args.deploy:
        gone = entry or {"slug": slug}
        cmd_deploy(
            args,
            [
                (share_url(gone), 404),
                *([(share_url(gone, old_key), 404)] if old_key else []),
            ],
        )


def cmd_revoke(args: argparse.Namespace) -> None:
    slug = clean_slug(args.slug)
    private = load_list(PRIVATE)
    entry = find(private, slug)
    if not entry:
        sys.exit(f"Error: {slug!r} is not a private share.\n  python3 scratch.py list")
    if args.dry_run:
        print(f"would replace the key for {slug}, deploy, and delete older deployments")
        return
    keys = load_keys()
    old_key, key = keys.get(slug), secrets.token_urlsafe(24)
    keys[slug] = key
    entry["keyHash"] = key_hash(key)
    save_list(PRIVATE, private)
    save_keys(keys)
    print(f"new key for {slug}")
    cmd_deploy(
        args,
        [
            (share_url(entry), 404),
            (share_url(entry, key), 302),
            *([(share_url(entry, old_key), 404)] if old_key else []),
        ],
    )
    print(f"url: {share_url(entry, key)}")


def cmd_check(args: argparse.Namespace) -> None:
    verify(live_checks(clean_slug(args.slug)))


def cmd_list(_: argparse.Namespace) -> None:
    public, private = load_list(LIVE), load_list(PRIVATE)
    if not public and not private:
        print("0 live")
        return
    for access, items in (("public", public), ("private", private)):
        for item in items:
            print(
                f"{item.get('slug', '')}\t{access}\t{share_url(item)}\t{item.get('title', '')}"
            )


def cmd_link(args: argparse.Namespace) -> None:
    slug = args.slug.strip("/").strip()
    if entry := find(load_list(LIVE), slug):
        print(share_url(entry))
        return
    entry, key = find(load_list(PRIVATE), slug), load_keys().get(slug)
    if not entry or not key:
        sys.exit(
            f"Error: no private share or key for {slug!r}.\n  python3 scratch.py list"
        )
    print(share_url(entry, key))


def wrangler(
    *args: str, cwd: Path, capture: bool = False
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.setdefault("CLOUDFLARE_ACCOUNT_ID", "bb9c6e1c45f208657aed12579feb6e3b")
    # Wrangler OAuth lives in its config file. Do not copy that token into
    # CLOUDFLARE_API_TOKEN — expired or OAuth tokens there fail as API tokens.
    env.pop("CLOUDFLARE_API_TOKEN", None)
    cmd = ["npx", "--yes", "wrangler", "pages", *args, "--project-name", PROJECT]
    return subprocess.run(
        cmd, check=False, cwd=cwd, env=env, capture_output=capture, text=True
    )


def cmd_deploy(
    args: argparse.Namespace, checks: list[tuple[str, int]] | None = None
) -> None:
    """Deploy only the listed shares, verify, then delete every older deployment."""
    public, private = load_list(LIVE), load_list(PRIVATE)
    slugs = [i["slug"] for i in public + private]
    if args.dry_run:
        print(f"would deploy {len(slugs)} shares and delete older deployments")
        return
    if socket.gethostname().split(".")[0] != PUBLISHER:
        sys.exit(
            "Error: only mac-mini deploys scratch; its tree holds the live shares and keys.\n"
            "  scp -r SRC mac-mini:/tmp/scratch-SLUG && ssh mac-mini "
            "'python3 ~/repos/personal/binaryloom-scratch/scratch.py up --slug SLUG --src /tmp/scratch-SLUG --title TITLE'"
        )
    missing = [s for s in slugs if not (ROOT / s).is_dir()]
    if missing:
        sys.exit(
            f"Error: listed shares have no folder: {', '.join(missing)}\n  python3 scratch.py list"
        )
    with tempfile.TemporaryDirectory() as tmp:
        # Functions must sit beside the upload folder, not inside it. The
        # middleware imports ../private.json and ../live.json from there, so
        # private.json is never a static file.
        stage = Path(tmp)
        site = stage / "site"
        site.mkdir()
        shutil.copytree(ROOT / "functions", stage / "functions")
        (stage / "private.json").write_text(json.dumps(private))
        (stage / "live.json").write_text(json.dumps(public))
        for name in SITE_FILES:
            shutil.copy2(ROOT / name, site / name)
        shutil.copy2(LIVE, site / "live.json")
        for slug in slugs:
            shutil.copytree(ROOT / slug, site / slug)
        result = wrangler(
            "deploy",
            "site",
            "--branch",
            "main",
            "--commit-dirty=true",
            cwd=stage,
            capture=True,
        )
    print(result.stdout + result.stderr, end="")
    match = re.search(
        r"https://([0-9a-f]{8})\." + re.escape(PROJECT) + r"\.pages\.dev", result.stdout
    )
    if result.returncode != 0 or not match:
        sys.exit("Error: deploy failed; older deployments were left alone.")
    # Verify before pruning: deleting the deployment an edge still routes to
    # makes it answer with Cloudflare error 1101 until it switches over.
    verify(checks or [(f"{BASE_URL}/", 200)])
    # Every deployment keeps its own permanent URL, so older ones would still
    # serve taken-down shares and revoked keys.
    deleted = 0
    while True:
        # The listing returns one page of 25, so repeat until nothing old is left.
        listing = wrangler("deployment", "list", "--json", cwd=ROOT, capture=True)
        if listing.returncode != 0:
            sys.exit(f"Error: could not list deployments.\n{listing.stderr}")
        old = [
            d["Id"]
            for d in json.loads(listing.stdout)
            if not d["Id"].startswith(match[1])
        ]
        if not old:
            break
        for deployment in old:
            # Without --force wrangler asks for confirmation, and with no
            # terminal it answers no and still exits 0.
            wrangler(
                "deployment", "delete", deployment, "--force", cwd=ROOT, capture=True
            )
        still = [
            d["Id"]
            for d in json.loads(
                wrangler("deployment", "list", "--json", cwd=ROOT, capture=True).stdout
            )
        ]
        if any(d in still for d in old):
            sys.exit(
                f"Error: could not delete deployments: {', '.join(d for d in old if d in still)}\n"
                "  python3 scratch.py deploy"
            )
        deleted += len(old)
    print(f"deleted {deleted} older deployments")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scratch.py",
        description="Put a page up on scratch.binaryloom.io (private key link by default), or take it down.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser(
        "up", help="Copy a file or folder onto scratch, deploy, and verify"
    )
    up.add_argument("--slug", required=True, help="URL path, e.g. character-graph")
    up.add_argument(
        "--src", required=True, help="Any file, or a directory with index.html"
    )
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

    down = sub.add_parser(
        "down", help="Delete a share everywhere and verify it is gone"
    )
    down.add_argument("--slug", required=True)
    down.add_argument("--dry-run", action="store_true")
    down.add_argument("--no-deploy", action="store_true")
    down.set_defaults(func=cmd_down, deploy=True)

    revoke = sub.add_parser(
        "revoke", help="Replace a private share's key so old links stop working"
    )
    revoke.add_argument("--slug", required=True)
    revoke.add_argument("--dry-run", action="store_true")
    revoke.set_defaults(func=cmd_revoke)

    check = sub.add_parser(
        "check", help="Verify a share answers as the local tree says it should"
    )
    check.add_argument("--slug", required=True)
    check.set_defaults(func=cmd_check)

    listing = sub.add_parser("list", help="Print live slugs and URLs")
    listing.set_defaults(func=cmd_list)

    link = sub.add_parser("link", help="Print the share link, with its key if private")
    link.add_argument("--slug", required=True)
    link.set_defaults(func=cmd_link)

    deploy = sub.add_parser(
        "deploy", help="Deploy the listed shares and delete older deployments"
    )
    deploy.add_argument("--dry-run", action="store_true")
    deploy.set_defaults(func=cmd_deploy)

    return p


def main() -> None:
    args = build_parser().parse_args()
    if getattr(args, "no_deploy", False):
        args.deploy = False
    args.func(args)


if __name__ == "__main__":
    main()
