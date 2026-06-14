from pydantic import BaseModel


class AdviceItem(BaseModel):
    category: str           # "monster" | "spell" | "trap" | "extra" | "side" | "main_count" | role name
    label: str              # human-readable label
    your_value: int
    archetype_avg: float | None   # None if no archetype data
    archetype_sample: int         # 0 if no data
    ref_ideal_min: int
    ref_ideal_max: int
    status: str             # "ok" | "warning" | "critical"
    tip: str | None


class ArchetypeAverages(BaseModel):
    sample_size: int
    avg_main: float
    avg_monster: float
    avg_spell: float
    avg_trap: float
    avg_extra: float
    avg_side: float


class RatioAdviceOut(BaseModel):
    deck_id: int
    deck_title: str
    archetype_label: str | None
    main_count: int
    monster_count: int
    spell_count: int
    trap_count: int
    extra_count: int
    side_count: int
    role_counts: dict[str, int] | None        # None if no roles tagged
    archetype_averages: ArchetypeAverages | None
    advice: list[AdviceItem]
