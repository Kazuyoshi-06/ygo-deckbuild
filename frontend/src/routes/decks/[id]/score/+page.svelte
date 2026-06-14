<script lang="ts">
  import { untrack } from 'svelte';

  interface SubScore {
    value: number;
    label: string;
    weight: number;
    status: string;
    note: string;
    tip: string | null;
  }

  interface ScoreData {
    deck_id: number;
    deck_title: string;
    global_score: number;
    grade: string;
    has_roles: boolean;
    consistency: SubScore;
    power: SubScore;
    meta: SubScore;
    resilience: SubScore;
    summary: string;
  }

  let { data } = $props<{ data: { deckId: number; score: ScoreData } }>();
  const s = untrack(() => data.score);

  const SUB_META = {
    consistency: { color: '#818cf8', icon: '◈', desc: 'Probabilité d\'ouvrir starter + handtrap' },
    power:       { color: '#fbbf24', icon: '⚡', desc: 'Puissance de la end board' },
    meta:        { color: '#22d3ee', icon: '◎', desc: 'Alignement avec les decks populaires' },
    resilience:  { color: '#4ade80', icon: '⬡', desc: 'Fonctionnalité sous disruption' },
  };

  const SUBS: { key: keyof ScoreData; meta: typeof SUB_META['consistency'] }[] = [
    { key: 'consistency', meta: SUB_META.consistency },
    { key: 'power',       meta: SUB_META.power },
    { key: 'meta',        meta: SUB_META.meta },
    { key: 'resilience',  meta: SUB_META.resilience },
  ];

  function statusColor(st: string): string {
    if (st === 'strong')   return '#22c55e';
    if (st === 'ok')       return '#f59e0b';
    if (st === 'weak')     return '#f97316';
    return '#ef4444';
  }

  function statusLabel(st: string): string {
    if (st === 'strong')   return 'Fort';
    if (st === 'ok')       return 'Correct';
    if (st === 'weak')     return 'Faible';
    return 'Critique';
  }

  function gradeColor(g: string): string {
    if (g === 'S') return '#ffd700';
    if (g === 'A') return '#22c55e';
    if (g === 'B') return '#818cf8';
    if (g === 'C') return '#f59e0b';
    return '#ef4444';
  }

  // SVG arc for the score dial
  function arcPath(score: number, r = 72): string {
    const pct = Math.min(score / 100, 1);
    const angle = pct * 270 - 135;      // arc spans 270°, starts at -135°
    const rad = (angle * Math.PI) / 180;
    const cx = 90, cy = 90;
    const x = cx + r * Math.cos(rad);
    const y = cy + r * Math.sin(rad);
    const largeArc = pct > 0.5 ? 1 : 0;
    // Start point at -135° = 225° standard
    const startRad = (-135 * Math.PI) / 180;
    const sx = cx + r * Math.cos(startRad);
    const sy = cy + r * Math.sin(startRad);
    return `M ${sx} ${sy} A ${r} ${r} 0 ${largeArc} 1 ${x} ${y}`;
  }

  const trackPath = arcPath(100);
  const scorePath = $derived(arcPath(s.global_score));
  const scoreColor = $derived(gradeColor(s.grade));

  function weightPct(w: number): string {
    return (w * 100).toFixed(0) + '%';
  }
</script>

<svelte:head>
  <title>Score — {s.deck_title} — YGO Intel</title>
</svelte:head>

