"""
Decode YGOPRO/EdoPro cards.cdb binary fields into human-readable strings.

CDB format (SQLite):
  datas(id, ot, alias, setcode, type, atk, def, level, race, attribute, category)
  texts(id, name, desc, str1..str16)
"""

# ── Type flags ────────────────────────────────────────────────────────────────
T_MONSTER     = 0x1
T_SPELL       = 0x2
T_TRAP        = 0x4
T_NORMAL      = 0x10
T_EFFECT      = 0x20
T_FUSION      = 0x40
T_RITUAL      = 0x80
T_TPMONSTER   = 0x100    # Trap monster
T_SPIRIT      = 0x200
T_UNION       = 0x400
T_DUAL        = 0x800    # Gemini
T_TUNER       = 0x1000
T_SYNCHRO     = 0x2000
T_TOKEN       = 0x4000
T_XYZ         = 0x20000
T_PENDULUM    = 0x40000
T_FLIP        = 0x100000
T_TOON        = 0x200000
T_LINK        = 0x400000

# ── OT (origin) flags ─────────────────────────────────────────────────────────
OT_OCG        = 0x1
OT_TCG        = 0x2
OT_ANIME      = 0x4   # unofficial, skip
OT_RUSH       = 0x8   # Rush Duel, skip
OT_PRERELEASE = 0x100 # EdoPro pre-release flag (added on top of OCG/TCG bits)
# Valid combinations: OCG, TCG, both, and their pre-release variants
VALID_OT      = {0x1, 0x2, 0x3, 0x101, 0x102, 0x103}

# ── Attribute map ─────────────────────────────────────────────────────────────
_ATTR = {
    0x01: "EARTH", 0x02: "WATER", 0x04: "FIRE",
    0x08: "WIND",  0x10: "LIGHT", 0x20: "DARK",
    0x40: "DIVINE",
}

# ── Monster race map ──────────────────────────────────────────────────────────
_RACE = {
    0x1:       "Warrior",      0x2:       "Spellcaster", 0x4:       "Fairy",
    0x8:       "Fiend",        0x10:      "Zombie",       0x20:      "Machine",
    0x40:      "Aqua",         0x80:      "Pyro",         0x100:     "Rock",
    0x200:     "Winged Beast", 0x400:     "Plant",        0x800:     "Insect",
    0x1000:    "Thunder",      0x2000:    "Dragon",       0x4000:    "Beast",
    0x8000:    "Beast-Warrior",0x10000:   "Dinosaur",     0x20000:   "Fish",
    0x40000:   "Sea Serpent",  0x80000:   "Reptile",      0x100000:  "Psychic",
    0x200000:  "Divine-Beast", 0x400000:  "Creator God",  0x800000:  "Wyrm",
    0x1000000: "Cyberse",      0x2000000: "Illusion",
}

# ── Spell subtype (race column for Spell cards) ───────────────────────────────
_SPELL_RACE = {
    0:  "",             # Normal Spell Card
    1:  "Ritual ",
    2:  "Quick-Play ",
    4:  "Continuous ",
    8:  "Equip ",
    16: "Field ",
}

# ── Trap subtype ──────────────────────────────────────────────────────────────
_TRAP_RACE = {
    0: "",              # Normal Trap Card
    1: "Counter ",
    2: "Continuous ",
}


def decode_attribute(raw: int) -> str | None:
    return _ATTR.get(raw)


def decode_race(cdb_type: int, cdb_race: int) -> str | None:
    """Return the monster race string, or None for spells/traps."""
    if cdb_type & T_MONSTER:
        return _RACE.get(cdb_race)
    return None


