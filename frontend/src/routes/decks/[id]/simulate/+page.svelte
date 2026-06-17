<script lang="ts">
  import { untrack } from 'svelte';

  interface StarterDistEntry {
    count: number;
    simulations: number;
    pct: number;
  }

  interface CardBrickRate {
    card_id: number;
    name: string;
    role: string | null;
    total_appearances: number;
    dead_appearances: number;
    dead_pct: number;
  }

  interface SimulationData {
    deck_id: number;
    deck_title: string;
    main_count: number;
    n_simulations: number;
    hand_size: number;
    has_roles: boolean;
    win_rate: number;
    medium_rate: number;
    dead_rate: number;
    avg_starters: number;
    avg_handtraps: number;
    avg_garnets: number;
    starter_dist: StarterDistEntry[];
    brick_cards: CardBrickRate[];
  }

  let { data } = $props<{ data: { deckId: number; initial1: SimulationData; initial2: SimulationData } }>();

  const deckId = untrack(() => data.deckId);
  let result1 = $state<SimulationData>(untrack(() => data.initial1)); // Going First  — 5 cards
  let result2 = $state<SimulationData>(untrack(() => data.initial2)); // Going Second — 6 cards
  let running = $state(false);
  let nSim = $state(10000);
  let detailView = $state<5 | 6>(5);

  const SIM_OPTIONS = [1000, 5000, 10000, 25000, 50000];

  // Derived: the result used for the detailed section below the comparison
  let result = $derived(detailView === 5 ? result1 : result2);

  async function runSim() {
    running = true;
    try {
      const [res1, res2] = await Promise.all([
        fetch(`/api/v1/decks/${deckId}/simulate?n=${nSim}&hand=5`),
        fetch(`/api/v1/decks/${deckId}/simulate?n=${nSim}&hand=6`),
      ]);
      if (res1.ok) result1 = await res1.json();
      if (res2.ok) result2 = await res2.json();
    } finally {
      running = false;
    }
  }

  function pct(v: number): string {
    return (v * 100).toFixed(1) + '%';
  }

  function winColor(rate: number): string {
    if (rate >= 0.80) return '#22c55e';
    if (rate >= 0.65) return '#86efac';
    if (rate >= 0.50) return '#f59e0b';
    return '#ef4444';
  }

  function deadColor(rate: number): string {
    if (rate <= 0.05) return '#22c55e';
    if (rate <= 0.15) return '#f59e0b';
    return '#ef4444';
  }

  function roleColor(role: string | null): string {
    const MAP: Record<string, string> = {
      starter: '#22c55e', extender: '#3b82f6', handtrap: '#f59e0b',
      garnet: '#ef4444', tech: '#8b5cf6', boss: '#ec4899', other: '#6b7280',
    };
    return role ? (MAP[role] ?? '#6b7280') : '#475569';
  }

  function roleLabel(role: string | null): string {
    if (!role) return '—';
    const MAP: Record<string, string> = {
      starter: 'S', extender: 'E', handtrap: 'HT',
      garnet: 'G', tech: 'T', boss: 'B', other: '?',
    };
    return MAP[role] ?? role;
  }

  function avgLabel(avg: number): string {
    if (avg >= 1.2) return 'Excellent';
    if (avg >= 0.9) return 'Good';
    if (avg >= 0.6) return 'Average';
    return 'Low';
  }

  // Comparison delta: GS (hand=6) vs GF (hand=5)
  interface DeltaInfo { label: string; color: string }
  function delta(gf: number, gs: number, goodDirection: 'up' | 'down' = 'up'): DeltaInfo {
    const d = gs - gf;
    const sign = d > 0 ? '+' : '';
    const label = `${sign}${(d * 100).toFixed(1)}%`;
    const isGood = goodDirection === 'up' ? d > 0 : d < 0;
    const color = Math.abs(d) < 0.003 ? '#64748b' : isGood ? '#22c55e' : '#ef4444';
    return { label, color };
  }

  function avgDelta(gf: number, gs: number): DeltaInfo {
    const d = gs - gf;
    const sign = d > 0 ? '+' : '';
    const label = `${sign}${d.toFixed(2)}`;
    const color = Math.abs(d) < 0.01 ? '#64748b' : d > 0 ? '#22c55e' : '#ef4444';
    return { label, color };
  }

  // Histogram bar max for the selected detail view
  let maxDist = $derived(
    result.starter_dist.length > 0
      ? Math.max(...result.starter_dist.map((d: StarterDistEntry) => d.pct))
      : 1
  );

  // Top bricks for the selected detail view
  let topBricks = $derived(
    [...result.brick_cards]
      .sort((a: CardBrickRate, b: CardBrickRate) => b.dead_pct - a.dead_pct)
      .slice(0, 15)
  );

  // Pre-computed deltas for the comparison table
  let dWin     = $derived(delta(result1.win_rate,     result2.win_rate,     'up'));
  let dMed     = $derived(delta(result1.medium_rate,  result2.medium_rate,  'up'));
  let dDead    = $derived(delta(result1.dead_rate,    result2.dead_rate,    'down'));
  let dStart   = $derived(avgDelta(result1.avg_starters,  result2.avg_starters));
  let dHT      = $derived(avgDelta(result1.avg_handtraps, result2.avg_handtraps));

  // Interpretation texts for the comparison
  function winInterpretation(rate: number): string {
    if (rate >= 0.85) return 'Excellent — well above competitive standard (70%).';
    if (rate >= 0.75) return 'Very good — above the competitive benchmark (70%).';
    if (rate >= 0.70) return 'Good — meets the competitive benchmark.';
    if (rate >= 0.60) return 'Below competitive standard. Consider adding more starters.';
    return 'Insufficient. This deck bricks frequently — review your starter ratio.';
  }

  function deadInterpretation(rate: number): string {
    if (rate <= 0.04) return 'Excellent consistency — almost never bricks.';
    if (rate <= 0.08) return 'Good consistency — acceptable brick rate for competitive play.';
    if (rate <= 0.15) return 'Moderate — slightly higher than ideal.';
    return 'High brick rate. Review garnet count and starter balance.';
  }
