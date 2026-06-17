<script lang="ts">
  interface ExpectedMetaEntry {
    label: string;
    meta_share: number;
    deck_count: number;
  }

  interface WeightedSideCard {
    card_id: number;
    name: string;
    frame_type: string;
    image_url: string;
    weighted_score: number;
    archetype_coverage: Record<string, number>;
  }

  interface LegalityViolation {
    card_id: number;
    name: string;
    status: string;
    limit_value: number;
    actual_quantity: number;
  }

  interface RestrictedCard {
    card_id: number;
    name: string;
    status: string;
    limit_value: number;
  }

  interface DeckLegalityOut {
    deck_id: number;
    banlist_id: number | null;
    format: string;
    is_legal: boolean;
    violations: LegalityViolation[];
    restricted: RestrictedCard[];
  }

  interface TournamentPrepOut {
    deck_id: number;
    deck_title: string;
    expected_meta: ExpectedMetaEntry[];
    meta_source: string;
    side_recommendations: WeightedSideCard[];
    has_side_data: boolean;
    legality_tcg: DeckLegalityOut;
    legality_ocg: DeckLegalityOut;
  }

  let { data } = $props<{ data: { deckId: number; prep: TournamentPrepOut } }>();
  const prep = $derived(data.prep as TournamentPrepOut);

  const PALETTE = ['#C9A449', '#4E8CD4', '#9B7FE0', '#00B894', '#fb7185', '#22d3ee', '#facc15', '#a855f7'];

  function colorFor(label: string): string {
    const idx = prep.expected_meta.findIndex((e) => e.label === label);
    return PALETTE[idx >= 0 ? idx % PALETTE.length : 0];
  }

  function pct(v: number): string {
    return `${(v * 100).toFixed(1)}%`;
  }

  function handleImgError(e: Event) {
    (e.target as HTMLImageElement).src = '/media/placeholder-card.svg';
  }

  function statusLabel(s: string): string {
    if (s === 'forbidden') return 'Forbidden';
    if (s === 'limited') return 'Limited';
    if (s === 'semi_limited') return 'Semi-Limited';
    return s;
  }

  interface LegalityPanel {
    fmt: string;
    legality: DeckLegalityOut;
  }

  const legalityPanels = $derived<LegalityPanel[]>([
    { fmt: 'TCG', legality: prep.legality_tcg },
    { fmt: 'OCG', legality: prep.legality_ocg },
  ]);
</script>

