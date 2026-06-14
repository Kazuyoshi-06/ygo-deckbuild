"""Unit tests for the EdoPro CDB binary flag decoder."""

import pytest
from app.services.cdb_decoder import (
    decode_type_string,
    decode_frame_type,
    decode_level,
    decode_race,
    decode_attribute,
)
from app.services.card_cdb_service import _is_valid_ot

# ── Type flag constants (mirror cdb_decoder) ──────────────────────────────────
T_MONSTER  = 0x1
T_SPELL    = 0x2
T_TRAP     = 0x4
T_NORMAL   = 0x10
T_EFFECT   = 0x20
T_FUSION   = 0x40
T_RITUAL   = 0x80
T_TUNER    = 0x1000
T_SYNCHRO  = 0x2000
T_TOKEN    = 0x4000
T_XYZ      = 0x20000
T_PENDULUM = 0x40000
T_LINK     = 0x400000


# ── Frame type ────────────────────────────────────────────────────────────────

def test_frame_spell():
    assert decode_frame_type(T_SPELL) == "spell"

def test_frame_trap():
    assert decode_frame_type(T_TRAP) == "trap"

def test_frame_normal_monster():
    assert decode_frame_type(T_MONSTER | T_NORMAL) == "normal"

def test_frame_effect_monster():
    assert decode_frame_type(T_MONSTER | T_EFFECT) == "effect"

def test_frame_ritual():
    assert decode_frame_type(T_MONSTER | T_RITUAL) == "ritual"

def test_frame_fusion():
    assert decode_frame_type(T_MONSTER | T_FUSION) == "fusion"

def test_frame_synchro():
    assert decode_frame_type(T_MONSTER | T_SYNCHRO) == "synchro"

def test_frame_xyz():
    assert decode_frame_type(T_MONSTER | T_XYZ) == "xyz"

def test_frame_link():
    assert decode_frame_type(T_MONSTER | T_EFFECT | T_LINK) == "link"

def test_frame_token():
    assert decode_frame_type(T_MONSTER | T_NORMAL | T_TOKEN) == "token"

def test_frame_xyz_pendulum():
    assert decode_frame_type(T_MONSTER | T_EFFECT | T_XYZ | T_PENDULUM) == "xyz_pendulum"

def test_frame_synchro_pendulum():
    assert decode_frame_type(T_MONSTER | T_EFFECT | T_SYNCHRO | T_PENDULUM) == "synchro_pendulum"

def test_frame_fusion_pendulum():
    assert decode_frame_type(T_MONSTER | T_EFFECT | T_FUSION | T_PENDULUM) == "fusion_pendulum"

def test_frame_effect_pendulum():
    assert decode_frame_type(T_MONSTER | T_EFFECT | T_PENDULUM) == "effect_pendulum"

def test_frame_normal_pendulum():
    assert decode_frame_type(T_MONSTER | T_NORMAL | T_PENDULUM) == "normal_pendulum"


# ── Type string ───────────────────────────────────────────────────────────────

def test_type_effect_monster():
    assert decode_type_string(T_MONSTER | T_EFFECT, 0) == "Effect Monster"

def test_type_normal_monster():
    assert decode_type_string(T_MONSTER | T_NORMAL, 0) == "Normal Monster"

def test_type_spell_normal():
    assert decode_type_string(T_SPELL, 0) == "Spell Card"

def test_type_spell_quickplay():
    assert decode_type_string(T_SPELL, 2) == "Quick-Play Spell Card"

def test_type_spell_continuous():
    assert decode_type_string(T_SPELL, 4) == "Continuous Spell Card"

def test_type_spell_equip():
    assert decode_type_string(T_SPELL, 8) == "Equip Spell Card"

def test_type_spell_field():
    assert decode_type_string(T_SPELL, 16) == "Field Spell Card"

def test_type_spell_ritual():
    assert decode_type_string(T_SPELL, 1) == "Ritual Spell Card"

def test_type_trap_normal():
    assert decode_type_string(T_TRAP, 0) == "Trap Card"

def test_type_trap_counter():
    assert decode_type_string(T_TRAP, 1) == "Counter Trap Card"

def test_type_trap_continuous():
    assert decode_type_string(T_TRAP, 2) == "Continuous Trap Card"

def test_type_tuner():
    t = T_MONSTER | T_EFFECT | T_TUNER
    result = decode_type_string(t, 0)
    assert "Tuner" in result

def test_type_synchro():
    t = T_MONSTER | T_SYNCHRO
    result = decode_type_string(t, 0)
    assert "Synchro" in result

def test_type_xyz():
    t = T_MONSTER | T_XYZ
    result = decode_type_string(t, 0)
    assert "XYZ" in result

def test_type_link():
    t = T_MONSTER | T_EFFECT | T_LINK
    assert decode_type_string(t, 0) == "Link Monster"

def test_type_token():
    t = T_MONSTER | T_NORMAL | T_TOKEN
    assert decode_type_string(t, 0) == "Token"


# ── Attribute decode ──────────────────────────────────────────────────────────

def test_attribute_dark():
    assert decode_attribute(0x20) == "DARK"

def test_attribute_light():
    assert decode_attribute(0x10) == "LIGHT"

def test_attribute_fire():
    assert decode_attribute(0x04) == "FIRE"

def test_attribute_water():
    assert decode_attribute(0x02) == "WATER"

def test_attribute_earth():
    assert decode_attribute(0x01) == "EARTH"

def test_attribute_wind():
    assert decode_attribute(0x08) == "WIND"

def test_attribute_divine():
    assert decode_attribute(0x40) == "DIVINE"

def test_attribute_none():
    assert decode_attribute(0) is None


# ── Race decode ───────────────────────────────────────────────────────────────

def test_race_dragon():
    assert decode_race(T_MONSTER | T_NORMAL, 0x2000) == "Dragon"

def test_race_spellcaster():
    assert decode_race(T_MONSTER | T_EFFECT, 0x2) == "Spellcaster"

def test_race_spell_returns_none():
    assert decode_race(T_SPELL, 0) is None

def test_race_trap_returns_none():
    assert decode_race(T_TRAP, 0) is None


# ── Level decode ──────────────────────────────────────────────────────────────

def test_level_normal():
    lv, sl, sr = decode_level(4)
    assert lv == 4
    assert sl is None
    assert sr is None

def test_level_with_scales():
    # level 8, left scale 4, right scale 4
    raw = (4 << 28) | (4 << 24) | 8
    lv, sl, sr = decode_level(raw)
    assert lv == 8
    assert sl == 4
    assert sr == 4

def test_level_zero():
    lv, sl, sr = decode_level(0)
    assert lv == 0
    assert sl is None
    assert sr is None

def test_level_link_rating():
    lv, _, _ = decode_level(5)
    assert lv == 5


# ── OT validation ─────────────────────────────────────────────────────────────

def test_valid_ot_ocg():
    assert _is_valid_ot(1) is True

def test_valid_ot_tcg():
    assert _is_valid_ot(2) is True

def test_valid_ot_both():
    assert _is_valid_ot(3) is True

def test_valid_ot_prerelease_ocg():
    assert _is_valid_ot(0x101) is True

def test_valid_ot_prerelease_tcg():
    assert _is_valid_ot(0x102) is True

def test_invalid_ot_anime():
    assert _is_valid_ot(4) is False

def test_invalid_ot_rush_duel():
    assert _is_valid_ot(8) is False

def test_invalid_ot_rush_prerelease():
    assert _is_valid_ot(0x108) is False
