"""MkDocs build hooks for the A2A Events docs site.

Two jobs, both done at build time so the source files stay correct for plain
GitHub browsing (where ``DESIGN.md`` lives at the repo root):

1. Render the root ``DESIGN.md`` as the in-site **Specification** page.
2. Rewrite the cross-references that only make sense relative to the repo root
   (``../DESIGN.md``, ``../schemas`` …) into links that resolve on the site.
"""

from __future__ import annotations

import re
from pathlib import Path

# Source of truth for the spec lives at the repo root, outside ``docs/``.
SPEC_SOURCE = "DESIGN.md"
SPEC_PAGE = "specification.md"

REPO_TREE = "https://github.com/a2a-events/a2a-events/tree/main"
REPO_EDIT = "https://github.com/a2a-events/a2a-events/edit/main"

# ``../DESIGN.md`` and ``../DESIGN.md#anchor`` -> the in-site Specification page.
_DESIGN_LINK = re.compile(r"\]\(\.\./DESIGN\.md(#[^)]*)?\)")


def on_page_read_source(page, config):  # noqa: D401 - MkDocs hook
    """Feed the root DESIGN.md into the Specification page."""
    if page.file.src_uri == SPEC_PAGE:
        spec = Path(config.docs_dir).parent / SPEC_SOURCE
        return spec.read_text(encoding="utf-8")
    return None


def on_page_markdown(markdown, page, config, files):  # noqa: D401 - MkDocs hook
    """Rewrite repo-root-relative links so they resolve on the site."""
    md = markdown
    src = page.file.src_uri

    if src == SPEC_PAGE:
        # DESIGN.md links are relative to the repo root; on the site this page
        # already lives inside docs/, so drop the leading ``docs/``.
        md = md.replace("](docs/a2a-reference.md)", "](a2a-reference.md)")
        md = md.replace("](docs/prior-art.md)", "](prior-art.md)")
        # Point "edit this page" at the real source of truth.
        page.edit_url = f"{REPO_EDIT}/{SPEC_SOURCE}"

    # Applies to every page (docs/*.md and the rendered spec).
    md = _DESIGN_LINK.sub(lambda m: f"]({SPEC_PAGE}{m.group(1) or ''})", md)
    md = md.replace("](../docs/a2a-reference.md)", "](a2a-reference.md)")
    md = md.replace("](../schemas)", f"]({REPO_TREE}/schemas)")
    md = md.replace("](../conformance)", f"]({REPO_TREE}/conformance)")

    return md
