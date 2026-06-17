<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount, untrack } from 'svelte';

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

  interface ArchetypeCompareSummary {
    label: string;
    deck_count: number;
    meta_share: number;
    avg_main_count: number;
    avg_extra_count: number;
    avg_side_count: number;
    top_cards: CardFrequency[];
  }

  interface CommonCardEntry {
    card_id: number;
    name: string;
    image_url: string;
    type_label: string;
    frame_type: string;
    frequencies: Record<string, number>;
  }

  interface EvolutionSeries {
    archetype_label: string;
    months: string[];
    deck_counts: number[];
    total_decks: number;
    has_data: boolean;
  }

  interface ArchetypeCompareOut {
    archetypes: ArchetypeCompareSummary[];
    common_cards: CommonCardEntry[];
    exclusive_cards: Record<string, CardFrequency[]>;
    evolution: Record<string, EvolutionSeries>;
  }

  let { data } = $props<{
    data: {
      compare: ArchetypeCompareOut | null;
      error: string | null;
      labels: string[];
      topArchetypes: string[];
    };
  }>();

  const compare = $derived(data.compare as ArchetypeCompareOut | null);

  // ECharts color palette (matches design system / archetype detail page)
  const PALETTE = ['#C9A449', '#4E8CD4', '#9B7FE0', '#00B894'];
  const TYPE_COLOR: Record<string, string> = {
    Monster: 'var(--gold)',
    Spell: '#4e8cd4',
    Trap: '#d44e6e',
    Other: '#9b7fe0',
  };

  function colorFor(label: string): string {
    const idx = compare ? compare.archetypes.findIndex((a) => a.label === label) : -1;
    return PALETTE[idx >= 0 ? idx % PALETTE.length : 0];
  }

  function pct(v: number): string {
    return `${(v * 100).toFixed(1)}%`;
  }

  function handleImgError(e: Event) {
    (e.target as HTMLImageElement).src = '/media/placeholder-card.svg';
  }

  // ── Archetype picker ─────────────────────────────────────────────────────
  let pickerInputs: string[] = $state(
    untrack(() => (data.labels.length >= 2 ? [...data.labels] : ['', '']))
  );

  function addPickerInput() {
    if (pickerInputs.length < 4) pickerInputs.push('');
  }

  function removePickerInput(i: number) {
    if (pickerInputs.length > 2) pickerInputs.splice(i, 1);
  }

  function submitPicker() {
    const labels = [...new Set(pickerInputs.map((s) => s.trim()).filter(Boolean))];
    if (labels.length < 2) return;
    goto(`/analytics/compare?archetypes=${encodeURIComponent(labels.join(','))}`);
  }

  // ── Evolution chart ──────────────────────────────────────────────────────
  let evoEl: HTMLDivElement = $state(null as unknown as HTMLDivElement);

  function buildEvolutionOption(ev: Record<string, EvolutionSeries>) {
    const labels = Object.keys(ev);
    const allMonths = [...new Set(labels.flatMap((l) => ev[l].months))].sort();

    return {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', backgroundColor: '#1a1d2e', borderColor: '#232630', textStyle: { color: '#dce3ef', fontSize: 12 } },
      legend: { data: labels, textStyle: { color: '#8892A4', fontSize: 11 }, top: 0 },
      grid: { left: 10, right: 20, top: 36, bottom: 8, containLabel: true },
      xAxis: {
        type: 'category',
        data: allMonths,
        axisLabel: { color: '#8892A4', fontSize: 11 },
        axisLine: { lineStyle: { color: '#232630' } },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        axisLabel: { color: '#8892A4', fontSize: 11 },
        axisLine: { lineStyle: { color: '#232630' } },
        splitLine: { lineStyle: { color: '#232630' } },
      },
      series: labels.map((label) => {
        const series = ev[label];
        const monthMap = new Map(series.months.map((m, i) => [m, series.deck_counts[i]]));
        return {
          name: label,
          type: 'line',
          data: allMonths.map((m) => monthMap.get(m) ?? 0),
          smooth: 0.4,
          symbol: 'circle',
          symbolSize: 6,
          itemStyle: { color: colorFor(label) },
          lineStyle: { color: colorFor(label), width: 2 },
        };
      }),
    };
  }

  onMount(() => {
    if (!compare) return;
    const hasData = Object.values(compare.evolution).some((e) => e.has_data);
    if (!hasData) return;

    let chart: ReturnType<typeof import('echarts')['init']> | null = null;
    let ro: ResizeObserver | null = null;

    import('echarts').then((echarts) => {
      if (!evoEl) return;
      chart = echarts.init(evoEl, null, { renderer: 'canvas' });
      chart.setOption(buildEvolutionOption(compare.evolution));
      ro = new ResizeObserver(() => chart?.resize());
      ro.observe(evoEl);
    });

    return () => {
      ro?.disconnect();
      chart?.dispose();
    };
  });
</script>

