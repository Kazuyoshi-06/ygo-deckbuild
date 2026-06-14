<script lang="ts">
  import { onMount } from 'svelte';

  interface DistEntry {
    label: string;
    count: number;
  }

  interface LevelEntry {
    level: number;
    count: number;
  }

  interface DeckAnalytics {
    deck_id: number;
    title: string;
    total_cards: number;
    distinct_cards: number;
    type_distribution: DistEntry[];
    attribute_distribution: DistEntry[];
    level_distribution: LevelEntry[];
    frame_distribution: DistEntry[];
  }

  interface DeckBasic {
    id: number;
    title: string;
    main_count: number;
    extra_count: number;
    side_count: number;
  }

  let { data } = $props<{ data: { analytics: DeckAnalytics | null; deck: DeckBasic | null } }>();
  let analytics = $derived(data.analytics);
  let deck = $derived(data.deck);

  // ECharts colour tokens matching design system
  const C = {
    gold: '#c9a449',
    blue: '#4e8cd4',
    rose: '#d44e6e',
    purple: '#9b7fe0',
    teal: '#00b894',
    text: '#8892a4',
    grid: '#232630',
    bg: '#131620',
  };

  const ATTR_COLORS: Record<string, string> = {
    DARK: '#9b59b6',
    LIGHT: '#e8c84a',
    FIRE: '#e74c3c',
    EARTH: '#a07850',
    WATER: '#3498db',
    WIND: '#2ecc71',
    DIVINE: '#f39c12',
  };

  let typeEl: HTMLDivElement = $state(null as unknown as HTMLDivElement);
  let attrEl: HTMLDivElement = $state(null as unknown as HTMLDivElement);
  let levelEl: HTMLDivElement = $state(null as unknown as HTMLDivElement);
  let frameEl: HTMLDivElement = $state(null as unknown as HTMLDivElement);

  function axisCommon() {
    return {
      axisLabel: { color: C.text, fontFamily: 'Inter, sans-serif', fontSize: 12 },
      axisLine: { lineStyle: { color: C.grid } },
      splitLine: { lineStyle: { color: C.grid } },
    };
  }

  function buildTypeOption(dist: DistEntry[]) {
    const colorMap: Record<string, string> = {
      Monster: C.gold,
      Spell: C.blue,
      Trap: C.rose,
      Other: C.purple,
    };
    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
        backgroundColor: '#1a1d2e',
        borderColor: C.grid,
        textStyle: { color: '#dce3ef' },
      },
      legend: {
        bottom: 0,
        textStyle: { color: C.text, fontSize: 12 },
        icon: 'circle',
        itemWidth: 10,
        itemHeight: 10,
      },
      series: [
        {
          type: 'pie',
          radius: ['42%', '70%'],
          center: ['50%', '44%'],
          data: dist.map((d) => ({
            value: d.count,
            name: d.label,
            itemStyle: { color: colorMap[d.label] ?? C.purple },
          })),
          label: { show: false },
          emphasis: {
            label: { show: true, fontSize: 13, fontWeight: 'bold', color: '#dce3ef' },
            itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' },
          },
        },
      ],
    };
  }

  function buildAttrOption(dist: DistEntry[]) {
    const labels = dist.map((d) => d.label);
    const counts = dist.map((d) => d.count);
    const colors = labels.map((l) => ATTR_COLORS[l] ?? C.teal);

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1a1d2e',
        borderColor: C.grid,
        textStyle: { color: '#dce3ef' },
      },
      grid: { left: 60, right: 20, top: 10, bottom: 20, containLabel: false },
      xAxis: { type: 'value', ...axisCommon() },
      yAxis: { type: 'category', data: labels, ...axisCommon() },
      series: [
        {
          type: 'bar',
          data: counts.map((v, i) => ({ value: v, itemStyle: { color: colors[i], borderRadius: [0, 4, 4, 0] } })),
          barMaxWidth: 22,
        },
      ],
    };
  }

  function buildLevelOption(dist: LevelEntry[]) {
    const levels = dist.map((d) => String(d.level));
    const counts = dist.map((d) => d.count);

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1a1d2e',
        borderColor: C.grid,
        textStyle: { color: '#dce3ef' },
      },
      grid: { left: 30, right: 20, top: 10, bottom: 30, containLabel: true },
      xAxis: {
        type: 'category',
        data: levels,
        name: 'Level / Rank / Link',
        nameLocation: 'end',
        nameTextStyle: { color: C.text, fontSize: 11 },
        ...axisCommon(),
      },
      yAxis: { type: 'value', ...axisCommon() },
      series: [
        {
          type: 'bar',
          data: counts,
          barMaxWidth: 30,
          itemStyle: { color: C.purple, borderRadius: [4, 4, 0, 0] },
        },
      ],
    };
  }

  function buildFrameOption(dist: DistEntry[]) {
    const labels = dist.map((d) => d.label);
    const counts = dist.map((d) => d.count);

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1a1d2e',
        borderColor: C.grid,
        textStyle: { color: '#dce3ef' },
      },
      grid: { left: 20, right: 20, top: 10, bottom: 20, containLabel: true },
      xAxis: { type: 'value', ...axisCommon() },
      yAxis: { type: 'category', data: labels, ...axisCommon() },
      series: [
        {
          type: 'bar',
          data: counts.map((v) => ({
            value: v,
            itemStyle: { color: C.teal, borderRadius: [0, 4, 4, 0] },
          })),
          barMaxWidth: 22,
        },
      ],
    };
  }

  onMount(() => {
    if (!analytics) return;

    const snap = analytics;
    let charts: ReturnType<typeof import('echarts')['init']>[] = [];
    let ro: ResizeObserver | null = null;

    import('echarts').then((echarts) => {
      const els = [typeEl, attrEl, levelEl, frameEl];
      charts = els.map((el) => echarts.init(el, null, { renderer: 'canvas' }));

      charts[0].setOption(buildTypeOption(snap.type_distribution));
      charts[1].setOption(buildAttrOption(snap.attribute_distribution));
      charts[2].setOption(buildLevelOption(snap.level_distribution));
      charts[3].setOption(buildFrameOption(snap.frame_distribution));

      ro = new ResizeObserver(() => charts.forEach((c) => c.resize()));
      els.forEach((el) => ro!.observe(el));
    });

    return () => {
      ro?.disconnect();
      charts.forEach((c) => c.dispose());
    };
  });
