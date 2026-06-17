<script lang="ts">
  interface TopArchetype {
    label: string;
    deck_count: number;
  }

  interface OverviewStats {
    total_decks: number;
    total_cards_in_db: number;
    total_archetypes: number;
    top_archetypes: TopArchetype[];
  }

  interface MetaWinShareEntry {
    label: string;
    total_count: number;
    top8_count: number;
    meta_share: number;
    win_share: number;
  }

  interface MetaWinShareStats {
    total_placed_submissions: number;
    total_top8_submissions: number;
    entries: MetaWinShareEntry[];
    has_data: boolean;
  }

  interface TrendingEntry {
    label: string;
    trend: string;
    slope: number;
    current_share: number;
    deck_count: number;
  }

  interface TrendingStats {
    weeks_analyzed: number;
    rising: TrendingEntry[];
    falling: TrendingEntry[];
    has_data: boolean;
  }

  interface OcgToTcgEntry {
    archetype: string;
    ocg_release_date: string;
    card_count: number;
    predicted_tcg_date: string | null;
  }

  interface OcgToTcgPipelineStats {
    avg_gap_days: number | null;
    sample_size: number;
    pending: OcgToTcgEntry[];
    has_data: boolean;
  }

  let { data } = $props<{
    data: {
      overview: OverviewStats | null;
      metaWinShare: MetaWinShareStats | null;
      trending: TrendingStats | null;
      ocgTcgPipeline: OcgToTcgPipelineStats | null;
    };
  }>();
  let overview = $derived(data.overview);
  let metaWinShare = $derived(data.metaWinShare);
  let trending = $derived(data.trending);
  let ocgTcgPipeline = $derived(data.ocgTcgPipeline);

  function fmtDate(iso: string): string {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }

  const TREND_META: Record<string, { icon: string; color: string }> = {
    rising_strong: { icon: '↑↑', color: '#22c55e' },
    rising: { icon: '↑', color: '#86efac' },
    falling: { icon: '↓', color: '#f87171' },
    falling_strong: { icon: '↓↓', color: '#ef4444' },
  };

  function fmt(n: number) {
    return n.toLocaleString('en-US');
  }

  function pct(v: number): string {
    return `${(v * 100).toFixed(1)}%`;
  }

  // Positive = overperforming (wins more than its meta share would predict)
  function delta(entry: MetaWinShareEntry): number {
    return entry.win_share - entry.meta_share;
  }
</script>

