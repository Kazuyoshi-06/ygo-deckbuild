from pydantic import BaseModel


class SubScore(BaseModel):
    value: float          # 0–100
    label: str
    weight: float         # 0.0–1.0 (weight in final score)
    status: str           # "strong" | "ok" | "weak" | "critical"
    note: str             # 1-line explanation of what drove the value
    tip: str | None       # actionable advice if weak/critical


class CompetitiveScoreOut(BaseModel):
    deck_id: int
    deck_title: str
    global_score: float          # 0–100 weighted sum
    grade: str                   # "S" | "A" | "B" | "C" | "D"
    has_roles: bool
    consistency: SubScore
    power: SubScore
    meta: SubScore
    resilience: SubScore
    summary: str                 # one-line overall verdict
