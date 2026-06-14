import enum


class CardSection(str, enum.Enum):
    main = "main"
    extra = "extra"
    side = "side"


class ImageStatus(str, enum.Enum):
    missing = "missing"
    queued = "queued"
    ready = "ready"
    failed = "failed"


class DeckSourceType(str, enum.Enum):
    ydk_import = "ydk_import"
    manual = "manual"
    scraped = "scraped"
    api_import = "api_import"


class BanlistStatus(str, enum.Enum):
    forbidden = "forbidden"
    limited = "limited"
    semi_limited = "semi_limited"
    unlimited = "unlimited"


class SyncType(str, enum.Enum):
    cards = "cards"
    banlist = "banlist"
    cdb = "cdb"
    images = "images"
    analytics = "analytics"


class SyncStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"
