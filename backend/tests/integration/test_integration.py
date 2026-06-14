"""
Integration tests for YGO Intel API.

Requires a live PostgreSQL instance (see conftest.py for TEST_DATABASE_URL).
Each test starts with empty tables (autouse clean_db fixture).
"""
from datetime import date

from app.models.banlist import Banlist, BanlistEntry
from app.models.card import Card
from app.models.enums import BanlistStatus


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _card(ext_id: int, name: str) -> Card:
    return Card(
        external_card_id=ext_id,
        name=name,
        slug=f"{name.lower().replace(' ', '-')}-{ext_id}",
        type="Monster Card",
        frame_type="normal",
    )


def _ydk(main: list[int], extra: list[int] | None = None, side: list[int] | None = None) -> bytes:
    lines = ["#main"] + [str(i) for i in main]
    lines += ["#extra"] + [str(i) for i in (extra or [])]
    lines += ["#!side"] + [str(i) for i in (side or [])]
    return "\n".join(lines).encode()


async def _import_deck(client, card_id: int, qty: int = 3, title: str = "Test Deck") -> int:
    resp = await client.post(
        "/api/v1/decks/import/ydk",
        files={"file": ("deck.ydk", _ydk(main=[card_id] * qty), "text/plain")},
        data={"title": title},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["deck_id"]


# ─── YDK Import ───────────────────────────────────────────────────────────────


async def test_import_ydk_success(client, db):
    db.add(_card(89631139, "Blue-Eyes White Dragon"))
    db.add(_card(46986414, "Dark Magician"))
    await db.commit()

    ydk = _ydk(main=[89631139, 89631139, 89631139, 46986414, 46986414])
    resp = await client.post(
        "/api/v1/decks/import/ydk",
        files={"file": ("deck.ydk", ydk, "text/plain")},
        data={"title": "Blue-Eyes Build"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Blue-Eyes Build"
    assert data["main_count"] == 5
    assert data["extra_count"] == 0
    assert data["unknown_ids"] == []
    assert data["deck_id"] > 0
    assert data["submission_id"] > 0


async def test_import_ydk_unknown_cards(client):
    ydk = _ydk(main=[99999901, 99999902, 99999902])
    resp = await client.post(
        "/api/v1/decks/import/ydk",
        files={"file": ("unknown.ydk", ydk, "text/plain")},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["main_count"] == 0
    assert sorted(data["unknown_ids"]) == [99999901, 99999902]


async def test_import_ydk_mixed_known_unknown(client, db):
    db.add(_card(89631139, "Blue-Eyes White Dragon"))
    await db.commit()

    ydk = _ydk(main=[89631139, 89631139, 99999999])
    resp = await client.post(
        "/api/v1/decks/import/ydk",
        files={"file": ("mixed.ydk", ydk, "text/plain")},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["main_count"] == 2
    assert data["unknown_ids"] == [99999999]


async def test_import_ydk_with_extra_deck(client, db):
    db.add(_card(89631139, "Blue-Eyes White Dragon"))
    db.add(_card(38033121, "Blue-Eyes Ultimate Dragon"))
    await db.commit()

    ydk = _ydk(
        main=[89631139, 89631139, 89631139],
        extra=[38033121],
    )
    resp = await client.post(
        "/api/v1/decks/import/ydk",
        files={"file": ("fusion.ydk", ydk, "text/plain")},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["main_count"] == 3
    assert data["extra_count"] == 1


async def test_import_ydk_requires_auth(unauth_client):
    resp = await unauth_client.post(
        "/api/v1/decks/import/ydk",
        files={"file": ("deck.ydk", _ydk(main=[89631139]), "text/plain")},
    )
    assert resp.status_code == 401


async def test_import_ydk_rejects_non_ydk_extension(client):
    resp = await client.post(
        "/api/v1/decks/import/ydk",
        files={"file": ("deck.txt", b"not a ydk", "text/plain")},
    )
    assert resp.status_code == 422


async def test_import_ydk_rejects_empty_file(client):
    ydk = b"#main\n#extra\n#!side\n"
    resp = await client.post(
        "/api/v1/decks/import/ydk",
        files={"file": ("empty.ydk", ydk, "text/plain")},
    )
    assert resp.status_code == 422


# ─── Banlist Legality ──────────────────────────────────────────────────────────


async def _seed_banlist(db, card: Card, status: BanlistStatus, limit_value: int) -> Banlist:
    banlist = Banlist(
        format="TCG",
        source_name="Integration Test Banlist",
        effective_date=date.today(),
        version_label="test",
    )
    db.add(banlist)
    await db.flush()
    db.add(BanlistEntry(
        banlist_id=banlist.id,
        card_id=card.id,
        status=status,
        limit_value=limit_value,
    ))
    await db.commit()
    return banlist


async def test_legality_violation_limited_card(client, db):
    card = _card(46986414, "Dark Magician")
    db.add(card)
    await db.flush()
    await _seed_banlist(db, card, BanlistStatus.limited, limit_value=1)

    deck_id = await _import_deck(client, 46986414, qty=3)

    resp = await client.get(f"/api/v1/decks/{deck_id}/legality?format=TCG")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_legal"] is False
    assert len(data["violations"]) == 1
    v = data["violations"][0]
    assert v["name"] == "Dark Magician"
    assert v["status"] == "limited"
    assert v["actual_quantity"] == 3
    assert v["limit_value"] == 1


async def test_legality_violation_forbidden_card(client, db):
    card = _card(55144522, "Pot of Greed")
    db.add(card)
    await db.flush()
    await _seed_banlist(db, card, BanlistStatus.forbidden, limit_value=0)

    deck_id = await _import_deck(client, 55144522, qty=1)

    resp = await client.get(f"/api/v1/decks/{deck_id}/legality?format=TCG")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_legal"] is False
    v = data["violations"][0]
    assert v["status"] == "forbidden"
    assert v["actual_quantity"] == 1
    assert v["limit_value"] == 0


async def test_legality_clean_no_banlist(client, db):
    db.add(_card(89631139, "Blue-Eyes White Dragon"))
    await db.commit()

    deck_id = await _import_deck(client, 89631139, qty=3)

    resp = await client.get(f"/api/v1/decks/{deck_id}/legality?format=TCG")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_legal"] is True
    assert data["violations"] == []


async def test_legality_clean_unlimited_card(client, db):
    card = _card(89631139, "Blue-Eyes White Dragon")
    db.add(card)
    await db.flush()

    banlist = Banlist(
        format="TCG",
        source_name="Test Banlist",
        effective_date=date.today(),
    )
    db.add(banlist)
    await db.commit()

    deck_id = await _import_deck(client, 89631139, qty=3)

    resp = await client.get(f"/api/v1/decks/{deck_id}/legality?format=TCG")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_legal"] is True
    assert data["violations"] == []
    assert data["restricted"] == []


async def test_legality_deck_not_found(client):
    resp = await client.get("/api/v1/decks/99999/legality?format=TCG")
    assert resp.status_code == 404


# ─── Deck Pagination ─────────────────────────────────────────────────────────


async def _seed_n_decks(client, db, n: int) -> list[int]:
    db.add(_card(89631139, "Blue-Eyes White Dragon"))
    await db.commit()
    ids = []
    for i in range(n):
        deck_id = await _import_deck(client, 89631139, title=f"Deck {i:02d}")
        ids.append(deck_id)
    return ids


async def test_pagination_first_page(client, db):
    await _seed_n_decks(client, db, 7)

    resp = await client.get("/api/v1/decks?limit=5&page=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 7
    assert len(data["items"]) == 5
    assert data["page"] == 1
    assert data["limit"] == 5


async def test_pagination_second_page(client, db):
    await _seed_n_decks(client, db, 7)

    resp = await client.get("/api/v1/decks?limit=5&page=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 7
    assert len(data["items"]) == 2


async def test_pagination_empty_db(client):
    resp = await client.get("/api/v1/decks?limit=10&page=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_pagination_filter_by_tag(client, db):
    ids = await _seed_n_decks(client, db, 3)

    await client.patch(f"/api/v1/decks/{ids[0]}", json={"tags": ["Top 8"]})
    await client.patch(f"/api/v1/decks/{ids[1]}", json={"tags": ["Top 8"]})

    resp = await client.get("/api/v1/decks?tag=Top 8")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    returned_ids = {item["id"] for item in data["items"]}
    assert ids[0] in returned_ids
    assert ids[1] in returned_ids


async def test_pagination_filter_by_archetype(client, db):
    ids = await _seed_n_decks(client, db, 3)

    await client.patch(f"/api/v1/decks/{ids[0]}", json={"archetype_label": "Blue-Eyes"})

    resp = await client.get("/api/v1/decks?archetype=Blue-Eyes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == ids[0]


async def test_pagination_per_page_limit(client, db):
    await _seed_n_decks(client, db, 3)

    resp = await client.get("/api/v1/decks?limit=2&page=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
