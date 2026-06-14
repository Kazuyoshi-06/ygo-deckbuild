<script lang="ts">
  import { untrack } from 'svelte';

  interface CardTrend {
    card_id: number;
    name: string;
    frame_type: string;
    monthly_presence: number[];
    trend: string;
    slope: number;
    avg_presence: number;
    peak_presence: number;
  }

  interface EvolutionData {
    archetype_label: string;
    months: string[];
    deck_counts: number[];
    total_decks: number;
    cards: CardTrend[];
    has_data: boolean;
  }

  let { data } = $props<{ data: { label: string; evolution: EvolutionData | null } }>();
  const label = untrack(() => data.label);
  const evo = untrack(() => data.evolution);

  const TREND_META: Record<string, { icon: string; label: string; color: string }> = {
    rising_strong: { icon: '↑↑', label: 'Forte hausse', color: '#22c55e' },
    rising:        { icon: '↑',  label: 'En hausse',    color: '#86efac' },
    stable:        { icon: '→',  label: 'Stable',       color: '#94a3b8' },
    falling:       { icon: '↓',  label: 'En baisse',    color: '#f87171' },
    falling_strong:{ icon: '↓↓', label: 'Forte baisse', color: '#ef4444' },
  };

  const FRAME_COLORS: Record<string, string> = {
    spell:   '#4ade80', trap: '#c084fc', normal: '#fbbf24',
    effect:  '#fb923c', fusion: '#a855f7', synchro: '#e2e8f0',
    xyz:     '#94a3b8', link: '#60a5fa', ritual: '#818cf8',
  };

  function frameColor(ft: string): string {
    return FRAME_COLORS[ft?.toLowerCase()] ?? '#64748b';
  }

  function pct(v: number): string {
    return (v * 100).toFixed(0) + '%';
  }

  // Cell background: green gradient based on presence
  function cellBg(presence: number): string {
    if (presence === 0) return 'transparent';
    const alpha = Math.round(presence * 0.75 * 255).toString(16).padStart(2, '0');
    if (presence >= 0.75) return `#22c55e${alpha}`;
    if (presence >= 0.40) return `#f59e0b${alpha}`;
    return `#94a3b8${alpha}`;
  }

  function cellText(presence: number): string {
    if (presence === 0) return '—';
    return pct(presence);
  }

  // Format month: "2026-01" → "Jan 26"
  function fmtMonth(m: string): string {
    const [y, mo] = m.split('-');
    const names = ['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc'];
    return `${names[parseInt(mo) - 1]} ${y.slice(2)}`;
  }

  // Filter controls
  let trendFilter = $state<string>('all');
  let minPresence = $state(0);
  let searchTerm = $state('');

  const TREND_FILTERS = [
    { key: 'all',          label: 'Tous' },
    { key: 'rising_strong',label: '↑↑ Forte hausse' },
    { key: 'rising',       label: '↑ Hausse' },
    { key: 'stable',       label: '→ Stable' },
    { key: 'falling',      label: '↓ Baisse' },
    { key: 'falling_strong',label: '↓↓ Forte baisse' },
  ];

  const filteredCards = $derived(
    (evo?.cards ?? []).filter((c: CardTrend) => {
      if (trendFilter !== 'all' && c.trend !== trendFilter) return false;
      if (c.avg_presence < minPresence / 100) return false;
      if (searchTerm && !c.name.toLowerCase().includes(searchTerm.toLowerCase())) return false;
      return true;
    })
  );
</script>

<svelte:head>
  <title>Évolution — {label} — YGO Intel</title>
</svelte:head>

