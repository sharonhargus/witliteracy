#!/usr/bin/env python3
"""Upload the 16 lecture videos to a single Internet Archive item.

The source MP4 filenames in /Users/jingnongqu/Desktop/sharon/wit_literacy/
are inconsistent (mix of `_Wit_literacy_class`, `_wit_literacy_class`,
`_recorded class`, `_wit_lit2_N`). This script maps each source filename
to the canonical remote path that `manifest.yaml` expects, so the videos
land at predictable URLs without renaming local files.

Usage::

    python tools/upload_to_ia.py            # do the upload
    python tools/upload_to_ia.py --dry-run  # show the plan only

Requires the `internetarchive` Python package + a configured `ia.ini`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

import yaml
from internetarchive import upload, get_item

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.yaml"

# Where the source MP4s live on disk. Keep this as the single source of
# truth so re-uploads are reproducible.
SOURCE_ROOT = Path("/Users/jingnongqu/Desktop/sharon/wit_literacy")
LIT1_DIR = SOURCE_ROOT / "Witsuwit_en_literacy_1"
LIT2_DIR = SOURCE_ROOT / "Witsuwit_en_literacy_2"


def _find_lit1_mp4(date: str) -> Path:
    """Find the lecture MP4 for a given Literacy 1 session date.

    Tries the four naming variants seen in the source folder. Returns the
    first one that exists; raises FileNotFoundError if nothing matches.
    """
    candidates = [
        f"{date}_Wit_literacy_class.mp4",
        f"{date}_wit_literacy_class.mp4",
        f"{date}_recorded class.mp4",
        f"{date}_recorded_class.mp4",
    ]
    for name in candidates:
        p = LIT1_DIR / name
        if p.exists():
            return p
    # Last-ditch fuzzy: match any file with the date prefix.
    matches = sorted(LIT1_DIR.glob(f"{date}_*.mp4"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"No MP4 for Literacy 1 session dated {date} in {LIT1_DIR}")


def _find_lit2_mp4(date: str, session_no: int) -> Path:
    """Find the lecture MP4 for a Literacy 2 session by date + session number."""
    p = LIT2_DIR / f"{date}_wit_lit2_{session_no}.mp4"
    if p.exists():
        return p
    matches = sorted(LIT2_DIR.glob(f"{date}_*lit2_{session_no}.mp4"))
    if matches:
        return matches[0]
    raise FileNotFoundError(
        f"No MP4 for Literacy 2 session {session_no} dated {date} in {LIT2_DIR}"
    )


def _load_manifest() -> dict:
    with open(MANIFEST, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _date_to_dashed(iso_date: str) -> str:
    """Convert manifest's ISO date back to the m-d-yy form used in source filenames.

    e.g. ``"2019-03-04"`` -> ``"3-4-19"``; ``"2020-01-02"`` -> ``"1-2-20"``.
    """
    y, m, d = iso_date.split("-")
    yy = y[-2:]
    return f"{int(m)}-{int(d)}-{yy}"


def _build_plan(manifest: dict) -> list[tuple[Path, str]]:
    """Return a list of (local_path, remote_path) pairs."""
    plan: list[tuple[Path, str]] = []

    for s in manifest["literacy_1"]:
        date = _date_to_dashed(s["date"])
        plan.append((_find_lit1_mp4(date), s["video_path"]))

    for s in manifest["literacy_2"]:
        date = _date_to_dashed(s["date"])
        plan.append((_find_lit2_mp4(date, s["session_no"]), s["video_path"]))

    return plan


def _file_size_mb(p: Path) -> float:
    return p.stat().st_size / (1024 * 1024)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the upload plan without uploading.")
    parser.add_argument("--item",
                        help="Override the manifest's ia_item value.")
    args = parser.parse_args()

    manifest = _load_manifest()
    item_id = args.item or manifest["ia_item"]
    plan = _build_plan(manifest)

    print(f"IA item       : {item_id}")
    print(f"Total files   : {len(plan)}")
    total_mb = sum(_file_size_mb(p) for p, _ in plan)
    print(f"Total size    : {total_mb / 1024:.2f} GB ({total_mb:,.0f} MB)")
    print()
    print(f"{'Source file':70s}  →  Remote path")
    print("-" * 110)
    for local, remote in plan:
        print(f"{str(local.relative_to(SOURCE_ROOT)):70s}  →  {remote}")
    print()

    if args.dry_run:
        print("(dry-run; not uploading)")
        return 0

    metadata = {
        "title": "Witsuwit'en Literacy",
        "creator": "Sharon Hargus",
        "subject": ["Witsuwit'en", "language", "literacy", "Athabaskan"],
        "mediatype": "movies",
        "description": (
            "Lecture recordings from Sharon Hargus's two-volume Witsuwit'en "
            "literacy course taught in 2019–2020. Volume 1 covers the "
            "writing system and orthography; volume 2 covers grammar "
            "fundamentals (possessive prefixes, subject prefixes, areal "
            "marking, etc.). Worksheets and answer keys are at "
            "https://sharonhargus.github.io/witliteracy/"
        ),
        "language": "Witsuwit'en; eng",
        "rights": (
            "All rights reserved. Materials are publicly viewable for "
            "educational use. For reuse or redistribution please contact "
            "the author."
        ),
    }

    # Build {remote_path: local_path} for a single upload() call. This
    # keeps it to one item-create + one set of HTTP sessions.
    files = {remote: str(local) for local, remote in plan}

    print("Uploading… (this is a 2.4 GB transfer; can take 20–60+ minutes)")
    try:
        responses = upload(
            item_id,
            files=files,
            metadata=metadata,
            verbose=True,
            retries=5,
            queue_derive=True,
        )
    except Exception as exc:
        print(f"\nERROR: upload failed: {exc}", file=sys.stderr)
        return 1

    # Post-upload sanity check. ``item.files`` is a list of dicts in
    # current internetarchive versions, not File objects.
    item = get_item(item_id)
    have = {(f.get("name") if isinstance(f, dict) else getattr(f, "name", ""))
            for f in item.files}
    expected = set(files.keys())
    missing = expected - have
    if missing:
        print(f"\nWARN: {len(missing)} file(s) didn't show up on IA yet:")
        for m in sorted(missing):
            print(f"  - {m}")
        print("(IA's derive pipeline can lag a few minutes; rerun this script "
              "with --dry-run later to compare.)")
    else:
        print(f"\nSuccess. All {len(expected)} files present on IA item {item_id}.")
        print(f"Browse: https://archive.org/details/{item_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
