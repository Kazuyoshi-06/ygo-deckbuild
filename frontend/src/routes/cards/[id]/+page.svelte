<script lang="ts">
  interface DeckUsingCard {
    deck_id: number;
    title: string;
    archetype_label: string | null;
  }

  interface CardDetail {
    id: number;
    external_card_id: number;
    name: string;
    slug: string;
    type: string;
    frame_type: string;
    race: string | null;
    attribute: string | null;
    archetype: string | null;
    level_rank_link: number | null;
    atk: number | null;
    def_: number | null;
    scale: number | null;
    linkval: number | null;
    description: string | null;
    pend_description: string | null;
    monster_description: string | null;
    tcg_date: string | null;
    ocg_date: string | null;
    cardmarket_price: number | null;
    tcgplayer_price: number | null;
    current_banlist_status: { tcg: string | null; ocg: string | null };
    decks_using: DeckUsingCard[];
    decks_using_total: number;
    image_url: string;
  }

  interface BanlistHistoryEntry {
    banlist_id: number;
    format: string;
    effective_date: string;
    version_label: string | null;
    status: string;
  }

  interface ReplacementCandidate {
    card_id: number;
    name: string;
    image_url: string;
    frame_type: string;
    before_pct: number;
    after_pct: number;
    delta: number;
  }

  interface CardReplacementsOut {
    card_id: number;
    card_name: string;
    format: string;
    is_banned: boolean;
    ban_date: string | null;
    affected_archetypes: string[];
    before_deck_count: number;
    after_deck_count: number;
    replacements: ReplacementCandidate[];
    has_data: boolean;
  }

  let { data } = $props<{
    data: {
      card: CardDetail;
      history: BanlistHistoryEntry[];
      replacements: Record<string, CardReplacementsOut | null>;
    };
  }>();

  const card = $derived(data.card as CardDetail);
  let historyFormat: 'TCG' | 'OCG' = $state('TCG');

  let tcgHistory = $derived((data.history as BanlistHistoryEntry[]).filter((h) => h.format === 'TCG'));
  let ocgHistory = $derived((data.history as BanlistHistoryEntry[]).filter((h) => h.format === 'OCG'));
  let displayedHistory = $derived(historyFormat === 'TCG' ? tcgHistory : ocgHistory);

  $effect(() => {
    historyFormat = tcgHistory.length > 0 ? 'TCG' : 'OCG';
  });

  const bannedFormats = $derived(
    (['TCG', 'OCG'] as const).filter((fmt) => data.replacements[fmt]?.is_banned)
  );
  let replacementFormat: 'TCG' | 'OCG' = $state('TCG');

  $effect(() => {
    if (bannedFormats.length > 0) replacementFormat = bannedFormats[0];
  });

  const activeReplacements = $derived(data.replacements[replacementFormat] ?? null);

  function pct(v: number): string {
    return `${(v * 100).toFixed(0)}%`;
  }

  function statusLabel(s: string | null): string {
    if (!s) return 'Unlimited';
    if (s === 'forbidden') return 'Forbidden';
    if (s === 'limited') return 'Limited';
    if (s === 'semi_limited') return 'Semi-Limited';
    return s;
  }

  function formatDate(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function formatPrice(value: number | null, currency: 'EUR' | 'USD'): string {
    if (value === null) return '—';
    const symbol = currency === 'EUR' ? '€' : '$';
    return `${symbol}${value.toFixed(2)}`;
  }

  function typeInfo(c: CardDetail): string {
    const parts: string[] = [];
    if (c.attribute) parts.push(c.attribute);
    if (c.race) parts.push(c.race);
    if (c.level_rank_link !== null) {
      if (c.frame_type === 'link') parts.push(`Link ${c.linkval ?? c.level_rank_link}`);
      else if (c.frame_type.startsWith('xyz')) parts.push(`Rank ${c.level_rank_link}`);
      else parts.push(`Level ${c.level_rank_link}`);
    }
    return parts.join(' / ');
  }

  function handleImgError(e: Event) {
    (e.target as HTMLImageElement).src = '/media/placeholder-card.svg';
  }
</script>

<svelte:head>
  <title>{card.name} — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <a href="/cards" class="back-link">← Cards</a>

  <div class="card-layout">
    <!-- Left: large image -->
    <div class="image-col">
      <div class="image-wrap">
        <img src={card.image_url} alt={card.name} class="card-image" onerror={handleImgError} />
      </div>
      <div class="price-row">
        <div class="price-item">
          <span class="price-label">Cardmarket</span>
          <span class="price-value">{formatPrice(card.cardmarket_price, 'EUR')}</span>
        </div>
        <div class="price-item">
          <span class="price-label">TCGplayer</span>
          <span class="price-value">{formatPrice(card.tcgplayer_price, 'USD')}</span>
        </div>
      </div>
    </div>

    <!-- Right: info -->
    <div class="info-col">
      <header class="card-header">
        <span class="card-eyebrow">{card.type}</span>
        <h1 class="card-name">{card.name}</h1>
        {#if typeInfo(card)}
          <p class="card-meta">{typeInfo(card)}</p>
        {/if}
        {#if card.archetype}
          <a href="/analytics/archetypes/{encodeURIComponent(card.archetype)}" class="archetype-link">
            {card.archetype}
          </a>
        {/if}
      </header>

      {#if card.atk !== null || card.def_ !== null}
        <div class="stats-row">
          {#if card.atk !== null}
            <span class="stat-pill">ATK {card.atk === -1 ? '?' : card.atk}</span>
          {/if}
          {#if card.def_ !== null && card.frame_type !== 'link'}
            <span class="stat-pill">DEF {card.def_ === -1 ? '?' : card.def_}</span>
          {/if}
          {#if card.scale !== null}
            <span class="stat-pill">Scale {card.scale}</span>
          {/if}
        </div>
      {/if}

      <!-- Current banlist status -->
      <div class="banlist-status-row">
        {#each [['TCG', card.current_banlist_status.tcg], ['OCG', card.current_banlist_status.ocg]] as [fmt, status] (fmt)}
          <span class="status-badge status-badge--{status ?? 'unlimited'}">
            <span class="status-badge-fmt">{fmt}</span>
            {statusLabel(status as string | null)}
          </span>
        {/each}
      </div>

      <!-- Dates -->
      <div class="dates-row">
        <span class="date-item">TCG release: <strong>{formatDate(card.tcg_date)}</strong></span>
        <span class="date-item">OCG release: <strong>{formatDate(card.ocg_date)}</strong></span>
      </div>

      <!-- Description -->
      {#if card.description}
        <section class="desc-section">
          <h2 class="section-label">Card Text</h2>
          <p class="card-description">{card.description}</p>
        </section>
      {/if}
      {#if card.pend_description}
        <section class="desc-section">
          <h2 class="section-label">Pendulum Effect</h2>
          <p class="card-description">{card.pend_description}</p>
        </section>
      {/if}

      <!-- Banlist history -->
      <section class="history-section">
        <h2 class="section-label">Banlist History</h2>
        <div class="history-tabs" role="tablist">
          {#each [['TCG', tcgHistory.length], ['OCG', ocgHistory.length]] as [fmt, count] (fmt)}
            <button
              role="tab"
              class="history-tab"
              class:active={historyFormat === fmt}
              onclick={() => (historyFormat = fmt as 'TCG' | 'OCG')}
              aria-selected={historyFormat === fmt}
            >
              {fmt} <span class="history-tab-count">{count}</span>
            </button>
          {/each}
        </div>

        {#if displayedHistory.length === 0}
          <p class="history-empty">Never restricted in {historyFormat}.</p>
        {:else}
          <ul class="history-timeline">
            {#each displayedHistory as entry, i (entry.banlist_id)}
              <li class="history-entry">
                <div class="timeline-connector">
                  <span class="timeline-dot timeline-dot--{entry.status}" aria-hidden="true"></span>
                  {#if i !== displayedHistory.length - 1}<span class="timeline-line" aria-hidden="true"></span>{/if}
                </div>
                <div class="timeline-content">
                  <span class="timeline-status timeline-status--{entry.status}">{statusLabel(entry.status)}</span>
                  <span class="timeline-date">{entry.version_label ?? formatDate(entry.effective_date)}</span>
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </section>

      <!-- Replacement finder (T3.3) -->
      {#if bannedFormats.length > 0}
        <section class="replacements-section">
          <h2 class="section-label">Replacement Cards</h2>
          {#if bannedFormats.length > 1}
            <div class="history-tabs" role="tablist">
              {#each bannedFormats as fmt (fmt)}
                <button
                  role="tab"
                  class="history-tab"
                  class:active={replacementFormat === fmt}
                  onclick={() => (replacementFormat = fmt)}
                  aria-selected={replacementFormat === fmt}
                >{fmt}</button>
              {/each}
            </div>
          {/if}

          {#if activeReplacements}
            {#if activeReplacements.affected_archetypes.length === 0}
              <p class="history-empty">
                Forbidden since {formatDate(activeReplacements.ban_date)}, but no archetype in the
                database played it before the ban — not enough data to find replacements.
              </p>
            {:else if activeReplacements.replacements.length === 0}
              <p class="history-empty">
                Forbidden since {formatDate(activeReplacements.ban_date)} — affected
                {activeReplacements.affected_archetypes.join(', ')}, but no clear replacement has emerged yet.
              </p>
            {:else}
              <p class="replacements-desc">
                Forbidden since {formatDate(activeReplacements.ban_date)} — comparing
                {activeReplacements.before_deck_count} deck{activeReplacements.before_deck_count !== 1 ? 's' : ''} before
                vs {activeReplacements.after_deck_count} after, across {activeReplacements.affected_archetypes.join(', ')}.
              </p>
              <ul class="replacements-list">
                {#each activeReplacements.replacements as rep (rep.card_id)}
                  <li class="replacement-row">
                    <a href="/cards/{rep.card_id}" class="replacement-link">
                      <img
                        src={rep.image_url}
                        alt={rep.name}
                        class="replacement-thumb"
                        loading="lazy"
                        onerror={handleImgError}
                      />
                      <span class="replacement-name">{rep.name}</span>
                    </a>
                    <span class="replacement-stats">
                      <span class="replacement-before">{pct(rep.before_pct)}</span>
                      <span class="replacement-arrow" aria-hidden="true">→</span>
                      <span class="replacement-after">{pct(rep.after_pct)}</span>
                    </span>
                  </li>
                {/each}
              </ul>
            {/if}
          {/if}
        </section>
      {/if}

      <!-- Decks using this card -->
      <section class="decks-section">
        <h2 class="section-label">
          Decks using this card
          {#if card.decks_using_total > 0}<span class="section-count">{card.decks_using_total}</span>{/if}
        </h2>
        {#if card.decks_using.length === 0}
          <p class="history-empty">No decks in the database use this card yet.</p>
        {:else}
          <ul class="decks-list">
            {#each card.decks_using as deck (deck.deck_id)}
              <li>
                <a href="/decks/{deck.deck_id}" class="deck-link">
                  <span class="deck-link-title">{deck.title}</span>
                  {#if deck.archetype_label}
                    <span class="deck-link-archetype">{deck.archetype_label}</span>
                  {/if}
                </a>
              </li>
            {/each}
          </ul>
          {#if card.decks_using_total > card.decks_using.length}
            <p class="decks-more">+{card.decks_using_total - card.decks_using.length} more</p>
          {/if}
        {/if}
      </section>
    </div>
  </div>
</div>

<style>
  .page-body {
    padding-top: 2.5rem;
    padding-bottom: 5rem;
    max-width: 1100px;
  }

  .back-link {
    display: inline-block;
    color: var(--text-tertiary);
    font-size: 0.875rem;
    margin-bottom: 1.5rem;
    transition: color var(--duration-fast) var(--ease-out);
  }

  .back-link:hover {
    color: var(--gold);
  }

  .card-layout {
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 2.5rem;
  }

  @media (max-width: 720px) {
    .card-layout {
      grid-template-columns: 1fr;
    }
  }

  /* Image column */
  .image-col {
    position: sticky;
    top: 1.5rem;
    align-self: start;
  }

  .image-wrap {
    border-radius: var(--radius-lg);
    overflow: hidden;
    border: 1px solid var(--border-default);
    background: var(--bg-surface);
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.4);
  }

  .card-image {
    width: 100%;
    display: block;
  }

  .price-row {
    display: flex;
    gap: 0.75rem;
    margin-top: 1rem;
  }

  .price-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    padding: 0.625rem 0.75rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
  }

  .price-label {
    font-size: 0.625rem;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .price-value {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    color: var(--gold);
  }

  /* Info column */
  .card-eyebrow {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .card-name {
    font-size: 1.75rem;
    font-weight: 700;
    margin: 0.25rem 0 0.375rem;
  }

  .card-meta {
    font-size: 0.9375rem;
    color: var(--text-secondary);
    font-weight: 500;
  }

  .archetype-link {
    display: inline-block;
    margin-top: 0.5rem;
    font-size: 0.8125rem;
    color: var(--gold);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .archetype-link:hover {
    color: var(--gold-hover);
  }

  .stats-row,
  .banlist-status-row,
  .dates-row {
    display: flex;
    gap: 0.625rem;
    flex-wrap: wrap;
    margin-top: 1rem;
  }

  .stat-pill {
    padding: 0.3rem 0.7rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: 999px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.7rem;
    border-radius: 999px;
    font-size: 0.8125rem;
    font-weight: 600;
    border: 1px solid var(--border-default);
    background: var(--bg-surface);
    color: var(--text-tertiary);
  }

  .status-badge-fmt {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.6875rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    opacity: 0.7;
  }

  .status-badge--forbidden {
    color: #f87171;
    border-color: rgba(239, 68, 68, 0.35);
    background: rgba(239, 68, 68, 0.08);
  }

  .status-badge--limited {
    color: #fb923c;
    border-color: rgba(249, 115, 22, 0.35);
    background: rgba(249, 115, 22, 0.08);
  }

  .status-badge--semi_limited {
    color: #facc15;
    border-color: rgba(234, 179, 8, 0.35);
    background: rgba(234, 179, 8, 0.08);
  }

  .dates-row {
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .date-item strong {
    color: var(--text-primary);
    font-weight: 600;
  }

  .section-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.625rem;
  }

  .section-count {
    background: var(--gold-dim);
    color: var(--gold);
    border-radius: 999px;
    padding: 0.05rem 0.5rem;
    font-size: 0.6875rem;
  }

  .desc-section,
  .history-section,
  .replacements-section,
  .decks-section {
    margin-top: 1.75rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border-subtle);
  }

  .card-description {
    font-size: 0.875rem;
    line-height: 1.7;
    color: var(--text-secondary);
    white-space: pre-line;
  }

  /* Banlist history timeline */
  .history-tabs {
    display: inline-flex;
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    overflow: hidden;
    margin-bottom: 1rem;
  }

  .history-tab {
    padding: 0.45rem 0.875rem;
    background: var(--bg-surface);
    border: none;
    border-right: 1px solid var(--border-default);
    color: var(--text-tertiary);
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
  }

  .history-tab:last-child {
    border-right: none;
  }

  .history-tab.active {
    background: var(--bg-elevated);
    color: var(--text-primary);
  }

  .history-tab-count {
    opacity: 0.6;
  }

  .history-empty {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
  }

  .history-timeline {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .history-entry {
    display: flex;
    gap: 0.75rem;
  }

  .timeline-connector {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .timeline-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    margin-top: 0.3rem;
  }

  .timeline-dot--forbidden { background: #ef4444; box-shadow: 0 0 6px rgba(239, 68, 68, 0.4); }
  .timeline-dot--limited { background: #f97316; box-shadow: 0 0 6px rgba(249, 115, 22, 0.4); }
  .timeline-dot--semi_limited { background: #eab308; box-shadow: 0 0 6px rgba(234, 179, 8, 0.35); }

  .timeline-line {
    flex: 1;
    width: 1px;
    background: var(--border-default);
    margin: 0.2rem 0;
  }

  .timeline-content {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding-bottom: 1rem;
  }

  .timeline-status {
    font-size: 0.8125rem;
    font-weight: 600;
  }

  .timeline-status--forbidden { color: #f87171; }
  .timeline-status--limited { color: #fb923c; }
  .timeline-status--semi_limited { color: #facc15; }

  .timeline-date {
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  /* Replacement finder (T3.3) */
  .replacements-desc {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    line-height: 1.55;
    margin: 0.75rem 0 1rem;
  }

  .replacements-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .replacement-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.5rem 0.875rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
  }

  .replacement-link {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    min-width: 0;
  }

  .replacement-link:hover .replacement-name {
    color: var(--gold);
  }

  .replacement-thumb {
    width: 32px;
    height: 44px;
    flex-shrink: 0;
    border-radius: 3px;
    object-fit: cover;
    background: var(--bg-elevated);
  }

  .replacement-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .replacement-stats {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8125rem;
    flex-shrink: 0;
  }

  .replacement-before {
    color: var(--text-tertiary);
  }

  .replacement-arrow {
    color: var(--text-tertiary);
    opacity: 0.6;
  }

  .replacement-after {
    color: #4ade80;
    font-weight: 700;
  }

  /* Decks using this card */
  .decks-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .deck-link {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.625rem 0.875rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    transition: border-color var(--duration-fast) var(--ease-out),
      background var(--duration-fast) var(--ease-out);
  }

  .deck-link:hover {
    border-color: var(--gold);
    background: var(--bg-elevated);
  }

  .deck-link-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .deck-link-archetype {
    font-size: 0.75rem;
    color: var(--gold);
  }

  .decks-more {
    margin-top: 0.625rem;
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }
</style>
