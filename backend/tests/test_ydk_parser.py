"""Unit tests for the YDK file parser."""

import pytest
from app.services.ydk_parser import parse, ParsedYdk


# ── Fixtures ──────────────────────────────────────────────────────────────────

STANDARD_YDK = """\
#created by EDOPro
#main
89631139
89631139
89631139
14558127
14558127
#extra
38342335
84013237
#side
!side
43898403
"""

MINIMAL_YDK = """\
#main
12345678
#extra
#side
"""

EMPTY_YDK = """\
#main
#extra
#side
"""


# ── Basic parsing ─────────────────────────────────────────────────────────────

def test_parse_standard_deck():
    result = parse(STANDARD_YDK)
    assert result.main == [89631139, 89631139, 89631139, 14558127, 14558127]
    assert result.extra == [38342335, 84013237]
    assert result.side == [43898403]


def test_parse_minimal_deck():
    result = parse(MINIMAL_YDK)
    assert result.main == [12345678]
    assert result.extra == []
    assert result.side == []


def test_parse_empty_deck():
    result = parse(EMPTY_YDK)
    assert result.is_empty
    assert result.total == 0


# ── Section markers ───────────────────────────────────────────────────────────

def test_exclamation_side_marker():
    ydk = "#main\n11111111\n!side\n22222222\n"
    result = parse(ydk)
    assert result.main == [11111111]
    assert result.side == [22222222]


def test_hash_side_marker():
    ydk = "#main\n11111111\n#side\n22222222\n"
    result = parse(ydk)
    assert result.main == [11111111]
    assert result.side == [22222222]


def test_case_insensitive_markers():
    ydk = "#MAIN\n11111111\n#EXTRA\n22222222\n#SIDE\n33333333\n"
    result = parse(ydk)
    assert result.main == [11111111]
    assert result.extra == [22222222]
    assert result.side == [33333333]


# ── Comment handling ──────────────────────────────────────────────────────────

def test_comment_lines_skipped():
    ydk = "#created by some tool\n#main\n11111111\n# this is a comment\n22222222\n"
    result = parse(ydk)
    assert result.main == [11111111, 22222222]


def test_blank_lines_skipped():
    ydk = "#main\n\n11111111\n\n22222222\n\n"
    result = parse(ydk)
    assert result.main == [11111111, 22222222]


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_cards_before_any_section_ignored():
    ydk = "99999999\n#main\n11111111\n"
    result = parse(ydk)
    assert result.main == [11111111]
    assert 99999999 not in result.main


def test_zero_ids_skipped():
    ydk = "#main\n0\n11111111\n"
    result = parse(ydk)
    assert result.main == [11111111]


def test_negative_ids_skipped():
    ydk = "#main\n-1\n11111111\n"
    result = parse(ydk)
    assert result.main == [11111111]


def test_duplicate_ids_preserved():
    """Same card 3x should produce 3 entries (quantities are counted upstream)."""
    ydk = "#main\n11111111\n11111111\n11111111\n"
    result = parse(ydk)
    assert result.main == [11111111, 11111111, 11111111]


def test_empty_string():
    result = parse("")
    assert result.is_empty


def test_total_count():
    result = parse(STANDARD_YDK)
    assert result.total == 8   # 5 main + 2 extra + 1 side


def test_crlf_line_endings():
    ydk = "#main\r\n11111111\r\n22222222\r\n"
    result = parse(ydk)
    assert result.main == [11111111, 22222222]


def test_whitespace_around_ids():
    ydk = "#main\n  11111111  \n22222222\n"
    result = parse(ydk)
    assert result.main == [11111111, 22222222]


def test_large_realistic_deck():
    ids = list(range(10000000, 10000040))   # 40 unique IDs
    ydk = "#main\n" + "\n".join(str(i) for i in ids) + "\n#extra\n#side\n"
    result = parse(ydk)
    assert result.main == ids
    assert not result.is_empty
