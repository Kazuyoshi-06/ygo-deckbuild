<script lang="ts">
  import { goto } from '$app/navigation';
  import { untrack } from 'svelte';

  interface CardItem {
    id: number;
    external_card_id: number;
    name: string;
    type: string;
    frame_type: string;
    attribute: string | null;
    archetype: string | null;
    atk: number | null;
    def_: number | null;
    image_url: string;
    tcg_date: string | null;
    ocg_date: string | null;
  }

  interface DeckSlot {
    card_id: number;
    name: string;
    frame_type: string;
    image_url: string;
    quantity: number;
    tcg_date: string | null;
    ocg_date: string | null;
  }

  function cardBadge(tcg_date: string | null, ocg_date: string | null): 'OCG' | 'TCG' | null {
    if (tcg_date && ocg_date) return null;
    if (ocg_date && !tcg_date) return 'OCG';
    if (tcg_date && !ocg_date) return 'TCG';
    return null;
  }

  let { data } = $props<{ data: { initialCards: CardItem[] } }>();

  // ── Deck state ────────────────────────────────────────────────────────────
  let deckTitle: string = $state('New Deck');
  let mainDeck: DeckSlot[] = $state([]);
  let extraDeck: DeckSlot[] = $state([]);
  let sideDeck: DeckSlot[] = $state([]);

  let mainCount = $derived(mainDeck.reduce((s, c) => s + c.quantity, 0));
  let extraCount = $derived(extraDeck.reduce((s, c) => s + c.quantity, 0));
  let sideCount = $derived(sideDeck.reduce((s, c) => s + c.quantity, 0));
  let totalCards = $derived(mainCount + extraCount + sideCount);

  // ── Search state ──────────────────────────────────────────────────────────
  let searchQuery: string = $state('');
  let filterType: string = $state('');
  let filterAttribute: string = $state('');
  let searchResults: CardItem[] = $state(untrack(() => data.initialCards));
  let searchLoading: boolean = $state(false);

  // ── Save state ────────────────────────────────────────────────────────────
  let saving: boolean = $state(false);
  let saveError: string = $state('');

  // ── Card section detection ────────────────────────────────────────────────
  const EXTRA_FRAMES = new Set([
    'fusion', 'synchro', 'xyz', 'link',
    'xyz_pendulum', 'synchro_pendulum', 'fusion_pendulum',
  ]);

  function defaultSection(frameType: string): 'main' | 'extra' {
    return EXTRA_FRAMES.has(frameType) ? 'extra' : 'main';
  }

  // ── Deck operations ───────────────────────────────────────────────────────
  function addCard(card: CardItem, targetSection?: 'main' | 'extra' | 'side') {
    const section = targetSection ?? defaultSection(card.frame_type);
    const deck = section === 'main' ? mainDeck : section === 'extra' ? extraDeck : sideDeck;
    const existing = deck.find(c => c.card_id === card.id);
    if (existing) {
      if (existing.quantity < 3) existing.quantity++;
    } else {
      deck.push({
        card_id: card.id,
        name: card.name,
        frame_type: card.frame_type,
        image_url: card.image_url,
        quantity: 1,
        tcg_date: card.tcg_date,
        ocg_date: card.ocg_date,
      });
    }
  }

  function changeQty(deck: DeckSlot[], card_id: number, delta: number) {
    const idx = deck.findIndex(c => c.card_id === card_id);
    if (idx === -1) return;
    const newQty = deck[idx].quantity + delta;
    if (newQty <= 0) deck.splice(idx, 1);
    else if (newQty <= 3) deck[idx].quantity = newQty;
  }

  function removeCard(deck: DeckSlot[], card_id: number) {
    const idx = deck.findIndex(c => c.card_id === card_id);
    if (idx !== -1) deck.splice(idx, 1);
  }

  // Total quantity of a card across all sections
  let deckQtyMap = $derived(
    (() => {
      const m = new Map<number, number>();
      for (const c of [...mainDeck, ...extraDeck, ...sideDeck]) {
        m.set(c.card_id, (m.get(c.card_id) ?? 0) + c.quantity);
      }
      return m;
    })()
  );

  // ── Debounced search ──────────────────────────────────────────────────────
  let firstRender = true;

  $effect(() => {
    const q = searchQuery;
    const type = filterType;
    const attr = filterAttribute;

    if (firstRender) {
      firstRender = false;
      return;
    }

    const timer = setTimeout(async () => {
      searchLoading = true;
      const params = new URLSearchParams({ limit: '24' });
      if (q.trim()) params.set('q', q.trim());
      if (type) params.set('type', type);
      if (attr) params.set('attribute', attr);

      const res = await fetch(`/api/v1/cards?${params}`);
      const data = await res.json();
      searchResults = data.items ?? [];
      searchLoading = false;
    }, 280);

    return () => clearTimeout(timer);
  });

  function handleImgError(e: Event) {
    (e.target as HTMLImageElement).src = '/media/placeholder-card.svg';
  }

  // ── Section status ────────────────────────────────────────────────────────
  function mainStatus(count: number): 'ok' | 'warn' | 'error' {
    if (count >= 40 && count <= 60) return 'ok';
    if (count > 60) return 'error';
    return 'warn';
  }

  function extraSideStatus(count: number, max: number): 'ok' | 'error' {
    return count > max ? 'error' : 'ok';
  }

  // ── Save ──────────────────────────────────────────────────────────────────
  async function saveDeck() {
    if (!deckTitle.trim() || totalCards === 0) return;
    saving = true;
    saveError = '';

    const cards = [
      ...mainDeck.map(c => ({ card_id: c.card_id, section: 'main', quantity: c.quantity })),
      ...extraDeck.map(c => ({ card_id: c.card_id, section: 'extra', quantity: c.quantity })),
      ...sideDeck.map(c => ({ card_id: c.card_id, section: 'side', quantity: c.quantity })),
    ];

    try {
      const res = await fetch('/api/v1/decks/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: deckTitle.trim(), cards }),
      });
      const body = await res.json();
      if (!res.ok) {
        saveError = body.detail ?? 'Save failed';
        saving = false;
        return;
      }
      goto(`/decks/${body.deck_id}`);
    } catch {
      saveError = 'Network error';
      saving = false;
    }
  }

  const CARD_TYPES = [
    'Effect Monster', 'Normal Monster', 'Ritual Monster', 'Gemini Monster',
    'Fusion Monster', 'Synchro Monster', 'XYZ Monster', 'Link Monster',
    'Pendulum Effect Monster', 'Normal Spell Card', 'Continuous Spell Card',
    'Quick-Play Spell Card', 'Field Spell Card', 'Ritual Spell Card',
    'Normal Trap Card', 'Continuous Trap Card', 'Counter Trap Card',
  ];

  const ATTRIBUTES = ['DARK', 'LIGHT', 'EARTH', 'WATER', 'FIRE', 'WIND', 'DIVINE'];
