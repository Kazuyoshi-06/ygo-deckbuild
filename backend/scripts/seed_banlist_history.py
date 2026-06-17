"""One-off script: seed real historical TCG/OCG banlists from ProjectIgnis/LFLists GitHub history.

Each commit to 0TCG.lflist.conf / OCG.lflist.conf on GitHub represents a real banlist
update with an accurate date, going back to 2021. We replay that commit history to
build a real Banlist + BanlistEntry timeline instead of a single synced snapshot.

Run with: cd backend && .venv\\Scripts\\python.exe -m scripts.seed_banlist_history
"""

import asyncio
import logging
import re
from datetime import date, datetime

import httpx
from sqlalchemy import delete, select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Card
from app.models.banlist import Banlist, BanlistEntry
from app.models.enums import BanlistStatus

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seed_banlist_history")

REPO = "ProjectIgnis/LFLists"
FILES = {"TCG": "0TCG.lflist.conf", "OCG": "OCG.lflist.conf"}
STATUS_MAP = {0: BanlistStatus.forbidden, 1: BanlistStatus.limited, 2: BanlistStatus.semi_limited}
LIMIT_VALUE = {BanlistStatus.forbidden: 0, BanlistStatus.limited: 1, BanlistStatus.semi_limited: 2}

GITHUB_HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "ygo-deckbuild-seed-script"}


async def fetch_commits(client: httpx.AsyncClient, path: str) -> list[dict]:
    commits: list[dict] = []
    page = 1
    while True:
        resp = await client.get(
            f"https://api.github.com/repos/{REPO}/commits",
            params={"path": path, "per_page": 100, "page": page},
            headers=GITHUB_HEADERS,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        commits.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return commits


LABEL_DATE_RE = re.compile(r"(\d{4})\.(\d{1,2})\b")


def label_to_date(label: str) -> date | None:
    """Parse a header label like '2021.07 TCG' or '2023.1 OCG' into date(year, month, 1)."""
    match = LABEL_DATE_RE.search(label)
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if not (1 <= month <= 12):
        return None
    return date(year, month, 1)


def normalize_label(label: str, fmt: str, fallback_date: date) -> str:
    """Zero-pad the month in labels like '2023.1 OCG' -> '2023.01 OCG'; fall back to date-derived label."""
    match = LABEL_DATE_RE.search(label)
    if not match:
        return f"{fallback_date.year}.{fallback_date.month:02d} {fmt}"
    year, month = int(match.group(1)), int(match.group(2))
    return f"{year}.{month:02d} {fmt}"


def parse_lflist(content: str) -> dict[int, BanlistStatus]:
    entries: dict[int, BanlistStatus] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            passcode = int(parts[0])
            status_val = int(parts[1])
        except ValueError:
            continue
        status = STATUS_MAP.get(status_val)
        if status is not None:
            entries[passcode] = status
    return entries


async def fetch_snapshot(client: httpx.AsyncClient, fmt: str, path: str, commit: dict) -> dict | None:
    sha = commit["sha"]
    commit_date_str = commit["commit"]["author"]["date"]
    commit_date = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00")).date()

    raw_resp = await client.get(f"https://raw.githubusercontent.com/{REPO}/{sha}/{path}")
    if raw_resp.status_code != 200:
        logger.warning(f"  {fmt} {sha[:7]}: raw fetch failed ({raw_resp.status_code}) — skipped")
        return None

    header_match = re.search(r"^!(.+)$", raw_resp.text, re.MULTILINE)
    raw_label = header_match.group(1).strip() if header_match else f"{fmt} {commit_date.isoformat()}"

    # Prefer the period encoded in the list header (e.g. "2021.07 TCG") over the
    # git commit date — corrections/backfills are often committed long after the
    # period they describe, which would otherwise misorder the timeline.
    effective_date = label_to_date(raw_label) or commit_date
    version_label = normalize_label(raw_label, fmt, effective_date)

    return {
        "sha": sha,
        "commit_date": commit_date,
        "effective_date": effective_date,
        "version_label": version_label,
        "raw_text": raw_resp.text,
    }


async def seed_format(
    client: httpx.AsyncClient,
    db,
    fmt: str,
    path: str,
    ext_to_db: dict[int, int],
) -> int:
    commits = await fetch_commits(client, path)
    logger.info(f"{fmt}: {len(commits)} commits found for {path}")

    snapshots = []
    for commit in commits:
        snap = await fetch_snapshot(client, fmt, path, commit)
        if snap is not None:
            snapshots.append(snap)

    # Sort by the real effective date (derived from the list's own period label),
    # not by commit date, since history was partly backfilled out of order.
    snapshots.sort(key=lambda s: (s["effective_date"], s["commit_date"]))

    # Multiple commits can share the same period (typo/passcode corrections within
    # the same quarter) — keep only the latest commit per period, since it's the
    # canonical final state of that period, not a new banlist.
    by_period: dict[date, dict] = {}
    for snap in snapshots:
        by_period[snap["effective_date"]] = snap  # later commit overwrites earlier
    snapshots = sorted(by_period.values(), key=lambda s: s["effective_date"])

    last_fp: frozenset | None = None
    created = 0

    for snap in snapshots:
        passcode_status = parse_lflist(snap["raw_text"])
        mapped: dict[int, BanlistStatus] = {
            ext_to_db[passcode]: status
            for passcode, status in passcode_status.items()
            if passcode in ext_to_db
        }
        if not mapped:
            continue

        fp = frozenset((cid, st.value) for cid, st in mapped.items())
        if fp == last_fp:
            continue  # identical to previous historical snapshot — no real change

        last_fp = fp

        banlist = Banlist(
            format=fmt,
            source_name="ProjectIgnis LFLists (GitHub)",
            source_url=f"https://github.com/{REPO}/blob/{snap['sha']}/{path}",
            effective_date=snap["effective_date"],
            version_label=snap["version_label"],
        )
        db.add(banlist)
        await db.flush()

        for db_id, status in mapped.items():
            db.add(BanlistEntry(
                banlist_id=banlist.id,
                card_id=db_id,
                status=status,
                limit_value=LIMIT_VALUE[status],
            ))

        await db.commit()
        created += 1
        logger.info(
            f"  {fmt} {snap['effective_date']} ({snap['version_label']}): "
            f"{len(mapped)} entries — banlist id={banlist.id}"
        )

    return created


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(BanlistEntry))
        await db.execute(delete(Banlist))
        await db.commit()
        logger.info("Cleared existing banlist data\n")

        rows = await db.execute(select(Card.external_card_id, Card.id))
        ext_to_db = {ext: db_id for ext, db_id in rows}
        logger.info(f"Loaded {len(ext_to_db)} known cards for passcode matching\n")

        async with httpx.AsyncClient(timeout=60.0, verify=settings.verify_ssl) as client:
            total = 0
            for fmt, path in FILES.items():
                total += await seed_format(client, db, fmt, path, ext_to_db)
                logger.info("")
            logger.info(f"Done — {total} historical banlist snapshots created")


if __name__ == "__main__":
    asyncio.run(main())
