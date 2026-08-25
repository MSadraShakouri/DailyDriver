#!/usr/bin/env python3
"""Check all internal links in the built Starlight docs site (docs-site/dist).

Resolves every <a href> in the generated HTML against the site base
(/DailyDriver/) and verifies:
  * the target page file exists in dist, and
  * if there is an #anchor, the id exists in the target page.

External (http/https) links are reported but not fetched.
"""
import re
import sys
import html
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

DIST = Path(__file__).resolve().parent.parent / "docs-site" / "dist"
# fallback to old docs/dist for backwards compat
if not DIST.exists():
    DIST = Path(__file__).resolve().parent.parent / "docs" / "dist"
SITE = "https://msadrashakouri.ir"
BASE = "/DailyDriver"

A_RE = re.compile(r"<a\s+[^>]*href=\"([^\"]*)\"[^>]*>", re.I)
ID_RE = re.compile(r"\bid=\"([^\"]+)\"", re.I)

def main() -> int:
    pages = [p for p in DIST.rglob("*.html") if "pagefind" not in p.parts]
    broken, ok, external = [], 0, 0
    seen = set()

    for page in sorted(pages):
        # Real browser URL of the page: a directory URL with trailing slash.
        rel = page.relative_to(DIST)
        dir_path = rel.parent.as_posix()
        url = SITE + BASE + "/" + (dir_path + "/" if dir_path != "." else "")
        page_ids = set(ID_RE.findall(page.read_text(encoding="utf-8")))
        for href in A_RE.findall(page.read_text(encoding="utf-8")):
            href = html.unescape(href)
            if href in seen:
                continue
            seen.add(href)
            if href.startswith("http") or href.startswith(("mailto:", "tel:")):
                external += 1
                continue
            if href.startswith(("#", "javascript:")):
                target_url, frag = url, href.lstrip("#")
                target_file = page
            else:
                target_url = urljoin(url, href)
                p = urlparse(target_url)
                frag = p.fragment
                path = unquote(p.path)
                if not path.startswith(BASE):
                    # root-relative link that ignored the base path
                    broken.append(f"{page.name}: base-relative {href}")
                    continue
                rel = path[len(BASE):].lstrip("/")
                if not rel or rel.endswith("/"):
                    target_file = DIST / rel / "index.html"
                else:
                    target_file = DIST / rel
            src = page.relative_to(DIST).parent.as_posix() or "/"
            if not target_file.exists():
                broken.append(f"{src}: {href} -> {target_file.relative_to(DIST)}")
                continue
            if frag:
                ids = set(ID_RE.findall(target_file.read_text(encoding="utf-8")))
                if frag not in ids:
                    broken.append(f"{src}: {href} (missing #anchor '{frag}')")
                    continue
            ok += 1

    print(f"checked {len(pages)} pages | ok={ok} broken={len(broken)} external={external}")
    for b in broken:
        print(f"  BROKEN: {b}")
    return 1 if broken else 0

if __name__ == "__main__":
    sys.exit(main())
