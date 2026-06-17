<script lang="ts">
  import { untrack } from 'svelte';

  interface MatrixCell {
    wins: number;
    losses: number;
    draws: number;
    total: number;
    win_rate: number | null;
  }

  interface ArchetypeMatrixRow {
    archetype: string;
    total_matches: number;
    avg_win_rate: number | null;
    vs: Record<string, MatrixCell>;
  }

  interface MatrixData {
    archetypes: string[];
    rows: ArchetypeMatrixRow[];
    total_matches: number;
    has_data: boolean;
  }

  let { data } = $props<{ data: { matrix: MatrixData | null } }>();
  const matrix = untrack(() => data.matrix);

  // ── Filter ──────────────────────────────────────────────────────────
  let search = $state('');

  const filteredRows = $derived(
    !matrix
      ? []
      : search.trim()
      ? matrix.rows.filter((r: ArchetypeMatrixRow) =>
          r.archetype.toLowerCase().includes(search.toLowerCase())
        )
      : matrix.rows
  );

  const visibleArchs = $derived(
    !matrix ? [] : matrix.archetypes
  );

  // ── Cell helpers ────────────────────────────────────────────────────
  function cellBg(cell: MatrixCell | undefined): string {
    if (!cell || cell.win_rate === null) return 'transparent';
    const wr = cell.win_rate;
    if (wr >= 0.65) return '#14532d44';
    if (wr >= 0.55) return '#16653444';
    if (wr >= 0.45) return '#1e3a5f44';
    if (wr >= 0.35) return '#7c2d1244';
    return '#4c0d0d44';
  }

  function cellColor(cell: MatrixCell | undefined): string {
    if (!cell || cell.win_rate === null) return '#334155';
    const wr = cell.win_rate;
    if (wr >= 0.65) return '#4ade80';
    if (wr >= 0.55) return '#86efac';
    if (wr >= 0.45) return '#94a3b8';
    if (wr >= 0.35) return '#fca5a5';
    return '#f87171';
  }

  function wrStr(cell: MatrixCell | undefined): string {
    if (!cell || cell.win_rate === null) return '—';
    return Math.round(cell.win_rate * 100) + '%';
  }

  function avgColor(wr: number | null): string {
    if (wr === null) return '#334155';
    if (wr >= 0.6) return '#4ade80';
    if (wr >= 0.5) return '#94a3b8';
    return '#f87171';
  }
</script>

<svelte:head>
  <title>Matchup Matrix — YGO Intel</title>
</svelte:head>