def decode_type_string(cdb_type: int, cdb_race: int) -> str:
    """Human-readable card type (e.g. 'Effect Monster', 'Quick-Play Spell Card')."""
    if cdb_type & T_SPELL:
        prefix = _SPELL_RACE.get(cdb_race, "")
        return f"{prefix}Spell Card"

    if cdb_type & T_TRAP:
        prefix = _TRAP_RACE.get(cdb_race, "")
        return f"{prefix}Trap Card"

    # Monster — build qualifier list
    qualifiers: list[str] = []
    if cdb_type & T_FLIP:    qualifiers.append("Flip")
    if cdb_type & T_TOON:    qualifiers.append("Toon")
    if cdb_type & T_SPIRIT:  qualifiers.append("Spirit")
    if cdb_type & T_UNION:   qualifiers.append("Union")
    if cdb_type & T_DUAL:    qualifiers.append("Gemini")
    if cdb_type & T_TUNER:   qualifiers.append("Tuner")

    if cdb_type & T_TOKEN:   return "Token"
    if cdb_type & T_LINK:    return _join(qualifiers, "Link Monster")
    if cdb_type & T_XYZ:
        if cdb_type & T_PENDULUM: return _join(qualifiers, "XYZ Pendulum Effect Monster")
        return _join(qualifiers, "XYZ Monster")
    if cdb_type & T_SYNCHRO:
        if cdb_type & T_PENDULUM: return _join(qualifiers, "Synchro Pendulum Effect Monster")
        if cdb_type & T_NORMAL:   return _join(qualifiers, "Synchro Monster")
        return _join(qualifiers, "Synchro Effect Monster")
    if cdb_type & T_FUSION:
        if cdb_type & T_PENDULUM: return _join(qualifiers, "Fusion Pendulum Effect Monster")
        if cdb_type & T_NORMAL:   return _join(qualifiers, "Fusion Monster")
        return _join(qualifiers, "Fusion Effect Monster")
    if cdb_type & T_RITUAL:
        if cdb_type & T_PENDULUM: return _join(qualifiers, "Ritual Pendulum Effect Monster")
        if cdb_type & T_EFFECT:   return _join(qualifiers, "Ritual Effect Monster")
        return _join(qualifiers, "Ritual Monster")
    if cdb_type & T_PENDULUM:
        if cdb_type & T_NORMAL: return _join(qualifiers, "Normal Pendulum Monster")
        return _join(qualifiers, "Pendulum Effect Monster")
    if cdb_type & T_NORMAL:  return _join(qualifiers, "Normal Monster")
    if cdb_type & T_EFFECT:  return _join(qualifiers, "Effect Monster")
    return _join(qualifiers, "Monster")


def decode_frame_type(cdb_type: int) -> str:
    """YGOProDeck-compatible frame_type string."""
    if cdb_type & T_SPELL:  return "spell"
    if cdb_type & T_TRAP:   return "trap"
    if cdb_type & T_TOKEN:  return "token"
    if cdb_type & T_LINK:   return "link"
    if cdb_type & T_XYZ:
        return "xyz_pendulum" if (cdb_type & T_PENDULUM) else "xyz"
    if cdb_type & T_SYNCHRO:
        return "synchro_pendulum" if (cdb_type & T_PENDULUM) else "synchro"
    if cdb_type & T_FUSION:
        return "fusion_pendulum" if (cdb_type & T_PENDULUM) else "fusion"
    if cdb_type & T_RITUAL:
        return "ritual_pendulum" if (cdb_type & T_PENDULUM) else "ritual"
    if cdb_type & T_PENDULUM:
        return "normal_pendulum" if (cdb_type & T_NORMAL) else "effect_pendulum"
    if cdb_type & T_NORMAL:  return "normal"
    return "effect"


def decode_level(cdb_level: int) -> tuple[int, int | None, int | None]:
    """
    Returns (level_or_rank_or_link, scale_left, scale_right).
    Bits 0-7: level/rank/link value.
    Bits 24-27: left pendulum scale.
    Bits 28-31: right pendulum scale.
    """
    level = cdb_level & 0xFF
    scale_l_raw = (cdb_level >> 24) & 0xF
    scale_r_raw = (cdb_level >> 28) & 0xF
    scale_l = scale_l_raw if scale_l_raw else None
    scale_r = scale_r_raw if scale_r_raw else None
    return level, scale_l, scale_r


def _join(qualifiers: list[str], base: str) -> str:
    if not qualifiers:
        return base
    return " ".join(qualifiers) + " " + base
