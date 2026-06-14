<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';

  interface Deck {
    id: number;
    title: string;
    archetype_label: string | null;
    source_type: string;
    notes: string | null;
    tags: string[];
    created_at: string;
    updated_at: string;
  }

  const PRESET_TAGS = ['Top 8', 'Locals', 'Theory', 'Budget', 'Tested', 'Online', 'Casual'];

  let { data } = $props<{ data: { items: Deck[]; total: number } }>();

  let filterTag = $state('');

  const filteredDecks = $derived(
    filterTag
      ? data.items.filter((d: Deck) => d.tags.includes(filterTag))
      : data.items
  );

  const usedTags: string[] = $derived.by(() => {
    const all: string[] = data.items.flatMap((d: Deck): string[] => d.tags);
    return Array.from(new Set<string>(all)).filter((t) => PRESET_TAGS.includes(t));
  });

  const sourceLabel: Record<string, string> = {
    ydk_import: 'YDK',
    manual: 'Manual',
    scraped: 'Scraped',
    api_import: 'API',
  };

  // ── Selection mode ──────────────────────────────────────────────────────────
  let selectMode = $state(false);
  let selected = $state(new Set<number>());
  let confirmDelete = $state(false);
  let deleting = $state(false);

  function enterSelectMode() {
    selectMode = true;
    selected = new Set();
    confirmDelete = false;
  }

  function exitSelectMode() {
    selectMode = false;
    selected = new Set();
    confirmDelete = false;
  }

  function toggleSelect(id: number) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    selected = next;
  }

  function toggleAll() {
    if (selected.size === data.items.length) {
      selected = new Set();
    } else {
      selected = new Set(data.items.map((d: Deck) => d.id));
    }
  }

  async function deleteSelected() {
    if (selected.size === 0) return;
    deleting = true;
    try {
      await Promise.all(
        [...selected].map((id) => fetch(`/api/v1/decks/${id}`, { method: 'DELETE' }))
      );
      exitSelectMode();
      await invalidateAll();
    } catch {
      // silent
    } finally {
      deleting = false;
    }
  }

  const allSelected = $derived(data.items.length > 0 && selected.size === data.items.length);
  const someSelected = $derived(selected.size > 0);

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }
</script>

<svelte:head>
  <title>Decks — YGO Intel</title>
</svelte:head>

