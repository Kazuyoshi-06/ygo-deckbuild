<script lang="ts">
  import { untrack } from 'svelte';

  interface CardItem {
    id: number;
    external_card_id: number;
    name: string;
    card_type: string;
    type_line: string | null;
    attribute: string | null;
    archetype: string | null;
    level: number | null;
    atk: number | null;
    def_: number | null;
    link_val: number | null;
    image_url: string;
    tcg_date: string | null;
    ocg_date: string | null;
  }

  let { data } = $props<{ data: { initialCards: CardItem[]; total: number; initialQuery: string } }>();

  const PAGE_SIZE = 48;

  let cards: CardItem[] = $state(untrack(() => data.initialCards));
  let total: number = $state(untrack(() => data.total));
  let currentPage = $state(1);
  let loading = $state(false);
  let loadingMore = $state(false);

  let searchQuery = $state(untrack(() => data.initialQuery));
  let filterType = $state('');
  let filterAttribute = $state('');
  let filterFormat = $state('');
  let sortOrder = $state('');
  let copiedId = $state<number | null>(null);
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  const FORMAT_OPTIONS = [
    { value: '',        label: 'All' },
    { value: 'TCG',     label: 'TCG' },
    { value: 'OCG',     label: 'OCG' },
    { value: 'OCG_ONLY', label: 'OCG only' },
  ];

  const hasMore = $derived(cards.length < total && !loading);

  function buildUrl(page: number) {
    const params = new URLSearchParams();
    if (searchQuery.trim()) params.set('q', searchQuery.trim());
    if (filterType) params.set('type', filterType);
    if (filterAttribute) params.set('attribute', filterAttribute);
    if (filterFormat) params.set('format', filterFormat);
    if (sortOrder) params.set('sort', sortOrder);
    params.set('limit', String(PAGE_SIZE));
    params.set('page', String(page));
    return `/api/v1/cards?${params}`;
  }

  async function search() {
    loading = true;
    currentPage = 1;
    try {
      const res = await fetch(buildUrl(1));
      if (!res.ok) return;
      const json = await res.json();
      cards = json.items ?? [];
      total = json.total ?? 0;
    } finally {
      loading = false;
    }
  }

  async function loadMore() {
    loadingMore = true;
    const nextPage = currentPage + 1;
    try {
      const res = await fetch(buildUrl(nextPage));
      if (!res.ok) return;
      const json = await res.json();
      cards = [...cards, ...(json.items ?? [])];
      total = json.total ?? 0;
      currentPage = nextPage;
    } finally {
      loadingMore = false;
    }
  }

  function onSearchInput() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(search, 300);
  }

  function handleImgError(e: Event) {
    const img = e.target as HTMLImageElement;
    img.src = '/media/placeholder-card.svg';
  }

  function cardBadge(tcg: string | null, ocg: string | null): 'OCG' | 'TCG' | null {
    if (tcg && ocg) return null;
    if (ocg && !tcg) return 'OCG';
    if (tcg && !ocg) return 'TCG';
    return null;
  }

  const isFiltered = $derived(!!(searchQuery || filterType || filterAttribute || filterFormat || sortOrder));

  async function copyCardName(id: number, name: string) {
    await navigator.clipboard.writeText(name);
    copiedId = id;
    setTimeout(() => { copiedId = null; }, 1500);
  }
</script>