<svelte:head>
  <title>Compare Archetypes — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="/analytics" class="bc-link">Analytics</a>
    <span class="bc-sep" aria-hidden="true">/</span>
    <span class="bc-current">Compare</span>
  </nav>

  <header class="page-header">
    <div>
      <span class="label">Archetype Comparison</span>
      <h1 class="page-title">
        {#if compare}
          {compare.archetypes.map((a) => a.label).join(' vs ')}
        {:else}
          Compare Archetypes
        {/if}
      </h1>
    </div>
  </header>

  <!-- Picker -->
  <section class="picker">
    <div class="picker-inputs">
      {#each pickerInputs as _, i}
        <div class="picker-input-wrap">
          <input
            class="picker-input"
            type="text"
            placeholder="Archetype {i + 1}…"
            bind:value={pickerInputs[i]}
            list="archetype-suggestions"
            style="border-left: 3px solid {PALETTE[i % PALETTE.length]};"
          />
          {#if pickerInputs.length > 2}
            <button type="button" class="picker-remove" onclick={() => removePickerInput(i)} aria-label="Remove">×</button>
          {/if}
        </div>
      {/each}
      <datalist id="archetype-suggestions">
        {#each data.topArchetypes as label (label)}
          <option value={label}></option>
        {/each}
      </datalist>
    </div>
    <div class="picker-actions">
      {#if pickerInputs.length < 4}
        <button type="button" class="btn-ghost" onclick={addPickerInput}>+ Add archetype</button>
      {/if}
      <button type="button" class="btn-primary" onclick={submitPicker}>Compare →</button>
    </div>
  </section>

  {#if data.error}
    <div class="empty-state">
      <div class="empty-icon" aria-hidden="true">◎</div>
      <p class="empty-title">Could not compare these archetypes</p>
      <p class="empty-sub">{data.error}</p>
    </div>
  {:else if !compare}
    <div class="empty-state">
      <div class="empty-icon" aria-hidden="true">⇄</div>
      <p class="empty-title">Pick 2–4 archetypes to compare</p>
      <p class="empty-sub">Meta share, common/exclusive cards, and side-by-side evolution.</p>
    </div>
  {:else}
    <!-- Summary cards -->
    <div class="summary-grid" style="grid-template-columns: repeat({compare.archetypes.length}, 1fr);">
      {#each compare.archetypes as arch, i (arch.label)}
        <div class="summary-card" style="border-top-color: {PALETTE[i % PALETTE.length]};">
          <h2 class="summary-label">{arch.label}</h2>
          <div class="summary-stats">
            <div class="summary-stat">
              <span class="summary-num">{pct(arch.meta_share)}</span>
              <span class="summary-sub">Meta share</span>
            </div>
            <div class="summary-stat">
              <span class="summary-num">{arch.deck_count}</span>
              <span class="summary-sub">Decks</span>
            </div>
            <div class="summary-stat">
              <span class="summary-num">{arch.avg_main_count}</span>
              <span class="summary-sub">Avg Main</span>
            </div>
            <div class="summary-stat">
              <span class="summary-num">{arch.avg_extra_count}</span>
              <span class="summary-sub">Avg Extra</span>
            </div>
          </div>
        </div>
      {/each}
    </div>

    <!-- Evolution chart -->
    {#if Object.values(compare.evolution).some((e) => e.has_data)}
      <section class="chart-card">
        <h2 class="chart-title">Decks Added Over Time</h2>
        <div bind:this={evoEl} style="height: 320px; width: 100%;"></div>
      </section>
    {/if}

    <!-- Common cards -->
    <section class="cards-section">
      <h2 class="section-title">
        Common Cards
        <span class="section-count">{compare.common_cards.length}</span>
      </h2>
      <p class="section-desc">Core/flex cards (frequency ≥ 25%) shared by every compared archetype.</p>

      {#if compare.common_cards.length === 0}
        <div class="tab-empty">
          <span aria-hidden="true">—</span>
          No cards in common between these archetypes.
        </div>
      {:else}
        <div class="card-table">
          <div
            class="card-table-header"
            style="grid-template-columns: 44px 1fr repeat({compare.archetypes.length}, 100px);"
          >
            <span></span>
            <span>Card</span>
            {#each compare.archetypes as arch (arch.label)}
              <span class="th-freq">{arch.label}</span>
            {/each}
          </div>
          {#each compare.common_cards as card (card.card_id)}
            <div
              class="card-row"
              style="grid-template-columns: 44px 1fr repeat({compare.archetypes.length}, 100px);"
            >
              <div class="card-thumb-wrap">
                <img src={card.image_url} alt={card.name} class="card-thumb" loading="lazy" onerror={handleImgError} />
              </div>
              <div class="card-info">
                <span class="card-name">{card.name}</span>
                <span class="card-type-tag" style="color: {TYPE_COLOR[card.type_label] ?? TYPE_COLOR.Other}">{card.type_label}</span>
              </div>
              {#each compare.archetypes as arch (arch.label)}
                <span class="freq-label" style="color: {PALETTE[compare.archetypes.findIndex((a) => a.label === arch.label) % PALETTE.length]};">
                  {pct(card.frequencies[arch.label] ?? 0)}
                </span>
              {/each}
            </div>
          {/each}
        </div>
      {/if}
    </section>

    <!-- Exclusive cards -->
    <section class="cards-section">
      <h2 class="section-title">Exclusive Cards</h2>
      <p class="section-desc">Core/flex cards unique to one archetype — not played at all (even as tech) in the others.</p>

      <div class="exclusive-grid" style="grid-template-columns: repeat({compare.archetypes.length}, 1fr);">
        {#each compare.archetypes as arch, i (arch.label)}
          {@const exclusive = compare.exclusive_cards[arch.label] ?? []}
          <div class="exclusive-col">
            <h3 class="exclusive-col-title" style="color: {PALETTE[i % PALETTE.length]};">{arch.label}</h3>
            {#if exclusive.length === 0}
              <p class="tab-empty tab-empty--compact">No exclusive cards.</p>
            {:else}
              <ul class="exclusive-list">
                {#each exclusive as card (card.card_id)}
                  <li class="exclusive-item">
                    <img src={card.image_url} alt={card.name} class="card-thumb" loading="lazy" onerror={handleImgError} />
                    <div class="card-info">
                      <span class="card-name">{card.name}</span>
                      <span class="freq-label freq-label--inline">{pct(card.frequency)}</span>
                    </div>
                  </li>
                {/each}
              </ul>
            {/if}
          </div>
        {/each}
      </div>
    </section>
  {/if}
</div>

<style>
  .page-body {
    padding-top: 2rem;
    padding-bottom: 5rem;
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
    margin-bottom: 1.5rem;
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

  /* Picker */
  .picker {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    padding: 1.25rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    margin-bottom: 2.5rem;
  }

  .picker-inputs {
    display: flex;
    gap: 0.625rem;
    flex-wrap: wrap;
  }

  .picker-input-wrap {
    position: relative;
  }

  .picker-input {
    padding: 0.5rem 1.75rem 0.5rem 0.75rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.875rem;
    width: 180px;
    outline: none;
  }

  .picker-input:focus {
    border-color: var(--gold);
  }

  .picker-remove {
    position: absolute;
    right: 0.4rem;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    color: var(--text-tertiary);
    font-size: 1rem;
    cursor: pointer;
    line-height: 1;
  }

  .picker-remove:hover {
    color: var(--text-primary);
  }

  .picker-actions {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  /* Summary cards */
  .summary-grid {
    display: grid;
    gap: 1rem;
    margin-bottom: 2.5rem;
  }

  .summary-card {
    padding: 1.25rem 1.5rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-top: 3px solid;
    border-radius: var(--radius-md);
  }

  .summary-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.0625rem;
    font-weight: 700;
    margin-bottom: 1rem;
  }

  .summary-stats {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.875rem;
  }

  .summary-stat {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .summary-num {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .summary-sub {
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  /* Chart */
  .chart-card {
    padding: 1.5rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    margin-bottom: 2.5rem;
  }

  .chart-title {
    font-size: 0.9375rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }

  /* Sections */
  .cards-section {
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
  }

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

  .tab-empty--compact {
    padding: 1.25rem;
    font-size: 0.8125rem;
  }

  /* Card table (common cards) */
  .card-table {
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .card-table-header {
    display: grid;
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

  .th-freq {
    text-align: right;
  }

  .card-row {
    display: grid;
    gap: 1rem;
    align-items: center;
    padding: 0.5rem 1.25rem 0.5rem 0.75rem;
    border-top: 1px solid var(--border-subtle);
    transition: background var(--duration-fast) var(--ease-out);
  }

  .card-row:hover {
    background: var(--bg-elevated);
  }

  .card-thumb-wrap {
    width: 32px;
    height: 44px;
    flex-shrink: 0;
    border-radius: 3px;
    overflow: hidden;
    background: var(--bg-elevated);
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

  .freq-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8125rem;
    font-weight: 600;
    text-align: right;
  }

  .freq-label--inline {
    color: var(--text-tertiary);
    font-weight: 400;
    text-align: left;
  }

  /* Exclusive cards */
  .exclusive-grid {
    display: grid;
    gap: 1.25rem;
  }

  .exclusive-col-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.9375rem;
    font-weight: 700;
    margin-bottom: 0.75rem;
  }

  .exclusive-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .exclusive-item {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    padding: 0.4rem 0.625rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
  }

  /* Empty state */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 5rem 2rem;
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
    max-width: 40ch;
    line-height: 1.6;
  }

  @media (max-width: 720px) {
    .summary-grid,
    .exclusive-grid {
      grid-template-columns: 1fr !important;
    }
  }
</style>
