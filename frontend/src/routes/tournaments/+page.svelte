<script lang="ts">
  import { onMount } from 'svelte';

  interface Tournament {
    id: number;
    name: string;
    event_date: string | null;
    format: string | null;
    location: string | null;
    participants_count: number | null;
    entry_count: number;
  }

  let tournaments: Tournament[] = $state([]);
  let loading = $state(true);
  let error = $state('');
  let query = $state('');
  let formatFilter = $state('');

  let formats: string[] = $derived(
    [...new Set(tournaments.map(t => t.format).filter((f): f is string => !!f))].sort()
  );

  let filtered: Tournament[] = $derived(
    tournaments.filter(t => {
      const matchQ = !query || t.name.toLowerCase().includes(query.toLowerCase());
      const matchF = !formatFilter || t.format === formatFilter;
      return matchQ && matchF;
    })
  );

  onMount(async () => {
    try {
      const res = await fetch('/api/v1/tournaments?limit=100&page=1');
      if (res.ok) {
        tournaments = await res.json();
      } else {
        error = 'Failed to load tournaments';
      }
    } catch {
      error = 'Network error — is the server running?';
    } finally {
      loading = false;
    }
  });

  function formatDate(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso + 'T00:00:00').toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
    });
  }
</script>

<svelte:head>
  <title>Tournaments — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <header class="page-header">
    <div>
      <span class="label">Competitive</span>
      <h1 class="page-title">Tournaments</h1>
    </div>
    <a href="/tournaments/new" class="btn-primary">+ Log result</a>
  </header>

  {#if !loading && !error}
    <div class="controls">
      <div class="search-wrap">
        <span class="search-icon" aria-hidden="true">⌕</span>
        <input
          type="text"
          class="search-input"
          placeholder="Search tournaments…"
          bind:value={query}
          aria-label="Search tournaments"
        />
        {#if query}
          <button class="search-clear" onclick={() => (query = '')} aria-label="Clear search">✕</button>
        {/if}
      </div>
      <select class="format-select" bind:value={formatFilter} aria-label="Filter by format">
        <option value="">All formats</option>
        {#each formats as fmt}
          <option value={fmt}>{fmt}</option>
        {/each}
      </select>
    </div>
  {/if}

  {#if loading}
    <div class="state-block">
      <span class="state-spinner" aria-hidden="true"></span>
      <p class="state-text">Loading tournaments…</p>
    </div>

  {:else if error}
    <div class="state-block">
      <span class="state-icon error-icon" aria-hidden="true">✕</span>
      <p class="state-text">{error}</p>
    </div>

  {:else if filtered.length === 0}
    <div class="state-block">
      {#if tournaments.length === 0}
        <span class="state-icon empty-icon" aria-hidden="true">⊞</span>
        <p class="state-title">No tournaments yet</p>
        <p class="state-sub">Log your first tournament result to get started.</p>
        <a href="/tournaments/new" class="btn-primary">+ Log result</a>
      {:else}
        <span class="state-icon empty-icon" aria-hidden="true">⌕</span>
        <p class="state-title">No matches</p>
        <p class="state-sub">Try adjusting your search or format filter.</p>
        <button class="btn-ghost" onclick={() => { query = ''; formatFilter = ''; }}>Clear filters</button>
      {/if}
    </div>

  {:else}
    <p class="result-count">
      {filtered.length} tournament{filtered.length !== 1 ? 's' : ''}
      {#if formatFilter || query}&thinsp;·&thinsp;filtered{/if}
    </p>
    <div class="tournament-list">
      {#each filtered as t (t.id)}
        <a href="/tournaments/{t.id}" class="tournament-card card">
          <div class="tc-head">
            <span class="tc-name">{t.name}</span>
            {#if t.format}
              <span class="tc-format-badge">{t.format}</span>
            {/if}
          </div>
          <div class="tc-meta">
            {#if t.event_date}
              <span class="tc-meta-item">
                <span class="tc-meta-icon" aria-hidden="true">◷</span>
                {formatDate(t.event_date)}
              </span>
            {/if}
            {#if t.location}
              <span class="tc-sep" aria-hidden="true">·</span>
              <span class="tc-meta-item">{t.location}</span>
            {/if}
            {#if t.participants_count}
              <span class="tc-sep" aria-hidden="true">·</span>
              <span class="tc-meta-item">{t.participants_count.toLocaleString()} players</span>
            {/if}
          </div>
          <div class="tc-footer">
            <span class="tc-entries">
              {t.entry_count} deck{t.entry_count !== 1 ? 's' : ''} logged
            </span>
            <span class="tc-arrow" aria-hidden="true">→</span>
          </div>
        </a>
      {/each}
    </div>
  {/if}
</div>

<style>
  .page-body {
    padding-top: 3rem;
    padding-bottom: 5rem;
  }

  .page-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1.5rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
  }

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    margin-top: 0.375rem;
  }

  /* ── Controls ────────────────────────────────────────────────────────────── */
  .controls {
    display: flex;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
  }

  .search-wrap {
    position: relative;
    flex: 1;
    min-width: 200px;
  }

  .search-icon {
    position: absolute;
    left: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-tertiary);
    font-size: 1rem;
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    padding: 0.5rem 2.25rem 0.5rem 2.25rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.875rem;
    outline: none;
    transition: border-color var(--duration-fast) var(--ease-out);
  }

  .search-input::placeholder { color: var(--text-tertiary); }
  .search-input:focus { border-color: var(--gold); }

  .search-clear {
    position: absolute;
    right: 0.625rem;
    top: 50%;
    transform: translateY(-50%);
    background: transparent;
    border: none;
    color: var(--text-tertiary);
    font-size: 0.75rem;
    cursor: pointer;
    padding: 0.2rem;
    line-height: 1;
    transition: color var(--duration-fast) var(--ease-out);
  }

  .search-clear:hover { color: var(--text-primary); }

  .format-select {
    padding: 0.5rem 2rem 0.5rem 0.75rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.875rem;
    cursor: pointer;
    outline: none;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23888' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 0.625rem center;
    transition: border-color var(--duration-fast) var(--ease-out);
  }

  .format-select:focus { border-color: var(--gold); }

  /* ── Result count ────────────────────────────────────────────────────────── */
  .result-count {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    margin-bottom: 1rem;
  }

  /* ── Tournament list ──────────────────────────────────────────────────────── */
  .tournament-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .tournament-card {
    display: block;
    padding: 1.125rem 1.375rem;
    text-decoration: none;
    transition:
      border-color var(--duration-fast) var(--ease-out),
      transform var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .tournament-card:hover {
    border-color: var(--border-strong);
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  }

  .tc-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
  }

  .tc-name {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.3;
  }

  .tc-format-badge {
    flex-shrink: 0;
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.2rem 0.55rem;
    background: var(--gold-dim);
    color: var(--gold);
    border: 1px solid rgba(201, 164, 73, 0.25);
    border-radius: var(--radius-sm);
  }

  .tc-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.375rem;
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    margin-bottom: 0.875rem;
  }

  .tc-meta-item { display: flex; align-items: center; gap: 0.3rem; }
  .tc-meta-icon { font-size: 0.75rem; }
  .tc-sep { opacity: 0.4; }

  .tc-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 0.75rem;
    border-top: 1px solid var(--border-subtle);
  }

  .tc-entries {
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--text-secondary);
  }

  .tc-arrow {
    font-size: 0.875rem;
    color: var(--text-tertiary);
    transition: color var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
  }

  .tournament-card:hover .tc-arrow {
    color: var(--gold);
    transform: translateX(3px);
  }

  /* ── States ──────────────────────────────────────────────────────────────── */
  .state-block {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    padding: 4rem 2rem;
    text-align: center;
  }

  .state-spinner {
    display: block;
    width: 28px;
    height: 28px;
    border: 2.5px solid var(--border-default);
    border-top-color: var(--gold);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .state-icon { font-size: 2rem; color: var(--text-tertiary); opacity: 0.5; }
  .error-icon { color: var(--error); }

  .state-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.125rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .state-text, .state-sub {
    font-size: 0.875rem;
    color: var(--text-tertiary);
    max-width: 32ch;
  }
</style>
