#!/usr/bin/env python3
"""Fail if a built site fetches any subresource from an origin other than its own.

devsheet vendors KaTeX, Fuse.js and its webfonts so a published site talks to
nobody but the host serving it: no CDN outage can break it, no CDN compromise can
alter it, and no visitor IP leaks to a third party. That property is invisible in
review and easy to undo with one convenient <script src>, so it is asserted here.

HTML is parsed with html.parser rather than matched with regexes. Two earlier
regex versions of this script shipped with holes: an attribute value was attributed
to the wrong tag, so a fetching <link> immediately after a <link rel=canonical>
inherited the canonical's exemption — which is exactly where this theme emits its
font preloads. A parser knows which attribute belongs to which tag.

Only real fetches count. URLs inside <code>/<pre>, and in <a href>, are prose on a
developer blog, not requests.

Usage: check-no-external.py <build-dir> <baseURL>
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

# Attribute values the browser fetches.
FETCH_ATTRS = {"src", "data", "poster", "background", "formaction"}
SRCSET_ATTRS = {"srcset", "imagesrcset"}

# rel tokens that merely declare a relationship. FETCHING_REL wins, because
# "alternate stylesheet" does fetch.
DECLARATIVE_REL = {"canonical", "alternate", "me", "author", "prev", "next",
                   "bookmark", "license", "nofollow", "noopener", "noreferrer"}
FETCHING_REL = {"stylesheet", "preload", "prefetch", "preconnect", "dns-prefetch",
                "icon", "shortcut", "apple-touch-icon", "manifest",
                "modulepreload", "prerender"}

SKIP_TEXT_IN = {"code", "pre", "samp", "kbd"}

CSS_URL = re.compile(r"""(?:url\(\s*|@import\s+|image-set\(\s*)['"]?([^'")\s]+)""", re.I)
# setAttribute and open are narrowed to the argument shapes that actually fetch.
# A bare ".setAttribute(name, value)" match also swept up XML namespace URIs such
# as the MathML namespace KaTeX sets, which is declarative, not a request.
JS_URL = re.compile(
    r"""(?:\bfetch|\bimportScripts|\bnew\s+(?:Worker|SharedWorker|EventSource|WebSocket)"""
    r"""|\bnavigator\.sendBeacon)\s*\(\s*['"`]([^'"`]+)"""
    r"""|\.open\s*\(\s*['"`](?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)['"`]\s*,\s*['"`]([^'"`]+)"""
    r"""|\.setAttribute\s*\(\s*['"`](?:src|href|data|poster|srcset|imagesrcset)['"`]\s*,\s*['"`]([^'"`]+)""",
    re.I)

# Namespace URIs name a vocabulary; nothing is fetched.
NAMESPACE_HOSTS = {"www.w3.org", "w3.org", "www.sitemaps.org", "purl.org",
                   "schema.org", "gmpg.org", "ogp.me"}
JS_IMPORT = re.compile(r"""\b(?:import|from)\s*\(?\s*['"`]([^'"`]+)""", re.I)

SCANNED_SUFFIXES = (".html", ".htm", ".css", ".js", ".xml", ".svg", ".webmanifest")


def origin(url: str, fallback_scheme: str = "https"):
    """(scheme, host, port), or None for a relative URL. Port is significant."""
    url = url.strip()
    if url.startswith("//"):
        url = fallback_scheme + ":" + url
    try:
        p = urlparse(url)
    except ValueError:
        return None
    if not p.hostname:
        return None
    try:
        port = p.port
    except ValueError:
        port = None
    port = port or (443 if p.scheme == "https" else 80 if p.scheme == "http" else None)
    return (p.scheme or fallback_scheme, p.hostname, port)


def first_group(m):
    return next(g for g in m.groups() if g is not None)


def srcset_urls(value: str):
    for candidate in value.split(","):
        parts = candidate.strip().split()
        if parts:
            yield parts[0]


class FetchFinder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found = []
        self._inline = None

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self._inline = tag

        a = {k.lower(): (v or "") for k, v in attrs}

        for m in CSS_URL.finditer(a.get("style", "")):
            self.found.append(m.group(1))

        for name in FETCH_ATTRS:
            if name in a:
                self.found.append(a[name])
        for name in SRCSET_ATTRS:
            if name in a:
                self.found.extend(srcset_urls(a[name]))

        if "href" in a:
            if tag == "a":
                pass                                  # navigation, not a fetch
            elif tag == "link":
                tokens = {t.lower() for t in a.get("rel", "").split()}
                if tokens & FETCHING_REL or not (tokens & DECLARATIVE_REL):
                    self.found.append(a["href"])
            else:
                self.found.append(a["href"])          # <use href>, <image href>

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self._inline = None

    def handle_data(self, data):
        if self._inline == "style":
            self.found.extend(m.group(1) for m in CSS_URL.finditer(data))
        elif self._inline == "script":
            self.found.extend(first_group(m) for m in JS_URL.finditer(data))
            self.found.extend(m.group(1) for m in JS_IMPORT.finditer(data))


def urls_in(path: Path, text: str):
    suffix = path.suffix.lower()
    if suffix in (".html", ".htm", ".xml", ".svg", ".webmanifest"):
        parser = FetchFinder()
        try:
            parser.feed(text)
        except Exception:
            pass
        return parser.found
    if suffix == ".css":
        return [m.group(1) for m in CSS_URL.finditer(text)]
    if suffix == ".js":
        return ([first_group(m) for m in JS_URL.finditer(text)] +
                [m.group(1) for m in JS_IMPORT.finditer(text)])
    return []


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check-no-external.py <build-dir> <baseURL>", file=sys.stderr)
        return 2

    build_dir, base_url = Path(sys.argv[1]), sys.argv[2]
    if not build_dir.is_dir():
        print(f"::error::build directory does not exist: {build_dir}", file=sys.stderr)
        return 2

    own = origin(base_url)
    scheme = urlparse(base_url).scheme or "https"

    files = sorted(f for f in build_dir.rglob("*")
                   if f.is_file() and f.suffix.lower() in SCANNED_SUFFIXES)
    if not files:
        print(f"::error::no scannable files under {build_dir} — did the build run?",
              file=sys.stderr)
        return 2

    offenders = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for raw in urls_in(f, text):
            o = origin(raw, scheme)
            if o is None or o == own or o[1] in NAMESPACE_HOSTS:
                continue
            offenders.append(f"{f.relative_to(build_dir)}: {raw[:100]}")

    if offenders:
        print(f"::error::{len(offenders)} external subresource(s) in the build:")
        for line in sorted(set(offenders)):
            print(f"  {line}")
        print("\nVendor the asset under assets/ or static/ and record it in THIRD-PARTY.md.")
        return 1

    print(f"no external subresources across {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
