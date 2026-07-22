"""Client-side i18n coverage, guarded without a JS runtime.

The SPA's strings live in web/js/i18n.js as two object literals (ru, uz). Two
things must hold, and neither is visible until a user opens the app in Uzbek:

  * every Russian key has an Uzbek one — a missing key makes t() fall back to
    Russian, a silent leak;
  * no Uzbek value contains Cyrillic, except a few deliberately bilingual labels.

This parses the file directly rather than importing it, so it runs in the normal
pytest sweep with no Node dependency.
"""

import re
from pathlib import Path

import pytest

I18N_JS = Path(__file__).resolve().parent.parent / "web" / "js" / "i18n.js"

CYRILLIC = re.compile("[А-Яа-яЁё]")

# Labels that name the languages themselves and are bilingual on purpose.
BILINGUAL = {"home.lang_switch"}  # "Til / Язык"


def _block(src: str, lang: str) -> str:
    """The text of the `<lang>: { ... }` object literal inside MESSAGES."""
    m = re.search(rf"\n  {lang}:\s*\{{", src)
    if not m:
        raise AssertionError(f"no {lang} block in i18n.js")
    start = src.index("{", m.start())
    depth = 0
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start : i + 1]
    raise AssertionError(f"unbalanced {lang} block in i18n.js")


def _keys(block: str) -> dict[str, str]:
    """Map of "key": "value" pairs (string values only — all of them are)."""
    out: dict[str, str] = {}
    for m in re.finditer(r'"([^"]+)":\s*("(?:[^"\\]|\\.)*")', block):
        out[m.group(1)] = m.group(2).encode().decode("unicode_escape")
    return out


@pytest.fixture(scope="module")
def blocks() -> tuple[dict[str, str], dict[str, str]]:
    src = I18N_JS.read_text(encoding="utf-8")
    return _keys(_block(src, "ru")), _keys(_block(src, "uz"))


def test_every_russian_key_has_an_uzbek_one(blocks):
    ru, uz = blocks
    missing = sorted(k for k in ru if k not in uz)
    assert not missing, f"uz keys missing (would render Russian): {missing}"


def test_no_uzbek_only_keys(blocks):
    """An uz key absent from ru is almost always a typo in the key name."""
    ru, uz = blocks
    extra = sorted(k for k in uz if k not in ru)
    assert not extra, f"uz-only keys (typo?): {extra}"


def test_no_cyrillic_leaks_in_uzbek(blocks):
    _, uz = blocks
    leaks = {k: v for k, v in uz.items() if k not in BILINGUAL and CYRILLIC.search(v)}
    assert not leaks, f"untranslated Cyrillic in uz strings: {leaks}"


def test_the_two_blocks_are_non_trivial(blocks):
    """Guard the parser itself: a regex that silently matched nothing would make
    every assertion above vacuously pass."""
    ru, uz = blocks
    assert len(ru) > 100
    assert len(uz) > 100
