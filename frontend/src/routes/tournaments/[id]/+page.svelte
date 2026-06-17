<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';

  interface TournamentEntry {
    submission_id: number;
    deck_id: number;
    deck_title: string;
    archetype_label: string | null;
    player_name: string | null;
    player_country: string | null;
    placement: number | null;
    wins: number | null;
    losses: number | null;
    draws: number | null;
  }

  interface TournamentDetail {
    id: number;
    name: string;
    organizer: string | null;
    event_date: string | null;
    format: string | null;
    location: string | null;
    participants_count: number | null;
    notes: string | null;
    entries: TournamentEntry[];
  }

  let tournament: TournamentDetail | null = $state(null);
  let loading = $state(true);
  let error = $state('');

  function computeArchGroups(t: TournamentDetail | null): { label: string; count: number }[] {
    if (!t) return [];
    const counts: Record<string, number> = {};
    for (const e of t.entries) {
      const key = e.archetype_label ?? '—';
      counts[key] = (counts[key] ?? 0) + 1;
    }
    return Object.entries(counts)
      .map(([label, count]) => ({ label, count }))
      .sort((a, b) => b.count - a.count);
  }

  let archetypeGroups: { label: string; count: number }[] = $derived(computeArchGroups(tournament));

  onMount(async () => {
    const id = $page.params.id;
    try {
      const res = await fetch(`/api/v1/tournaments/${id}`);
      if (res.ok) {
        tournament = await res.json();
      } else if (res.status === 404) {
        error = 'Tournament not found';
      } else {
        error = 'Failed to load tournament';
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
      year: 'numeric', month: 'long', day: 'numeric',
    });
  }

  function ordinal(n: number): string {
    if (n >= 11 && n <= 13) return `${n}th`;
    const suffixes = ['th', 'st', 'nd', 'rd'];
    return `${n}${suffixes[n % 10] ?? 'th'}`;
  }

  function formatRecord(wins: number | null, losses: number | null, draws: number | null): string {
    if (wins === null && losses === null) return '';
    const w = wins ?? 0;
    const l = losses ?? 0;
    const d = draws ?? 0;
    return d > 0 ? `${w}W ${l}L ${d}D` : `${w}W ${l}L`;
  }

  function placementClass(n: number | null): string {
    if (n === 1) return 'p-gold';
    if (n === 2) return 'p-silver';
    if (n === 3) return 'p-bronze';
    return '';
  }
</script>

<svelte:head>
  <title>{tournament?.name ?? 'Tournament'} — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  {#if loading}
    <div class="state-block">
      <span class="state-spinner" aria-hidden="true"></span>
      <p class="state-text">Loading…</p>
    </div>

  {:else if error}
    <div class="state-block">
      <span class="state-icon" aria-hidden="true">✕</span>
      <p class="state-title">{error}</p>
      <a href="/tournaments" class="btn-ghost">← Back to tournaments</a>
    </div>

  {:else if tournament}
    <!-- Header -->
    <header class="page-header">
      <div>
        <a href="/tournaments" class="back-link">← Tournaments</a>
        <h1 class="page-title">{tournament.name}</h1>
      </div>
      <a href="/tournaments/new?tournament_id={tournament.id}" class="btn-primary">+ Add deck</a>
    </header>

    <!-- Tournament metadata card -->
    <div class="meta-card card">
      <div class="meta-grid">
        {#if tournament.event_date}
          <div class="meta-item">
            <span class="meta-key">Date</span>
            <span class="meta-val">{formatDate(tournament.event_date)}</span>
          </div>
        {/if}
        {#if tournament.format}
          <div class="meta-item">
            <span class="meta-key">Format</span>
            <span class="meta-val format-badge">{tournament.format}</span>
          </div>
        {/if}
        {#if tournament.location}
          <div class="meta-item">
            <span class="meta-key">Location</span>
            <span class="meta-val">{tournament.location}</span>
          </div>
        {/if}
        {#if tournament.participants_count}
          <div class="meta-item">
            <span class="meta-key">Players</span>
            <span class="meta-val">{tournament.participants_count.toLocaleString()}</span>
          </div>
        {/if}
        {#if tournament.organizer}
          <div class="meta-item">
            <span class="meta-key">Organizer</span>
            <span class="meta-val">{tournament.organizer}</span>
          </div>
        {/if}
        <div class="meta-item">
          <span class="meta-key">Entries</span>
          <span class="meta-val">{tournament.entries.length} deck{tournament.entries.length !== 1 ? 's' : ''}</span>
        </div>
      </div>
      {#if tournament.notes}
        <p class="meta-notes">{tournament.notes}</p>
      {/if}
    </div>

    <!-- Archetype breakdown -->
    {#if archetypeGroups.length > 0}
      <section class="section">
        <h2 class="section-title">Archetype breakdown</h2>
        <div class="arch-chips">
          {#each archetypeGroups as g}
            <div class="arch-chip" class:arch-chip-untagged={g.label === '—'}>
              <span class="arch-chip-label">{g.label}</span>
              <span class="arch-chip-count">{g.count}</span>
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <!-- Results table -->
    {#if tournament.entries.length === 0}
      <div class="state-block">
        <span class="state-icon" aria-hidden="true">⊞</span>
        <p class="state-title">No results logged yet</p>
        <p class="state-text">Add decks to this tournament to track placements.</p>
        <a href="/tournaments/new?tournament_id={tournament.id}" class="btn-primary">+ Add deck</a>
      </div>
    {:else}
      <section class="section">
        <h2 class="section-title">
          Results
          <span class="section-count">{tournament.entries.length}</span>
        </h2>
        <div class="results-table">
          <div class="results-head" aria-hidden="true">
            <span>Place</span>
            <span>Deck</span>
            <span>Archetype</span>
            <span>Player</span>
            <span>Record</span>
          </div>
          {#each tournament.entries as entry (entry.submission_id)}
            <div
              class="result-row"
              class:row-top3={entry.placement !== null && entry.placement <= 3}
            >
              <span class="placement {placementClass(entry.placement)}">
                {entry.placement !== null ? ordinal(entry.placement) : '—'}
              </span>
              <a href="/decks/{entry.deck_id}" class="deck-link">
                {entry.deck_title}
              </a>
              <span class="arch-cell">
                {#if entry.archetype_label}
                  <span class="arch-tag">{entry.archetype_label}</span>
                {:else}
                  <span class="arch-none">—</span>
                {/if}
              </span>
              <span class="player-cell">
                {#if entry.player_name}
                  {entry.player_name}
                  {#if entry.player_country}
                    <span class="country-code">{entry.player_country}</span>
                  {/if}
                {:else}
                  <span class="arch-none">—</span>
                {/if}
              </span>
              <span class="record-cell">{formatRecord(entry.wins, entry.losses, entry.draws)}</span>
            </div>
          {/each}
        </div>
      </section>
    {/if}
  {/if}
</div>

<style>
  .page-body {
    padding-top: 3rem;
    padding-bottom: 5rem;
    max-width: 900px;
  }

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
  }

  .back-link {
    display: inline-block;
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    text-decoration: none;
    margin-bottom: 0.5rem;
    transition: color var(--duration-fast) var(--ease-out);
  }

  .back-link:hover { color: var(--text-secondary); }

  .page-title {
    font-size: 1.875rem;
    font-weight: 700;
    line-height: 1.2;
  }

  /* ── Meta card ───────────────────────────────────────────────────────────── */
  .meta-card {
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
  }

  .meta-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 2rem;
  }

  .meta-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0;
  }

  .meta-key {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    min-width: 72px;
  }

  .meta-val {
    font-size: 0.9rem;
    color: var(--text-primary);
  }

  .format-badge {
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

  .meta-notes {
    margin-top: 0.875rem;
    padding-top: 0.875rem;
    border-top: 1px solid var(--border-subtle);
    font-size: 0.875rem;
    color: var(--text-secondary);
    line-height: 1.55;
  }

  /* ── Sections ────────────────────────────────────────────────────────────── */
  .section {
    margin-bottom: 2rem;
  }

  .section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8125rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 0.875rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .section-count {
    font-size: 0.75rem;
    padding: 0.1rem 0.45rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    color: var(--text-tertiary);
    font-weight: 500;
    letter-spacing: 0;
    text-transform: none;
  }

  /* ── Archetype chips ──────────────────────────────────────────────────────── */
  .arch-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .arch-chip {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.625rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
  }

  .arch-chip-untagged {
    opacity: 0.6;
  }

  .arch-chip-label {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    font-weight: 500;
  }

  .arch-chip-count {
    font-size: 0.6875rem;
    font-weight: 700;
    color: var(--text-tertiary);
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 999px;
    padding: 0.05rem 0.4rem;
    min-width: 18px;
    text-align: center;
  }

  /* ── Results table ──────────────────────────────────────────────────────── */
  .results-table {
    display: flex;
    flex-direction: column;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
    overflow-x: auto;
  }

  .results-head,
  .result-row {
    display: grid;
    grid-template-columns: 80px 1fr 160px 180px 100px;
    align-items: center;
    gap: 0;
    min-width: 600px;
  }

  .results-head {
    padding: 0.6rem 1rem;
    background: var(--bg-elevated);
    border-bottom: 1px solid var(--border-subtle);
  }

  .results-head span {
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    padding: 0 0.5rem;
  }

  .results-head span:first-child { padding-left: 0; }

  .result-row {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border-subtle);
    transition: background var(--duration-fast) var(--ease-out);
  }

  .result-row:last-child { border-bottom: none; }

  .result-row:hover { background: var(--bg-elevated); }

  .row-top3 {
    background: rgba(201, 164, 73, 0.03);
  }

  .row-top3:hover {
    background: rgba(201, 164, 73, 0.07);
  }

  /* Placement column */
  .placement {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.875rem;
    font-weight: 700;
    color: var(--text-secondary);
    padding-right: 0.5rem;
  }

  .p-gold { color: var(--gold); }
  .p-silver { color: #c0c0c0; }
  .p-bronze { color: #cd7f32; }

  /* Deck link */
  .deck-link {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    text-decoration: none;
    padding: 0 0.5rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    transition: color var(--duration-fast) var(--ease-out);
  }

  .deck-link:hover { color: var(--gold); }

  /* Archetype */
  .arch-cell {
    padding: 0 0.5rem;
    overflow: hidden;
  }

  .arch-tag {
    display: inline-block;
    font-size: 0.75rem;
    color: var(--text-tertiary);
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 0.15rem 0.45rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }

  .arch-none {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    opacity: 0.4;
  }

  /* Player */
  .player-cell {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    padding: 0 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    overflow: hidden;
  }

  .country-code {
    font-size: 0.6875rem;
    color: var(--text-tertiary);
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 0.1rem 0.35rem;
    white-space: nowrap;
    flex-shrink: 0;
  }

  /* Record */
  .record-cell {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-tertiary);
    padding: 0 0.5rem;
    text-align: right;
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
  .state-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.125rem;
    font-weight: 700;
    color: var(--text-primary);
  }
  .state-text { font-size: 0.875rem; color: var(--text-tertiary); }
</style>
