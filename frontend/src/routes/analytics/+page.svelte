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

  let { data } = $props<{ data: { overview: OverviewStats | null } }>();
  let overview = $derived(data.overview);

  function fmt(n: number) {
    return n.toLocaleString('en-US');
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
