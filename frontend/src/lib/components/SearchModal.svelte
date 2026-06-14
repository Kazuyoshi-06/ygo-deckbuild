<script lang="ts">
  import { goto } from '$app/navigation';

  interface CardHit { id: number; name: string; type_label: string; image_url: string }
  interface DeckHit { id: number; title: string; archetype_label: string | null }
  interface ArchetypeHit { label: string; deck_count: number }
  interface SearchResults { cards: CardHit[]; decks: DeckHit[]; archetypes: ArchetypeHit[] }

  type FlatItem = { url: string; label: string; kind: 'card' | 'deck' | 'archetype' };

  let { onclose }: { onclose: () => void } = $props();

  let query = $state('');
  let results = $state<SearchResults | null>(null);
  let loading = $state(false);
  let focusedIdx = $state(-1);
  let inputEl: HTMLInputElement = $state(null as unknown as HTMLInputElement);
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  const flatItems: FlatItem[] = $derived.by(() => {
    const r = results;
    if (!r) return [];
    const items: FlatItem[] = [];
    for (const c of r.cards)
      items.push({ url: `/cards?q=${encodeURIComponent(c.name)}`, label: c.name, kind: 'card' });
    for (const d of r.decks)
      items.push({ url: `/decks/${d.id}`, label: d.title, kind: 'deck' });
    for (const a of r.archetypes)
      items.push({ url: `/analytics/archetypes/${encodeURIComponent(a.label)}`, label: a.label, kind: 'archetype' });
    return items;
  });

  const hasResults = $derived(
    !!results && (results.cards.length + results.decks.length + results.archetypes.length) > 0
  );
  const isEmpty = $derived(!!results && !hasResults && query.trim().length >= 2);

  async function doSearch(q: string) {
    if (q.trim().length < 2) { results = null; return; }
    loading = true;
    try {
      const res = await fetch(`/api/v1/search?q=${encodeURIComponent(q.trim())}`);
      if (res.ok) results = await res.json();
    } finally {
      loading = false;
    }
  }

  function onInput() {
    focusedIdx = -1;
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => doSearch(query), 200);
  }

  function navigate(url: string) {
    goto(url);
    onclose();
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') { onclose(); return; }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      focusedIdx = Math.min(focusedIdx + 1, flatItems.length - 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      focusedIdx = Math.max(focusedIdx - 1, -1);
      if (focusedIdx === -1) inputEl?.focus();
    } else if (e.key === 'Enter' && focusedIdx >= 0) {
      e.preventDefault();
      navigate(flatItems[focusedIdx].url);
    }
  }

  $effect(() => {
    inputEl?.focus();
  });
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="backdrop" onclick={onclose} aria-hidden="true"></div>

<div
  class="modal"
  role="dialog"
  aria-label="Global search"
  aria-modal="true"
  tabindex="-1"
  onkeydown={onKeyDown}