<!-- Selection bar (sticky, appears in select mode) -->
{#if selectMode}
  <div class="select-bar">
    <div class="page-container select-bar-inner">
      <label class="select-all-label">
        <input
          type="checkbox"
          class="checkbox"
          checked={allSelected}
          indeterminate={someSelected && !allSelected}
          onchange={toggleAll}
        />
        <span>{selected.size} selected</span>
      </label>

      <div class="select-bar-actions">
        {#if confirmDelete}
          <span class="confirm-text">Delete {selected.size} deck{selected.size !== 1 ? 's' : ''}?</span>
          <button class="btn-delete-confirm" onclick={deleteSelected} disabled={deleting}>
            {deleting ? 'Deleting…' : 'Yes, delete'}
          </button>
          <button class="btn-ghost btn-sm" onclick={() => (confirmDelete = false)}>Cancel</button>
        {:else}
          <button
            class="btn-delete-selected"
            disabled={!someSelected}
            onclick={() => (confirmDelete = true)}
          >
            Delete selected{someSelected ? ` (${selected.size})` : ''}
          </button>
        {/if}
        <button class="btn-ghost btn-sm" onclick={exitSelectMode}>Cancel</button>
      </div>
    </div>
  </div>
{/if}

<div class="page-container page-body">
  <header class="page-header">
    <div>
      <span class="label">Library</span>
      <h1 class="page-title">Decks</h1>
    </div>
    <div class="header-actions">
      {#if data.items.length > 0 && !selectMode}
        <button class="btn-ghost btn-select" onclick={enterSelectMode}>Select</button>
      {/if}
      <a href="/builder" class="btn-ghost">Build deck</a>
      <a href="/import" class="btn-primary">Import .ydk ↑</a>
    </div>
  </header>

  {#if data.items.length === 0}
    <div class="empty-state">
      <div class="empty-icon" aria-hidden="true">◫</div>
      <p class="empty-title">No decks yet</p>
      <p class="empty-sub">
        Import a .ydk file from YGOPRO, Dueling Nexus or any compatible tool to get started.
      </p>
      <div class="empty-actions">
        <a href="/builder" class="btn-ghost">Build a deck</a>
        <a href="/import" class="btn-primary">Import .ydk ↑</a>
      </div>
    </div>
  {:else}
    <div class="list-header">
      <p class="deck-count">{filteredDecks.length} deck{filteredDecks.length !== 1 ? 's' : ''}{filterTag ? ` tagged "${filterTag}"` : ''}</p>
      {#if usedTags.length > 0}
        <div class="tag-filter" role="group" aria-label="Filter by tag">
          {#each usedTags as t}
            <button
              class="tag-filter-btn"
              class:tag-filter-btn--active={filterTag === t}
              onclick={() => { filterTag = filterTag === t ? '' : t; }}
              type="button"
            >{t}</button>
          {/each}
          {#if filterTag}
            <button class="tag-filter-clear" onclick={() => (filterTag = '')} type="button" aria-label="Clear filter">✕</button>
          {/if}
        </div>
      {/if}
    </div>
    <div class="deck-grid">
      {#each filteredDecks as deck (deck.id)}
        {@const isSelected = selected.has(deck.id)}

        {#if selectMode}
          <!-- In select mode: clickable div with checkbox -->
          <div
            class="deck-card"
            class:is-selected={isSelected}
            role="checkbox"
            aria-checked={isSelected}
            tabindex="0"
            onclick={() => toggleSelect(deck.id)}
            onkeydown={(e) => e.key === ' ' && toggleSelect(deck.id)}
          >
            <div class="card-checkbox" aria-hidden="true">
              <div class="checkbox-box" class:checked={isSelected}>
                {#if isSelected}<span class="checkbox-tick">✓</span>{/if}
              </div>
            </div>

            <div class="deck-card-top">
              <span class="source-badge">{sourceLabel[deck.source_type] ?? deck.source_type}</span>
              <span class="deck-date">{formatDate(deck.created_at)}</span>
            </div>
            <h2 class="deck-title">{deck.title}</h2>
            {#if deck.archetype_label}
              <p class="deck-archetype">{deck.archetype_label}</p>
            {/if}
            {#if deck.notes}
              <p class="deck-notes">{deck.notes}</p>
            {/if}
            {#if deck.tags.length > 0}
              <div class="deck-tags" aria-label="Tags">
                {#each deck.tags as tag}<span class="deck-tag">{tag}</span>{/each}
              </div>
            {/if}
          </div>

        {:else}
          <!-- Normal mode: navigate on click -->
          <a href="/decks/{deck.id}" class="deck-card">
            <div class="deck-card-top">
              <span class="source-badge">{sourceLabel[deck.source_type] ?? deck.source_type}</span>
              <span class="deck-date">{formatDate(deck.created_at)}</span>
            </div>
            <h2 class="deck-title">{deck.title}</h2>
            {#if deck.archetype_label}
              <p class="deck-archetype">{deck.archetype_label}</p>
            {/if}
            {#if deck.notes}
              <p class="deck-notes">{deck.notes}</p>
            {/if}
            {#if deck.tags.length > 0}
              <div class="deck-tags" aria-label="Tags">
                {#each deck.tags as tag}<span class="deck-tag">{tag}</span>{/each}
              </div>
            {/if}
            <div class="deck-arrow" aria-hidden="true">→</div>
          </a>
        {/if}
      {/each}
    </div>
  {/if}
</div>

<style>
  .page-body {
    padding-top: 3rem;
    padding-bottom: 4rem;
  }

  /* ── Selection bar ──────────────────────────────────────────────────────── */
  .select-bar {
    position: sticky;
    top: 60px;
    z-index: 50;
    background: rgba(17, 19, 24, 0.96);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border-default);
    animation: slideDown 150ms var(--ease-out);
  }

  @keyframes slideDown {
    from { transform: translateY(-100%); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }

  .select-bar-inner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding-top: 0.75rem;
    padding-bottom: 0.75rem;
    flex-wrap: wrap;
  }

  .select-all-label {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
    cursor: pointer;
    user-select: none;
  }

  .checkbox {
    width: 16px;
    height: 16px;
    accent-color: var(--gold);
    cursor: pointer;
    flex-shrink: 0;
  }

  .select-bar-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .btn-delete-selected {
    display: inline-flex;
    align-items: center;
    padding: 0.4375rem 1rem;
    background: rgba(224, 84, 84, 0.12);
    border: 1px solid rgba(224, 84, 84, 0.3);
    border-radius: var(--radius-md);
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--error);
    cursor: pointer;
    transition: background var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out);
  }

  .btn-delete-selected:hover:not(:disabled) {
    background: rgba(224, 84, 84, 0.2);
    border-color: rgba(224, 84, 84, 0.5);
  }

  .btn-delete-selected:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .confirm-text {
    font-size: 0.8125rem;
    color: var(--error);
    font-weight: 500;
  }

  .btn-delete-confirm {
    padding: 0.375rem 0.875rem;
    background: var(--error);
    color: #fff;
    border: none;
    border-radius: var(--radius-md);
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8125rem;
    font-weight: 700;
    cursor: pointer;
    transition: opacity var(--duration-fast) var(--ease-out);
  }

  .btn-delete-confirm:hover:not(:disabled) { opacity: 0.85; }
  .btn-delete-confirm:disabled { opacity: 0.5; cursor: not-allowed; }

  .btn-sm {
    font-size: 0.8125rem;
    padding: 0.375rem 0.75rem;
  }

  /* ── Page header ────────────────────────────────────────────────────────── */
  .page-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1.5rem;
    margin-bottom: 2.5rem;
    flex-wrap: wrap;
  }

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    margin-top: 0.375rem;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    flex-wrap: wrap;
  }

  .btn-select {
    font-size: 0.8125rem;
    padding: 0.5rem 0.875rem;
  }

  .list-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
  }

  .deck-count {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    white-space: nowrap;
  }

  /* Tag filter pills */
  .tag-filter {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    flex-wrap: wrap;
  }

  .tag-filter-btn {
    padding: 0.2rem 0.625rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: 99px;
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--text-tertiary);
    cursor: pointer;
    transition: background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out);
  }

  .tag-filter-btn:hover {
    color: var(--text-secondary);
    border-color: var(--border-strong);
  }

  .tag-filter-btn--active {
    background: rgba(201, 164, 73, 0.12);
    border-color: rgba(201, 164, 73, 0.35);
    color: var(--gold);
  }

  .tag-filter-clear {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-tertiary);
    font-size: 0.6875rem;
    cursor: pointer;
    border-radius: 50%;
    transition: background var(--duration-fast) var(--ease-out);
  }

  .tag-filter-clear:hover {
    background: var(--bg-elevated);
    color: var(--text-secondary);
  }

  /* Tags on deck cards */
  .deck-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-top: 0.25rem;
  }

  .deck-tag {
    padding: 0.1rem 0.45rem;
    background: rgba(201, 164, 73, 0.08);
    border: 1px solid rgba(201, 164, 73, 0.2);
    border-radius: 99px;
    font-size: 0.625rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--gold);
    opacity: 0.85;
  }

  /* ── Deck grid ──────────────────────────────────────────────────────────── */
  .deck-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
  }

  .deck-card {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 1.375rem 1.5rem 1.25rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    text-decoration: none;
    cursor: pointer;
    transition:
      border-color var(--duration-base) var(--ease-out),
      background var(--duration-base) var(--ease-out),
      transform var(--duration-fast) var(--ease-out);
    overflow: hidden;
  }

  .deck-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--gold), transparent);
    opacity: 0;
    transition: opacity var(--duration-base) var(--ease-out);
  }

  .deck-card:hover {
    border-color: var(--border-strong);
    background: var(--bg-elevated);
    transform: translateY(-2px);
  }

  .deck-card:hover::before {
    opacity: 1;
  }

  /* Selected state */
  .deck-card.is-selected {
    border-color: var(--gold);
    background: var(--bg-elevated);
    box-shadow: 0 0 0 1px rgba(201, 164, 73, 0.2), inset 0 0 0 1px rgba(201, 164, 73, 0.05);
  }

  .deck-card.is-selected::before {
    opacity: 1;
  }

  /* Checkbox overlay */
  .card-checkbox {
    position: absolute;
    top: 0.875rem;
    right: 0.875rem;
  }

  .checkbox-box {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1.5px solid var(--border-strong);
    background: var(--bg-overlay);
    display: flex;
    align-items: center;
    justify-content: center;
    transition:
      background var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out);
  }

  .checkbox-box.checked {
    background: var(--gold);
    border-color: var(--gold);
  }

  .checkbox-tick {
    font-size: 0.625rem;
    font-weight: 800;
    color: #0a0800;
    line-height: 1;
  }

  .deck-card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
  }

  .source-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.15rem 0.55rem;
    background: var(--gold-dim);
    border: 1px solid rgba(201, 164, 73, 0.2);
    border-radius: 99px;
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    color: var(--gold);
    text-transform: uppercase;
  }

  .deck-date {
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  .deck-title {
    font-size: 1.0625rem;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.3;
    font-family: 'Space Grotesk', sans-serif;
  }

  .deck-archetype {
    font-size: 0.8125rem;
    color: var(--gold);
    opacity: 0.8;
    margin-top: -0.125rem;
  }

  .deck-notes {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .deck-arrow {
    position: absolute;
    bottom: 1.25rem;
    right: 1.5rem;
    font-size: 1rem;
    color: var(--text-tertiary);
    transition: transform var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
  }

  .deck-card:hover .deck-arrow {
    transform: translateX(4px);
    color: var(--gold);
  }

  /* ── Empty state ────────────────────────────────────────────────────────── */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
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
    max-width: 380px;
    line-height: 1.6;
  }

  .empty-actions {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-top: 1.75rem;
    flex-wrap: wrap;
    justify-content: center;
  }
</style>
