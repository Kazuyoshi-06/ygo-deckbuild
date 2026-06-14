<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  let { data } = $props();

  // ── Types ──────────────────────────────────────────────────────────────────

  interface DeckSummary {
    id: number;
    title: string;
    archetype_label: string | null;
    tags: string[];
    created_at: string;
  }

  interface ComparedCard {
    card_id: number;
    external_card_id: number;
    name: string;
    type: string;
    frame_type: string;
    image_url: string;
    presence_pct: number;
    quantities: number[];
  }

  interface DeckRatios {
    main_count: number;
    monster_count: number;
    spell_count: number;
    trap_count: number;
    extra_count: number;
    side_count: number;
  }

  interface DeckMeta {
    id: number;
    title: string;
    archetype_label: string | null;
    tags: string[];
    created_at: string;
  }

  interface CompareOut {
    deck_ids: number[];
    decks: DeckMeta[];
    core: ComparedCard[];
    flex: ComparedCard[];
    unique: ComparedCard[];
    ratios: DeckRatios[];
    divergence_score: number;
  }

  // ── State ──────────────────────────────────────────────────────────────────

  let selectedIds = $state<number[]>([]);
  let search = $state('');
  let showPicker = $state(true);
  let comparison = $state<CompareOut | null>(null);
  let loading = $state(false);
  let fetchError = $state('');

  // ── Init from URL on mount ─────────────────────────────────────────────────

  onMount(() => {
    const param = new URLSearchParams(window.location.search).get('ids');
    if (param) {
      selectedIds = param.split(',').map(Number).filter(Boolean);
      showPicker = selectedIds.length < 2;
    }
  });

  // ── Reactive fetch when selection changes ──────────────────────────────────

  $effect(() => {
    const ids = [...selectedIds];
    if (ids.length < 2) {
      comparison = null;
      return;
    }
    let cancelled = false;
    loading = true;
    fetchError = '';
    fetch(`/api/v1/compare?deck_ids=${ids.join(',')}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.statusText))
      .then(d => { if (!cancelled) { comparison = d; loading = false; } })
      .catch(e => { if (!cancelled) { fetchError = String(e); loading = false; } });
    return () => { cancelled = true; };
  });

  // ── Derived ───────────────────────────────────────────────────────────────

  const filteredDecks = $derived(
    (data.decks as DeckSummary[]).filter(d =>
      !selectedIds.includes(d.id) &&
      d.title.toLowerCase().includes(search.toLowerCase())
    )
  );

  const selectedDecks = $derived(
    selectedIds.map(id => (data.decks as DeckSummary[]).find(d => d.id === id)).filter(Boolean) as DeckSummary[]
  );

  // ── Helpers ───────────────────────────────────────────────────────────────

  function addDeck(id: number) {
    if (selectedIds.length >= 5 || selectedIds.includes(id)) return;
    selectedIds = [...selectedIds, id];
    search = '';
    updateUrl();
  }

  function removeDeck(id: number) {
    selectedIds = selectedIds.filter(x => x !== id);
    updateUrl();
  }

  function updateUrl() {
    const q = selectedIds.length ? `?ids=${selectedIds.join(',')}` : '';
    goto(`/compare${q}`, { replaceState: true, noScroll: true });
  }

  const FRAME_COLORS: Record<string, string> = {
    spell:    '#4ade80',
    trap:     '#c084fc',
    normal:   '#fbbf24',
    effect:   '#fb923c',
    fusion:   '#a855f7',
    synchro:  '#e2e8f0',
    xyz:      '#94a3b8',
    link:     '#60a5fa',
    ritual:   '#818cf8',
    token:    '#6b7280',
  };

  function frameColor(ft: string): string {
    const base = ft.replace(/_pendulum$/, '').replace(/^pendulum_/, '');
    return FRAME_COLORS[base] ?? FRAME_COLORS[ft] ?? '#8b8fa8';
  }

  function formatQty(q: number): string {
    return q === 0 ? '—' : `×${q}`;
  }

  // Recommended ranges for ratios (TCG competitive 2025-2026)
  const RATIO_ADVICE: Record<keyof DeckRatios, { min: number; max: number; label: string }> = {
    main_count:    { min: 40, max: 40,  label: 'Main deck' },
    monster_count: { min: 18, max: 26,  label: 'Monsters' },
    spell_count:   { min: 8,  max: 16,  label: 'Spells' },
    trap_count:    { min: 0,  max: 10,  label: 'Traps' },
    extra_count:   { min: 14, max: 15,  label: 'Extra deck' },
    side_count:    { min: 0,  max: 15,  label: 'Side deck' },
  };

  function ratioStatus(key: keyof DeckRatios, val: number): 'ok' | 'warn' | 'bad' {
    const { min, max } = RATIO_ADVICE[key];
    if (val >= min && val <= max) return 'ok';
    const margin = Math.max(1, Math.round((max - min) / 2));
    if (val >= min - margin && val <= max + margin) return 'warn';
    return 'bad';
  }

  function divergenceLabel(score: number): string {
    if (score <= 0.15) return 'Quasi-identiques';
    if (score <= 0.30) return 'Similaires — tech différente';
    if (score <= 0.50) return 'Variantes distinctes';
    if (score <= 0.70) return 'Builds différents';
    return 'Totalement différents';
  }

  function divergenceColor(score: number): string {
    if (score <= 0.15) return 'var(--success)';
    if (score <= 0.35) return 'var(--gold)';
    return 'var(--error)';
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  const RATIO_KEYS: (keyof DeckRatios)[] = [
    'main_count', 'monster_count', 'spell_count', 'trap_count', 'extra_count', 'side_count'
  ];
</script>

<svelte:head>
  <title>Comparer des decks — YGO Intel</title>
</svelte:head>

<div class="page-container compare-page">
  <header class="compare-header">
    <h1 class="compare-title">
      <span class="title-icon" aria-hidden="true">⊞</span>
      Comparateur de Decklists
    </h1>
    <p class="compare-sub">Sélectionnez 2 à 5 decklists pour analyser les différences, ratios et divergences.</p>
  </header>

  <!-- ── Deck Picker ──────────────────────────────────────────────────────── -->
  <section class="picker-section">
    <div class="selected-pills">
      {#each selectedDecks as deck (deck.id)}
        <span class="deck-pill">
          <span class="pill-title">{deck.title}</span>
          <button class="pill-remove" onclick={() => removeDeck(deck.id)} aria-label="Retirer {deck.title}" type="button">✕</button>
        </span>
      {/each}
      {#if selectedIds.length < 5}
        <button
          class="pill-add"
          onclick={() => (showPicker = !showPicker)}
          type="button"
          aria-expanded={showPicker}
        >
          {showPicker ? '▲ Fermer' : '＋ Ajouter un deck'}
        </button>
      {/if}
      {#if selectedIds.length > 0 && selectedIds.length < 2}
        <span class="picker-hint">Ajoutez au moins un autre deck pour comparer.</span>
      {/if}
    </div>

    {#if showPicker}
      <div class="picker-box">
        <input
          class="picker-search"
          type="search"
          placeholder="Rechercher un deck…"
          bind:value={search}
          autocomplete="off"
        />
        <div class="picker-list" aria-label="Decks disponibles">
          {#if filteredDecks.length === 0}
            <p class="picker-empty">Aucun deck trouvé.</p>
          {/if}
          {#each filteredDecks.slice(0, 30) as deck (deck.id)}
            <button
              class="picker-item"
              type="button"
              onclick={() => addDeck(deck.id)}
              aria-label="Ajouter {deck.title}"
            >
              <span class="picker-item-title">{deck.title}</span>
              <span class="picker-item-meta">
                {#if deck.archetype_label}<span class="picker-arch">{deck.archetype_label}</span>{/if}
                {formatDate(deck.created_at)}
              </span>
            </button>
          {/each}
        </div>
      </div>
    {/if}
  </section>

  <!-- ── Empty state ─────────────────────────────────────────────────────── -->
  {#if selectedIds.length < 2 && !loading}
    <div class="empty-state">
      <span class="empty-icon" aria-hidden="true">⊞</span>
      <p>Sélectionnez 2 à 5 decklists pour démarrer la comparaison.</p>
      <a href="/decks" class="btn-secondary">Voir mes decks</a>
    </div>

  <!-- ── Loading ─────────────────────────────────────────────────────────── -->
  {:else if loading}
    <div class="loading-state">
      <span class="loading-dot"></span>
      <span>Analyse en cours…</span>
    </div>

  <!-- ── Error ───────────────────────────────────────────────────────────── -->
  {:else if fetchError}
    <div class="error-state">Erreur : {fetchError}</div>

  <!-- ── Results ─────────────────────────────────────────────────────────── -->
  {:else if comparison}
    {@const c = comparison}

    <!-- Divergence banner -->
    <div class="divergence-banner">
      <span class="divergence-label">Score de divergence</span>
      <span class="divergence-score" style="color: {divergenceColor(c.divergence_score)}">
        {(c.divergence_score * 100).toFixed(0)}%
      </span>
      <span class="divergence-desc">— {divergenceLabel(c.divergence_score)}</span>
    </div>

    <!-- Ratio table -->
    <section class="section">
      <h2 class="section-title">Ratios</h2>
      <div class="ratio-table-wrap">
        <table class="ratio-table">
          <thead>
            <tr>
              <th class="ratio-metric">Métrique</th>
              {#each c.decks as deck}
                <th class="ratio-deck-col" title={deck.title}>{deck.title.slice(0, 22)}{deck.title.length > 22 ? '…' : ''}</th>
              {/each}
              <th class="ratio-ref">Conseillé</th>
            </tr>
          </thead>
          <tbody>
            {#each RATIO_KEYS as key}
              {@const advice = RATIO_ADVICE[key]}
              <tr class="ratio-row" class:ratio-row--sub={key !== 'main_count' && key !== 'extra_count' && key !== 'side_count'}>
                <td class="ratio-metric">
                  {#if key === 'monster_count' || key === 'spell_count' || key === 'trap_count'}
                    <span class="ratio-indent">└</span>
                  {/if}
                  {advice.label}
                </td>
                {#each c.ratios as r, i}
                  {@const val = r[key]}
                  {@const status = ratioStatus(key, val)}
                  <td class="ratio-val" class:ratio-ok={status === 'ok'} class:ratio-warn={status === 'warn'} class:ratio-bad={status === 'bad'}>
                    {val}
                  </td>
                {/each}
                <td class="ratio-ref">
                  {advice.min === advice.max ? advice.min : `${advice.min}–${advice.max}`}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <!-- Core cards -->
    {#if c.core.length > 0}
      <section class="section">
        <h2 class="section-title">
          <span class="section-badge section-badge--core">CORE</span>
          Cartes communes ({c.core.length})
          <span class="section-sub">Présentes dans tous les decks</span>
        </h2>
        <div class="card-grid">
          {#each c.core as card}
            <div class="card-row">
              <img
                class="card-thumb"
                src={card.image_url}
                alt={card.name}
                loading="lazy"
                width="32"
                height="44"
              />
              <span
                class="frame-dot"
                style="background: {frameColor(card.frame_type)}"
                aria-hidden="true"
              ></span>
              <span class="card-name">{card.name}</span>
              <span class="qty-row">
                {#each card.quantities as qty, i}
                  <span class="qty-cell" class:qty-zero={qty === 0} class:qty-max={qty === 3}>
                    {formatQty(qty)}
                  </span>
                {/each}
              </span>
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <!-- Flex cards -->
    {#if c.flex.length > 0}
      <section class="section">
        <h2 class="section-title">
          <span class="section-badge section-badge--flex">FLEX</span>
          Cartes variables ({c.flex.length})
          <span class="section-sub">Présentes dans 50–99% des decks</span>
        </h2>
        <div class="card-grid">
          {#each c.flex as card}
            <div class="card-row">
              <img
                class="card-thumb"
                src={card.image_url}
                alt={card.name}
                loading="lazy"
                width="32"
                height="44"
              />
              <span
                class="frame-dot"
                style="background: {frameColor(card.frame_type)}"
                aria-hidden="true"
              ></span>
              <span class="card-name">{card.name}</span>
              <span class="presence-bar" title="{card.presence_pct}% des decks">
                <span class="presence-fill" style="width: {card.presence_pct}%"></span>
              </span>
              <span class="qty-row">
                {#each card.quantities as qty}
                  <span class="qty-cell" class:qty-zero={qty === 0} class:qty-max={qty === 3}>
                    {formatQty(qty)}
                  </span>
                {/each}
              </span>
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <!-- Unique cards -->
    {#if c.unique.length > 0}
      <section class="section">
        <h2 class="section-title">
          <span class="section-badge section-badge--unique">TECH</span>
          Cartes spécifiques ({c.unique.length})
          <span class="section-sub">Exclusives à un ou quelques decks</span>
        </h2>
        <div class="card-grid">
          {#each c.unique as card}
            <div class="card-row">
              <img
                class="card-thumb"
                src={card.image_url}
                alt={card.name}
                loading="lazy"
                width="32"
                height="44"
              />
              <span
                class="frame-dot"
                style="background: {frameColor(card.frame_type)}"
                aria-hidden="true"
              ></span>
              <span class="card-name">{card.name}</span>
              <span class="qty-row">
                {#each card.quantities as qty}
                  <span class="qty-cell" class:qty-zero={qty === 0} class:qty-max={qty === 3}>
                    {formatQty(qty)}
                  </span>
                {/each}
              </span>
            </div>
          {/each}
        </div>
      </section>
    {/if}
  {/if}
</div>

<style>
  .compare-page { padding: 2rem 0 4rem; }

  .compare-header { margin-bottom: 2rem; }
  .compare-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.4rem;
  }
  .title-icon { color: var(--gold); font-size: 1.5rem; }
  .compare-sub { color: var(--text-secondary); font-size: 0.95rem; }

  /* ── Picker ─────────────────────────────────────────────────────────────── */
  .picker-section { margin-bottom: 2.5rem; }

  .selected-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 1rem;
  }

  .deck-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: var(--bg-elevated);
    border: 1px solid var(--gold);
    color: var(--gold);
    border-radius: 20px;
    padding: 0.3rem 0.75rem 0.3rem 0.9rem;
    font-size: 0.85rem;
    font-weight: 600;
  }
  .pill-title { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pill-remove {
    background: none; border: none; cursor: pointer;
    color: var(--text-secondary); font-size: 0.8rem; padding: 0 0 0 0.2rem;
    transition: color var(--duration-fast);
  }
  .pill-remove:hover { color: var(--error); }

  .pill-add {
    background: var(--bg-elevated);
    border: 1px dashed var(--border-strong);
    color: var(--text-secondary);
    border-radius: 20px;
    padding: 0.3rem 0.9rem;
    font-size: 0.85rem;
    cursor: pointer;
    transition: border-color var(--duration-fast), color var(--duration-fast);
  }
  .pill-add:hover { border-color: var(--gold); color: var(--gold); }

  .picker-hint { color: var(--text-tertiary); font-size: 0.85rem; font-style: italic; }

  .picker-box {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    padding: 1rem;
    max-width: 540px;
  }

  .picker-search {
    width: 100%;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    padding: 0.55rem 0.85rem;
    font-size: 0.9rem;
    margin-bottom: 0.75rem;
    outline: none;
  }
  .picker-search:focus { border-color: var(--gold); }

  .picker-list { max-height: 280px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
  .picker-empty { color: var(--text-tertiary); font-size: 0.9rem; text-align: center; padding: 1rem; }

  .picker-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 0.55rem 0.75rem;
    border-radius: var(--radius-sm);
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
    transition: background var(--duration-fast);
  }
  .picker-item:hover { background: var(--bg-elevated); }
  .picker-item-title { font-size: 0.9rem; color: var(--text-primary); font-weight: 500; }
  .picker-item-meta { font-size: 0.78rem; color: var(--text-tertiary); display: flex; align-items: center; gap: 0.5rem; }
  .picker-arch {
    background: var(--gold-dim);
    color: var(--gold);
    border-radius: 4px;
    padding: 0.1rem 0.4rem;
    font-size: 0.72rem;
  }

  /* ── Empty / Loading / Error ─────────────────────────────────────────────── */
  .empty-state {
    display: flex; flex-direction: column; align-items: center;
    gap: 1rem; padding: 4rem 1rem; color: var(--text-secondary); text-align: center;
  }
  .empty-icon { font-size: 3rem; color: var(--text-tertiary); }
  .btn-secondary {
    padding: 0.5rem 1.25rem; border-radius: var(--radius-sm);
    border: 1px solid var(--border-strong); color: var(--text-secondary);
    text-decoration: none; font-size: 0.9rem;
    transition: border-color var(--duration-fast), color var(--duration-fast);
  }
  .btn-secondary:hover { border-color: var(--gold); color: var(--gold); }

  .loading-state {
    display: flex; align-items: center; gap: 0.75rem;
    color: var(--text-secondary); padding: 3rem 0;
  }
  .loading-dot {
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--gold); animation: pulse 1.2s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100% { opacity: 0.3; } 50% { opacity: 1; } }

  .error-state { color: var(--error); padding: 2rem 0; }

  /* ── Divergence Banner ──────────────────────────────────────────────────── */
  .divergence-banner {
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    padding: 1rem 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
  }
  .divergence-label { color: var(--text-secondary); font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
  .divergence-score { font-size: 1.5rem; font-weight: 800; }
  .divergence-desc { color: var(--text-secondary); font-size: 0.9rem; }

  /* ── Sections ────────────────────────────────────────────────────────────── */
  .section { margin-bottom: 2.5rem; }

  .section-title {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.9rem;
    flex-wrap: wrap;
  }
  .section-sub { color: var(--text-tertiary); font-size: 0.8rem; font-weight: 400; }

  .section-badge {
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    padding: 0.2rem 0.55rem;
    border-radius: 4px;
  }
  .section-badge--core   { background: rgba(201,164,73,0.15);  color: var(--gold); }
  .section-badge--flex   { background: rgba(91,142,255,0.12);  color: var(--blue); }
  .section-badge--unique { background: rgba(74,186,122,0.12);  color: var(--success); }

  /* ── Ratio Table ─────────────────────────────────────────────────────────── */
  .ratio-table-wrap { overflow-x: auto; }
  .ratio-table {
    width: 100%; border-collapse: collapse;
    font-size: 0.88rem; min-width: 360px;
  }
  .ratio-table th {
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 0.8rem;
    text-align: left;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--border-default);
    white-space: nowrap;
  }
  .ratio-deck-col { text-align: center; max-width: 140px; }
  .ratio-metric { color: var(--text-primary) !important; }
  .ratio-ref { color: var(--text-tertiary) !important; text-align: center; }

  .ratio-row td { padding: 0.45rem 0.75rem; border-bottom: 1px solid var(--border-subtle); }
  .ratio-row:last-child td { border-bottom: none; }
  .ratio-row--sub td { color: var(--text-secondary); font-size: 0.84rem; }
  .ratio-indent { color: var(--text-tertiary); margin-right: 0.25rem; }

  .ratio-val { text-align: center; font-weight: 600; }
  .ratio-ok   { color: var(--success); }
  .ratio-warn { color: var(--warning); }
  .ratio-bad  { color: var(--error); }
  .ratio-ref  { text-align: center; font-size: 0.82rem; }

  /* ── Card Grid ───────────────────────────────────────────────────────────── */
  .card-grid {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .card-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.4rem 0.75rem;
    border-bottom: 1px solid var(--border-subtle);
    transition: background var(--duration-fast);
  }
  .card-row:last-child { border-bottom: none; }
  .card-row:hover { background: var(--bg-elevated); }

  .card-thumb {
    width: 32px; height: 44px;
    object-fit: cover;
    border-radius: 3px;
    flex-shrink: 0;
    background: var(--bg-elevated);
  }

  .frame-dot {
    width: 8px; height: 8px; border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 0 6px currentColor;
  }

  .card-name {
    flex: 1;
    font-size: 0.875rem;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .presence-bar {
    width: 48px; height: 4px; border-radius: 2px;
    background: var(--bg-overlay);
    flex-shrink: 0;
    overflow: hidden;
  }
  .presence-fill { height: 100%; background: var(--blue); border-radius: 2px; }

  .qty-row { display: flex; gap: 0.3rem; flex-shrink: 0; }
  .qty-cell {
    min-width: 28px; text-align: center;
    font-size: 0.8rem; font-weight: 600;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
  }
  .qty-zero { color: var(--text-tertiary); font-weight: 400; }
  .qty-max  { color: var(--gold); }

  /* ── Mobile ─────────────────────────────────────────────────────────────── */
  @media (max-width: 640px) {
    .compare-title { font-size: 1.4rem; }
    .divergence-banner { flex-direction: column; align-items: flex-start; gap: 0.3rem; }
    .card-name { max-width: 120px; }
    .presence-bar { display: none; }
  }
</style>
