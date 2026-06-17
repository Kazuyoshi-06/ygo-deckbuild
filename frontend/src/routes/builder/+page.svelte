<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount, untrack } from 'svelte';
  import CardPreview from '$lib/components/CardPreview.svelte';

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
    cardmarket_price: number | null;
    tcgplayer_price: number | null;
  }

  interface DeckSlot {
    card_id: number;
    name: string;
    frame_type: string;
    image_url: string;
    quantity: number;
    tcg_date: string | null;
    ocg_date: string | null;
    cardmarket_price: number | null;
    archetype: string | null;
  }

  interface TechCard {
    card_id: number;
    name: string;
    image_url: string;
    type_label: string;
    frame_type: string;
    deck_count: number;
    frequency: number;
    avg_quantity: number;
  }

  function cardBadge(tcg_date: string | null, ocg_date: string | null): 'OCG' | 'TCG' | null {
    if (tcg_date && ocg_date) return null;
    if (ocg_date && !tcg_date) return 'OCG';
    if (tcg_date && !ocg_date) return 'TCG';
    return null;
  }

  let { data } = $props<{
    data: {
      initialCards: CardItem[];
      tcgBan: Record<number, string>;
      ocgBan: Record<number, string>;
    };
  }>();

  // ── Deck state ────────────────────────────────────────────────────────────
  let deckTitle: string = $state('New Deck');
  let mainDeck: DeckSlot[] = $state([]);
  let extraDeck: DeckSlot[] = $state([]);
  let sideDeck: DeckSlot[] = $state([]);

  let mainCount = $derived(mainDeck.reduce((s, c) => s + c.quantity, 0));
  let extraCount = $derived(extraDeck.reduce((s, c) => s + c.quantity, 0));
  let sideCount = $derived(sideDeck.reduce((s, c) => s + c.quantity, 0));
  let totalCards = $derived(mainCount + extraCount + sideCount);

  function deckBudget(...decks: DeckSlot[][]): number | null {
    let total = 0;
    let hasPrice = false;
    for (const deck of decks) {
      for (const c of deck) {
        if (c.cardmarket_price !== null) {
          total += c.cardmarket_price * c.quantity;
          hasPrice = true;
        }
      }
    }
    return hasPrice ? total : null;
  }

  let totalBudget = $derived(deckBudget(mainDeck, extraDeck, sideDeck));

  function formatPrice(value: number | null): string {
    if (value === null) return '—';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'EUR' }).format(value);
  }

  // ── Search state ──────────────────────────────────────────────────────────
  let searchQuery: string = $state('');
  let filterType: string = $state('');
  let filterAttribute: string = $state('');
  let sortBy: string = $state('');
  let searchResults: CardItem[] = $state(untrack(() => data.initialCards));
  let searchLoading: boolean = $state(false);

  // ── Advanced filters (T2.3) ──────────────────────────────────────────────
  let showAdvanced: boolean = $state(false);
  let filterRace: string = $state('');
  let filterLevelMin: string = $state('');
  let filterLevelMax: string = $state('');
  let filterAtkMin: string = $state('');
  let filterAtkMax: string = $state('');
  let filterDefMin: string = $state('');
  let filterDefMax: string = $state('');

  let advancedActiveCount = $derived(
    [filterRace, filterLevelMin, filterLevelMax, filterAtkMin, filterAtkMax, filterDefMin, filterDefMax]
      .filter((v) => v !== '').length
  );

  function resetAdvancedFilters() {
    filterRace = '';
    filterLevelMin = '';
    filterLevelMax = '';
    filterAtkMin = '';
    filterAtkMax = '';
    filterDefMin = '';
    filterDefMax = '';
  }

  // ── Save state ────────────────────────────────────────────────────────────
  let saving: boolean = $state(false);
  let saveError: string = $state('');

  // ── Deck validation ───────────────────────────────────────────────────────
  interface ValidationIssue {
    level: 'error' | 'warn';
    msg: string;
  }

  let validationIssues = $derived<ValidationIssue[]>((() => {
    const issues: ValidationIssue[] = [];
    if (mainCount > 60)  issues.push({ level: 'error', msg: `Main deck: ${mainCount} cards — max 60` });
    if (extraCount > 15) issues.push({ level: 'error', msg: `Extra deck: ${extraCount} cards — max 15` });
    if (sideCount > 15)  issues.push({ level: 'error', msg: `Side deck: ${sideCount} cards — max 15` });
    if (mainCount < 40 && mainCount > 0) issues.push({ level: 'warn', msg: `Main deck: ${mainCount} cards — needs at least 40 for tournament play` });
    return issues;
  })());

  let hasErrors = $derived(validationIssues.some((i) => i.level === 'error'));

  // ── Banlist enforcement ───────────────────────────────────────────────────
  let activeBanFormat: 'TCG' | 'OCG' = $state('TCG');
  let blockedMessage: string = $state('');
  let blockedTimer: ReturnType<typeof setTimeout> | undefined;

  // ── Card section detection ────────────────────────────────────────────────
  const EXTRA_FRAMES = new Set([
    'fusion', 'synchro', 'xyz', 'link',
    'xyz_pendulum', 'synchro_pendulum', 'fusion_pendulum',
  ]);

  function defaultSection(frameType: string): 'main' | 'extra' {
    return EXTRA_FRAMES.has(frameType) ? 'extra' : 'main';
  }

  // ── Banlist helpers ───────────────────────────────────────────────────────
  function banLabel(st: string): string {
    if (st === 'forbidden') return 'BAN';
    if (st === 'limited') return '×1';
    return '×2';
  }

  // Max copies allowed in active format (across ALL sections combined)
  function maxAllowed(card_id: number): number {
    const st = banMap[card_id];
    if (st === 'forbidden') return 0;
    if (st === 'limited') return 1;
    if (st === 'semi_limited') return 2;
    return 3;
  }

  // ── Deck operations ───────────────────────────────────────────────────────
  interface AddableCard {
    id: number;
    name: string;
    frame_type: string;
    image_url: string;
    tcg_date?: string | null;
    ocg_date?: string | null;
    cardmarket_price?: number | null;
    archetype?: string | null;
  }

  function addCard(card: AddableCard, targetSection?: 'main' | 'extra' | 'side') {
    const section = targetSection ?? defaultSection(card.frame_type);
    const deck = section === 'main' ? mainDeck : section === 'extra' ? extraDeck : sideDeck;
    const max = maxAllowed(card.id);

    if (max === 0) {
      blockedMessage = `${card.name} is Forbidden in ${activeBanFormat}`;
      clearTimeout(blockedTimer);
      blockedTimer = setTimeout(() => { blockedMessage = ''; }, 2500);
      return;
    }

    const totalQty = deckQtyMap.get(card.id) ?? 0;
    if (totalQty >= max) return;

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
        tcg_date: card.tcg_date ?? null,
        ocg_date: card.ocg_date ?? null,
        cardmarket_price: card.cardmarket_price ?? null,
        archetype: card.archetype ?? null,
      });
    }
  }

  function changeQty(deck: DeckSlot[], card_id: number, delta: number) {
    const idx = deck.findIndex(c => c.card_id === card_id);
    if (idx === -1) return;
    const newQty = deck[idx].quantity + delta;
    if (newQty <= 0) {
      deck.splice(idx, 1);
    } else if (delta > 0) {
      const totalQty = deckQtyMap.get(card_id) ?? 0;
      if (totalQty >= maxAllowed(card_id)) return;
      if (newQty <= 3) deck[idx].quantity = newQty;
    } else {
      deck[idx].quantity = newQty;
    }
  }

  function removeCard(deck: DeckSlot[], card_id: number) {
    const idx = deck.findIndex(c => c.card_id === card_id);
    if (idx !== -1) deck.splice(idx, 1);
  }

  // Active format's banlist map
  let banMap = $derived(activeBanFormat === 'TCG' ? data.tcgBan : data.ocgBan);

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

  // ── Tech suggestions (T2.9) ──────────────────────────────────────────────
  // Most common archetype among main/extra deck cards, weighted by quantity.
  let deckArchetype = $derived(
    (() => {
      const counts = new Map<string, number>();
      for (const c of [...mainDeck, ...extraDeck]) {
        if (!c.archetype) continue;
        counts.set(c.archetype, (counts.get(c.archetype) ?? 0) + c.quantity);
      }
      let best: string | null = null;
      let bestCount = 0;
      for (const [label, count] of counts) {
        if (count > bestCount) {
          best = label;
          bestCount = count;
        }
      }
      return best;
    })()
  );

  let techSuggestions: TechCard[] = $state([]);
  let techLoading: boolean = $state(false);
  let techArchetype: string | null = $state(null);

  $effect(() => {
    const archetype = deckArchetype;
    if (!archetype) {
      techSuggestions = [];
      techArchetype = null;
      return;
    }

    const timer = setTimeout(async () => {
      techLoading = true;
      try {
        const res = await fetch(
          `/api/v1/analytics/archetypes/${encodeURIComponent(archetype)}/tech-suggestions?limit=10`
        );
        if (res.ok) {
          const body = await res.json();
          techSuggestions = body.cards ?? [];
        } else {
          techSuggestions = [];
        }
      } catch {
        techSuggestions = [];
      } finally {
        techArchetype = archetype;
        techLoading = false;
      }
    }, 400);

    return () => clearTimeout(timer);
  });

  function addTechCard(card: TechCard) {
    addCard({
      id: card.card_id,
      name: card.name,
      frame_type: card.frame_type,
      image_url: card.image_url,
      archetype: techArchetype,
    });
  }

  // ── Debounced search ──────────────────────────────────────────────────────
  let firstRender = true;

  $effect(() => {
    const q = searchQuery;
    const type = filterType;
    const attr = filterAttribute;
    const sort = sortBy;
    const race = filterRace;
    const levelMin = filterLevelMin;
    const levelMax = filterLevelMax;
    const atkMin = filterAtkMin;
    const atkMax = filterAtkMax;
    const defMin = filterDefMin;
    const defMax = filterDefMax;

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
      if (sort) params.set('sort', sort);
      if (race) params.set('race', race);
      if (levelMin) params.set('level_min', levelMin);
      if (levelMax) params.set('level_max', levelMax);
      if (atkMin) params.set('atk_min', atkMin);
      if (atkMax) params.set('atk_max', atkMax);
      if (defMin) params.set('def_min', defMin);
      if (defMax) params.set('def_max', defMax);

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
      clearDraft();
      goto(`/decks/${body.deck_id}`);
    } catch {
      saveError = 'Network error';
      saving = false;
    }
  }

  // ── Autosave draft (localStorage) ────────────────────────────────────────
  const DRAFT_KEY = 'ygo-builder-draft';
  const AUTOSAVE_INTERVAL_MS = 30_000;

  interface DraftPayload {
    title: string;
    mainDeck: DeckSlot[];
    extraDeck: DeckSlot[];
    sideDeck: DeckSlot[];
    savedAt: string;
  }

  let draftSavedFlash: boolean = $state(false);
  let draftRestoredAt: string | null = $state(null);
  let draftFlashTimer: ReturnType<typeof setTimeout> | undefined;

  function clearDraft() {
    localStorage.removeItem(DRAFT_KEY);
  }

  function saveDraft() {
    if (totalCards === 0) {
      clearDraft();
      return;
    }
    const payload: DraftPayload = {
      title: deckTitle,
      mainDeck,
      extraDeck,
      sideDeck,
      savedAt: new Date().toISOString(),
    };
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(payload));
    } catch {
      return;
    }
    draftSavedFlash = true;
    clearTimeout(draftFlashTimer);
    draftFlashTimer = setTimeout(() => { draftSavedFlash = false; }, 2500);
  }

  function loadDraft(): DraftPayload | null {
    try {
      const raw = localStorage.getItem(DRAFT_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as DraftPayload;
      if (!parsed || !Array.isArray(parsed.mainDeck)) return null;
      return parsed;
    } catch {
      return null;
    }
  }

  function discardDraft() {
    clearDraft();
    draftRestoredAt = null;
    deckTitle = 'New Deck';
    mainDeck = [];
    extraDeck = [];
    sideDeck = [];
  }

  function formatDraftTime(iso: string): string {
    return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }

  onMount(() => {
    const draft = loadDraft();
    if (draft) {
      deckTitle = draft.title;
      mainDeck = draft.mainDeck;
      extraDeck = draft.extraDeck;
      sideDeck = draft.sideDeck;
      draftRestoredAt = draft.savedAt;
    }

    const interval = setInterval(saveDraft, AUTOSAVE_INTERVAL_MS);
    return () => {
      clearInterval(interval);
      clearTimeout(draftFlashTimer);
    };
  });

  const CARD_TYPES = [
    'Effect Monster', 'Normal Monster', 'Ritual Monster', 'Gemini Monster',
    'Fusion Monster', 'Synchro Monster', 'XYZ Monster', 'Link Monster',
    'Pendulum Effect Monster', 'Normal Spell Card', 'Continuous Spell Card',
    'Quick-Play Spell Card', 'Field Spell Card', 'Ritual Spell Card',
    'Normal Trap Card', 'Continuous Trap Card', 'Counter Trap Card',
  ];

  const ATTRIBUTES = ['DARK', 'LIGHT', 'EARTH', 'WATER', 'FIRE', 'WIND', 'DIVINE'];

  const RACES = [
    'Aqua', 'Beast', 'Beast-Warrior', 'Creator God', 'Cyberse', 'Dinosaur',
    'Divine-Beast', 'Dragon', 'Fairy', 'Fiend', 'Fish', 'Illusion', 'Insect',
    'Machine', 'Plant', 'Psychic', 'Pyro', 'Reptile', 'Rock', 'Sea Serpent',
    'Spellcaster', 'Thunder', 'Warrior', 'Winged Beast', 'Wyrm', 'Zombie',
  ];

  // ── Card hover preview ────────────────────────────────────────────────────
  let previewCardId: number | null = $state(null);
  let previewX = $state(0);
  let previewY = $state(0);
  let hoverTimer: ReturnType<typeof setTimeout> | null = null;

  function showPreview(id: number, e: MouseEvent) {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    if (hoverTimer) clearTimeout(hoverTimer);
    hoverTimer = setTimeout(() => {
      previewCardId = id;
      previewX = rect.right;
      previewY = rect.top + rect.height / 2;
    }, 120);
  }

  function hidePreview() {
    if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
    previewCardId = null;
  }
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
    {#if draftSavedFlash}
      <span class="draft-badge" role="status">● Draft saved</span>
    {/if}
  </div>
  <div class="topbar-right">
    {#if blockedMessage}
      <span class="blocked-msg" role="alert">{blockedMessage}</span>
    {:else if saveError}
      <span class="save-error">{saveError}</span>
    {/if}

    <!-- Format toggle for banlist enforcement -->
    <div class="ban-format-toggle" role="group" aria-label="Banlist format">
      <span class="ban-format-label">Banlist</span>
      {#each (['TCG', 'OCG'] as const) as fmt}
        <button
          class="ban-fmt-btn"
          class:active={activeBanFormat === fmt}
          onclick={() => (activeBanFormat = fmt)}
          aria-pressed={activeBanFormat === fmt}
        >{fmt}</button>
      {/each}
    </div>

    <span class="total-badge" class:has-cards={totalCards > 0}>{totalCards} cards</span>
    {#if totalBudget !== null}
      <span class="budget-badge">{formatPrice(totalBudget)}</span>
    {/if}
    <button
      class="btn-primary save-btn"
      onclick={saveDeck}
      disabled={saving || totalCards === 0 || !deckTitle.trim() || hasErrors}
      title={hasErrors ? 'Fix deck errors before saving' : undefined}
    >
      {#if saving}
        <span class="spinner" aria-hidden="true"></span> Saving…
      {:else}
        Save deck ↑
      {/if}
    </button>
  </div>
</div>

<!-- ── Draft restored notice ──────────────────────────────────────────────── -->
{#if draftRestoredAt}
  <div class="draft-notice" role="status">
    <span>Restored unsaved draft from {formatDraftTime(draftRestoredAt)}.</span>
    <button type="button" class="draft-notice-discard" onclick={discardDraft}>Discard</button>
    <button
      type="button"
      class="draft-notice-dismiss"
      onclick={() => (draftRestoredAt = null)}
      aria-label="Dismiss"
    >×</button>
  </div>
{/if}

<!-- ── Validation strip ───────────────────────────────────────────────────── -->
{#if validationIssues.length > 0}
  <div class="validation-strip" role="alert" aria-live="polite">
    {#each validationIssues as issue (issue.msg)}
      <span class="val-issue val-issue--{issue.level}">
        <span class="val-icon" aria-hidden="true">{issue.level === 'error' ? '✕' : '!'}</span>
        {issue.msg}
      </span>
    {/each}
  </div>
{/if}

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
      <select class="filter-select filter-select--full" bind:value={sortBy} aria-label="Sort by">
        <option value="">Sort: Name</option>
        <option value="price_asc">Sort: Price ↑</option>
        <option value="price_desc">Sort: Price ↓</option>
      </select>
    </div>

    <button
      type="button"
      class="advanced-toggle"
      onclick={() => (showAdvanced = !showAdvanced)}
      aria-expanded={showAdvanced}
    >
      <span>Advanced filters{advancedActiveCount > 0 ? ` (${advancedActiveCount})` : ''}</span>
      <span class="advanced-chevron" class:advanced-chevron--open={showAdvanced} aria-hidden="true">▾</span>
    </button>

    {#if showAdvanced}
      <div class="advanced-panel">
        <select class="filter-select filter-select--full" bind:value={filterRace} aria-label="Filter by race">
          <option value="">All races</option>
          {#each RACES as r}
            <option value={r}>{r}</option>
          {/each}
        </select>
        <div class="range-row">
          <span class="range-label">Level/Rank/Link</span>
          <input
            type="number"
            class="range-input"
            placeholder="Min"
            bind:value={filterLevelMin}
            aria-label="Minimum Level/Rank/Link"
            min="0"
            max="13"
          />
          <span class="range-sep">–</span>
          <input
            type="number"
            class="range-input"
            placeholder="Max"
            bind:value={filterLevelMax}
            aria-label="Maximum Level/Rank/Link"
            min="0"
            max="13"
          />
        </div>
        <div class="range-row">
          <span class="range-label">ATK</span>
          <input
            type="number"
            class="range-input"
            placeholder="Min"
            bind:value={filterAtkMin}
            aria-label="Minimum ATK"
            min="0"
          />
          <span class="range-sep">–</span>
          <input
            type="number"
            class="range-input"
            placeholder="Max"
            bind:value={filterAtkMax}
            aria-label="Maximum ATK"
            min="0"
          />
        </div>
        <div class="range-row">
          <span class="range-label">DEF</span>
          <input
            type="number"
            class="range-input"
            placeholder="Min"
            bind:value={filterDefMin}
            aria-label="Minimum DEF"
            min="0"
          />
          <span class="range-sep">–</span>
          <input
            type="number"
            class="range-input"
            placeholder="Max"
            bind:value={filterDefMax}
            aria-label="Maximum DEF"
            min="0"
          />
        </div>
        {#if advancedActiveCount > 0}
          <button type="button" class="advanced-clear" onclick={resetAdvancedFilters}>Clear advanced filters</button>
        {/if}
      </div>
    {/if}

    {#if searchLoading}
      <ul class="card-grid-sm" aria-label="Loading cards" aria-busy="true">
        {#each Array(12) as _, i (i)}
          <li><div class="skeleton card-thumb-skeleton"></div></li>
        {/each}
      </ul>
    {:else if searchResults.length === 0}
      <div class="search-empty">No cards found</div>
    {:else}
      <ul class="card-grid-sm" aria-label="Search results">
        {#each searchResults as card (card.id)}
          {@const qty = deckQtyMap.get(card.id) ?? 0}
          {@const max = maxAllowed(card.id)}
          {@const maxed = qty >= max}
          {@const badge = cardBadge(card.tcg_date, card.ocg_date)}
          {@const banSt = banMap[card.id] ?? null}
          <li>
            <button
              class="card-thumb"
              class:maxed
              class:card-thumb--banned={banSt === 'forbidden'}
              title="{card.name}{qty > 0 ? ` (×${qty} in deck)` : ''}{badge ? ` [${badge}]` : ''}{banSt ? ` · ${activeBanFormat}: ${banLabel(banSt)}` : ''} · Ctrl+click to add to side"
              onclick={(e) => addCard(card, (e as MouseEvent).ctrlKey || (e as MouseEvent).metaKey ? 'side' : undefined)}
              onmouseenter={(e) => showPreview(card.id, e)}
              onmouseleave={hidePreview}
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
              {#if banSt}
                <span class="ban-strip ban-strip--{banSt}" aria-hidden="true"></span>
                <span class="ban-chip ban-chip--{banSt}">{banLabel(banSt)}</span>
              {/if}
              {#if qty > 0}
                <span class="qty-overlay" class:maxed>{qty}</span>
              {/if}
              {#if card.cardmarket_price !== null}
                <span class="price-chip">{formatPrice(card.cardmarket_price)}</span>
              {/if}
            </button>
          </li>
        {/each}
      </ul>
    {/if}

    <!-- ── Tech suggestions (T2.9) ───────────────────────────────────────── -->
    {#if deckArchetype}
      <div class="tech-section">
        <h3 class="tech-label">
          Tech suggestions <span class="tech-archetype">— {deckArchetype}</span>
        </h3>
        {#if techLoading && techSuggestions.length === 0}
          <div class="tech-loading">
            <span class="spinner-dark" aria-hidden="true"></span>
          </div>
        {:else if techSuggestions.length === 0}
          <p class="tech-empty">No tech cards found for this archetype yet.</p>
        {:else}
          <ul class="card-grid-sm" aria-label="Tech suggestions">
            {#each techSuggestions as card (card.card_id)}
              {@const qty = deckQtyMap.get(card.card_id) ?? 0}
              {@const max = maxAllowed(card.card_id)}
              {@const maxed = qty >= max}
              {@const banSt = banMap[card.card_id] ?? null}
              <li>
                <button
                  class="card-thumb"
                  class:maxed
                  class:card-thumb--banned={banSt === 'forbidden'}
                  title="{card.name} · played in {Math.round(card.frequency * 100)}% of {deckArchetype} decks{qty > 0 ? ` (×${qty} in deck)` : ''}"
                  onclick={(e) => addTechCard(card)}
                  onmouseenter={(e) => showPreview(card.card_id, e)}
                  onmouseleave={hidePreview}
                  aria-label="Add {card.name} to deck"
                >
                  <img
                    src={card.image_url}
                    alt={card.name}
                    class="card-thumb-img"
                    loading="lazy"
                    onerror={handleImgError}
                  />
                  <span class="tech-freq-chip">{Math.round(card.frequency * 100)}%</span>
                  {#if banSt}
                    <span class="ban-strip ban-strip--{banSt}" aria-hidden="true"></span>
                    <span class="ban-chip ban-chip--{banSt}">{banLabel(banSt)}</span>
                  {/if}
                  {#if qty > 0}
                    <span class="qty-overlay" class:maxed>{qty}</span>
                  {/if}
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
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
            {@const tcgSt = data.tcgBan[slot.card_id] ?? null}
            {@const ocgSt = data.ocgBan[slot.card_id] ?? null}
            <li class="deck-row" onmouseenter={(e) => showPreview(slot.card_id, e)} onmouseleave={hidePreview}>
              <div class="row-img-wrap">
                <img src={slot.image_url} alt={slot.name} class="row-img" loading="lazy" onerror={handleImgError} />
              </div>
              <span class="row-name">{slot.name}</span>
              {#if badge}
                <span class="row-badge row-badge--{badge.toLowerCase()}">{badge}</span>
              {/if}
              {#if tcgSt || ocgSt}
                <div class="row-ban-badges">
                  {#if tcgSt}<span class="row-ban row-ban--{tcgSt}">TCG {banLabel(tcgSt)}</span>{/if}
                  {#if ocgSt}<span class="row-ban row-ban--{ocgSt}">OCG {banLabel(ocgSt)}</span>{/if}
                </div>
              {/if}
              <div class="row-controls">
                <button class="qty-btn" onclick={() => changeQty(mainDeck, slot.card_id, -1)} aria-label="Decrease">−</button>
                <span class="qty-val">×{slot.quantity}</span>
                <button class="qty-btn" onclick={() => changeQty(mainDeck, slot.card_id, 1)} aria-label="Increase" disabled={slot.quantity >= 3 || (deckQtyMap.get(slot.card_id) ?? 0) >= maxAllowed(slot.card_id)}>+</button>
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
            {@const tcgSt = data.tcgBan[slot.card_id] ?? null}
            {@const ocgSt = data.ocgBan[slot.card_id] ?? null}
            <li class="deck-row" onmouseenter={(e) => showPreview(slot.card_id, e)} onmouseleave={hidePreview}>
              <div class="row-img-wrap">
                <img src={slot.image_url} alt={slot.name} class="row-img" loading="lazy" onerror={handleImgError} />
              </div>
              <span class="row-name">{slot.name}</span>
              {#if badge}
                <span class="row-badge row-badge--{badge.toLowerCase()}">{badge}</span>
              {/if}
              {#if tcgSt || ocgSt}
                <div class="row-ban-badges">
                  {#if tcgSt}<span class="row-ban row-ban--{tcgSt}">TCG {banLabel(tcgSt)}</span>{/if}
                  {#if ocgSt}<span class="row-ban row-ban--{ocgSt}">OCG {banLabel(ocgSt)}</span>{/if}
                </div>
              {/if}
              <div class="row-controls">
                <button class="qty-btn" onclick={() => changeQty(extraDeck, slot.card_id, -1)} aria-label="Decrease">−</button>
                <span class="qty-val">×{slot.quantity}</span>
                <button class="qty-btn" onclick={() => changeQty(extraDeck, slot.card_id, 1)} aria-label="Increase" disabled={slot.quantity >= 3 || (deckQtyMap.get(slot.card_id) ?? 0) >= maxAllowed(slot.card_id)}>+</button>
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
            {@const tcgSt = data.tcgBan[slot.card_id] ?? null}
            {@const ocgSt = data.ocgBan[slot.card_id] ?? null}
            <li class="deck-row" onmouseenter={(e) => showPreview(slot.card_id, e)} onmouseleave={hidePreview}>
              <div class="row-img-wrap">
                <img src={slot.image_url} alt={slot.name} class="row-img" loading="lazy" onerror={handleImgError} />
              </div>
              <span class="row-name">{slot.name}</span>
              {#if badge}
                <span class="row-badge row-badge--{badge.toLowerCase()}">{badge}</span>
              {/if}
              {#if tcgSt || ocgSt}
                <div class="row-ban-badges">
                  {#if tcgSt}<span class="row-ban row-ban--{tcgSt}">TCG {banLabel(tcgSt)}</span>{/if}
                  {#if ocgSt}<span class="row-ban row-ban--{ocgSt}">OCG {banLabel(ocgSt)}</span>{/if}
                </div>
              {/if}
              <div class="row-controls">
                <button class="qty-btn" onclick={() => changeQty(sideDeck, slot.card_id, -1)} aria-label="Decrease">−</button>
                <span class="qty-val">×{slot.quantity}</span>
                <button class="qty-btn" onclick={() => changeQty(sideDeck, slot.card_id, 1)} aria-label="Increase" disabled={slot.quantity >= 3 || (deckQtyMap.get(slot.card_id) ?? 0) >= maxAllowed(slot.card_id)}>+</button>
                <button class="rm-btn" onclick={() => removeCard(sideDeck, slot.card_id)} aria-label="Remove">✕</button>
              </div>
            </li>
          {/each}
        </ul>
      {/if}
    </section>

  </main>
</div>

<CardPreview cardId={previewCardId} anchorX={previewX} anchorY={previewY} />

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

  .draft-badge {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.6875rem;
    font-weight: 600;
    color: #4ade80;
    white-space: nowrap;
    animation: draft-fade 2.5s ease-out forwards;
  }

  @keyframes draft-fade {
    0%, 60% { opacity: 1; }
    100% { opacity: 0; }
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

  .budget-badge {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8125rem;
    font-weight: 700;
    color: var(--gold);
    white-space: nowrap;
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

  .filter-select--full {
    grid-column: 1 / -1;
  }

  .advanced-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    margin-top: 0.5rem;
    padding: 0.4rem 0.1rem;
    background: none;
    border: none;
    color: var(--text-tertiary);
    font-family: inherit;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: color var(--duration-fast) var(--ease-out);
  }

  .advanced-toggle:hover {
    color: var(--text-secondary);
  }

  .advanced-chevron {
    transition: transform var(--duration-fast) var(--ease-out);
  }

  .advanced-chevron--open {
    transform: rotate(180deg);
  }

  .advanced-panel {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 0.25rem;
    padding: 0.625rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
  }

  .range-row {
    display: grid;
    grid-template-columns: auto 1fr auto 1fr;
    align-items: center;
    gap: 0.4rem;
  }

  .range-label {
    font-size: 0.6875rem;
    color: var(--text-tertiary);
    white-space: nowrap;
  }

  .range-sep {
    color: var(--text-tertiary);
    text-align: center;
  }

  .range-input {
    width: 100%;
    padding: 0.3rem 0.4rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.75rem;
    outline: none;
  }

  .range-input:focus {
    border-color: var(--gold);
  }

  .advanced-clear {
    align-self: flex-start;
    padding: 0.2rem 0;
    background: none;
    border: none;
    color: var(--gold);
    font-size: 0.6875rem;
    font-weight: 600;
    cursor: pointer;
  }

  .advanced-clear:hover {
    color: var(--gold-hover);
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

  .card-thumb-skeleton {
    aspect-ratio: 421 / 614;
    border-radius: 4px;
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

  .price-chip {
    position: absolute;
    bottom: 2px;
    left: 2px;
    padding: 0.05rem 0.28rem;
    background: rgba(0, 0, 0, 0.75);
    backdrop-filter: blur(2px);
    border-radius: 3px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.5rem;
    font-weight: 700;
    color: var(--gold);
    line-height: 1.6;
    pointer-events: none;
  }

  /* ── Tech suggestions (T2.9) ───────────────────────────────────────────── */
  .tech-section {
    margin-top: 1.25rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border-subtle);
  }

  .tech-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.6875rem;
    font-weight: 700;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 0 0 0.625rem;
  }

  .tech-archetype {
    color: var(--gold);
    text-transform: none;
    letter-spacing: normal;
    font-weight: 600;
  }

  .tech-loading {
    display: flex;
    justify-content: center;
    padding: 1rem;
  }

  .tech-empty {
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  .tech-freq-chip {
    position: absolute;
    top: 3px;
    left: 3px;
    padding: 0.05rem 0.28rem;
    background: rgba(0, 0, 0, 0.75);
    backdrop-filter: blur(2px);
    border-radius: 3px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.5rem;
    font-weight: 700;
    color: var(--text-secondary);
    line-height: 1.6;
    pointer-events: none;
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

  /* ── Mobile fallback (T3.6) ─────────────────────────────────────────────── */
  @media (max-width: 768px) {
    .builder-layout {
      grid-template-columns: 1fr;
    }

    .search-panel {
      position: static;
      height: auto;
      border-right: none;
      border-bottom: 1px solid var(--border-subtle);
      padding: 1rem;
    }

    .deck-panel {
      padding: 1.25rem 1rem;
    }

    /* 2 columns instead of 4 — thumbnails stay tappable on narrow screens */
    .card-grid-sm {
      grid-template-columns: repeat(2, 1fr);
      gap: 0.5rem;
    }

    /* Topbar wraps to two rows instead of squeezing/overflowing horizontally */
    .topbar {
      flex-wrap: wrap;
      padding: 0.625rem 1rem;
      row-gap: 0.625rem;
    }

    .topbar-left {
      flex: 1 1 100%;
    }

    .topbar-right {
      flex: 1 1 100%;
      flex-wrap: wrap;
    }

    .title-input {
      max-width: none;
    }

    /* Larger touch targets for deck row controls (was 22px, below the ~44px guideline) */
    .qty-btn,
    .rm-btn {
      width: 32px;
      height: 32px;
    }

    .deck-row {
      padding: 0.5rem 0;
      gap: 0.5rem;
    }
  }

  /* ── Validation strip ───────────────────────────────────────────────────── */
  .draft-notice {
    display: flex;
    align-items: center;
    gap: 0.875rem;
    padding: 0.5rem 1.5rem;
    background: rgba(201, 164, 73, 0.08);
    border-bottom: 1px solid rgba(201, 164, 73, 0.2);
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .draft-notice-discard {
    background: none;
    border: none;
    color: var(--gold);
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    padding: 0;
  }

  .draft-notice-discard:hover {
    color: var(--gold-hover);
  }

  .draft-notice-dismiss {
    margin-left: auto;
    background: none;
    border: none;
    color: var(--text-tertiary);
    font-size: 1rem;
    line-height: 1;
    cursor: pointer;
    padding: 0;
  }

  .draft-notice-dismiss:hover {
    color: var(--text-primary);
  }

  .validation-strip {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.375rem 1rem;
    padding: 0.5rem 1.5rem;
    background: rgba(8, 9, 13, 0.9);
    border-bottom: 1px solid var(--border-subtle);
    position: sticky;
    top: 120px; /* nav (60px) + topbar (~60px) */
    z-index: 40;
    backdrop-filter: blur(8px);
  }

  .val-issue {
    display: flex;
    align-items: center;
    gap: 0.3125rem;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .val-issue--error {
    color: #f87171;
  }

  .val-issue--warn {
    color: #fbbf24;
  }

  .val-icon {
    font-size: 0.625rem;
    font-weight: 800;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .val-issue--error .val-icon {
    background: rgba(239, 68, 68, 0.2);
    color: #f87171;
  }

  .val-issue--warn .val-icon {
    background: rgba(251, 191, 36, 0.15);
    color: #fbbf24;
  }

  /* ── Banlist format toggle (topbar) ─────────────────────────────────────── */
  .ban-format-toggle {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 0.1875rem 0.375rem 0.1875rem 0.5rem;
    flex-shrink: 0;
  }

  .ban-format-label {
    font-size: 0.625rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-right: 0.125rem;
  }

  .ban-fmt-btn {
    padding: 0.125rem 0.4375rem;
    border-radius: 3px;
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--text-tertiary);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
  }

  .ban-fmt-btn:hover {
    color: var(--text-primary);
  }

  .ban-fmt-btn.active {
    background: var(--bg-elevated);
    color: var(--gold);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  }

  /* Blocked message */
  .blocked-msg {
    font-size: 0.75rem;
    color: #f87171;
    white-space: nowrap;
    animation: fadeIn 0.15s ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(2px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  /* ── Banlist badges on search thumbnails ─────────────────────────────────── */
  .ban-strip {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 3px;
    pointer-events: none;
  }

  .ban-strip--forbidden    { background: rgba(239, 68, 68, 0.95); }
  .ban-strip--limited      { background: rgba(249, 115, 22, 0.95); }
  .ban-strip--semi_limited { background: rgba(234, 179, 8, 0.95); }

  /* Small chip label at top-right of thumbnail */
  .ban-chip {
    position: absolute;
    top: 2px;
    right: 2px;
    padding: 0 0.25rem;
    border-radius: 3px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.5rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    line-height: 1.6;
    pointer-events: none;
  }

  .ban-chip--forbidden    { background: rgba(239, 68, 68, 0.88); color: #fff; }
  .ban-chip--limited      { background: rgba(249, 115, 22, 0.88); color: #fff; }
  .ban-chip--semi_limited { background: rgba(234, 179, 8, 0.88); color: #0a0800; }

  /* Forbidden cards get a dim overlay */
  .card-thumb--banned {
    filter: grayscale(0.4);
  }

  /* ── Banlist badges on deck rows ─────────────────────────────────────────── */
  .row-ban-badges {
    display: flex;
    align-items: center;
    gap: 3px;
    flex-shrink: 0;
  }

  .row-ban {
    padding: 0.0625rem 0.3125rem;
    border-radius: 3px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.5rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    line-height: 1.7;
    white-space: nowrap;
  }

  .row-ban--forbidden {
    background: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.3);
  }

  .row-ban--limited {
    background: rgba(249, 115, 22, 0.15);
    color: #fb923c;
    border: 1px solid rgba(249, 115, 22, 0.3);
  }

  .row-ban--semi_limited {
    background: rgba(234, 179, 8, 0.12);
    color: #facc15;
    border: 1px solid rgba(234, 179, 8, 0.25);
  }
</style>