</script>

<svelte:head>
  <title>Deck Builder — YGO Intel</title>
</svelte:head>

<!-- ── Top bar ────────────────────────────────────────────────────────────── -->
<div class="topbar">
  <div class="topbar-left">
    <a href="/decks" class="topbar-back">← Decks</a>
    <input
      class="title-input"
      type="text"
      placeholder="Deck name…"
      bind:value={deckTitle}
      maxlength="255"
      aria-label="Deck name"
    />
  </div>
  <div class="topbar-right">
    {#if saveError}
      <span class="save-error">{saveError}</span>
    {/if}
    <span class="total-badge" class:has-cards={totalCards > 0}>{totalCards} cards</span>
    <button
      class="btn-primary save-btn"
      onclick={saveDeck}
      disabled={saving || totalCards === 0 || !deckTitle.trim()}
    >
      {#if saving}
        <span class="spinner" aria-hidden="true"></span> Saving…
      {:else}
        Save deck ↑
      {/if}
    </button>
  </div>
</div>

<!-- ── Builder body ───────────────────────────────────────────────────────── -->
<div class="builder-layout">

  <!-- ── Left: Card browser ─────────────────────────────────────────────── -->
  <aside class="search-panel">
    <h2 class="panel-label">Card Browser</h2>

    <input
      class="search-input"
      type="search"
      placeholder="Search cards…"
      bind:value={searchQuery}
      aria-label="Search cards"
    />

    <div class="filters">
      <select class="filter-select" bind:value={filterType} aria-label="Filter by type">
        <option value="">All types</option>
        {#each CARD_TYPES as t}
          <option value={t}>{t}</option>
        {/each}
      </select>
      <select class="filter-select" bind:value={filterAttribute} aria-label="Filter by attribute">
        <option value="">All attrs</option>
        {#each ATTRIBUTES as a}
          <option value={a}>{a}</option>
        {/each}
      </select>
    </div>

    {#if searchLoading}
      <div class="search-loading">
        <span class="spinner-dark" aria-hidden="true"></span>
      </div>
    {:else if searchResults.length === 0}
      <div class="search-empty">No cards found</div>
    {:else}
      <ul class="card-grid-sm" aria-label="Search results">
        {#each searchResults as card (card.id)}
          {@const qty = deckQtyMap.get(card.id) ?? 0}
          {@const maxed = qty >= 3}
          {@const badge = cardBadge(card.tcg_date, card.ocg_date)}
          <li>
            <button
              class="card-thumb"
              class:maxed
              title="{card.name}{qty > 0 ? ` (×${qty} in deck)` : ''}{badge ? ` [${badge}]` : ''} · Ctrl+click to add to side"
              onclick={(e) => addCard(card, (e as MouseEvent).ctrlKey || (e as MouseEvent).metaKey ? 'side' : undefined)}
              aria-label="Add {card.name} to deck"
            >
              <img
                src={card.image_url}
                alt={card.name}
                class="card-thumb-img"
                loading="lazy"
                onerror={handleImgError}
              />
              {#if badge}
                <span class="format-badge format-badge--{badge.toLowerCase()}">{badge}</span>
              {/if}
              {#if qty > 0}
                <span class="qty-overlay" class:maxed>{qty}</span>
              {/if}
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </aside>

  <!-- ── Right: Deck ─────────────────────────────────────────────────────── -->
  <main class="deck-panel">

    <!-- Main deck -->
    <section class="deck-section">
      <header class="section-hd">
        <span class="section-name">Main Deck</span>
        <span
          class="section-count"
          class:warn={mainStatus(mainCount) === 'warn'}
          class:error={mainStatus(mainCount) === 'error'}
          class:ok={mainStatus(mainCount) === 'ok'}
        >
          {mainCount} / 60
        </span>
      </header>

      {#if mainDeck.length === 0}
        <p class="section-empty">Click a card to add it here</p>
      {:else}
        <ul class="deck-list">
          {#each mainDeck as slot (slot.card_id)}
            {@const badge = cardBadge(slot.tcg_date, slot.ocg_date)}
            <li class="deck-row">
              <div class="row-img-wrap">
                <img src={slot.image_url} alt={slot.name} class="row-img" loading="lazy" onerror={handleImgError} />
              </div>
              <span class="row-name">{slot.name}</span>
              {#if badge}
                <span class="row-badge row-badge--{badge.toLowerCase()}">{badge}</span>
              {/if}
              <div class="row-controls">
                <button class="qty-btn" onclick={() => changeQty(mainDeck, slot.card_id, -1)} aria-label="Decrease">−</button>
                <span class="qty-val">×{slot.quantity}</span>
                <button class="qty-btn" onclick={() => changeQty(mainDeck, slot.card_id, 1)} aria-label="Increase" disabled={slot.quantity >= 3}>+</button>
                <button class="rm-btn" onclick={() => removeCard(mainDeck, slot.card_id)} aria-label="Remove">✕</button>
              </div>
            </li>
          {/each}
        </ul>
      {/if}
    </section>

    <!-- Extra deck -->
    <section class="deck-section">
      <header class="section-hd">
        <span class="section-name">Extra Deck</span>
        <span
          class="section-count"
          class:error={extraSideStatus(extraCount, 15) === 'error'}
          class:ok={extraSideStatus(extraCount, 15) === 'ok'}
        >
          {extraCount} / 15
        </span>
      </header>

      {#if extraDeck.length === 0}
        <p class="section-empty">Fusion, Synchro, XYZ and Link monsters</p>
      {:else}
        <ul class="deck-list">
          {#each extraDeck as slot (slot.card_id)}
            {@const badge = cardBadge(slot.tcg_date, slot.ocg_date)}
            <li class="deck-row">
              <div class="row-img-wrap">
                <img src={slot.image_url} alt={slot.name} class="row-img" loading="lazy" onerror={handleImgError} />
              </div>
              <span class="row-name">{slot.name}</span>
              {#if badge}
                <span class="row-badge row-badge--{badge.toLowerCase()}">{badge}</span>
              {/if}
              <div class="row-controls">
                <button class="qty-btn" onclick={() => changeQty(extraDeck, slot.card_id, -1)} aria-label="Decrease">−</button>
                <span class="qty-val">×{slot.quantity}</span>
                <button class="qty-btn" onclick={() => changeQty(extraDeck, slot.card_id, 1)} aria-label="Increase" disabled={slot.quantity >= 3}>+</button>
                <button class="rm-btn" onclick={() => removeCard(extraDeck, slot.card_id)} aria-label="Remove">✕</button>
              </div>
            </li>
          {/each}
        </ul>
      {/if}
    </section>

    <!-- Side deck -->
    <section class="deck-section">
      <header class="section-hd">
        <span class="section-name">Side Deck</span>
        <span
          class="section-count"
          class:error={extraSideStatus(sideCount, 15) === 'error'}
          class:ok={extraSideStatus(sideCount, 15) === 'ok'}
        >
          {sideCount} / 15
        </span>
      </header>

      {#if sideDeck.length === 0}
        <p class="section-empty">Ctrl+click a card to add it to the side deck</p>
      {:else}
        <ul class="deck-list">
          {#each sideDeck as slot (slot.card_id)}
            {@const badge = cardBadge(slot.tcg_date, slot.ocg_date)}
            <li class="deck-row">
              <div class="row-img-wrap">
                <img src={slot.image_url} alt={slot.name} class="row-img" loading="lazy" onerror={handleImgError} />
              </div>
              <span class="row-name">{slot.name}</span>
              {#if badge}
                <span class="row-badge row-badge--{badge.toLowerCase()}">{badge}</span>
              {/if}
              <div class="row-controls">
                <button class="qty-btn" onclick={() => changeQty(sideDeck, slot.card_id, -1)} aria-label="Decrease">−</button>
                <span class="qty-val">×{slot.quantity}</span>
                <button class="qty-btn" onclick={() => changeQty(sideDeck, slot.card_id, 1)} aria-label="Increase" disabled={slot.quantity >= 3}>+</button>
                <button class="rm-btn" onclick={() => removeCard(sideDeck, slot.card_id)} aria-label="Remove">✕</button>
              </div>
            </li>
          {/each}
        </ul>
      {/if}
    </section>

  </main>
</div>

<style>
  /* ── Top bar ────────────────────────────────────────────────────────────── */
  .topbar {
    position: sticky;
    top: 60px;
    z-index: 50;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.75rem 1.5rem;
    background: rgba(8, 9, 13, 0.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border-subtle);
    flex-wrap: wrap;
  }

  .topbar-left {
    display: flex;
    align-items: center;
    gap: 1rem;
    min-width: 0;
    flex: 1;
  }

  .topbar-back {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    white-space: nowrap;
    transition: color var(--duration-fast) var(--ease-out);
    flex-shrink: 0;
  }

  .topbar-back:hover {
    color: var(--text-secondary);
  }

  .title-input {
    flex: 1;
    min-width: 160px;
    max-width: 360px;
    padding: 0.4375rem 0.75rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.9375rem;
    font-weight: 600;
    outline: none;
    transition: border-color var(--duration-fast) var(--ease-out);
  }

  .title-input:focus {
    border-color: var(--gold);
  }

  .topbar-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
  }

  .save-error {
    font-size: 0.8125rem;
    color: var(--error);
  }

  .total-badge {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    white-space: nowrap;
  }

  .total-badge.has-cards {
    color: var(--text-secondary);
  }

  .save-btn {
    font-size: 0.875rem;
    padding: 0.5rem 1.125rem;
  }

  .save-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
    transform: none !important;
    box-shadow: none !important;
  }

  /* ── Layout ─────────────────────────────────────────────────────────────── */
  .builder-layout {
    display: grid;
    grid-template-columns: 340px 1fr;
    min-height: calc(100vh - 120px);
  }

  @media (min-width: 1200px) {
    .builder-layout {
      grid-template-columns: 380px 1fr;
    }
  }

  /* ── Search panel ───────────────────────────────────────────────────────── */
  .search-panel {
    position: sticky;
    top: 120px; /* nav + topbar */
    height: calc(100vh - 120px);
    overflow-y: auto;
    border-right: 1px solid var(--border-subtle);
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
  }

  .panel-label {
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .search-input {
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.875rem;
    outline: none;
    transition: border-color var(--duration-fast) var(--ease-out);
  }

  .search-input:focus {
    border-color: var(--gold);
  }

  .filters {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
  }

  .filter-select {
    padding: 0.375rem 0.5rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    font-family: inherit;
    font-size: 0.75rem;
    outline: none;
    cursor: pointer;
  }

  .filter-select:focus {
    border-color: var(--gold);
  }

  .search-loading {
    display: flex;
    justify-content: center;
    padding: 2rem;
  }

  .search-empty {
    text-align: center;
    padding: 2rem;
    font-size: 0.875rem;
    color: var(--text-tertiary);
  }

  /* Card grid for search results */
  .card-grid-sm {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 5px;
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .card-grid-sm li {
    display: contents;
  }

  .card-thumb {
    position: relative;
    aspect-ratio: 421 / 614;
    border-radius: 4px;
    overflow: hidden;
    cursor: pointer;
    border: 1px solid transparent;
    background: var(--bg-elevated);
    padding: 0;
    transition:
      border-color var(--duration-fast) var(--ease-out),
      transform var(--duration-fast) var(--ease-out),
      opacity var(--duration-fast) var(--ease-out);
  }

  .card-thumb:hover:not(.maxed) {
    border-color: var(--gold);
    transform: translateY(-2px) scale(1.04);
    z-index: 2;
  }

  .card-thumb.maxed {
    opacity: 0.45;
    cursor: default;
  }

  .card-thumb-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  /* Format badges on thumbnails */
  .format-badge {
    position: absolute;
    top: 3px;
    left: 3px;
    padding: 0.05rem 0.28rem;
    border-radius: 3px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.5rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    line-height: 1.6;
    pointer-events: none;
  }

  .format-badge--ocg {
    background: rgba(210, 105, 30, 0.92);
    color: #fff;
  }

  .format-badge--tcg {
    background: rgba(37, 99, 180, 0.88);
    color: #fff;
  }

  /* Format badges on deck rows */
  .row-badge {
    flex-shrink: 0;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.5625rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    line-height: 1.5;
  }

  .row-badge--ocg {
    background: rgba(210, 105, 30, 0.2);
    color: #e8853a;
    border: 1px solid rgba(210, 105, 30, 0.35);
  }

  .row-badge--tcg {
    background: rgba(37, 99, 180, 0.18);
    color: #5b9bd5;
    border: 1px solid rgba(37, 99, 180, 0.3);
  }

  .qty-overlay {
    position: absolute;
    bottom: 2px;
    right: 2px;
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--gold);
    color: #0a0800;
    border-radius: 3px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.6rem;
    font-weight: 800;
    line-height: 1;
  }

  .qty-overlay.maxed {
    background: var(--text-tertiary);
    color: var(--bg-base);
  }

  /* ── Deck panel ─────────────────────────────────────────────────────────── */
  .deck-panel {
    padding: 1.5rem 2rem;
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .deck-section {
    padding-bottom: 1.5rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .deck-section:last-child {
    border-bottom: none;
  }

  .section-hd {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
  }

  .section-name {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-secondary);
  }

  .section-count {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-tertiary);
    transition: color var(--duration-fast) var(--ease-out);
  }

  .section-count.ok { color: var(--success); }
  .section-count.warn { color: var(--warning); }
  .section-count.error { color: var(--error); }

  .section-empty {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    padding: 0.75rem 0;
    font-style: italic;
  }

  /* Deck list rows */
  .deck-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .deck-row {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    padding: 0.3125rem 0;
    border-bottom: 1px solid var(--border-subtle);
    transition: background var(--duration-fast) var(--ease-out);
  }

  .deck-row:last-child {
    border-bottom: none;
  }

  .deck-row:hover {
    background: var(--bg-elevated);
    border-radius: var(--radius-sm);
  }

  .row-img-wrap {
    width: 32px;
    aspect-ratio: 421 / 614;
    border-radius: 3px;
    overflow: hidden;
    flex-shrink: 0;
    background: var(--bg-overlay);
  }

  .row-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .row-name {
    flex: 1;
    font-size: 0.8125rem;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .row-controls {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    flex-shrink: 0;
  }

  .qty-btn {
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-overlay);
    border: 1px solid var(--border-subtle);
    border-radius: 4px;
    color: var(--text-secondary);
    font-size: 0.875rem;
    cursor: pointer;
    transition:
      background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
    padding: 0;
    line-height: 1;
  }

  .qty-btn:hover:not(:disabled) {
    background: var(--bg-elevated);
    color: var(--text-primary);
    border-color: var(--border-strong);
  }

  .qty-btn:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .qty-val {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text-secondary);
    min-width: 24px;
    text-align: center;
  }

  .rm-btn {
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-tertiary);
    font-size: 0.6875rem;
    cursor: pointer;
    border-radius: 4px;
    padding: 0;
    margin-left: 2px;
    transition: color var(--duration-fast) var(--ease-out),
      background var(--duration-fast) var(--ease-out);
  }

  .rm-btn:hover {
    color: var(--error);
    background: rgba(224, 84, 84, 0.1);
  }

  /* ── Spinners ───────────────────────────────────────────────────────────── */
  .spinner {
    display: inline-block;
    width: 13px;
    height: 13px;
    border: 2px solid rgba(0, 0, 0, 0.25);
    border-top-color: #000;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
    vertical-align: middle;
  }

  .spinner-dark {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 2px solid var(--border-default);
    border-top-color: var(--gold);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* ── Mobile fallback ────────────────────────────────────────────────────── */
  @media (max-width: 768px) {
    .builder-layout {
      grid-template-columns: 1fr;
    }

    .search-panel {
      position: static;
      height: auto;
      border-right: none;
      border-bottom: 1px solid var(--border-subtle);
    }
  }
</style>