<div class="page">
  <div class="topbar">
    <a href="/analytics" class="back">← Analytics</a>
    <h1>Matchup Matrix</h1>
    {#if matrix}
      <span class="total-badge">{matrix.total_matches} matches reportés</span>
    {/if}
  </div>

  {#if !matrix || !matrix.has_data}
    <div class="empty-state">
      <div class="empty-icon">◎</div>
      <h2>Pas encore de données de matchup</h2>
      <p>
        Ouvre la page d'un deck et utilise <strong>Matchups</strong> pour enregistrer tes résultats de tournoi.<br/>
        La matrice se construit automatiquement à partir des données reportées.
      </p>
      <a href="/decks" class="btn-go">Voir mes decks</a>
    </div>
  {:else}
    <p class="matrix-hint">
      Taux de victoire de chaque archétype (ligne) contre chaque archétype adverse (colonne).
      Calculé sur <strong>{matrix.total_matches} match{matrix.total_matches > 1 ? 's' : ''}</strong> reportés.
      <span class="hint-formula">W = (V + 0.5×N) / total</span>
    </p>

    <div class="controls">
      <input
        type="text"
        bind:value={search}
        placeholder="Filtrer par archétype..."
        class="search-input"
      />
    </div>

    <!-- Matrix table — horizontally scrollable -->
    <div class="table-wrap">
      <table class="matrix-table">
        <thead>
          <tr>
            <th class="corner-cell">Mon archétype ↓ / Adversaire →</th>
            {#each visibleArchs as opp}
              <th class="header-opp" title={opp}>{opp.slice(0, 10)}{opp.length > 10 ? '…' : ''}</th>
            {/each}
            <th class="header-avg">Moy.</th>
            <th class="header-total">Matchs</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredRows as row}
            <tr>
              <td class="row-label">
                <a href="/analytics/matchups/{encodeURIComponent(row.archetype)}" class="arch-link">
                  {row.archetype}
                </a>
              </td>
              {#each visibleArchs as opp}
                {@const cell = row.vs[opp]}
                <td
                  class="cell"
                  class:self-cell={opp === row.archetype}
                  style="background:{opp === row.archetype ? 'transparent' : cellBg(cell)};color:{opp === row.archetype ? '#1e293b' : cellColor(cell)}"
                  title={cell ? `${cell.wins}V / ${cell.draws}N / ${cell.losses}D (${cell.total} matchs)` : 'Aucune donnée'}
                >
                  {opp === row.archetype ? '—' : wrStr(cell)}
                </td>
              {/each}
              <td class="cell avg-cell" style="color:{avgColor(row.avg_win_rate)}">
                {row.avg_win_rate !== null ? Math.round(row.avg_win_rate * 100) + '%' : '—'}
              </td>
              <td class="cell total-cell">{row.total_matches}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Legend -->
    <div class="legend">
      <span class="leg-item" style="color:#4ade80">■ ≥ 65% favorable</span>
      <span class="leg-item" style="color:#86efac">■ 55-64% bon</span>
      <span class="leg-item" style="color:#94a3b8">■ 45-54% équilibré</span>
      <span class="leg-item" style="color:#fca5a5">■ 35-44% difficile</span>
      <span class="leg-item" style="color:#f87171">■ &lt; 35% défavorable</span>
      <span class="leg-item" style="color:#334155">■ — aucune donnée</span>
    </div>
  {/if}
</div>

<style>
  .page {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1.5rem 1rem 4rem;
    color: #e2e8f0;
  }

  .topbar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }
  .back { color: #94a3b8; text-decoration: none; font-size: 0.875rem; }
  .back:hover { color: #e2e8f0; }
  h1 { font-size: 1.25rem; font-weight: 700; margin: 0; flex: 1; }
  .total-badge {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 20px;
    padding: 0.2rem 0.7rem;
    font-size: 0.75rem;
    color: #94a3b8;
  }

  .matrix-hint {
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 0.75rem;
    line-height: 1.5;
  }
  .hint-formula {
    display: inline-block;
    background: #1e293b;
    border-radius: 4px;
    padding: 0.1rem 0.4rem;
    font-family: monospace;
    font-size: 0.78rem;
    color: #94a3b8;
  }

  .controls { margin-bottom: 0.75rem; }
  .search-input {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #e2e8f0;
    font-size: 0.875rem;
    padding: 0.45rem 0.75rem;
    width: 280px;
    max-width: 100%;
  }
  .search-input:focus { outline: none; border-color: #a855f7; }

  /* Matrix table */
  .table-wrap {
    overflow-x: auto;
    border: 1px solid #1e293b;
    border-radius: 12px;
    background: #0f172a;
  }

  .matrix-table {
    border-collapse: collapse;
    font-size: 0.78rem;
    min-width: 100%;
  }

  .corner-cell {
    background: #0a1628;
    color: #334155;
    font-size: 0.65rem;
    font-weight: 400;
    padding: 0.6rem 0.75rem;
    text-align: left;
    white-space: nowrap;
    position: sticky;
    left: 0;
    z-index: 2;
    border-right: 1px solid #1e293b;
    border-bottom: 1px solid #1e293b;
    min-width: 160px;
  }

  .header-opp {
    background: #0a1628;
    color: #475569;
    font-weight: 600;
    padding: 0.5rem 0.5rem;
    text-align: center;
    white-space: nowrap;
    border-bottom: 1px solid #1e293b;
    min-width: 56px;
    font-size: 0.7rem;
  }

  .header-avg {
    background: #0a1628;
    color: #475569;
    font-weight: 700;
    padding: 0.5rem 0.5rem;
    text-align: center;
    border-bottom: 1px solid #1e293b;
    border-left: 1px solid #334155;
    min-width: 48px;
  }

  .header-total {
    background: #0a1628;
    color: #334155;
    font-weight: 600;
    padding: 0.5rem 0.5rem;
    text-align: center;
    border-bottom: 1px solid #1e293b;
    min-width: 48px;
  }

  .row-label {
    background: #0a1628;
    padding: 0.45rem 0.75rem;
    white-space: nowrap;
    font-weight: 600;
    font-size: 0.8rem;
    border-right: 1px solid #1e293b;
    position: sticky;
    left: 0;
    z-index: 1;
  }
  .arch-link { color: #e2e8f0; text-decoration: none; }
  .arch-link:hover { color: #a855f7; }

  .cell {
    padding: 0.4rem 0.5rem;
    text-align: center;
    font-weight: 700;
    font-size: 0.78rem;
    border-left: 1px solid #0f172a;
    transition: background 0.1s;
  }
  .cell.self-cell { background: #0a1628 !important; color: #1e293b !important; }
  .cell.avg-cell { border-left: 1px solid #334155; }
  .cell.total-cell { color: #334155 !important; font-weight: 400; }

  tr:hover .cell:not(.self-cell) { filter: brightness(1.15); }

  /* Legend */
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-top: 0.875rem;
    font-size: 0.75rem;
  }
  .leg-item { display: flex; align-items: center; gap: 0.3rem; }

  /* Empty state */
  .empty-state {
    text-align: center;
    padding: 4rem 1rem;
    background: #0f172a;
    border: 1px dashed #1e293b;
    border-radius: 16px;
    margin-top: 1rem;
  }
  .empty-icon { font-size: 2.5rem; color: #334155; margin-bottom: 1rem; }
  .empty-state h2 { font-size: 1.1rem; font-weight: 700; margin: 0 0 0.75rem; color: #94a3b8; }
  .empty-state p { font-size: 0.875rem; color: #475569; margin: 0 0 1.5rem; line-height: 1.6; }
  .btn-go {
    display: inline-block;
    background: #a855f7;
    color: white;
    font-weight: 700;
    font-size: 0.875rem;
    padding: 0.6rem 1.5rem;
    border-radius: 8px;
    text-decoration: none;
  }
  .btn-go:hover { background: #9333ea; }
</style>
