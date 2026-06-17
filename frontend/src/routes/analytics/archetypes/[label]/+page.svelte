<script lang="ts">
  import { onMount } from 'svelte';

  interface CardFrequency {
    card_id: number;
    name: string;
    image_url: string;
    type_label: string;
    frame_type: string;
    deck_count: number;
    frequency: number;
    avg_quantity: number;
  }

  interface MonthlyEntry {
    month: string;
    count: number;
  }

  interface ArchetypeAnalytics {
    archetype_label: string;
    deck_count: number;
    avg_main_count: number;
    avg_extra_count: number;
    avg_side_count: number;
    core_cards: CardFrequency[];
    flex_cards: CardFrequency[];
    tech_cards: CardFrequency[];
    monthly_submissions: MonthlyEntry[];
  }

  interface DeckSummary {
    id: number;
    title: string;
    tags: string[];
    main_count: number;
    extra_count: number;
    side_count: number;
    created_at: string;
    updated_at: string;
  }

  let { data } = $props<{ data: { analytics: ArchetypeAnalytics | null; decks: DeckSummary[]; label: string } }>();
  let analytics = $derived(data.analytics);
  let decks = $derived(data.decks);

  // Active tab for card sections
  let activeTab: 'core' | 'flex' | 'tech' = $state('core');

  // ── Image skeleton loading (T2.8) ────────────────────────────────────────
  let loadedImages = $state(new Set<number>());

  function markImageLoaded(cardId: number) {
    loadedImages.add(cardId);
  }

  // ECharts color palette (matches design system)
  const C = {
    gold:   '#C9A449',
    blue:   '#4E8CD4',
    purple: '#9B7FE0',
    teal:   '#00B894',
    text:   '#8892A4',
    grid:   '#232630',
    bg:     '#131620',
  };

  // Color per frequency tier
  function tierColor(freq: number): string {
    if (freq >= 0.75) return C.gold;
    if (freq >= 0.25) return C.blue;
    return C.purple;
  }

  // Label for the type tag
  const TYPE_COLOR: Record<string, string> = {
    Monster: 'var(--gold)',
    Spell:   '#4e8cd4',
    Trap:    '#d44e6e',
    Other:   '#9b7fe0',
  };

  interface ChartCards {
    core_cards: CardFrequency[];
    flex_cards: CardFrequency[];
    tech_cards: CardFrequency[];
  }

  let freqEl: HTMLDivElement  = $state(null as unknown as HTMLDivElement);
  let timeEl: HTMLDivElement  = $state(null as unknown as HTMLDivElement);

  function axisStyle() {
    return {
      axisLabel: { color: C.text, fontFamily: 'Inter, sans-serif', fontSize: 11 },
      axisLine:  { lineStyle: { color: C.grid } },
      splitLine: { lineStyle: { color: C.grid } },
    };
  }

  function buildFreqOption(cards: ChartCards) {
    // Top 15 across all tiers, already sorted by frequency desc
    const top = [...cards.core_cards, ...cards.flex_cards, ...cards.tech_cards].slice(0, 15);
    const names  = top.map(c => c.name).reverse();
    const values = top.map(c => c.frequency).reverse();
    const colors = top.map(c => tierColor(c.frequency)).reverse();

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1a1d2e',
        borderColor: C.grid,
        textStyle: { color: '#dce3ef', fontSize: 12 },
        formatter: (params: { name: string; value: number }[]) => {
          const p = params[0];
          return `${p.name}<br/><b>${(p.value * 100).toFixed(1)}%</b> of decks`;
        },
      },
      grid: { left: 10, right: 70, top: 8, bottom: 8, containLabel: true },
      xAxis: {
        type: 'value',
        max: 1,
        axisLabel: {
          color: C.text,
          fontSize: 11,
          formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
        },
        axisLine:  { lineStyle: { color: C.grid } },
        splitLine: { lineStyle: { color: C.grid } },
      },
      yAxis: { type: 'category', data: names, ...axisStyle() },
      series: [{
        type: 'bar',
        data: values.map((v, i) => ({
          value: v,
          itemStyle: { color: colors[i], borderRadius: [0, 4, 4, 0] },
        })),
        barMaxWidth: 24,
        label: {
          show: true,
          position: 'right',
          formatter: (p: { value: number }) => `${(p.value * 100).toFixed(0)}%`,
          color: C.text,
          fontSize: 11,
        },
      }],
    };
  }

  function buildTimeOption(monthly: MonthlyEntry[]) {
    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1a1d2e',
        borderColor: C.grid,
        textStyle: { color: '#dce3ef', fontSize: 12 },
        formatter: (params: { name: string; value: number }[]) =>
          `${params[0].name}<br/><b>${params[0].value} deck${params[0].value !== 1 ? 's' : ''}</b>`,
      },
      grid: { left: 10, right: 20, top: 12, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: monthly.map(m => m.month), ...axisStyle() },
      yAxis: { type: 'value', minInterval: 1, ...axisStyle() },
      series: [{
        type: 'line',
        data: monthly.map(m => m.count),
        smooth: 0.4,
        symbol: 'circle',
        symbolSize: 7,
        itemStyle: { color: C.gold },
        lineStyle: { color: C.gold, width: 2 },
        areaStyle: { color: 'rgba(201,164,73,0.08)' },
      }],
    };
  }

  onMount(() => {
    if (!analytics) return;

    const snap = analytics;
    let charts: ReturnType<typeof import('echarts')['init']>[] = [];
    let ro: ResizeObserver | null = null;

    import('echarts').then((echarts) => {
      const initialized: ReturnType<typeof echarts.init>[] = [];

      if (freqEl) {
        const c = echarts.init(freqEl, null, { renderer: 'canvas' });
        c.setOption(buildFreqOption(snap as unknown as ChartCards));
        initialized.push(c);
      }

      if (timeEl && snap.monthly_submissions.length >= 2) {
        const c = echarts.init(timeEl, null, { renderer: 'canvas' });
        c.setOption(buildTimeOption(snap.monthly_submissions));
        initialized.push(c);
      }

      charts = initialized;
      ro = new ResizeObserver(() => charts.forEach(c => c.resize()));
      [freqEl, timeEl].filter(Boolean).forEach(el => ro!.observe(el));
    });

    return () => {
      ro?.disconnect();
      charts.forEach(c => c.dispose());
    };
  });

  function pct(freq: number) {
    return `${(freq * 100).toFixed(1)}%`;
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function barWidth(freq: number) {
    return `${(freq * 100).toFixed(1)}%`;
  }

  const activeCards = $derived(
    activeTab === 'core' ? analytics?.core_cards ?? []
    : activeTab === 'flex' ? analytics?.flex_cards ?? []
    : analytics?.tech_cards ?? []
  );
</script>

<svelte:head>
  <title>{data.label} — Archetype Analytics · YGO Intel</title>
</svelte:head>

<div class="page-container page-body">

  <!-- Breadcrumb -->
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="/analytics" class="bc-link">Analytics</a>
    <span class="bc-sep" aria-hidden="true">/</span>
    <span class="bc-current">{data.label}</span>
  </nav>

  {#if !analytics}
    <div class="empty-state">
      <div class="empty-icon" aria-hidden="true">◎</div>
      <p class="empty-title">No data for "{data.label}"</p>
      <p class="empty-sub">Import decks with this archetype label to unlock cross-deck analytics.</p>
      <a href="/analytics" class="btn-ghost">← Back to analytics</a>
    </div>
  {:else}

    <!-- Header -->
    <header class="page-header">
      <div>
        <span class="label">Archetype</span>
        <h1 class="page-title">{analytics.archetype_label}</h1>
      </div>
      <div class="header-actions">
        <a href="/analytics" class="btn-ghost">← Analytics</a>
        <a href="/analytics/archetypes/{data.label}/evolution" class="btn-evolution">Évolution ↗</a>
      </div>
    </header>

    <!-- Stats pills -->
    <div class="stats-row">
      <div class="stat-pill stat-pill--highlight">
        <span class="stat-num">{analytics.deck_count}</span>
        <span class="stat-lbl">Builds analyzed</span>
      </div>
      <div class="stat-pill">
        <span class="stat-num">{analytics.avg_main_count}</span>
        <span class="stat-lbl">Avg Main</span>
      </div>
      {#if analytics.avg_extra_count > 0}
        <div class="stat-pill">
          <span class="stat-num">{analytics.avg_extra_count}</span>
          <span class="stat-lbl">Avg Extra</span>
        </div>
      {/if}
      {#if analytics.avg_side_count > 0}
        <div class="stat-pill">
          <span class="stat-num">{analytics.avg_side_count}</span>
          <span class="stat-lbl">Avg Side</span>
        </div>
      {/if}
      <div class="stat-pill">
        <span class="stat-num">{analytics.core_cards.length}</span>
        <span class="stat-lbl">Core cards</span>
      </div>
      <div class="stat-pill">
        <span class="stat-num">{analytics.flex_cards.length}</span>
        <span class="stat-lbl">Flex cards</span>
      </div>
    </div>

    <!-- Charts -->
    <div class="charts-row">
      <!-- Frequency bar chart -->
      <div class="chart-card chart-card--freq">
        <h2 class="chart-title">Card Frequency — Top 15</h2>
        <div class="chart-legend">
          <span class="legend-dot" style="background:{C.gold}"></span><span>Core ≥75%</span>
          <span class="legend-dot" style="background:{C.blue}"></span><span>Flex 25–74%</span>
          <span class="legend-dot" style="background:{C.purple}"></span><span>Tech &lt;25%</span>
        </div>
        {#if analytics.core_cards.length + analytics.flex_cards.length + analytics.tech_cards.length === 0}
          <p class="chart-empty">No card data available.</p>
        {:else}
          <div bind:this={freqEl} style="height: 360px; width: 100%;"></div>
        {/if}
      </div>

      <!-- Timeline (only if ≥ 2 data points) -->
      {#if analytics.monthly_submissions.length >= 2}
        <div class="chart-card chart-card--time">
          <h2 class="chart-title">Decks Added Over Time</h2>
          <div bind:this={timeEl} style="height: 360px; width: 100%;"></div>
        </div>
      {/if}
    </div>

    <!-- Card section tabs -->
    <section class="cards-section">
      <div class="tabs-row">
        <button
          class="tab-btn"
          class:active={activeTab === 'core'}
          onclick={() => (activeTab = 'core')}
        >
          <span class="tab-dot" style="background:{C.gold}"></span>
          Core
          <span class="tab-count">{analytics.core_cards.length}</span>
        </button>
        <button
          class="tab-btn"
          class:active={activeTab === 'flex'}
          onclick={() => (activeTab = 'flex')}
        >
          <span class="tab-dot" style="background:{C.blue}"></span>
          Flex
          <span class="tab-count">{analytics.flex_cards.length}</span>
        </button>
        <button
          class="tab-btn"
          class:active={activeTab === 'tech'}
          onclick={() => (activeTab = 'tech')}
        >
          <span class="tab-dot" style="background:{C.purple}"></span>
          Tech
          <span class="tab-count">{analytics.tech_cards.length}</span>
        </button>
      </div>

      <!-- Tab description -->
      <p class="tab-desc">
        {#if activeTab === 'core'}
          Present in <strong>≥ 75%</strong> of builds — the non-negotiable cards that define the archetype.
        {:else if activeTab === 'flex'}
          Present in <strong>25–74%</strong> of builds — cards that vary between players and reflect meta choices.
        {:else}
          Present in <strong>&lt; 25%</strong> of builds — situational tech picks and one-of meta calls.
        {/if}
      </p>

      {#if activeCards.length === 0}
        <div class="tab-empty">
          <span aria-hidden="true">—</span>
          No {activeTab} cards found for this archetype.
        </div>
      {:else}
        <div class="card-table">
          <div class="card-table-header">
            <span>Card</span>
            <span class="th-freq">Frequency</span>
            <span class="th-avg">Avg copies</span>
          </div>
          {#each activeCards as card (card.card_id)}
            <div class="card-row">
              <!-- Thumbnail -->
              <div class="card-thumb-wrap" class:skeleton={!loadedImages.has(card.card_id)}>
                <img
                  src={card.image_url}
                  alt={card.name}
                  class="card-thumb"
                  loading="lazy"
                  onload={() => markImageLoaded(card.card_id)}
                  onerror={(e) => { (e.target as HTMLImageElement).src = '/media/placeholder-card.svg'; }}
                />
              </div>

              <!-- Name + type -->
              <div class="card-info">
                <span class="card-name">{card.name}</span>
                <span
                  class="card-type-tag"
                  style="color: {TYPE_COLOR[card.type_label] ?? TYPE_COLOR.Other}"
                >{card.type_label}</span>
              </div>

              <!-- Frequency bar -->
              <div class="freq-cell">
                <div class="freq-bar-bg">
                  <div
                    class="freq-bar-fill"
                    style="width: {barWidth(card.frequency)}; background: {tierColor(card.frequency)};"
                  ></div>
                </div>
                <span class="freq-label">{pct(card.frequency)}</span>
              </div>

              <!-- Avg copies -->
              <span class="avg-qty">×{card.avg_quantity.toFixed(2)}</span>
            </div>
          {/each}
        </div>
      {/if}
    </section>

    <!-- Decks listing -->
    <section class="decks-section">
      <h2 class="section-title">
        Decks
        <span class="section-count">{decks.length}</span>
      </h2>

      {#if decks.length === 0}
        <div class="decks-empty">
          <span aria-hidden="true">◎</span>
          No decks found for this archetype.
        </div>
      {:else}
        <div class="decks-table">
          <div class="decks-table-header">
            <span>Title</span>
            <span class="th-tags">Tags</span>
            <span class="th-size">Main</span>
            <span class="th-size">Extra</span>
            <span class="th-date">Date</span>
          </div>
          {#each decks as d (d.id)}
            <a href="/decks/{d.id}" class="deck-row">
              <span class="deck-row-title">{d.title}</span>
              <span class="deck-row-tags">
                {#each d.tags as tag}<span class="deck-tag">{tag}</span>{/each}
              </span>
              <span class="deck-row-size">{d.main_count}</span>
              <span class="deck-row-size">{d.extra_count}</span>
              <span class="deck-row-date">{formatDate(d.created_at)}</span>
            </a>
          {/each}
        </div>
      {/if}
    </section>

  {/if}
</div>

<style>
  .page-body {
    padding-top: 2rem;
    padding-bottom: 5rem;
  }

  .header-actions { display: flex; align-items: center; gap: 0.75rem; }

  /* Breadcrumb */
  .breadcrumb { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 2rem; font-size: 0.8125rem; }
  .bc-link { color: var(--text-tertiary); transition: color var(--duration-fast) var(--ease-out); }
  .bc-link:hover { color: var(--text-secondary); }
  .bc-sep { color: var(--text-tertiary); opacity: 0.4; }
  .bc-current { color: var(--text-secondary); }

  /* Header */
  .page-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1.5rem;
    flex-wrap: wrap;
    margin-bottom: 2rem;
    padding-bottom: 2rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    margin-top: 0.375rem;
  }

  /* Stats */
  .stats-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 2.5rem;
  }

  .stat-pill {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.15rem;
    padding: 0.875rem 1.375rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    min-width: 80px;
  }

  .stat-pill--highlight {
    border-color: rgba(201, 164, 73, 0.3);
    background: rgba(201, 164, 73, 0.04);
  }

  .stat-num {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--gold);
    line-height: 1;
  }

  .stat-lbl {
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    white-space: nowrap;
  }

  /* Charts row */
  .charts-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.25rem;
    margin-bottom: 3rem;
  }

  .chart-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 1.25rem 1.5rem 1rem;
  }

  /* Full-width if there's only the freq chart (no timeline) */
  .chart-card--freq:only-child {
    grid-column: 1 / -1;
  }

  .chart-title {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 0.625rem;
  }

  .chart-legend {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
    font-size: 0.75rem;
    color: var(--text-tertiary);
    flex-wrap: wrap;
  }

  .legend-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
    margin-right: 0.25rem;
  }

  .chart-empty {
    font-size: 0.875rem;
    color: var(--text-tertiary);
    padding: 3rem 0;
    text-align: center;
  }

  /* Card sections */
  .cards-section { margin-top: 1rem; }

  .tabs-row {
    display: flex;
    gap: 0.25rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--border-subtle);
    padding-bottom: 0;
  }

  .tab-btn {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.5rem 1rem 0.625rem;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-tertiary);
    transition: color var(--duration-fast) var(--ease-out),
                border-color var(--duration-fast) var(--ease-out);
    margin-bottom: -1px;
  }

  .tab-btn:hover { color: var(--text-secondary); }

  .tab-btn.active {
    color: var(--text-primary);
    border-bottom-color: var(--gold);
  }

  .tab-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .tab-count {
    font-size: 0.6875rem;
    font-weight: 700;
    padding: 0.1rem 0.4rem;
    background: var(--bg-elevated);
    border-radius: 99px;
    color: var(--text-tertiary);
    min-width: 1.5rem;
    text-align: center;
  }

  .tab-desc {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    margin-bottom: 1.25rem;
    line-height: 1.55;
  }

  .tab-desc strong { color: var(--text-secondary); }

  .tab-empty {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 2.5rem 1.25rem;
    font-size: 0.9rem;
    color: var(--text-tertiary);
    border: 1px dashed var(--border-subtle);
    border-radius: var(--radius-md);
  }

  /* Card table */
  .card-table {
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .card-table-header {
    display: grid;
    grid-template-columns: 44px 1fr 200px 80px;
    gap: 1rem;
    align-items: center;
    padding: 0.5rem 1.25rem 0.5rem 0.75rem;
    background: var(--bg-elevated);
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .th-freq { text-align: left; }
  .th-avg  { text-align: right; }

  .card-row {
    display: grid;
    grid-template-columns: 44px 1fr 200px 80px;
    gap: 1rem;
    align-items: center;
    padding: 0.5rem 1.25rem 0.5rem 0.75rem;
    border-top: 1px solid var(--border-subtle);
    transition: background var(--duration-fast) var(--ease-out);
  }

  .card-row:hover { background: var(--bg-surface); }

  .card-thumb-wrap {
    width: 32px;
    height: 44px;
    flex-shrink: 0;
    border-radius: 3px;
    overflow: hidden;
    background: var(--bg-elevated);
  }

  /* Shimmer while the card image is still loading (T2.8) */
  .card-thumb-wrap.skeleton {
    background: linear-gradient(
      90deg,
      var(--bg-elevated) 25%,
      var(--bg-overlay) 50%,
      var(--bg-elevated) 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
  }

  .card-thumb {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .card-info {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    min-width: 0;
  }

  .card-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .card-type-tag {
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.04em;
  }

  /* Frequency bar */
  .freq-cell {
    display: flex;
    align-items: center;
    gap: 0.625rem;
  }

  .freq-bar-bg {
    flex: 1;
    height: 6px;
    background: var(--bg-elevated);
    border-radius: 99px;
    overflow: hidden;
  }

  .freq-bar-fill {
    height: 100%;
    border-radius: 99px;
    transition: width 0.3s var(--ease-out);
  }

  .freq-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-secondary);
    width: 3.5rem;
    text-align: right;
    flex-shrink: 0;
  }

  .avg-qty {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    text-align: right;
  }

  /* Empty state */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 6rem 2rem;
    border: 1px dashed var(--border-default);
    border-radius: var(--radius-xl);
    background: var(--bg-surface);
    gap: 0.75rem;
  }

  .empty-icon { font-size: 2.5rem; color: var(--text-tertiary); line-height: 1; }
  .empty-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary);
  }
  .empty-sub { font-size: 0.9rem; color: var(--text-secondary); max-width: 38ch; line-height: 1.6; }

  /* Decks listing */
  .decks-section {
    margin-top: 3rem;
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    font-size: 0.8125rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 1.25rem;
  }

  .section-count {
    font-size: 0.6875rem;
    font-weight: 700;
    padding: 0.1rem 0.45rem;
    background: var(--bg-elevated);
    border-radius: 99px;
    color: var(--text-tertiary);
    text-transform: none;
    letter-spacing: 0;
  }

  .decks-empty {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 2.5rem 1.25rem;
    font-size: 0.9rem;
    color: var(--text-tertiary);
    border: 1px dashed var(--border-subtle);
    border-radius: var(--radius-md);
  }

  .decks-table {
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .decks-table-header {
    display: grid;
    grid-template-columns: 1fr auto 56px 56px 110px;
    gap: 1rem;
    align-items: center;
    padding: 0.5rem 1.25rem;
    background: var(--bg-elevated);
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .deck-row {
    display: grid;
    grid-template-columns: 1fr auto 56px 56px 110px;
    gap: 1rem;
    align-items: center;
    padding: 0.75rem 1.25rem;
    border-top: 1px solid var(--border-subtle);
    text-decoration: none;
    color: inherit;
    transition: background var(--duration-fast) var(--ease-out);
  }

  .deck-row:hover {
    background: var(--bg-surface);
  }

  .deck-row-title {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .deck-row:hover .deck-row-title {
    color: var(--gold);
  }

  .deck-row-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
  }

  .deck-tag {
    font-size: 0.625rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    padding: 0.1rem 0.4rem;
    background: var(--gold-dim);
    border: 1px solid rgba(201, 164, 73, 0.2);
    border-radius: 99px;
    color: var(--gold);
    white-space: nowrap;
  }

  .deck-row-size {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    text-align: center;
  }

  .deck-row-date {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    text-align: right;
    white-space: nowrap;
  }

  /* Responsive */
  @media (max-width: 860px) {
    .charts-row { grid-template-columns: 1fr; }
    .chart-card--freq:only-child { grid-column: 1; }
  }

  @media (max-width: 640px) {
    .card-table-header,
    .card-row { grid-template-columns: 32px 1fr 120px; }
    .th-avg, .avg-qty { display: none; }

    .card-table-header,
    .card-row { padding-left: 0.625rem; }

    .decks-table-header,
    .deck-row { grid-template-columns: 1fr 56px 110px; }
    .th-tags, .deck-row-tags { display: none; }
    .decks-table-header > span:nth-child(4),
    .deck-row > span:nth-child(4) { display: none; }
  }
</style>
