import re
from dataclasses import dataclass, field

# frame_types that belong in the Extra Deck
EXTRA_FRAME_TYPES = frozenset({
    'fusion', 'synchro', 'xyz', 'link',
    'xyz-pendulum', 'synchro-pendulum', 'fusion-pendulum',
})

# ── Parsing regexes ──────────────────────────────────────────────────────────

_QTY_PREFIX = re.compile(r'^([1-3])\s*[xX×]\s*(.+)$')
_QTY_PREFIX_DIGIT = re.compile(r'^([1-3])\s+(.+)$')
_QTY_SUFFIX = re.compile(r'^(.+?)\s*[xX×]\s*([1-3])\s*$')
_TYPE_COUNT = re.compile(r'^[A-Za-z ]+:\s*\d+\s*$')   # "Monsters: 20"
_PURE_NUM = re.compile(r'^\d+\s*$')


@dataclass
class ParsedTextDeck:
    main: list[tuple[str, int]] = field(default_factory=list)   # (name, qty)
    extra: list[tuple[str, int]] = field(default_factory=list)
    side: list[tuple[str, int]] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.main or self.extra or self.side)

    def all_entries(self) -> list[tuple[str, int, str]]:
        return (
            [(n, q, 'main')  for n, q in self.main]
            + [(n, q, 'extra') for n, q in self.extra]
            + [(n, q, 'side')  for n, q in self.side]
        )


def _detect_section(line: str) -> str | None:
    """Return 'main', 'extra', 'side', or None if the line is not a section header."""
    lower = line.lower().strip()

    # YDK / YGOPRO markers
    if lower.startswith('#main'):
        return 'main'
    if lower.startswith('#extra'):
        return 'extra'
    if lower.startswith('!side') or lower.startswith('#side'):
        return 'side'

    # Strip trailing metadata like "(40)", ": 15", "- 20" to get the bare label
    clean = re.sub(r'[\s:()\d\-=*]+$', '', lower).strip()
    if clean in ('main deck', 'main', 'maindeck'):
        return 'main'
    if clean in ('extra deck', 'extra', 'extradeck'):
        return 'extra'
    if clean in ('side deck', 'side', 'sidedeck', 'side-deck'):
        return 'side'

    # "=== Main Deck ===" / "--- Side ---" decorative headers
    inner = re.sub(r'^[=\-*\s]+|[=\-*\s]+$', '', lower)
    if inner in ('main deck', 'main', 'maindeck'):
        return 'main'
    if inner in ('extra deck', 'extra', 'extradeck'):
        return 'extra'
    if inner in ('side deck', 'side', 'sidedeck', 'side-deck'):
        return 'side'

    return None


def _parse_card_line(line: str) -> tuple[str, int] | None:
    """
    Extract (card_name, quantity) from a single line.
    Returns None if the line is not a card entry.

    Supported formats:
      3x Card Name   |  3× Card Name   |  3 Card Name
      Card Name x3   |  Card Name ×3
      Card Name          (quantity defaults to 1)
    """
    # Skip comments and decorative separators
    if not line or line.startswith(('#', '//', '--', '==')):
        return None

    # Skip pure numbers (section counts like "40")
    if _PURE_NUM.match(line):
        return None

    # Skip "Type: Count" headers like "Monsters: 20", "Spells: 10"
    if _TYPE_COUNT.match(line):
        return None

    # "3x Card Name" or "3× Card Name"
    m = _QTY_PREFIX.match(line)
    if m:
        name = m.group(2).strip()
        if name:
            return name, int(m.group(1))

    # "3 Card Name" — only digits 1-3 to avoid parsing "40 monsters" as a card
    m = _QTY_PREFIX_DIGIT.match(line)
    if m:
        name = m.group(2).strip()
        if name and not name.isdigit():
            return name, int(m.group(1))

    # "Card Name x3" or "Card Name ×3"
    m = _QTY_SUFFIX.match(line)
    if m:
        name = m.group(1).strip()
        if name:
            return name, int(m.group(2))

    # Bare card name without quantity — assume 1 copy
    if len(line) >= 2:
        return line, 1

    return None


def parse_text(text: str) -> ParsedTextDeck:
    """Parse a free-form deck list into (name, qty) tuples grouped by section.

    Section headers are auto-detected. Without explicit headers, all cards go
    to the main deck and extra-deck monsters are moved automatically after DB lookup.
    """
    result = ParsedTextDeck()
    current: list[tuple[str, int]] = result.main

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        section = _detect_section(line)
        if section == 'main':
            current = result.main
            continue
        if section == 'extra':
            current = result.extra
            continue
        if section == 'side':
            current = result.side
            continue

        parsed = _parse_card_line(line)
        if parsed:
            name, qty = parsed
            current.append((name, min(qty, 3)))

    return result