</script>

<svelte:head>
  <title>{analytics?.title ?? 'Analytics'} · Analytics — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <!-- Breadcrumb -->
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="/decks" class="breadcrumb-link">Decks</a>
    <span class="breadcrumb-sep" aria-hidden="true">/</span>
    {#if deck}
      <a href="/decks/{deck.id}" class="breadcrumb-link">{deck.title}</a>
      <span class="breadcrumb-sep" aria-hidden="true">/</span>
    {/if}
    <span class="breadcrumb-current">Analytics</span>
  </nav>

  {#if !analytics}
    <div class="empty-state">
      <p class="empty-text">Deck not found or analytics unavailable.</p>
      <a href="/decks" class="btn-back">← Back to decks</a>
    </div>
  {:else}
    <!-- Header -->
    <header class="page-header">
      <div>
        <p class="analytics-eyebrow">Analytics</p>
        <h1 class="page-title">{analytics.title}</h1>
      </div>
      {#if deck}
        <a href="/decks/{deck.id}" class="btn-back-header">← View deck</a>
      {/if}
    </header>

    <!-- Stats row -->
    <div class="stats-row">
      <div class="stat-pill">
        <span class="stat-num">{analytics.total_cards}</span>
        <span class="stat-lbl">Total cards</span>
      </div>
      <div class="stat-pill">
        <span class="stat-num">{analytics.distinct_cards}</span>
        <span class="stat-lbl">Distinct cards</span>
      </div>
      {#if deck}
        <div class="stat-pill">
          <span class="stat-num">{deck.main_count}</span>
          <span class="stat-lbl">Main deck</span>
        </div>
        <div class="stat-pill">
          <span class="stat-num">{deck.extra_count}</span>
          <span class="stat-lbl">Extra deck</span>
        </div>
        <div class="stat-pill">
          <span class="stat-num">{deck.side_count}</span>
          <span class="stat-lbl">Side deck</span>
        </div>
      {/if}
    </div>

    <!-- Charts -->
    <div class="charts-grid">
      <!-- Type distribution -->
      <div class="chart-card">
        <h2 class="chart-title">Type Distribution</h2>
        <div bind:this={typeEl} class="chart-area" style="height: 260px;"></div>
      </div>

      <!-- Attribute distribution -->
      <div class="chart-card">
        <h2 class="chart-title">Attribute Distribution</h2>
        {#if analytics.attribute_distribution.length === 0}
          <p class="chart-empty">No monster cards in this deck.</p>
        {:else}
          <div bind:this={attrEl} class="chart-area" style="height: 260px;"></div>
        {/if}
      </div>

      <!-- Level / Rank / Link -->
      <div class="chart-card">
        <h2 class="chart-title">Level / Rank / Link</h2>
        {#if analytics.level_distribution.length === 0}
          <p class="chart-empty">No monster cards with a level/rank.</p>
        {:else}
          <div bind:this={levelEl} class="chart-area" style="height: 260px;"></div>
        {/if}
      </div>

      <!-- Frame types -->
      <div class="chart-card">
        <h2 class="chart-title">Card Frames</h2>
        <div bind:this={frameEl} class="chart-area" style="height: 260px;"></div>
      </div>
    </div>
  {/if}
</div>

<style>
  .page-body {
    padding-top: 2rem;
    padding-bottom: 5rem;
  }

  /* Breadcrumb */
  .breadcrumb {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 2rem;
    font-size: 0.8125rem;
  }
  .breadcrumb-link {
    color: var(--text-tertiary);
    transition: color var(--duration-fast) var(--ease-out);
  }
  .breadcrumb-link:hover { color: var(--text-secondary); }
  .breadcrumb-sep { color: var(--text-tertiary); opacity: 0.5; }
  .breadcrumb-current { color: var(--text-secondary); }

  /* Header */
  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 2rem;
    padding-bottom: 2rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .analytics-eyebrow {
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--gold);
    opacity: 0.8;
    margin-bottom: 0.375rem;
  }

  .page-title {
    font-size: 1.75rem;
    font-weight: 700;
    letter-spacing: -0.025em;
    line-height: 1.2;
  }

  .btn-back-header {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--text-secondary);
    transition: color var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out);
  }
  .btn-back-header:hover {
    color: var(--text-primary);
    border-color: var(--gold);
  }

  /* Stats row */
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
    min-width: 88px;
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

  /* Charts grid */
  .charts-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.25rem;
  }

  @media (max-width: 720px) {
    .charts-grid {
      grid-template-columns: 1fr;
    }
  }

  .chart-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 1.25rem 1.5rem 1rem;
  }

  .chart-title {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 1rem;
  }

  .chart-area {
    width: 100%;
  }

  .chart-empty {
    font-size: 0.875rem;
    color: var(--text-tertiary);
    padding: 2rem 0;
    text-align: center;
  }

  /* Empty state */
  .empty-state {
    padding: 5rem 0;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.25rem;
  }

  .empty-text {
    font-size: 1rem;
    color: var(--text-tertiary);
  }

  .btn-back {
    font-size: 0.875rem;
    color: var(--gold);
    opacity: 0.75;
    transition: opacity var(--duration-fast) var(--ease-out);
  }
  .btn-back:hover { opacity: 1; }
</style>
