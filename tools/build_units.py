#!/usr/bin/env python3
"""Render per-session HTML pages and per-course index pages from
``manifest.yaml``. Idempotent — re-running just rewrites the same
files.

Usage::

    python tools/build_units.py

Reads:
    manifest.yaml
    units/_template.html
    literacy_1/_template.html
    literacy_2/_template.html

Writes:
    units/litN-NN.html       (one per session, 16 total)
    literacy_1/index.html
    literacy_2/index.html
"""

from __future__ import annotations

import datetime as _dt
import html as _html
import sys
from pathlib import Path

import yaml  # ships with miniforge / available via `pip install pyyaml`

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_date(iso: str) -> str:
    """Return a friendly display date like 'March 4, 2019'."""
    try:
        dt = _dt.date.fromisoformat(iso)
    except ValueError:
        return iso
    return dt.strftime("%B %-d, %Y")


def _video_url(item: str, video_path: str) -> str:
    return f"https://archive.org/download/{item}/{video_path}"


def _esc(s: str) -> str:
    return _html.escape(s, quote=True)


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _write_if_changed(path: Path, content: str) -> bool:
    """Write ``content`` to ``path``, but only if it actually changed.
    Returns True when the file was rewritten. Keeps git diffs tidy when the
    builder is rerun without a real change."""
    if path.exists() and _read_text(path) == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Per-session unit page
# ---------------------------------------------------------------------------


def _render_unit(
    session: dict,
    *,
    course_no: int,
    course_dir: str,
    prev: dict | None,
    next_: dict | None,
    ia_item: str,
    template: str,
) -> str:
    title = session["title"] or f"Literacy {course_no}, session {session['session_no']}"
    blurb = (session.get("blurb") or "").strip()
    blurb_block = (
        f'<div class="notes"><p>{_esc(blurb)}</p></div>'
        if blurb else ""
    )

    if session.get("answers"):
        answers_btn = (
            f'<a class="dl-button secondary" '
            f'href="../{_esc(session["answers"])}" '
            f'target="_blank" rel="noopener">'
            f'✅ Answer key (PDF)'
            f'</a>'
        )
    else:
        answers_btn = ""

    if prev is not None:
        prev_link = (
            f'<a class="prev" href="../units/{prev["id"]}.html">'
            f'← Session {prev["session_no"]}: {_esc(prev["title"])}'
            f'</a>'
        )
    else:
        prev_link = '<span class="prev disabled">← First session</span>'

    if next_ is not None:
        next_link = (
            f'<a class="next" href="../units/{next_["id"]}.html">'
            f'Session {next_["session_no"]}: {_esc(next_["title"])} →'
            f'</a>'
        )
    else:
        next_link = '<span class="next disabled">Last session →</span>'

    subs = {
        "{{COURSE_NO}}": str(course_no),
        "{{COURSE_DIR}}": course_dir,
        "{{SESSION_NO}}": str(session["session_no"]),
        "{{TITLE_ESC}}": _esc(title),
        "{{DATE_DISPLAY}}": _format_date(session["date"]),
        "{{BLURB_BLOCK}}": blurb_block,
        "{{VIDEO_URL}}": _esc(_video_url(ia_item, session["video_path"])),
        "{{HANDOUT_PATH}}": _esc(session["handout"]),
        "{{ANSWERS_BUTTON}}": answers_btn,
        "{{PREV_LINK}}": prev_link,
        "{{NEXT_LINK}}": next_link,
    }
    out = template
    for k, v in subs.items():
        out = out.replace(k, v)
    return out


# ---------------------------------------------------------------------------
# Per-course index page
# ---------------------------------------------------------------------------


def _render_course_index(
    sessions: list[dict],
    *,
    course_no: int,
    course_title: str,
    course_subtitle: str,
    template: str,
) -> str:
    rows: list[str] = []
    for s in sessions:
        rows.append(
            '<li>'
            f'<span class="session-no">Session {s["session_no"]}</span>'
            f'<a class="session-title" href="../units/{s["id"]}.html">'
            f'{_esc(s["title"])}'
            '</a>'
            f'<span class="session-date">{_format_date(s["date"])}</span>'
            '</li>'
        )

    subs = {
        "{{COURSE_TITLE}}": _esc(course_title),
        "{{COURSE_LABEL}}": f"Literacy {course_no}",
        "{{COURSE_SUBTITLE}}": _esc(course_subtitle),
        "{{ROWS}}": "\n".join(rows),
    }
    out = template
    for k, v in subs.items():
        out = out.replace(k, v)
    return out


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main() -> int:
    if not MANIFEST.exists():
        print(f"ERROR: {MANIFEST} not found", file=sys.stderr)
        return 1
    data = yaml.safe_load(_read_text(MANIFEST))
    ia_item = data["ia_item"]

    course_meta = {
        1: {
            "title": "Witsuwit'en Literacy 1",
            "subtitle": "Writing system & orthography — March 2019",
            "dir": "literacy_1",
        },
        2: {
            "title": "Witsuwit'en Literacy 2",
            "subtitle": "Grammar fundamentals — November 2019 to January 2020",
            "dir": "literacy_2",
        },
    }

    unit_template = _read_text(ROOT / "units" / "_template.html")

    n_written = 0
    for course_no in (1, 2):
        sessions = data[f"literacy_{course_no}"]
        info = course_meta[course_no]

        # Per-session pages.
        for i, s in enumerate(sessions):
            prev = sessions[i - 1] if i > 0 else None
            next_ = sessions[i + 1] if i + 1 < len(sessions) else None
            html_out = _render_unit(
                s,
                course_no=course_no,
                course_dir=info["dir"],
                prev=prev,
                next_=next_,
                ia_item=ia_item,
                template=unit_template,
            )
            target = ROOT / "units" / f'{s["id"]}.html'
            if _write_if_changed(target, html_out):
                n_written += 1
                print(f"  wrote {target.relative_to(ROOT)}")

        # Per-course index page.
        idx_template = _read_text(ROOT / info["dir"] / "_template.html")
        idx_html = _render_course_index(
            sessions,
            course_no=course_no,
            course_title=info["title"],
            course_subtitle=info["subtitle"],
            template=idx_template,
        )
        target = ROOT / info["dir"] / "index.html"
        if _write_if_changed(target, idx_html):
            n_written += 1
            print(f"  wrote {target.relative_to(ROOT)}")

    print(f"\n{n_written} file(s) updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