<div class="page">
  <div class="topbar">
    <a href="/decks/{s.deck_id}" class="back">← Deck</a>
    <h1>{s.deck_title}</h1>
  </div>

  {#if !s.has_roles}
    <div class="roles-cta">
      Score partiel — <a href="/decks/{s.deck_id}/probability">taguez vos cartes</a> pour un score précis sur la consistance et la résilience.
    </div>
  {/if}

  <!-- ── Score dial ────────────────────────────────────────────── -->
  <div class="score-hero">
    <div class="dial-wrap">
      <svg viewBox="0 0 180 180" class="dial-svg">
        <!-- Track -->
        <path d={trackPath} fill="none" stroke="#1e293b" stroke-width="12" stroke-linecap="round" />
        <!-- Score arc -->
        <path d={scorePath} fill="none" stroke={scoreColor} stroke-width="12" stroke-linecap="round"
              style="filter: drop-shadow(0 0 8px {scoreColor}66)" />
        <!-- Grade -->
        <text x="90" y="82" text-anchor="middle" class="dial-grade" fill={scoreColor}>{s.grade}</text>
        <!-- Score number -->
        <text x="90" y="108" text-anchor="middle" class="dial-score">{s.global_score.toFixed(0)}</text>
        <text x="90" y="122" text-anchor="middle" class="dial-label">/ 100</text>
      </svg>
    </div>

    <div class="hero-right">
      <p class="summary">{s.summary}</p>

      <!-- Weight breakdown mini-legend -->
      <div class="weights">
        {#each SUBS as sub}
          {@const ss = s[sub.key] as SubScore}
          <div class="weight-row">
            <span class="weight-dot" style="background:{sub.meta.color}"></span>
            <span class="weight-label">{ss.label}</span>
            <span class="weight-pct">{weightPct(ss.weight)}</span>
          </div>
        {/each}
      </div>
    </div>
  </div>

  <!-- ── Sub-scores ─────────────────────────────────────────────── -->
  <div class="sub-scores">
    {#each SUBS as sub}
      {@const ss = s[sub.key] as SubScore}
      <div class="sub-card">
        <div class="sub-header">
          <span class="sub-icon" style="color:{sub.meta.color}">{sub.meta.icon}</span>
          <span class="sub-label">{ss.label}</span>
          <span class="sub-weight">× {weightPct(ss.weight)}</span>
          <span class="sub-status" style="color:{statusColor(ss.status)}">{statusLabel(ss.status)}</span>
        </div>

        <div class="sub-value-row">
          <span class="sub-num" style="color:{sub.meta.color}">{ss.value.toFixed(0)}</span>
          <div class="sub-bar-track">
            <div class="sub-bar" style="width:{ss.value}%;background:{sub.meta.color}"></div>
            <div class="sub-contribution" style="width:{ss.value * ss.weight}%;background:{sub.meta.color}44" title="Contribution au score global"></div>
          </div>
          <span class="sub-contrib-val" style="color:{sub.meta.color}88" title="Contribution pondérée">+{(ss.value * ss.weight).toFixed(1)}</span>
        </div>

        <p class="sub-desc">{sub.meta.desc}</p>
        <p class="sub-note">{ss.note}</p>

        {#if ss.tip}
          <div class="sub-tip" style="border-left-color:{statusColor(ss.status)}">
            {ss.tip}
          </div>
        {/if}
      </div>
    {/each}
  </div>

  <!-- ── Grade scale ────────────────────────────────────────────── -->
  <div class="grade-scale">
    {#each [['S','≥85','#ffd700'],['A','72-84','#22c55e'],['B','58-71','#818cf8'],['C','42-57','#f59e0b'],['D','< 42','#ef4444']] as [g, range, color]}
      <div class="grade-item" class:current={s.grade === g}>
        <span class="grade-letter" style="color:{color}">{g}</span>
        <span class="grade-range">{range}</span>
      </div>
    {/each}
  </div>
</div>

<style>
  .page {
    max-width: 780px;
    margin: 0 auto;
    padding: 1.5rem 1rem 4rem;
    color: #e2e8f0;
  }

  .topbar {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
  }
  .back { color: #94a3b8; text-decoration: none; font-size: 0.875rem; }
  .back:hover { color: #e2e8f0; }
  h1 { font-size: 1.25rem; font-weight: 600; margin: 0; }

  .roles-cta {
    background: #1e293b22; border: 1px solid #f59e0b44;
    border-radius: 8px; padding: 0.75rem 1rem;
    font-size: 0.85rem; color: #f59e0b; margin-bottom: 1.25rem;
  }
  .roles-cta a { color: #fbbf24; font-weight: 600; text-decoration: none; }

  /* Dial */
  .score-hero {
    display: flex;
    align-items: center;
    gap: 2rem;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }
  .dial-wrap { flex-shrink: 0; width: 180px; }
  .dial-svg { width: 100%; }
  .dial-grade {
    font-size: 2.2rem;
    font-weight: 900;
    font-family: monospace;
  }
  .dial-score {
    font-size: 1.5rem;
    font-weight: 700;
    fill: #e2e8f0;
  }
  .dial-label { font-size: 0.65rem; fill: #475569; }

  .hero-right { flex: 1; min-width: 200px; }
  .summary { font-size: 0.95rem; color: #cbd5e1; margin: 0 0 1.25rem; line-height: 1.55; }

  .weights { display: flex; flex-direction: column; gap: 0.35rem; }
  .weight-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; }
  .weight-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .weight-label { flex: 1; color: #94a3b8; }
  .weight-pct { color: #475569; }

  /* Sub-scores */
  .sub-scores {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }
  @media (max-width: 580px) { .sub-scores { grid-template-columns: 1fr; } }

  .sub-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .sub-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.1rem;
  }
  .sub-icon { font-size: 1rem; }
  .sub-label { font-size: 0.875rem; font-weight: 600; flex: 1; }
  .sub-weight { font-size: 0.7rem; color: #475569; }
  .sub-status { font-size: 0.72rem; font-weight: 700; }

  .sub-value-row {
    display: flex;
    align-items: center;
    gap: 0.625rem;
  }
  .sub-num { font-size: 1.6rem; font-weight: 800; width: 44px; flex-shrink: 0; line-height: 1; }
  .sub-bar-track {
    flex: 1;
    position: relative;
    height: 8px;
    background: #1e293b;
    border-radius: 4px;
    overflow: hidden;
  }
  .sub-bar {
    position: absolute;
    top: 0; left: 0;
    height: 100%;
    border-radius: 4px;
    opacity: 0.9;
    transition: width 0.6s;
  }
  .sub-contribution {
    position: absolute;
    top: 0; left: 0;
    height: 100%;
    border-radius: 4px;
  }
  .sub-contrib-val { font-size: 0.72rem; width: 34px; text-align: right; flex-shrink: 0; }

  .sub-desc { font-size: 0.73rem; color: #475569; margin: 0; }
  .sub-note { font-size: 0.78rem; color: #64748b; margin: 0; line-height: 1.4; }

  .sub-tip {
    font-size: 0.78rem;
    color: #cbd5e1;
    border-left: 2px solid;
    padding-left: 0.6rem;
    margin-top: 0.15rem;
    line-height: 1.5;
  }

  /* Grade scale */
  .grade-scale {
    display: flex;
    gap: 0.5rem;
    justify-content: center;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 0.875rem 1.25rem;
  }
  .grade-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.2rem;
    flex: 1;
    opacity: 0.4;
    transition: opacity 0.2s;
  }
  .grade-item.current { opacity: 1; }
  .grade-letter { font-size: 1.25rem; font-weight: 800; }
  .grade-range { font-size: 0.65rem; color: #475569; }
</style>
