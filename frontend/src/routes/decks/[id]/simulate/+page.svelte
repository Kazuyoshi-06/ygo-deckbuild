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

  let { data } = $props<{ data: { deckId: number; initial: SimulationData } }>();

  const deckId = untrack(() => data.deckId);
  let result = $state<SimulationData>(untrack(() => data.initial));
  let running = $state(false);
  let handSize = $state(5);
  let nSim = $state(10000);

  const SIM_OPTIONS = [1000, 5000, 10000, 25000, 50000];

  async function runSim() {
    running = true;
    try {
      const res = await fetch(`/api/v1/decks/${deckId}/simulate?n=${nSim}&hand=${handSize}`);
      if (res.ok) result = await res.json();
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
      starter:   '#22c55e',
      extender:  '#3b82f6',
      handtrap:  '#f59e0b',
      garnet:    '#ef4444',
      tech:      '#8b5cf6',
      boss:      '#ec4899',
      other:     '#6b7280',
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

  // Histogram bar max
  const maxDist = $derived(
    result.starter_dist.length > 0
      ? Math.max(...result.starter_dist.map(d => d.pct))
      : 1
  );

  // Top bricks: cards with highest dead_pct, limit 15
  const topBricks = $derived(
    [...result.brick_cards]
      .sort((a, b) => b.dead_pct - a.dead_pct)
      .slice(0, 15)
  );

  // Avg quality indicator
  function avgLabel(avg: number): string {
    if (avg >= 1.2) return 'Excellent';
    if (avg >= 0.9) return 'Bon';
    if (avg >= 0.6) return 'Moyen';
    return 'Faible';
  }
</script>

<svelte:head>
  <title>Simulateur — {result.deck_title} — YGO Intel</title>
</svelte:head>

<div class="page">
  <div class="topbar">
    <a href="/decks/{deckId}" class="back">← Deck</a>
    <h1>{result.deck_title}</h1>
    <span class="badge">{result.main_count} cartes · {result.n_simulations.toLocaleString()} simulations</span>
  </div>

  {#if !result.has_roles}
    <div class="no-roles">
      Les résultats sont basiques sans rôles tagués.
      <a href="/decks/{deckId}/probability">Taguez vos cartes →</a>
    </div>
  {/if}

  <!-- ── Controls ──────────────────────────────────────────────── -->
  <div class="controls">
    <div class="ctrl-group">
      <span class="ctrl-label">Main</span>
      <div class="toggle">
        {#each [5, 6] as h}
          <button
            type="button"
            class="toggle-btn"
            class:active={handSize === h}
            onclick={() => (handSize = h)}
          >
            {h} cartes {h === 5 ? '(going 1st)' : '(going 2nd)'}
          </button>
        {/each}
      </div>
    </div>

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
      {running ? 'Simulation en cours…' : '▶ Lancer la simulation'}
    </button>
  </div>

  <!-- ── Win / Medium / Dead rates ─────────────────────────────── -->
  <section class="rates-grid">
    <div class="rate-card win">
      <div class="rate-icon">▲</div>
      <div class="rate-val" style="color:{winColor(result.win_rate)}">{pct(result.win_rate)}</div>
      <div class="rate-label">Mains gagnantes</div>
      <div class="rate-sub">≥1 starter en main</div>
      <div class="rate-bar-track">
        <div class="rate-bar" style="width:{result.win_rate*100}%;background:{winColor(result.win_rate)}"></div>
      </div>
    </div>

    <div class="rate-card medium">
      <div class="rate-icon">◆</div>
      <div class="rate-val" style="color:#f59e0b">{pct(result.medium_rate)}</div>
      <div class="rate-label">Mains passables</div>
      <div class="rate-sub">0 starter · ≥1 handtrap</div>
      <div class="rate-bar-track">
        <div class="rate-bar" style="width:{result.medium_rate*100}%;background:#f59e0b"></div>
      </div>
    </div>

    <div class="rate-card dead">
      <div class="rate-icon">▼</div>
      <div class="rate-val" style="color:{deadColor(result.dead_rate)}">{pct(result.dead_rate)}</div>
      <div class="rate-label">Mains mortes</div>
      <div class="rate-sub">0 starter · 0 handtrap</div>
      <div class="rate-bar-track">
        <div class="rate-bar" style="width:{result.dead_rate*100}%;background:{deadColor(result.dead_rate)}"></div>
      </div>
    </div>
  </section>

  <!-- ── Averages ───────────────────────────────────────────────── -->
  <section class="avgs-row">
    <div class="avg-item">
      <span class="avg-val" style="color:#22c55e">{result.avg_starters.toFixed(2)}</span>
      <span class="avg-label">starters / main</span>
      <span class="avg-qual" style="color:{result.avg_starters >= 0.9 ? '#22c55e' : '#f59e0b'}">{avgLabel(result.avg_starters)}</span>
    </div>
    <div class="avg-sep"></div>
    <div class="avg-item">
      <span class="avg-val" style="color:#f59e0b">{result.avg_handtraps.toFixed(2)}</span>
      <span class="avg-label">handtraps / main</span>
      <span class="avg-qual" style="color:{result.avg_handtraps >= 0.8 ? '#22c55e' : '#f59e0b'}">{avgLabel(result.avg_handtraps)}</span>
    </div>
    <div class="avg-sep"></div>
    <div class="avg-item">
      <span class="avg-val" style="color:#ef4444">{result.avg_garnets.toFixed(2)}</span>
      <span class="avg-label">garnets / main</span>
      <span class="avg-qual" style="color:{result.avg_garnets <= 0.3 ? '#22c55e' : result.avg_garnets <= 0.5 ? '#f59e0b' : '#ef4444'}">
        {result.avg_garnets <= 0.3 ? 'OK' : result.avg_garnets <= 0.5 ? 'Élevé' : 'Trop élevé'}
      </span>
    </div>
  </section>

  <!-- ── Starter distribution histogram ────────────────────────── -->
  {#if result.starter_dist.length > 0}
    <section class="section">
      <h2>Distribution des starters en main ({result.hand_size} cartes)</h2>
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
    </section>
  {/if}

  <!-- ── Brick analysis ─────────────────────────────────────────── -->
  {#if topBricks.length > 0}
    <section class="section">
      <h2>Analyse des briques</h2>
      <p class="section-sub">
        Fréquence d'apparition dans une main morte (0 starter · 0 handtrap).
        Une haute valeur indique une carte souvent "inutile en main".
      </p>
      <table class="brick-table">
        <thead>
          <tr>
            <th>Carte</th>
            <th>Rôle</th>
            <th title="Fois vue dans une main morte / fois vue en main">Taux brique</th>
            <th>Apparitions totales</th>
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
    max-width: 860px;
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
    padding: 1rem 1.25rem;
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
    padding: 0.5rem 1.25rem; border-radius: 8px;
    border: none; background: #6366f1; color: #fff;
    font-size: 0.875rem; font-weight: 600; cursor: pointer;
    transition: opacity 0.15s;
  }
  .run-btn:hover:not(:disabled) { opacity: 0.85; }
  .run-btn:disabled { opacity: 0.4; cursor: default; }

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
