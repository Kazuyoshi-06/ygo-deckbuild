from dataclasses import dataclass, field


@dataclass
class ParsedYdk:
    main: list[int] = field(default_factory=list)
    extra: list[int] = field(default_factory=list)
    side: list[int] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.main) + len(self.extra) + len(self.side)

    @property
    def is_empty(self) -> bool:
        return self.total == 0


def parse(content: str) -> ParsedYdk:
    """Parse a .ydk file content into card ID lists per section.

    Handles #main / #extra / !side (or #side) section markers.
    Lines starting with # that aren't section markers are treated as comments.
    """
    result = ParsedYdk()
    current: list[int] | None = None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        lower = line.lower()

        if lower.startswith("#main"):
            current = result.main
        elif lower.startswith("#extra"):
            current = result.extra
        elif lower.startswith("!side") or lower.startswith("#side"):
            current = result.side
        elif lower.startswith("#"):
            continue  # skip #created by ... and other comments
        elif current is not None and line.lstrip("-").isdigit():
            card_id = int(line)
            if card_id > 0:
                current.append(card_id)

    return result