</script>

<svelte:head>
  <title>Simulator — {result1.deck_title} — YGO Intel</title>
</svelte:head>

<div class="page">
  <div class="topbar">
    <a href="/decks/{deckId}" class="back">← Deck</a>
    <h1>{result1.deck_title}</h1>
    <span class="badge">{result1.main_count} cards · {nSim.toLocaleString()} simulations</span>
  </div>

  {#if !result1.has_roles}
    <div class="no-roles">
      Results are basic without tagged card roles.
      <a href="/decks/{deckId}/probability">Tag your cards →</a>
    </div>
  {/if}

  <!-- ── Controls ──────────────────────────────────────────── -->
  <div class="controls">
    <div class="ctrl-group">
      <span class="ctrl-label">Simulations</span>
      <div class="toggle">
        {#each SIM_OPTIONS as n}
          <button
            type="button"
            class="toggle-btn"
            class:active={nSim === n}
            onclick={() => (nSim = n)}
          >
            {n.toLocaleString()}
          </button>
        {/each}
      </div>
    </div>

    <button
      type="button"
      class="run-btn"
      onclick={runSim}
      disabled={running}
    >
      {#if running}
        <span class="run-spinner" aria-hidden="true"></span>
        Running…
      {:else}
        ▶ Run Both Simulations
      {/if}
    </button>
  </div>

  <!-- ── Going First vs Going Second comparison ────────────── -->
  <section class="compare-panel">
    <div class="compare-header">
      <span class="compare-title">Going First vs Going Second</span>
      <span class="compare-sub">{result1.n_simulations.toLocaleString()} simulations each</span>
    </div>

    <div class="compare-grid">
      <!-- Column headers -->
      <div class="compare-col-hd"></div>
      <div class="compare-col-hd gf-hd">
        <span class="gf-label">Going First</span>
        <span class="hand-badge">5 cards</span>
      </div>
      <div class="compare-col-hd gs-hd">
        <span class="gs-label">Going Second</span>
        <span class="hand-badge">6 cards</span>
      </div>
      <div class="compare-col-hd delta-hd">
        <span>Δ GS − GF</span>
      </div>

      <!-- Win rate -->
      <div class="compare-row-label">Win rate <span class="row-hint">≥1 starter</span></div>
      <div class="compare-val" style="color:{winColor(result1.win_rate)}">{pct(result1.win_rate)}</div>
      <div class="compare-val" style="color:{winColor(result2.win_rate)}">{pct(result2.win_rate)}</div>
      <div class="compare-delta" style="color:{dWin.color}">{dWin.label}</div>

      <!-- Medium rate -->
      <div class="compare-row-label">Medium hand <span class="row-hint">0 starter + ≥1 HT</span></div>
      <div class="compare-val" style="color:#f59e0b">{pct(result1.medium_rate)}</div>
      <div class="compare-val" style="color:#f59e0b">{pct(result2.medium_rate)}</div>
      <div class="compare-delta" style="color:{dMed.color}">{dMed.label}</div>

      <!-- Dead rate -->
      <div class="compare-row-label">Brick rate <span class="row-hint">0 starter · 0 HT</span></div>
      <div class="compare-val" style="color:{deadColor(result1.dead_rate)}">{pct(result1.dead_rate)}</div>
      <div class="compare-val" style="color:{deadColor(result2.dead_rate)}">{pct(result2.dead_rate)}</div>
      <div class="compare-delta" style="color:{dDead.color}">{dDead.label}</div>

      <!-- Avg starters -->
      <div class="compare-row-label">Avg starters</div>
      <div class="compare-val muted">{result1.avg_starters.toFixed(2)}</div>
      <div class="compare-val muted">{result2.avg_starters.toFixed(2)}</div>
      <div class="compare-delta" style="color:{dStart.color}">{dStart.label}</div>

      <!-- Avg handtraps -->
      <div class="compare-row-label">Avg handtraps</div>
      <div class="compare-val muted">{result1.avg_handtraps.toFixed(2)}</div>
      <div class="compare-val muted">{result2.avg_handtraps.toFixed(2)}</div>
      <div class="compare-delta" style="color:{dHT.color}">{dHT.label}</div>
    </div>

    <!-- Interpretation of Going First win rate -->
    <div class="interpret-row">
      <div class="interpret-item">
        <span class="interpret-tag">GF</span>
        <span class="interpret-text">{winInterpretation(result1.win_rate)}</span>
      </div>
      <div class="interpret-sep"></div>
      <div class="interpret-item">
        <span class="interpret-tag">GS</span>
        <span class="interpret-text">{winInterpretation(result2.win_rate)}</span>
      </div>
    </div>
  </section>

  <!-- ── Detailed analysis toggle ──────────────────────────── -->
  <div class="detail-switcher">
    <span class="detail-label">Detailed analysis</span>
    <div class="view-toggle">
      <button
        type="button"
        class="view-btn"
        class:view-btn--active={detailView === 5}
        onclick={() => (detailView = 5)}
      >
        Going First
        <span class="hand-tag">5 cards</span>
      </button>
      <button
        type="button"
        class="view-btn"
        class:view-btn--active={detailView === 6}
        onclick={() => (detailView = 6)}
      >
        Going Second
        <span class="hand-tag">6 cards</span>
      </button>
    </div>
  </div>

  <!-- ── Win / Medium / Dead rates ─────────────────────────── -->
  <section class="rates-grid">
    <div class="rate-card win">
      <div class="rate-icon">▲</div>
      <div class="rate-val" style="color:{winColor(result.win_rate)}">{pct(result.win_rate)}</div>
      <div class="rate-label">Winning hands</div>
      <div class="rate-sub">≥1 starter drawn</div>
      <div class="rate-bar-track">
        <div class="rate-bar" style="width:{result.win_rate*100}%;background:{winColor(result.win_rate)}"></div>
      </div>
      <div class="rate-interp">{winInterpretation(result.win_rate)}</div>
    </div>

    <div class="rate-card medium">
      <div class="rate-icon">◆</div>
      <div class="rate-val" style="color:#f59e0b">{pct(result.medium_rate)}</div>
      <div class="rate-label">Playable hands</div>
      <div class="rate-sub">0 starter · ≥1 handtrap</div>
      <div class="rate-bar-track">
        <div class="rate-bar" style="width:{result.medium_rate*100}%;background:#f59e0b"></div>
      </div>
    </div>

    <div class="rate-card dead">
      <div class="rate-icon">▼</div>
      <div class="rate-val" style="color:{deadColor(result.dead_rate)}">{pct(result.dead_rate)}</div>
      <div class="rate-label">Brick hands</div>
      <div class="rate-sub">0 starter · 0 handtrap</div>
      <div class="rate-bar-track">
        <div class="rate-bar" style="width:{result.dead_rate*100}%;background:{deadColor(result.dead_rate)}"></div>
      </div>
      <div class="rate-interp">{deadInterpretation(result.dead_rate)}</div>
    </div>
  </section>

  <!-- ── Averages ───────────────────────────────────────────── -->
  <section class="avgs-row">
    <div class="avg-item">
      <span class="avg-val" style="color:#22c55e">{result.avg_starters.toFixed(2)}</span>
      <span class="avg-label">starters / hand</span>
      <span class="avg-qual" style="color:{result.avg_starters >= 0.9 ? '#22c55e' : '#f59e0b'}">{avgLabel(result.avg_starters)}</span>
    </div>
    <div class="avg-sep"></div>
    <div class="avg-item">
      <span class="avg-val" style="color:#f59e0b">{result.avg_handtraps.toFixed(2)}</span>
      <span class="avg-label">handtraps / hand</span>
      <span class="avg-qual" style="color:{result.avg_handtraps >= 0.8 ? '#22c55e' : '#f59e0b'}">{avgLabel(result.avg_handtraps)}</span>
    </div>
    <div class="avg-sep"></div>
    <div class="avg-item">
      <span class="avg-val" style="color:#ef4444">{result.avg_garnets.toFixed(2)}</span>
      <span class="avg-label">garnets / hand</span>
      <span class="avg-qual" style="color:{result.avg_garnets <= 0.3 ? '#22c55e' : result.avg_garnets <= 0.5 ? '#f59e0b' : '#ef4444'}">
        {result.avg_garnets <= 0.3 ? 'OK' : result.avg_garnets <= 0.5 ? 'High' : 'Too high'}
      </span>
    </div>
  </section>

  <!-- ── Starter distribution histogram ────────────────────── -->
  {#if result.starter_dist.length > 0}
    <section class="section">
      <h2>Starter distribution — {detailView === 5 ? 'Going First (5 cards)' : 'Going Second (6 cards)'}</h2>
      <div class="histogram">
        {#each result.starter_dist as entry}
          <div class="hist-col">
            <span class="hist-pct">{pct(entry.pct)}</span>
            <div class="hist-bar-track">
              <div
                class="hist-bar"
                style="height:{(entry.pct / maxDist) * 100}%;background:{entry.count === 0 ? '#ef4444' : entry.count === 1 ? '#f59e0b' : '#22c55e'}"
              ></div>
            </div>
            <span class="hist-label">{entry.count === 3 ? '3+' : entry.count} starter{entry.count !== 1 ? 's' : ''}</span>
          </div>
        {/each}
      </div>
      <p class="hist-interp">
        {#if result.starter_dist[0]}
          You open 0 starters in <strong>{pct(result.starter_dist[0].pct)}</strong> of games
          ({detailView === 5 ? 'Going First' : 'Going Second'}, {result.n_simulations.toLocaleString()} simulations).
          {result.starter_dist[0].pct <= 0.20
            ? 'Excellent starter density.'
            : result.starter_dist[0].pct <= 0.30
            ? 'Good — slightly above the 20% target.'
            : 'Above the competitive target of ≤20%. Consider increasing your starter count.'}
        {/if}
      </p>
    </section>
  {/if}

  <!-- ── Brick analysis ─────────────────────────────────────── -->
  {#if topBricks.length > 0}
    <section class="section">
      <h2>Brick analysis — {detailView === 5 ? 'Going First' : 'Going Second'}</h2>
      <p class="section-sub">
        How often each card appears in a dead hand (0 starters · 0 handtraps).
        A high value means the card is frequently "stuck" in hand — a potential garnet or bricker.
      </p>
      <table class="brick-table">
        <thead>
          <tr>
            <th>Card</th>
            <th>Role</th>
            <th title="Appearances in a dead hand / total appearances in hand">Brick rate</th>
            <th>Total appearances</th>
          </tr>
        </thead>
        <tbody>
          {#each topBricks as card}
            <tr class:highlight={card.dead_pct > 0.5}>
              <td class="card-name-cell">{card.name}</td>
              <td>
                <span
                  class="role-chip"
                  style="color:{roleColor(card.role)};border-color:{roleColor(card.role)}44;background:{roleColor(card.role)}18"
                >
                  {roleLabel(card.role)}
                </span>
              </td>
              <td class="brick-pct-cell">
                <div class="mini-bar-wrap">
                  <div class="mini-bar-track">
                    <div
                      class="mini-bar"
                      style="width:{card.dead_pct * 100}%;background:{card.dead_pct > 0.5 ? '#ef4444' : card.dead_pct > 0.25 ? '#f59e0b' : '#22c55e'}"
                    ></div>
                  </div>
                  <span class="mini-pct" style="color:{card.dead_pct > 0.5 ? '#ef4444' : card.dead_pct > 0.25 ? '#f59e0b' : '#22c55e'}">
                    {pct(card.dead_pct)}
                  </span>
                </div>
              </td>
              <td class="num-cell">{card.total_appearances.toLocaleString()}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>
  {/if}
</div>

<style>
  .page {
    max-width: 900px;
    margin: 0 auto;
    padding: 1.5rem 1rem 4rem;
    color: #e2e8f0;
  }

  /* Topbar */
  .topbar {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
  }
  .back { color: #94a3b8; text-decoration: none; font-size: 0.875rem; }
  .back:hover { color: #e2e8f0; }
  h1 { font-size: 1.25rem; font-weight: 600; margin: 0; flex: 1; }
  .badge {
    background: #1e293b; border: 1px solid #334155;
    border-radius: 999px; padding: 0.2rem 0.75rem;
    font-size: 0.75rem; color: #94a3b8;
  }

  .no-roles {
    background: #1e293b22; border: 1px solid #f59e0b44;
    border-radius: 8px; padding: 0.75rem 1rem;
    font-size: 0.85rem; color: #f59e0b;
    margin-bottom: 1rem;
  }
  .no-roles a { color: #fbbf24; text-decoration: none; font-weight: 600; }

  /* Controls */
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 1rem;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 0.875rem 1.25rem;
    margin-bottom: 1.25rem;
  }
  .ctrl-group { display: flex; align-items: center; gap: 0.625rem; flex-wrap: wrap; }
  .ctrl-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap; }
  .toggle { display: flex; gap: 0.25rem; }
  .toggle-btn {
    padding: 0.3rem 0.625rem; border-radius: 6px;
    border: 1px solid #334155; background: #0f172a;
    color: #94a3b8; font-size: 0.75rem; cursor: pointer;
    transition: all 0.15s;
  }
  .toggle-btn.active { background: #6366f1; border-color: #6366f1; color: #fff; }
  .toggle-btn:hover:not(.active) { border-color: #6366f1; color: #e2e8f0; }

  .run-btn {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1.25rem; border-radius: 8px;
    border: none; background: #6366f1; color: #fff;
    font-size: 0.875rem; font-weight: 600; cursor: pointer;
    transition: opacity 0.15s;
  }
  .run-btn:hover:not(:disabled) { opacity: 0.85; }
  .run-btn:disabled { opacity: 0.4; cursor: default; }

  .run-spinner {
    display: block;
    width: 13px;
    height: 13px;
    border: 2px solid rgba(255, 255, 255, 0.25);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.65s linear infinite;
    flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Comparison panel ─────────────────────────────────────── */
  .compare-panel {
    background: #0a0f1a;
    border: 1px solid #1e2d45;
    border-radius: 14px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    overflow: hidden;
  }

  .compare-header {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }
  .compare-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.875rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
  }
  .compare-sub {
    font-size: 0.7rem;
    color: #334155;
  }

  /* 4-column grid: label | GF | GS | delta */
  .compare-grid {
    display: grid;
    grid-template-columns: 1fr auto auto auto;
    gap: 0 1.5rem;
    align-items: center;
  }

  .compare-col-hd {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #475569;
    padding-bottom: 0.625rem;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 0.625rem;
    text-align: center;
  }
  .compare-col-hd:first-child { text-align: left; }

  .gf-hd { color: #818cf8; }
  .gs-hd { color: #34d399; }
  .delta-hd { color: #64748b; }

  .gf-label { display: block; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #818cf8; }
  .gs-label { display: block; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #34d399; }
  .hand-badge {
    display: block;
    font-size: 0.625rem;
    font-weight: 500;
    color: #334155;
    margin-top: 0.1rem;
    letter-spacing: 0.03em;
  }

  .compare-row-label {
    font-size: 0.8rem;
    color: #94a3b8;
    padding: 0.4rem 0;
    border-bottom: 1px solid #0f172a;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .row-hint {
    font-size: 0.65rem;
    color: #334155;
    font-style: italic;
  }
  .compare-val {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    text-align: center;
    padding: 0.4rem 0;
    border-bottom: 1px solid #0f172a;
  }
  .compare-val.muted {
    font-size: 0.875rem;
    color: #cbd5e1;
    font-weight: 600;
  }
  .compare-delta {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8125rem;
    font-weight: 700;
    text-align: center;
    padding: 0.4rem 0;
    border-bottom: 1px solid #0f172a;
    min-width: 64px;
  }

  /* Interpretation row */
  .interpret-row {
    display: flex;
    gap: 0;
    margin-top: 1rem;
    background: #0f172a;
    border-radius: 8px;
    overflow: hidden;
  }
  .interpret-item {
    flex: 1;
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.625rem 0.875rem;
    font-size: 0.75rem;
    color: #64748b;
    line-height: 1.5;
  }
  .interpret-tag {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.6rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    color: #475569;
    background: #1e293b;
    border-radius: 3px;
    padding: 0.1rem 0.3rem;
    flex-shrink: 0;
    margin-top: 0.05rem;
  }
  .interpret-sep {
    width: 1px;
    background: #1e293b;
  }
  .interpret-text { color: #94a3b8; }

  /* ── Detail switcher ─────────────────────────────────────── */
  .detail-switcher {
    display: flex;
    align-items: center;
    gap: 0.875rem;
    margin-bottom: 0.875rem;
  }
  .detail-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #475569;
    white-space: nowrap;
  }
  .view-toggle {
    display: flex;
    border: 1px solid #1e293b;
    border-radius: 8px;
    overflow: hidden;
  }
  .view-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.45rem 1rem;
    background: #0f172a;
    border: none;
    border-right: 1px solid #1e293b;
    color: #475569;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    letter-spacing: 0.02em;
  }
  .view-btn:last-child { border-right: none; }
  .view-btn:hover:not(.view-btn--active) {
    background: #1e293b;
    color: #94a3b8;
  }
  .view-btn--active {
    background: #1e293b;
    color: #e2e8f0;
  }
  .view-btn--active:first-child { color: #818cf8; }
  .view-btn--active:last-child { color: #34d399; }
  .hand-tag {
    font-size: 0.65rem;
    font-weight: 500;
    color: inherit;
    opacity: 0.6;
  }

  /* Rates */
  .rates-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    margin-bottom: 0.75rem;
  }
  @media (max-width: 600px) { .rates-grid { grid-template-columns: 1fr; } }

  .rate-card {
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 12px; padding: 1.25rem 1rem;
    display: flex; flex-direction: column; align-items: center; gap: 0.25rem;
    text-align: center;
  }
  .rate-icon { font-size: 0.75rem; color: #334155; }
  .rate-val { font-size: 2rem; font-weight: 800; line-height: 1; }
  .rate-label { font-size: 0.8rem; font-weight: 600; color: #e2e8f0; }
  .rate-sub { font-size: 0.7rem; color: #475569; }
  .rate-bar-track { width: 100%; height: 4px; background: #1e293b; border-radius: 2px; margin-top: 0.5rem; overflow: hidden; }
  .rate-bar { height: 100%; border-radius: 2px; transition: width 0.6s; }
  .rate-interp {
    font-size: 0.68rem;
    color: #475569;
    line-height: 1.5;
    margin-top: 0.25rem;
    text-align: center;
  }

  /* Averages row */
  .avgs-row {
    display: flex;
    align-items: center;
    gap: 0;
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 12px; padding: 1rem 1.5rem;
    margin-bottom: 1rem;
  }
  .avg-item { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 0.15rem; }
  .avg-val { font-size: 1.5rem; font-weight: 700; }
  .avg-label { font-size: 0.7rem; color: #475569; }
  .avg-qual { font-size: 0.75rem; font-weight: 600; }
  .avg-sep { width: 1px; height: 40px; background: #1e293b; margin: 0 0.5rem; }

  /* Sections */
  .section {
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 12px; padding: 1.25rem;
    margin-bottom: 1rem;
  }
  .section h2 {
    font-size: 0.875rem; font-weight: 600;
    color: #94a3b8; text-transform: uppercase;
    letter-spacing: 0.05em; margin: 0 0 0.75rem;
  }
  .section-sub { font-size: 0.8rem; color: #475569; margin: -0.25rem 0 0.875rem; line-height: 1.5; }

  /* Histogram */
  .histogram {
    display: flex;
    align-items: flex-end;
    gap: 1rem;
    height: 140px;
    margin-bottom: 0.875rem;
  }
  .hist-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    gap: 0.25rem;
  }
  .hist-pct { font-size: 0.75rem; font-weight: 600; color: #cbd5e1; }
  .hist-bar-track {
    flex: 1;
    width: 100%;
    display: flex;
    align-items: flex-end;
    background: #1e293b;
    border-radius: 4px 4px 0 0;
    overflow: hidden;
  }
  .hist-bar { width: 100%; border-radius: 4px 4px 0 0; transition: height 0.5s; }
  .hist-label { font-size: 0.7rem; color: #64748b; text-align: center; }

  .hist-interp {
    font-size: 0.775rem;
    color: #475569;
    line-height: 1.6;
    margin: 0;
    padding-top: 0.375rem;
    border-top: 1px solid #1e293b;
  }
  .hist-interp strong { color: #94a3b8; }

  /* Brick table */
  .brick-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  .brick-table th {
    text-align: left; color: #475569; font-weight: 500;
    padding: 0.3rem 0.5rem 0.6rem;
    border-bottom: 1px solid #1e293b;
    font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em;
  }
  .brick-table td { padding: 0.45rem 0.5rem; border-bottom: 1px solid #0f172a; }
  .brick-table tr.highlight td { background: #ef444408; }
  .card-name-cell { font-weight: 500; color: #e2e8f0; max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .num-cell { text-align: right; color: #64748b; font-size: 0.8rem; }

  .role-chip {
    display: inline-block; padding: 0.1rem 0.4rem;
    border-radius: 4px; border: 1px solid;
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.04em;
  }

  .brick-pct-cell { min-width: 140px; }
  .mini-bar-wrap { display: flex; align-items: center; gap: 0.5rem; }
  .mini-bar-track { flex: 1; height: 6px; background: #1e293b; border-radius: 3px; overflow: hidden; }
  .mini-bar { height: 100%; border-radius: 3px; transition: width 0.4s; }
  .mini-pct { font-size: 0.8rem; font-weight: 600; width: 44px; text-align: right; flex-shrink: 0; }
</style>
