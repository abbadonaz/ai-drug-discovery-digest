"""URL policy for the parsed tree produced by Python-Markdown.

Raw HTML must still be escaped by the caller. This is a URL boundary, not a
general-purpose HTML sanitizer for arbitrary HTML or Markdown extensions.
"""

from html import unescape
import re
import unicodedata
from urllib.parse import unquote, urlsplit
from xml.etree.ElementTree import Element

from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


def _safe_url(value: str, *, image: bool = False) -> bool:
    # Inspect a fully decoded view, but preserve the original safe URL. Bound
    # repeated decoding and fail closed if nested encodings do not stabilize.
    decoded = value
    for _ in range(8):
        normalized = unescape(unquote(decoded, errors="strict"))
        if normalized == decoded:
            break
        decoded = normalized
    else:
        return False

    if not decoded or decoded != decoded.strip():
        return False
    if "\\" in decoded or any(unicodedata.category(char).startswith("C") for char in decoded):
        return False
    if decoded.startswith("//"):
        return False

    parsed = urlsplit(decoded)
    scheme = parsed.scheme.lower()
    if scheme in {"http", "https"}:
        # Require an absolute authority, rather than ambiguous forms like
        # https:example.org. Accessing port also validates malformed ports.
        _ = parsed.port
        return bool(parsed.hostname) and not any(char.isspace() for char in parsed.netloc)
    if scheme == "mailto" and not image:
        if parsed.netloc or parsed.fragment:
            return False
        # Support ordinary addresses and comma-separated recipients, with
        # optional query headers. Reject empty recipients and malformed addresses.
        return all(
            re.fullmatch(r"[^\s@/?#,:;<>]+@[^\s@/?#,:;<>]+", address)
            for address in parsed.path.split(",")
        )
    if scheme:
        return False

    # A colon in the first path segment may be an obfuscated/invalid scheme.
    # Colons in later segments, query strings and anchors are ordinary data.
    return not parsed.netloc and ":" not in parsed.path.split("/", 1)[0]


class _SafeURLTreeprocessor(Treeprocessor):
    def run(self, root: Element) -> Element:
        for element in root.iter():
            for attribute, value in list(element.attrib.items()):
                name = attribute.lower()
                # The enabled attr_list extension can introduce browser-active
                # attributes as well as override Markdown's href/src. Do not
                # permit alternate image sources, link pings, CSS URLs or script
                # handlers to bypass this URL boundary.
                if name in {"srcset", "ping", "style"} or name.startswith("on"):
                    del element.attrib[attribute]
                    continue
                if name not in {"href", "src"}:
                    continue
                try:
                    safe = _safe_url(value, image=name == "src")
                except (ValueError, UnicodeError):
                    safe = False
                if not safe:
                    del element.attrib[attribute]
        return root


class SafeURLExtension(Extension):
    def extendMarkdown(self, md):
        # Run after inline parsing, attribute lists, and Markdown unescaping so
        # reference links, autolinks, images and attribute overrides share policy.
        md.treeprocessors.register(_SafeURLTreeprocessor(md), "safe_urls", -10)