>
  <div class="search-bar">
    <span class="search-icon" aria-hidden="true">⌕</span>
    <input
      bind:this={inputEl}
      bind:value={query}
      oninput={onInput}
      class="search-input"
      placeholder="Search cards, decks, archetypes…"
      type="search"
      autocomplete="off"
      spellcheck="false"
      aria-label="Search"
    />
    {#if loading}
      <span class="spinner" aria-hidden="true"></span>
    {:else if query}
      <button class="clear-btn" onclick={() => { query = ''; results = null; focusedIdx = -1; inputEl?.focus(); }} aria-label="Clear search">✕</button>
    {:else}
      <kbd class="hint-esc">Esc</kbd>
    {/if}
  </div>

  {#if hasResults}
    <div class="results" role="listbox" aria-label="Search results">
      {#if results!.cards.length}
        <div class="section">
          <p class="section-label">Cards</p>
          {#each results!.cards as card, i}
            {@const gIdx = i}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <div
              class="row"
              class:row--focused={focusedIdx === gIdx}
              role="option"
              tabindex="-1"
              aria-selected={focusedIdx === gIdx}
              onmouseenter={() => (focusedIdx = gIdx)}
              onclick={() => navigate(`/cards?q=${encodeURIComponent(card.name)}`)}
            >
              <img
                src={card.image_url}
                alt=""
                class="row-thumb"
                onerror={(e) => { (e.target as HTMLImageElement).src = '/media/placeholder-card.svg'; }}
              />
              <div class="row-info">
                <span class="row-name">{card.name}</span>
                <span class="row-sub">{card.type_label}</span>
              </div>
              <span class="row-badge row-badge--card">Card</span>
            </div>
          {/each}
        </div>
      {/if}

      {#if results!.decks.length}
        <div class="section">
          <p class="section-label">Decks</p>
          {#each results!.decks as deck, i}
            {@const gIdx = results!.cards.length + i}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <div
              class="row"
              class:row--focused={focusedIdx === gIdx}
              role="option"
              tabindex="-1"
              aria-selected={focusedIdx === gIdx}
              onmouseenter={() => (focusedIdx = gIdx)}
              onclick={() => navigate(`/decks/${deck.id}`)}
            >
              <div class="row-icon">▤</div>
              <div class="row-info">
                <span class="row-name">{deck.title}</span>
                {#if deck.archetype_label}<span class="row-sub">{deck.archetype_label}</span>{/if}
              </div>
              <span class="row-badge row-badge--deck">Deck</span>
            </div>
          {/each}
        </div>
      {/if}

      {#if results!.archetypes.length}
        <div class="section">
          <p class="section-label">Archetypes</p>
          {#each results!.archetypes as arch, i}
            {@const gIdx = results!.cards.length + results!.decks.length + i}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <div
              class="row"
              class:row--focused={focusedIdx === gIdx}
              role="option"
              tabindex="-1"
              aria-selected={focusedIdx === gIdx}
              onmouseenter={() => (focusedIdx = gIdx)}
              onclick={() => navigate(`/analytics/archetypes/${encodeURIComponent(arch.label)}`)}
            >
              <div class="row-icon row-icon--arch">◈</div>
              <div class="row-info">
                <span class="row-name">{arch.label}</span>
                <span class="row-sub">{arch.deck_count} deck{arch.deck_count > 1 ? 's' : ''}</span>
              </div>
              <span class="row-badge row-badge--arch">Archetype</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>

  {:else if isEmpty}
    <div class="empty-state">
      <span class="empty-icon" aria-hidden="true">◈</span>
      <p class="empty-text">No results for "<strong>{query}</strong>"</p>
    </div>

  {:else}
    <div class="hint-area" aria-hidden="true">
      <p class="hint-line">
        <kbd>↑</kbd><kbd>↓</kbd> navigate &ensp;·&ensp; <kbd>↵</kbd> open &ensp;·&ensp; <kbd>Esc</kbd> close
      </p>
    </div>
  {/if}
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 400;
    background: rgba(8, 9, 13, 0.72);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    animation: fadeIn 120ms ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  .modal {
    position: fixed;
    top: 80px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 500;
    width: min(600px, calc(100vw - 2rem));
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-xl);
    box-shadow: 0 32px 80px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(201, 164, 73, 0.08);
    overflow: hidden;
    animation: slideDown 160ms cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes slideDown {
    from { opacity: 0; transform: translateX(-50%) translateY(-12px); }
    to   { opacity: 1; transform: translateX(-50%) translateY(0); }
  }

  /* Search bar */
  .search-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0 1rem;
    height: 56px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .search-icon {
    color: var(--text-tertiary);
    font-size: 1.25rem;
    line-height: 1;
    flex-shrink: 0;
  }

  .search-input {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: var(--text-primary);
    font-family: inherit;
    font-size: 1rem;
    line-height: 1.5;
  }

  .search-input::placeholder {
    color: var(--text-tertiary);
  }

  .search-input::-webkit-search-cancel-button {
    display: none;
  }

  .hint-esc {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.6875rem;
    font-weight: 600;
    padding: 0.2rem 0.45rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: 4px;
    color: var(--text-tertiary);
    letter-spacing: 0.04em;
    flex-shrink: 0;
  }

  .clear-btn {
    background: transparent;
    border: none;
    color: var(--text-tertiary);
    font-size: 0.75rem;
    cursor: pointer;
    padding: 0.25rem 0.375rem;
    border-radius: var(--radius-sm);
    transition: color var(--duration-fast) var(--ease-out),
      background var(--duration-fast) var(--ease-out);
    flex-shrink: 0;
  }

  .clear-btn:hover {
    color: var(--text-secondary);
    background: var(--bg-elevated);
  }

  .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--gold);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
    flex-shrink: 0;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  /* Results */
  .results {
    max-height: 420px;
    overflow-y: auto;
    padding: 0.5rem 0;
  }

  .results::-webkit-scrollbar { width: 4px; }
  .results::-webkit-scrollbar-track { background: transparent; }
  .results::-webkit-scrollbar-thumb { background: var(--border-default); border-radius: 2px; }

  .section {
    margin-bottom: 0.25rem;
  }

  .section-label {
    padding: 0.5rem 1rem 0.25rem;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  /* Result row */
  .row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 1rem;
    cursor: pointer;
    transition: background var(--duration-fast) var(--ease-out);
  }

  .row--focused {
    background: var(--bg-elevated);
  }

  .row-thumb {
    width: 28px;
    height: 40px;
    object-fit: cover;
    border-radius: 2px;
    background: var(--bg-elevated);
    flex-shrink: 0;
    border: 1px solid var(--border-subtle);
  }

  .row-icon {
    width: 28px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    color: var(--text-tertiary);
    flex-shrink: 0;
  }

  .row-icon--arch {
    color: var(--gold);
    opacity: 0.7;
  }

  .row-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .row-name {
    font-size: 0.9375rem;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .row-sub {
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  .row-badge {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.625rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 0.15rem 0.4rem;
    border-radius: 3px;
    flex-shrink: 0;
  }

  .row-badge--card {
    background: rgba(201, 164, 73, 0.12);
    color: var(--gold);
  }

  .row-badge--deck {
    background: rgba(100, 149, 237, 0.12);
    color: #7eb3f8;
  }

  .row-badge--arch {
    background: rgba(130, 197, 150, 0.12);
    color: #82c596;
  }

  /* Empty & hint */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 2.5rem 1rem;
    color: var(--text-tertiary);
  }

  .empty-icon {
    font-size: 1.5rem;
    opacity: 0.4;
  }

  .empty-text {
    font-size: 0.9rem;
    color: var(--text-secondary);
  }

  .empty-text strong {
    color: var(--text-primary);
  }

  .hint-area {
    padding: 1rem 1.25rem;
    border-top: 1px solid var(--border-subtle);
  }

  .hint-line {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    color: var(--text-tertiary);
    flex-wrap: wrap;
  }

  .hint-line kbd {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.625rem;
    font-weight: 700;
    padding: 0.15rem 0.35rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: 3px;
    color: var(--text-secondary);
  }

  @media (max-width: 640px) {
    .modal {
      top: 16px;
      border-radius: var(--radius-lg);
    }
  }
</style>