<div class="page">
  <div class="topbar">
    <a href="/analytics/archetypes/{label}" class="back">← {label}</a>
    <h1>Évolution <span class="arch-name">{label}</span></h1>
    {#if evo?.has_data}
      <span class="badge">{evo.total_decks} decks · {evo.months.length} mois</span>
    {/if}
  </div>

  {#if !evo || !evo.has_data}
    <div class="empty">
      <p>Pas assez de données pour afficher l'évolution de <strong>{label}</strong>.</p>
      <p class="empty-sub">Importez des decks de cet archétype avec des dates variées pour voir les tendances apparaître.</p>
      <a href="/analytics/archetypes/{label}" class="back-link">← Retour à l'archétype</a>
    </div>
  {:else}
    <!-- ── Trend legend ──────────────────────────────────────── -->
    <div class="legend">
      {#each Object.entries(TREND_META) as [key, meta]}
        <span class="leg-item" style="color:{meta.color}">
          {meta.icon} {meta.label}
        </span>
      {/each}
    </div>

    <!-- ── Filters ───────────────────────────────────────────── -->
    <div class="filters">
      <input
        class="search-input"
        type="text"
        placeholder="Rechercher une carte…"
        bind:value={searchTerm}
      />

      <div class="filter-group">
        {#each TREND_FILTERS as f}
          <button
            type="button"
            class="filter-btn"
            class:active={trendFilter === f.key}
            onclick={() => (trendFilter = f.key)}
          >{f.label}</button>
        {/each}
      </div>

      <label class="presence-filter">
        <span>Présence min.</span>
        <input type="range" min="0" max="80" step="5" bind:value={minPresence} />
        <span class="range-val">{minPresence}%</span>
      </label>
    </div>

    <!-- ── Evolution table ──────────────────────────────────── -->
    <div class="table-wrap">
      <table class="evo-table">
        <thead>
          <tr>
            <th class="col-card">Carte</th>
            <th class="col-avg">Moy.</th>
            <th class="col-trend">Tendance</th>
            {#each evo.months as m, i}
              <th class="col-month" title="{m} — {evo.deck_counts[i]} deck(s)">
                {fmtMonth(m)}
                <span class="deck-count">{evo.deck_counts[i]}d</span>
              </th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each filteredCards as card (card.card_id)}
            {@const meta = TREND_META[card.trend]}
            <tr>
              <td class="col-card">
                <span class="card-dot" style="background:{frameColor(card.frame_type)}"></span>
                <span class="card-name">{card.name}</span>
              </td>
              <td class="col-avg num">{pct(card.avg_presence)}</td>
              <td class="col-trend">
                <span class="trend-badge" style="color:{meta.color};border-color:{meta.color}44;background:{meta.color}12">
                  {meta.icon}
                  {#if Math.abs(card.slope) >= 0.02}
                    <span class="slope">{card.slope > 0 ? '+' : ''}{(card.slope * 100).toFixed(0)}pp/m</span>
                  {/if}
                </span>
              </td>
              {#each evo.months as m, i}
                {@const presence = card.monthly_presence[i] ?? 0}
                <td
                  class="col-month num"
                  style="background:{cellBg(presence)}"
                  title="{card.name} — {m} : {pct(presence)}"
                >
                  {cellText(presence)}
                </td>
              {/each}
            </tr>
          {/each}

          {#if filteredCards.length === 0}
            <tr>
              <td colspan={3 + evo.months.length} class="no-results">
                Aucune carte ne correspond aux filtres.
              </td>
            </tr>
          {/if}
        </tbody>
      </table>
    </div>

    <p class="footnote">
      Présence = % des decks de l'archétype joués ce mois-là qui incluent cette carte.
      Basé sur la soumission la plus récente de chaque deck.
    </p>
  {/if}
</div>

<style>
  .page {
    max-width: 1100px;
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
  .back { color: #94a3b8; text-decoration: none; font-size: 0.875rem; white-space: nowrap; }
  .back:hover { color: #e2e8f0; }
  h1 { font-size: 1.25rem; font-weight: 600; margin: 0; }
  .arch-name { color: #818cf8; }
  .badge {
    background: #1e293b; border: 1px solid #334155;
    border-radius: 999px; padding: 0.2rem 0.75rem;
    font-size: 0.75rem; color: #94a3b8; white-space: nowrap;
  }

  /* Legend */
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem 1.25rem;
    font-size: 0.8rem;
    margin-bottom: 1rem;
  }
  .leg-item { font-weight: 600; }

  /* Filters */
  .filters {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 0.875rem 1rem;
    margin-bottom: 1rem;
  }
  .search-input {
    background: #1e293b; border: 1px solid #334155;
    border-radius: 6px; padding: 0.35rem 0.75rem;
    color: #e2e8f0; font-size: 0.85rem; width: 200px;
  }
  .search-input:focus { outline: none; border-color: #6366f1; }
  .filter-group { display: flex; flex-wrap: wrap; gap: 0.25rem; }
  .filter-btn {
    padding: 0.25rem 0.6rem; border-radius: 5px;
    border: 1px solid #334155; background: transparent;
    color: #94a3b8; font-size: 0.75rem; cursor: pointer;
    transition: all 0.12s;
  }
  .filter-btn.active { background: #6366f1; border-color: #6366f1; color: #fff; }
  .filter-btn:hover:not(.active) { border-color: #6366f1; color: #e2e8f0; }
  .presence-filter {
    display: flex; align-items: center; gap: 0.5rem;
    font-size: 0.8rem; color: #64748b; margin-left: auto;
  }
  .presence-filter input[type="range"] { width: 80px; accent-color: #6366f1; }
  .range-val { font-weight: 600; color: #e2e8f0; min-width: 32px; }

  /* Table */
  .table-wrap {
    overflow-x: auto;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
  }

  .evo-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
    white-space: nowrap;
  }

  .evo-table th {
    padding: 0.5rem 0.6rem;
    text-align: left;
    background: #0f172a;
    border-bottom: 1px solid #1e293b;
    color: #475569;
    font-weight: 500;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    position: sticky;
    top: 0;
    z-index: 1;
  }
  .evo-table th.col-card { position: sticky; left: 0; z-index: 2; min-width: 200px; }
  .evo-table th.col-month { text-align: center; }

  .evo-table td {
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid #0a0f1a;
  }
  .evo-table tr:last-child td { border-bottom: none; }
  .evo-table tr:hover td { background-color: #ffffff08; }

  .col-card {
    position: sticky;
    left: 0;
    background: #0f172a;
    z-index: 1;
    min-width: 200px;
    max-width: 250px;
  }
  .evo-table tr:hover .col-card { background: #1a2337; }

  .card-dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    margin-right: 0.4rem;
    flex-shrink: 0;
    vertical-align: middle;
  }
  .card-name {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 190px;
    display: inline-block;
    vertical-align: middle;
  }

  .col-avg { text-align: right; color: #64748b; }
  .col-trend { white-space: nowrap; }
  .col-month {
    text-align: center;
    font-size: 0.78rem;
    min-width: 58px;
    transition: background 0.2s;
  }
  .num { font-variant-numeric: tabular-nums; }

  .deck-count { display: block; font-size: 0.65rem; color: #334155; font-weight: 400; }

  .trend-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
    border: 1px solid;
    font-size: 0.75rem;
    font-weight: 700;
  }
  .slope { font-weight: 400; font-size: 0.7rem; opacity: 0.85; }

  .no-results { text-align: center; color: #475569; padding: 2rem; }

  /* Empty state */
  .empty {
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 12px; padding: 3rem 2rem;
    text-align: center; color: #94a3b8;
  }
  .empty p { margin: 0 0 0.5rem; }
  .empty-sub { font-size: 0.85rem; color: #475569; }
  .back-link { display: inline-block; margin-top: 1.5rem; color: #818cf8; text-decoration: none; font-size: 0.875rem; }
  .back-link:hover { text-decoration: underline; }

  .footnote { font-size: 0.75rem; color: #334155; margin-top: 0.75rem; font-style: italic; }
</style>