<svelte:head>
  <title>Tournament Prep — {prep.deck_title} — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="/decks/{data.deckId}" class="bc-link">{prep.deck_title}</a>
    <span class="bc-sep" aria-hidden="true">/</span>
    <span class="bc-current">Tournament Prep</span>
  </nav>

  <header class="page-header">
    <div>
      <span class="label">Pre-Tournament Briefing</span>
      <h1 class="page-title">{prep.deck_title}</h1>
    </div>
  </header>

  <!-- Expected meta -->
  <section class="section">
    <h2 class="section-title">Expected Meta</h2>
    <p class="section-desc">
      {#if prep.meta_source === 'tournament'}
        Based on reported tournament results (meta share = % of placed submissions).
      {:else}
        Based on the full deck database (no tournament results logged yet — meta share = % of all decks).
      {/if}
    </p>

    {#if prep.expected_meta.length === 0}
      <div class="tab-empty">
        <span aria-hidden="true">—</span>
        Not enough archetype data in the database yet to estimate the expected meta.
      </div>
    {:else}
      <div class="meta-grid">
        {#each prep.expected_meta as entry (entry.label)}
          <div class="meta-card" style="border-top-color: {colorFor(entry.label)};">
            <a href="/analytics/archetypes/{encodeURIComponent(entry.label)}" class="meta-label">{entry.label}</a>
            <span class="meta-share">{pct(entry.meta_share)}</span>
            <span class="meta-sub">{entry.deck_count} deck{entry.deck_count !== 1 ? 's' : ''}</span>
          </div>
        {/each}
      </div>
    {/if}
  </section>

  <!-- Banlist legality -->
  <section class="section">
    <h2 class="section-title">Banlist Legality</h2>
    <div class="legality-grid">
      {#each legalityPanels as { fmt, legality } (fmt)}
        <div class="legality-card">
          <div class="legality-card-header">
            <span class="legality-fmt">{fmt}</span>
            <div class="legality-badge" class:legal={legality.is_legal} class:illegal={!legality.is_legal}>
              <span class="legality-dot" aria-hidden="true"></span>
              <span class="legality-label">
                {legality.is_legal
                  ? `${fmt} Legal`
                  : `${legality.violations.length} violation${legality.violations.length > 1 ? 's' : ''}`}
              </span>
            </div>
          </div>
          {#if legality.violations.length > 0}
            <ul class="violation-list">
              {#each legality.violations as v (v.card_id)}
                <li>
                  <strong>{v.name}</strong> — {statusLabel(v.status)} (max {v.limit_value}), you run {v.actual_quantity}
                </li>
              {/each}
            </ul>
          {/if}
        </div>
      {/each}
    </div>
  </section>

  <!-- Side recommendations -->
  <section class="section">
    <h2 class="section-title">
      Recommended Side Cards
      <span class="section-count">{prep.side_recommendations.length}</span>
    </h2>
    <p class="section-desc">
      Weighted by how often pilots of each expected archetype side these cards themselves — a proxy for
      what the field is teching against right now.
    </p>

    {#if !prep.has_side_data || prep.side_recommendations.length === 0}
      <div class="tab-empty">
        <span aria-hidden="true">—</span>
        Not enough side-deck data yet for the expected archetypes (each needs ≥ 2 decks in the database).
      </div>
    {:else}
      <ul class="side-list">
        {#each prep.side_recommendations as card (card.card_id)}
          <li class="side-row">
            <img src={card.image_url} alt={card.name} class="side-thumb" loading="lazy" onerror={handleImgError} />
            <div class="side-info">
              <span class="side-name">{card.name}</span>
              <div class="side-coverage">
                {#each Object.entries(card.archetype_coverage) as [label, p] (label)}
                  <span class="coverage-chip" style="color:{colorFor(label)};border-color:{colorFor(label)}44;background:{colorFor(label)}12">
                    {label} {pct(p)}
                  </span>
                {/each}
              </div>
            </div>
            <span class="side-score">{(card.weighted_score * 100).toFixed(1)}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
</div>

<style>
  .page-body {
    padding-top: 2rem;
    padding-bottom: 5rem;
    max-width: 900px;
  }

  .breadcrumb {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8125rem;
    margin-bottom: 1.5rem;
  }

  .bc-link {
    color: var(--text-tertiary);
  }

  .bc-link:hover {
    color: var(--gold);
  }

  .bc-sep {
    color: var(--text-tertiary);
    opacity: 0.5;
  }

  .bc-current {
    color: var(--text-secondary);
  }

  .page-header {
    margin-bottom: 2rem;
  }

  .label {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .page-title {
    font-size: 1.75rem;
    font-weight: 700;
    margin-top: 0.25rem;
  }

  .section {
    margin-bottom: 2.5rem;
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8125rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 0.375rem;
  }

  .section-count {
    background: var(--gold-dim);
    color: var(--gold);
    border-radius: 999px;
    padding: 0.05rem 0.5rem;
    font-size: 0.6875rem;
  }

  .section-desc {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    margin-bottom: 1.25rem;
    line-height: 1.55;
    max-width: 60ch;
  }

  .tab-empty {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 2.25rem 1.25rem;
    font-size: 0.875rem;
    color: var(--text-tertiary);
    border: 1px dashed var(--border-subtle);
    border-radius: var(--radius-md);
  }

  /* Expected meta */
  .meta-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 1rem;
  }

  .meta-card {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 1rem 1.25rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-top: 3px solid;
    border-radius: var(--radius-md);
  }

  .meta-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.9375rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .meta-label:hover {
    color: var(--gold);
  }

  .meta-share {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .meta-sub {
    font-size: 0.6875rem;
    color: var(--text-tertiary);
  }

  /* Legality */
  .legality-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }

  .legality-card {
    padding: 1rem 1.25rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
  }

  .legality-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .legality-fmt {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.875rem;
    font-weight: 700;
    color: var(--text-secondary);
  }

  .legality-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.65rem;
    border-radius: 99px;
    font-size: 0.6875rem;
    font-weight: 600;
  }

  .legality-badge.legal {
    background: rgba(34, 197, 94, 0.12);
    border: 1px solid rgba(34, 197, 94, 0.25);
    color: #4ade80;
  }

  .legality-badge.illegal {
    background: rgba(220, 38, 38, 0.12);
    border: 1px solid rgba(220, 38, 38, 0.3);
    color: #f87171;
  }

  .legality-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .legality-badge.legal .legality-dot {
    background: #4ade80;
  }

  .legality-badge.illegal .legality-dot {
    background: #f87171;
  }

  .violation-list {
    list-style: none;
    margin: 0.875rem 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .violation-list li {
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .violation-list strong {
    color: #f87171;
  }

  /* Side recommendations */
  .side-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .side-row {
    display: flex;
    align-items: center;
    gap: 0.875rem;
    padding: 0.625rem 1rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
  }

  .side-thumb {
    width: 32px;
    height: 44px;
    flex-shrink: 0;
    border-radius: 3px;
    object-fit: cover;
    background: var(--bg-elevated);
  }

  .side-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .side-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .side-coverage {
    display: flex;
    gap: 0.375rem;
    flex-wrap: wrap;
  }

  .coverage-chip {
    padding: 0.05rem 0.4rem;
    border-radius: 4px;
    border: 1px solid;
    font-size: 0.625rem;
    font-weight: 600;
  }

  .side-score {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 700;
    color: var(--gold);
    flex-shrink: 0;
  }

  @media (max-width: 600px) {
    .legality-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