<svelte:head>
  <title>Cards — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <header class="page-header">
    <div>
      <span class="label">Catalog</span>
      <h1 class="page-title">Cards</h1>
    </div>
    {#if total > 0}
      <span class="total-count">{total.toLocaleString('en-US')} cards</span>
    {/if}
  </header>

  <!-- Toolbar -->
  <div class="toolbar">
    <div class="search-wrap">
      <span class="search-icon" aria-hidden="true">⌕</span>
      <input
        type="search"
        class="search-input"
        placeholder="Search by name, archetype…"
        bind:value={searchQuery}
        oninput={onSearchInput}
        aria-label="Search cards"
      />
    </div>
    <div class="filter-row">
      <select
        class="filter-select"
        bind:value={filterType}
        onchange={search}
        aria-label="Filter by type"
      >
        <option value="">All types</option>
        <option value="Monster">Monster</option>
        <option value="Spell">Spell</option>
        <option value="Trap">Trap</option>
      </select>
      <select
        class="filter-select"
        bind:value={filterAttribute}
        onchange={search}
        aria-label="Filter by attribute"
      >
        <option value="">All attributes</option>
        {#each ['DARK', 'LIGHT', 'FIRE', 'WATER', 'EARTH', 'WIND', 'DIVINE'] as attr}
          <option value={attr}>{attr}</option>
        {/each}
      </select>
      <div class="format-toggle" role="group" aria-label="Filter by format">
        {#each FORMAT_OPTIONS as opt}
          <button
            class="format-btn"
            class:format-btn--active={filterFormat === opt.value}
            class:format-btn--ocg={opt.value === 'OCG' || opt.value === 'OCG_ONLY'}
            class:format-btn--tcg={opt.value === 'TCG'}
            onclick={() => { filterFormat = opt.value; search(); }}
            type="button"
          >{opt.label}</button>
        {/each}
      </div>
      <select
        class="filter-select"
        bind:value={sortOrder}
        onchange={search}
        aria-label="Sort order"
      >
        <option value="">Name A→Z</option>
        <option value="name_desc">Name Z→A</option>
        <option value="ocg_newest">Newest OCG</option>
      </select>
    </div>
  </div>

  <!-- Loading skeleton -->
  {#if loading}
    <div class="card-grid" aria-busy="true" aria-label="Loading cards">
      {#each Array(48) as _, i (i)}
        <div class="card-slot">
          <div class="skeleton card-img-skeleton"></div>
          <div class="skeleton card-name-skeleton"></div>
        </div>
      {/each}
    </div>

  <!-- Empty state -->
  {:else if cards.length === 0}
    <div class="empty-state">
      <div class="empty-icon" aria-hidden="true">◈</div>
      <p class="empty-title">
        {isFiltered ? 'No cards match your search' : 'Card database not synced'}
      </p>
      <p class="empty-sub">
        {isFiltered
          ? 'Try adjusting your search or filters.'
          : 'Sync the card catalog from the admin panel to start browsing.'}
      </p>
      {#if !isFiltered}
        <a href="/admin" class="btn-primary empty-cta">Go to sync panel</a>
      {/if}
    </div>

  <!-- Card grid -->
  {:else}
    <div class="card-grid">
      {#each cards as card (card.id)}
        {@const badge = cardBadge(card.tcg_date, card.ocg_date)}
        <div
          class="card-slot"
          title="{card.name}{card.archetype ? ` · ${card.archetype}` : ''}{badge ? ` [${badge}]` : ''}"
        >
          <div class="card-img-wrap">
            <img
              src={card.image_url}
              alt={card.name}
              class="card-img"
              loading="lazy"
              onerror={handleImgError}
            />
            {#if badge}
              <span class="format-badge format-badge--{badge.toLowerCase()}">{badge}</span>
            {/if}
            <button
              class="copy-btn"
              class:copy-btn--done={copiedId === card.id}
              onclick={(e) => { e.stopPropagation(); copyCardName(card.id, card.name); }}
              type="button"
              aria-label="Copy card name"
              title="Copy name"
            >{copiedId === card.id ? '✓' : '⎘'}</button>
          </div>
          <p class="card-name">{card.name}</p>
        </div>
      {/each}
    </div>

    {#if hasMore}
      <div class="load-more-row">
        <button
          class="btn-ghost load-more-btn"
          onclick={loadMore}
          disabled={loadingMore}
        >
          {#if loadingMore}
            <span class="spinner" aria-hidden="true"></span>
            Loading…
          {:else}
            Load more
            <span class="load-more-hint">({(total - cards.length).toLocaleString('en-US')} remaining)</span>
          {/if}
        </button>
      </div>
    {/if}
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

  .total-count {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-tertiary);
    letter-spacing: 0.02em;
    padding-bottom: 0.25rem;
  }

  /* Toolbar */
  .toolbar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1.75rem;
    flex-wrap: wrap;
  }

  .search-wrap {
    position: relative;
    flex: 1;
    min-width: 220px;
  }

  .search-icon {
    position: absolute;
    left: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-tertiary);
    font-size: 1.125rem;
    pointer-events: none;
    line-height: 1;
  }

  .search-input {
    width: 100%;
    padding: 0.625rem 0.875rem 0.625rem 2.375rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.9375rem;
    outline: none;
    transition: border-color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .search-input::placeholder {
    color: var(--text-tertiary);
  }

  .search-input:focus {
    border-color: var(--gold);
    box-shadow: 0 0 0 3px rgba(201, 164, 73, 0.12);
  }

  .search-input::-webkit-search-cancel-button {
    display: none;
  }

  .filter-row {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .filter-select {
    padding: 0.625rem 2.25rem 0.625rem 0.875rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.8125rem;
    font-weight: 500;
    cursor: pointer;
    outline: none;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' fill='none'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%235a5e73' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 0.75rem center;
    transition: border-color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .filter-select:focus {
    border-color: var(--gold);
    box-shadow: 0 0 0 3px rgba(201, 164, 73, 0.12);
  }

  /* Format toggle */
  .format-toggle {
    display: flex;
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .format-btn {
    padding: 0.625rem 0.75rem;
    background: var(--bg-surface);
    border: none;
    border-right: 1px solid var(--border-default);
    color: var(--text-tertiary);
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    cursor: pointer;
    transition: background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
    white-space: nowrap;
  }

  .format-btn:last-child {
    border-right: none;
  }

  .format-btn:hover:not(.format-btn--active) {
    background: var(--bg-elevated);
    color: var(--text-secondary);
  }

  .format-btn--active {
    background: var(--bg-elevated);
    color: var(--text-primary);
  }

  .format-btn--tcg.format-btn--active {
    background: rgba(37, 99, 180, 0.18);
    color: #7eb3f8;
  }

  .format-btn--ocg.format-btn--active {
    background: rgba(210, 105, 30, 0.18);
    color: #f4a36b;
  }

  /* Card grid */
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
    gap: 0.625rem;
  }

  @media (min-width: 640px) {
    .card-grid {
      grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
    }
  }

  @media (min-width: 1024px) {
    .card-grid {
      grid-template-columns: repeat(auto-fill, minmax(106px, 1fr));
    }
  }

  .card-slot {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .card-img-wrap {
    position: relative;
    aspect-ratio: 421 / 614;
    border-radius: var(--radius-sm);
    overflow: hidden;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    transition:
      border-color var(--duration-fast) var(--ease-out),
      transform var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .card-slot:hover .card-img-wrap {
    border-color: var(--gold);
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(201, 164, 73, 0.3);
    z-index: 1;
  }

  .card-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .format-badge {
    position: absolute;
    top: 4px;
    left: 4px;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.5625rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    line-height: 1.6;
    pointer-events: none;
  }

  .format-badge--ocg {
    background: rgba(210, 105, 30, 0.88);
    color: #fff;
  }

  .format-badge--tcg {
    background: rgba(37, 99, 180, 0.82);
    color: #fff;
  }

  /* Copy name button */
  .copy-btn {
    position: absolute;
    bottom: 4px;
    right: 4px;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.72);
    backdrop-filter: blur(4px);
    border: none;
    border-radius: 3px;
    font-size: 0.6875rem;
    color: var(--text-secondary);
    cursor: pointer;
    opacity: 0;
    transition: opacity var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
    line-height: 1;
  }

  .card-slot:hover .copy-btn {
    opacity: 1;
  }

  .copy-btn--done {
    color: #4ade80;
  }

  .card-name {
    font-size: 0.6875rem;
    color: var(--text-secondary);
    line-height: 1.3;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    text-align: center;
  }

  /* Skeleton states */
  .card-img-skeleton {
    aspect-ratio: 421 / 614;
    border-radius: var(--radius-sm);
  }

  .card-name-skeleton {
    height: 0.6875rem;
    width: 75%;
    margin: 0 auto;
    border-radius: 3px;
  }

  /* Load more */
  .load-more-row {
    display: flex;
    justify-content: center;
    margin-top: 2.5rem;
  }

  .load-more-btn {
    min-width: 200px;
    justify-content: center;
  }

  .load-more-hint {
    font-size: 0.75rem;
    opacity: 0.55;
    margin-left: 0.125rem;
  }

  .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.15);
    border-top-color: var(--text-secondary);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* Empty state */
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
    max-width: 340px;
    line-height: 1.6;
  }

  .empty-cta {
    margin-top: 1.75rem;
  }
</style>