<svelte:head>
  <title>Analytics — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <header class="page-header">
    <div>
      <span class="label">Platform</span>
      <h1 class="page-title">Analytics</h1>
      <p class="page-subtitle">Platform-wide statistics and insights</p>
    </div>
  </header>

  {#if !overview}
    <div class="empty-state">
      <div class="empty-icon" aria-hidden="true">◎</div>
      <p class="empty-title">Analytics unavailable</p>
      <p class="empty-sub">Could not reach the API. Make sure the backend is running.</p>
      <a href="/admin" class="btn-primary empty-cta">Go to admin panel</a>
    </div>
  {:else}
    <!-- Platform stats -->
    <section class="stats-grid">
      <div class="stat-card">
        <span class="stat-value">{fmt(overview.total_decks)}</span>
        <span class="stat-label">Decks stored</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{fmt(overview.total_cards_in_db)}</span>
        <span class="stat-label">Cards in database</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{fmt(overview.total_archetypes)}</span>
        <span class="stat-label">Archetypes tracked</span>
      </div>
    </section>

    <!-- Top archetypes -->
    {#if overview.top_archetypes.length > 0}
      <section class="section">
        <h2 class="section-title">Top Archetypes</h2>
        <div class="archetype-table">
          <div class="table-header">
            <span>Archetype</span>
            <span>Decks</span>
            <span></span>
          </div>
          {#each overview.top_archetypes as arch (arch.label)}
            <div class="table-row">
              <span class="arch-name">{arch.label}</span>
              <span class="arch-count">{arch.deck_count}</span>
              <a
                href="/analytics/archetypes/{encodeURIComponent(arch.label)}"
                class="arch-link"
              >View →</a>
            </div>
          {/each}
        </div>
      </section>
    {:else}
      <section class="section">
        <h2 class="section-title">Archetypes</h2>
        <p class="hint-text">
          Import decks and set an archetype label to unlock cross-deck analytics — core cards,
          flex spots, and frequency data.
        </p>
      </section>
    {/if}

    <!-- Trending archetypes -->
    {#if trending?.has_data && (trending.rising.length > 0 || trending.falling.length > 0)}
      <section class="section">
        <h2 class="section-title">Trending Archetypes</h2>
        <p class="hint-text">
          Meta share movement over the last {trending.weeks_analyzed} weeks, based on tournament submission dates.
        </p>
        <div class="trend-grid">
          <div class="trend-col">
            <h3 class="trend-col-title trend-col-title--up">↑ Rising</h3>
            {#if trending.rising.length === 0}
              <p class="trend-empty">No archetypes trending up right now.</p>
            {:else}
              <ul class="trend-list">
                {#each trending.rising as entry (entry.label)}
                  {@const meta = TREND_META[entry.trend]}
                  <li class="trend-item">
                    <a href="/analytics/archetypes/{encodeURIComponent(entry.label)}" class="trend-label">{entry.label}</a>
                    <span class="trend-badge" style="color:{meta.color};border-color:{meta.color}44;background:{meta.color}12">
                      {meta.icon} {pct(entry.current_share)}
                    </span>
                  </li>
                {/each}
              </ul>
            {/if}
          </div>
          <div class="trend-col">
            <h3 class="trend-col-title trend-col-title--down">↓ Falling</h3>
            {#if trending.falling.length === 0}
              <p class="trend-empty">No archetypes trending down right now.</p>
            {:else}
              <ul class="trend-list">
                {#each trending.falling as entry (entry.label)}
                  {@const meta = TREND_META[entry.trend]}
                  <li class="trend-item">
                    <a href="/analytics/archetypes/{encodeURIComponent(entry.label)}" class="trend-label">{entry.label}</a>
                    <span class="trend-badge" style="color:{meta.color};border-color:{meta.color}44;background:{meta.color}12">
                      {meta.icon} {pct(entry.current_share)}
                    </span>
                  </li>
                {/each}
              </ul>
            {/if}
          </div>
        </div>
      </section>
    {/if}

    <!-- OCG -> TCG pipeline -->
    {#if ocgTcgPipeline?.has_data}
      <section class="section">
        <h2 class="section-title">OCG → TCG Pipeline</h2>
        <p class="hint-text">
          Archetypes currently OCG-exclusive, with a predicted TCG arrival based on the historical
          average release gap{#if ocgTcgPipeline.avg_gap_days !== null}
            (~{Math.round(ocgTcgPipeline.avg_gap_days)} days, from {ocgTcgPipeline.sample_size} archetypes
            already released in both formats)
          {/if}. Heuristic only — actual release schedules vary.
        </p>
        <div class="pipeline-grid">
          {#each ocgTcgPipeline.pending as entry (entry.archetype)}
            <div class="pipeline-card">
              <span class="pipeline-archetype">{entry.archetype}</span>
              <div class="pipeline-dates">
                <span class="pipeline-date-item">
                  <span class="pipeline-date-label">OCG release</span>
                  <span class="pipeline-date-value">{fmtDate(entry.ocg_release_date)}</span>
                </span>
                {#if entry.predicted_tcg_date}
                  <span class="pipeline-arrow" aria-hidden="true">→</span>
                  <span class="pipeline-date-item">
                    <span class="pipeline-date-label">Predicted TCG</span>
                    <span class="pipeline-date-value pipeline-date-value--predicted">{fmtDate(entry.predicted_tcg_date)}</span>
                  </span>
                {/if}
              </div>
              <span class="pipeline-card-count">{entry.card_count} cards</span>
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <!-- Meta share vs win share -->
    {#if metaWinShare?.has_data}
      <section class="section">
        <h2 class="section-title">Meta Share vs Win Share</h2>
        <p class="hint-text">
          Meta share = % of all tournament submissions on record. Win share = % of top-8 placements.
          A positive Δ means the archetype wins more than its popularity alone would suggest.
        </p>
        <div class="msws-table">
          <div class="table-header msws-row">
            <span>Archetype</span>
            <span>Meta Share</span>
            <span>Win Share</span>
            <span>Δ</span>
          </div>
          {#each metaWinShare.entries as entry (entry.label)}
            {@const d = delta(entry)}
            <div class="table-row msws-row">
              <a href="/analytics/archetypes/{encodeURIComponent(entry.label)}" class="arch-name">{entry.label}</a>
              <div class="share-cell">
                <div class="share-bar-bg">
                  <div class="share-bar-fill share-bar-fill--meta" style="width: {pct(entry.meta_share)};"></div>
                </div>
                <span class="share-label">{pct(entry.meta_share)}</span>
              </div>
              <div class="share-cell">
                <div class="share-bar-bg">
                  <div class="share-bar-fill share-bar-fill--win" style="width: {pct(entry.win_share)};"></div>
                </div>
                <span class="share-label">{pct(entry.win_share)}</span>
              </div>
              <span
                class="delta-badge"
                class:delta-badge--up={d > 0.01}
                class:delta-badge--down={d < -0.01}
              >{d > 0 ? '+' : ''}{(d * 100).toFixed(1)}pp</span>
            </div>
          {/each}
        </div>
        <p class="footnote">
          Based on {metaWinShare.total_placed_submissions} tournament submission{metaWinShare.total_placed_submissions !== 1 ? 's' : ''}
          ({metaWinShare.total_top8_submissions} top-8 finish{metaWinShare.total_top8_submissions !== 1 ? 'es' : ''}).
        </p>
      </section>
    {/if}

    <!-- Archetype comparison -->
    {#if overview.top_archetypes.length >= 2}
      <section class="section">
        <h2 class="section-title">Compare Archetypes</h2>
        <p class="hint-text">
          Meta share, common/exclusive cards, and side-by-side evolution for 2–4 archetypes.
        </p>
        <a href="/analytics/compare" class="btn-secondary mt-sm">Compare archetypes →</a>
      </section>
    {/if}

    <!-- Matchup matrix -->
    <section class="section">
      <h2 class="section-title">Matchup Matrix</h2>
      <p class="hint-text">
        Win rates entre archétypes, basés sur les résultats de matches reportés.
        Enregistrez vos résultats depuis la page d'un deck → Matchups.
      </p>
      <a href="/analytics/matchups" class="btn-secondary mt-sm">Voir la matrice →</a>
    </section>

    <!-- Per-deck analytics prompt -->
    {#if overview.total_decks > 0}
      <section class="section">
        <h2 class="section-title">Per-Deck Analytics</h2>
        <p class="hint-text">
          Open any deck to explore its composition: type distribution, attribute spread, level
          curve and frame breakdown.
        </p>
        <a href="/decks" class="btn-secondary mt-sm">Browse decks →</a>
      </section>
    {/if}
  {/if}
</div>

<style>
  .page-body {
    padding-top: 2rem;
    padding-bottom: 5rem;
  }

  .page-header {
    margin-bottom: 2.5rem;
    padding-bottom: 2rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    margin-bottom: 0.25rem;
  }

  .page-subtitle {
    font-size: 0.9375rem;
    color: var(--text-tertiary);
  }

  /* Stats grid */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
    margin-bottom: 3rem;
  }

  .stat-card {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 1.5rem 1.75rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
  }

  .stat-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: var(--gold);
    letter-spacing: -0.03em;
    line-height: 1;
  }

  .stat-label {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  /* Sections */
  .section {
    margin-bottom: 3rem;
  }

  .section-title {
    font-size: 0.8125rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 1.25rem;
  }

  /* Archetype table */
  .archetype-table {
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .table-header {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 1rem;
    padding: 0.625rem 1.25rem;
    background: var(--bg-elevated);
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .table-row {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 1rem;
    align-items: center;
    padding: 0.875rem 1.25rem;
    border-top: 1px solid var(--border-subtle);
    transition: background var(--duration-fast) var(--ease-out);
  }

  .table-row:hover {
    background: var(--bg-surface);
  }

  .arch-name {
    font-size: 0.9375rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .arch-count {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.9375rem;
    font-weight: 600;
    color: var(--text-secondary);
    text-align: right;
    min-width: 3rem;
  }

  .arch-link {
    font-size: 0.8125rem;
    color: var(--gold);
    font-weight: 500;
    opacity: 0.7;
    transition: opacity var(--duration-fast) var(--ease-out);
    white-space: nowrap;
  }

  .arch-link:hover {
    opacity: 1;
  }

  /* Trending archetypes */
  .trend-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
  }

  .trend-col-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8125rem;
    font-weight: 700;
    margin-bottom: 0.75rem;
  }

  .trend-col-title--up {
    color: #4ade80;
  }

  .trend-col-title--down {
    color: #f87171;
  }

  .trend-empty {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
  }

  .trend-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .trend-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.625rem 0.875rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
  }

  .trend-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .trend-label:hover {
    color: var(--gold);
  }

  .trend-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    border: 1px solid;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    white-space: nowrap;
  }

  @media (max-width: 720px) {
    .trend-grid {
      grid-template-columns: 1fr;
    }
  }

  /* OCG -> TCG pipeline */
  .pipeline-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 1rem;
  }

  .pipeline-card {
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
    padding: 1rem 1.25rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
  }

  .pipeline-archetype {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.9375rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .pipeline-dates {
    display: flex;
    align-items: center;
    gap: 0.625rem;
  }

  .pipeline-date-item {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .pipeline-date-label {
    font-size: 0.625rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .pipeline-date-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .pipeline-date-value--predicted {
    color: var(--gold);
    font-weight: 600;
  }

  .pipeline-arrow {
    color: var(--text-tertiary);
    opacity: 0.6;
    align-self: center;
    margin-top: 0.75rem;
  }

  .pipeline-card-count {
    font-size: 0.6875rem;
    color: var(--text-tertiary);
  }

  /* Meta share vs win share */
  .msws-table {
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
    margin-bottom: 0.75rem;
  }

  .msws-row {
    grid-template-columns: 1fr 160px 160px 80px;
  }

  .share-cell {
    display: flex;
    align-items: center;
    gap: 0.625rem;
  }

  .share-bar-bg {
    flex: 1;
    height: 6px;
    background: var(--bg-elevated);
    border-radius: 99px;
    overflow: hidden;
  }

  .share-bar-fill {
    height: 100%;
    border-radius: 99px;
    transition: width 0.3s var(--ease-out);
  }

  .share-bar-fill--meta {
    background: #4e8cd4;
  }

  .share-bar-fill--win {
    background: var(--gold);
  }

  .share-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-secondary);
    width: 3.5rem;
    text-align: right;
    flex-shrink: 0;
  }

  .delta-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8125rem;
    font-weight: 700;
    color: var(--text-tertiary);
    text-align: right;
  }

  .delta-badge--up {
    color: #4ade80;
  }

  .delta-badge--down {
    color: #f87171;
  }

  .footnote {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    font-style: italic;
    margin-bottom: 1.25rem;
  }

  .hint-text {
    font-size: 0.9rem;
    color: var(--text-tertiary);
    line-height: 1.6;
    max-width: 56ch;
    margin-bottom: 1.25rem;
  }

  .btn-secondary {
    display: inline-flex;
    align-items: center;
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
    transition: color var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out);
  }

  .btn-secondary:hover {
    color: var(--text-primary);
    border-color: var(--gold);
  }

  .mt-sm {
    margin-top: 0.5rem;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 6rem 2rem;
    border: 1px dashed var(--border-default);
    border-radius: var(--radius-xl);
    background: var(--bg-surface);
  }

  .empty-icon {
    font-size: 2.5rem;
    color: var(--text-tertiary);
    margin-bottom: 1.25rem;
    line-height: 1;
  }

  .empty-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
  }

  .empty-sub {
    font-size: 0.9rem;
    color: var(--text-secondary);
    max-width: 36ch;
    line-height: 1.6;
  }

  .empty-cta {
    margin-top: 1.75rem;
  }
</style>
