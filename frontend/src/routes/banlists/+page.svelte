<script lang="ts">
  interface BanlistSummary {
    id: number;
    format: string;
    effective_date: string;
    version_label: string | null;
    forbidden_count: number;
    limited_count: number;
    semi_limited_count: number;
  }

  interface BanlistEntry {
    card_id: number;
    external_card_id: number;
    name: string;
    image_url: string;
    status: string;
    limit_value: number;
  }

  interface BanlistDetail {
    id: number;
    format: string;
    effective_date: string;
    version_label: string | null;
    forbidden: BanlistEntry[];
    limited: BanlistEntry[];
    semi_limited: BanlistEntry[];
  }

  interface BanlistDiffEntry {
    card_id: number;
    external_card_id: number;
    name: string;
    image_url: string;
    from_status: string | null;
    to_status: string | null;
  }

  interface BanlistDiffOut {
    from_banlist: BanlistSummary;
    to_banlist: BanlistSummary;
    hits: BanlistDiffEntry[];
    shifts: BanlistDiffEntry[];
    frees: BanlistDiffEntry[];
  }

  let { data } = $props<{
    data: {
      tcg: BanlistDetail | null;
      ocg: BanlistDetail | null;
      allBanlists: BanlistSummary[];
    };
  }>();

  let activeFormat: 'TCG' | 'OCG' = $state('TCG');
  let mode: 'current' | 'compare' | 'predict' = $state('current');

  // Current banlist view
  let current = $derived(activeFormat === 'TCG' ? data.tcg : data.ocg);

  // Compare mode
  let formatBanlists = $derived(data.allBanlists.filter((b: BanlistSummary) => b.format === activeFormat));

  let fromId = $state<number | null>(null);
  let toId = $state<number | null>(null);
  let diffResult = $state<BanlistDiffOut | null>(null);
  let diffLoading = $state(false);
  let diffError = $state<string | null>(null);

  // Reset selectors when format or mode changes
  $effect(() => {
    const list = formatBanlists;
    fromId = list.length >= 2 ? list[1].id : list.length === 1 ? list[0].id : null;
    toId = list.length >= 1 ? list[0].id : null;
    diffResult = null;
    diffError = null;
  });

  async function runDiff() {
    if (fromId === null || toId === null || fromId === toId) return;
    diffLoading = true;
    diffError = null;
    diffResult = null;
    try {
      const res = await fetch(`/api/v1/banlists/diff?from_id=${fromId}&to_id=${toId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      diffResult = await res.json();
    } catch (e) {
      diffError = e instanceof Error ? e.message : 'Unknown error';
    } finally {
      diffLoading = false;
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }

  function statusLabel(s: string | null): string {
    if (!s) return 'Unlimited';
    if (s === 'forbidden') return 'Forbidden';
    if (s === 'limited') return 'Limited';
    if (s === 'semi_limited') return 'Semi-Limited';
    return s;
  }

  function handleImgError(e: Event) {
    const img = e.target as HTMLImageElement;
    img.src = '/media/placeholder-card.svg';
  }

  let totalDiff = $derived(
    diffResult ? diffResult.hits.length + diffResult.shifts.length + diffResult.frees.length : 0
  );

  // ── Card history panel ────────────────────────────────────────────────────
  interface BanlistCardHistoryEntry {
    banlist_id: number;
    format: string;
    effective_date: string;
    version_label: string | null;
    status: string;
  }

  interface SelectedCard {
    card_id: number;
    name: string;
    image_url: string;
  }

  let selectedCard = $state<SelectedCard | null>(null);
  let historyFormat: 'TCG' | 'OCG' = $state('TCG');
  let cardHistory = $state<BanlistCardHistoryEntry[] | null>(null);
  let historyLoading = $state(false);
  let historyError = $state<string | null>(null);

  let tcgHistory = $derived(cardHistory?.filter((h) => h.format === 'TCG') ?? []);
  let ocgHistory = $derived(cardHistory?.filter((h) => h.format === 'OCG') ?? []);
  let displayedHistory = $derived(historyFormat === 'TCG' ? tcgHistory : ocgHistory);

  async function openCardHistory(card: SelectedCard) {
    selectedCard = card;
    historyFormat = activeFormat;
    cardHistory = null;
    historyError = null;
    historyLoading = true;
    try {
      const res = await fetch(`/api/v1/banlists/cards/${card.card_id}/history`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      cardHistory = await res.json();
    } catch (e) {
      historyError = e instanceof Error ? e.message : 'Unknown error';
    } finally {
      historyLoading = false;
    }
  }

  function closeCardHistory() {
    selectedCard = null;
    cardHistory = null;
    historyError = null;
  }
</script>

<svelte:head>
  <title>Banlists — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <!-- Header -->
  <header class="page-header">
    <div class="header-top">
      <span class="page-eyebrow">CARD LEGALITY</span>
      <h1 class="page-title">Banlists</h1>
      <p class="page-sub">Forbidden &amp; limited card lists — choose your format below</p>
    </div>

    <!-- Mode toggle -->
    <div class="mode-toggle" role="tablist" aria-label="View mode">
      <button
        role="tab"
        class="mode-btn"
        class:active={mode === 'current'}
        onclick={() => (mode = 'current')}
        aria-selected={mode === 'current'}
      >
        Current List
      </button>
      <button
        role="tab"
        class="mode-btn"
        class:active={mode === 'compare'}
        onclick={() => (mode = 'compare')}
        aria-selected={mode === 'compare'}
      >
        Compare ↔
      </button>
      <button
        role="tab"
        class="mode-btn"
        class:active={mode === 'predict'}
        onclick={() => (mode = 'predict')}
        aria-selected={mode === 'predict'}
      >
        Predict ⚠
      </button>
    </div>

    <!-- Format selector -->
    <div class="format-selector" role="tablist" aria-label="Select format">
      {#each (['TCG', 'OCG'] as const) as fmt}
        {@const fmtData = fmt === 'TCG' ? data.tcg : data.ocg}
        <button
          role="tab"
          class="format-btn"
          class:active={activeFormat === fmt}
          onclick={() => (activeFormat = fmt)}
          aria-selected={activeFormat === fmt}
        >
          <span class="format-btn-label">{fmt}</span>
          {#if fmtData && mode === 'current'}
            <span class="format-btn-counts">
              <span class="fmt-count fmt-forbidden">{fmtData.forbidden.length}</span>
              <span class="fmt-sep">/</span>
              <span class="fmt-count fmt-limited">{fmtData.limited.length}</span>
              <span class="fmt-sep">/</span>
              <span class="fmt-count fmt-semi">{fmtData.semi_limited.length}</span>
            </span>
            <span class="format-btn-legend">Forbidden / Limited / Semi</span>
          {:else}
            {@const n = data.allBanlists.filter((b: BanlistSummary) => b.format === fmt).length}
            <span class="format-btn-legend">{n} banlist{n !== 1 ? 's' : ''} available</span>
          {/if}
        </button>
      {/each}
    </div>
  </header>

  <!-- ───────────────── CURRENT MODE ───────────────── -->
  {#if mode === 'current'}
    {#if !current}
      <div class="empty-state">
        <div class="empty-icon" aria-hidden="true">⊘</div>
        <p class="empty-title">No {activeFormat} banlist synced yet</p>
        <p class="empty-sub">Trigger a banlist sync from the admin panel to populate this page.</p>
        <a href="/admin" class="btn-primary empty-cta">Go to sync panel</a>
      </div>
    {:else}
      <div class="banlist-meta">
        <span class="meta-date">Last updated {formatDate(current.effective_date)}</span>
      </div>

      {#if current.forbidden.length > 0}
        <section class="ban-section">
          <header class="section-header">
            <span class="section-dot dot-forbidden" aria-hidden="true"></span>
            <h2 class="section-title">Forbidden</h2>
            <span class="section-count">{current.forbidden.length} cards</span>
            <span class="section-rule">— Cannot be used (0 copies)</span>
          </header>
          <div class="card-grid">
            {#each current.forbidden as entry (entry.card_id)}
              <div class="card-item card-item--clickable"
                role="button" tabindex="0"
                onclick={() => openCardHistory(entry)}
                onkeydown={(e) => e.key === 'Enter' && openCardHistory(entry)}
                aria-label="View {entry.name} banlist history">
                <div class="card-img-wrap">
                  <img src={entry.image_url} alt={entry.name} class="card-img" loading="lazy" onerror={handleImgError} />
                  <span class="status-strip strip-forbidden" aria-hidden="true"></span>
                </div>
                <p class="card-name">{entry.name}</p>
              </div>
            {/each}
          </div>
        </section>
      {/if}

      {#if current.limited.length > 0}
        <section class="ban-section">
          <header class="section-header">
            <span class="section-dot dot-limited" aria-hidden="true"></span>
            <h2 class="section-title">Limited</h2>
            <span class="section-count">{current.limited.length} cards</span>
            <span class="section-rule">— Maximum 1 copy</span>
          </header>
          <div class="card-grid">
            {#each current.limited as entry (entry.card_id)}
              <div class="card-item card-item--clickable"
                role="button" tabindex="0"
                onclick={() => openCardHistory(entry)}
                onkeydown={(e) => e.key === 'Enter' && openCardHistory(entry)}
                aria-label="View {entry.name} banlist history">
                <div class="card-img-wrap">
                  <img src={entry.image_url} alt={entry.name} class="card-img" loading="lazy" onerror={handleImgError} />
                  <span class="status-strip strip-limited" aria-hidden="true"></span>
                </div>
                <p class="card-name">{entry.name}</p>
              </div>
            {/each}
          </div>
        </section>
      {/if}

      {#if current.semi_limited.length > 0}
        <section class="ban-section">
          <header class="section-header">
            <span class="section-dot dot-semi" aria-hidden="true"></span>
            <h2 class="section-title">Semi-Limited</h2>
            <span class="section-count">{current.semi_limited.length} cards</span>
            <span class="section-rule">— Maximum 2 copies</span>
          </header>
          <div class="card-grid">
            {#each current.semi_limited as entry (entry.card_id)}
              <div class="card-item card-item--clickable"
                role="button" tabindex="0"
                onclick={() => openCardHistory(entry)}
                onkeydown={(e) => e.key === 'Enter' && openCardHistory(entry)}
                aria-label="View {entry.name} banlist history">
                <div class="card-img-wrap">
                  <img src={entry.image_url} alt={entry.name} class="card-img" loading="lazy" onerror={handleImgError} />
                  <span class="status-strip strip-semi" aria-hidden="true"></span>
                </div>
                <p class="card-name">{entry.name}</p>
              </div>
            {/each}
          </div>
        </section>
      {/if}
    {/if}
  {/if}

  <!-- ───────────────── COMPARE MODE ───────────────── -->
  {#if mode === 'compare'}
    {#if formatBanlists.length < 2}
      <div class="empty-state">
        <div class="empty-icon" aria-hidden="true">⊘</div>
        <p class="empty-title">Not enough {activeFormat} banlists</p>
        <p class="empty-sub">At least two banlists must be synced to compare.</p>
      </div>
    {:else}
      <div class="compare-controls">
        <div class="compare-selectors">
          <div class="compare-field">
            <label class="compare-label" for="from-select">From</label>
            <select id="from-select" class="compare-select" bind:value={fromId}>
              {#each formatBanlists as bl (bl.id)}
                <option value={bl.id}>
                  {bl.version_label ?? formatDate(bl.effective_date)}
                </option>
              {/each}
            </select>
          </div>

          <span class="compare-arrow" aria-hidden="true">→</span>

          <div class="compare-field">
            <label class="compare-label" for="to-select">To</label>
            <select id="to-select" class="compare-select" bind:value={toId}>
              {#each formatBanlists as bl (bl.id)}
                <option value={bl.id}>
                  {bl.version_label ?? formatDate(bl.effective_date)}
                </option>
              {/each}
            </select>
          </div>
        </div>

        <button
          class="btn-primary compare-run"
          onclick={runDiff}
          disabled={diffLoading || fromId === null || toId === null || fromId === toId}
        >
          {diffLoading ? 'Loading…' : 'Compare'}
        </button>
      </div>

      {#if fromId === toId && fromId !== null}
        <p class="compare-same-warn">Select two different banlists to compare.</p>
      {/if}

      {#if diffError}
        <div class="diff-error">Failed to load diff: {diffError}</div>
      {/if}

      {#if diffResult}
        {#if totalDiff === 0}
          <div class="diff-empty">
            <p class="diff-empty-title">No changes between these two banlists.</p>
            <p class="diff-empty-sub">Every card kept the same restriction status.</p>
          </div>
        {:else}
          <div class="diff-header">
            <span class="diff-label">
              {diffResult.from_banlist.version_label ?? formatDate(diffResult.from_banlist.effective_date)}
            </span>
            <span class="diff-arrow" aria-hidden="true">→</span>
            <span class="diff-label">
              {diffResult.to_banlist.version_label ?? formatDate(diffResult.to_banlist.effective_date)}
            </span>
            <span class="diff-total">{totalDiff} change{totalDiff !== 1 ? 's' : ''}</span>
          </div>

          <!-- Hits: newly restricted or worsened -->
          {#if diffResult.hits.length > 0}
            <section class="diff-section diff-section--hit">
              <header class="diff-sec-header">
                <span class="diff-sec-icon" aria-hidden="true">↓</span>
                <h3 class="diff-sec-title">Newly Restricted</h3>
                <span class="diff-sec-count">{diffResult.hits.length}</span>
              </header>
              <ul class="diff-list">
                {#each diffResult.hits as entry (entry.card_id)}
                  <li class="diff-entry diff-entry--clickable"
                    role="button" tabindex="0"
                    onclick={() => openCardHistory(entry)}
                    onkeydown={(e) => e.key === 'Enter' && openCardHistory(entry)}>
                    <div class="diff-img-wrap">
                      <img
                        src={entry.image_url}
                        alt={entry.name}
                        class="diff-img"
                        loading="lazy"
                        onerror={handleImgError}
                      />
                      <span class="diff-strip diff-strip--hit" aria-hidden="true"></span>
                    </div>
                    <div class="diff-info">
                      <p class="diff-name">{entry.name}</p>
                      <p class="diff-change">
                        <span class="diff-from">{statusLabel(entry.from_status)}</span>
                        <span class="diff-ch-arrow" aria-hidden="true">→</span>
                        <span class="diff-to diff-to--hit">{statusLabel(entry.to_status)}</span>
                      </p>
                    </div>
                  </li>
                {/each}
              </ul>
            </section>
          {/if}

          <!-- Shifts: still restricted but eased -->
          {#if diffResult.shifts.length > 0}
            <section class="diff-section diff-section--shift">
              <header class="diff-sec-header">
                <span class="diff-sec-icon" aria-hidden="true">↑</span>
                <h3 class="diff-sec-title">Eased</h3>
                <span class="diff-sec-count">{diffResult.shifts.length}</span>
              </header>
              <ul class="diff-list">
                {#each diffResult.shifts as entry (entry.card_id)}
                  <li class="diff-entry diff-entry--clickable"
                    role="button" tabindex="0"
                    onclick={() => openCardHistory(entry)}
                    onkeydown={(e) => e.key === 'Enter' && openCardHistory(entry)}>
                    <div class="diff-img-wrap">
                      <img
                        src={entry.image_url}
                        alt={entry.name}
                        class="diff-img"
                        loading="lazy"
                        onerror={handleImgError}
                      />
                      <span class="diff-strip diff-strip--shift" aria-hidden="true"></span>
                    </div>
                    <div class="diff-info">
                      <p class="diff-name">{entry.name}</p>
                      <p class="diff-change">
                        <span class="diff-from">{statusLabel(entry.from_status)}</span>
                        <span class="diff-ch-arrow" aria-hidden="true">→</span>
                        <span class="diff-to diff-to--shift">{statusLabel(entry.to_status)}</span>
                      </p>
                    </div>
                  </li>
                {/each}
              </ul>
            </section>
          {/if}

          <!-- Frees: fully removed from banlist -->
          {#if diffResult.frees.length > 0}
            <section class="diff-section diff-section--free">
              <header class="diff-sec-header">
                <span class="diff-sec-icon" aria-hidden="true">✓</span>
                <h3 class="diff-sec-title">Released</h3>
                <span class="diff-sec-count">{diffResult.frees.length}</span>
              </header>
              <ul class="diff-list">
                {#each diffResult.frees as entry (entry.card_id)}
                  <li class="diff-entry diff-entry--clickable"
                    role="button" tabindex="0"
                    onclick={() => openCardHistory(entry)}
                    onkeydown={(e) => e.key === 'Enter' && openCardHistory(entry)}>
                    <div class="diff-img-wrap">
                      <img
                        src={entry.image_url}
                        alt={entry.name}
                        class="diff-img"
                        loading="lazy"
                        onerror={handleImgError}
                      />
                      <span class="diff-strip diff-strip--free" aria-hidden="true"></span>
                    </div>
                    <div class="diff-info">
                      <p class="diff-name">{entry.name}</p>
                      <p class="diff-change">
                        <span class="diff-from">{statusLabel(entry.from_status)}</span>
                        <span class="diff-ch-arrow" aria-hidden="true">→</span>
                        <span class="diff-to diff-to--free">Unlimited</span>
                      </p>
                    </div>
                  </li>
                {/each}
              </ul>
            </section>
          {/if}
        {/if}
      {/if}
    {/if}
  {/if}

  <!-- ───────────────── PREDICT MODE ───────────────── -->
  {#if mode === 'predict'}
    {@const prediction = activeFormat === 'TCG' ? data.predictionTCG : data.predictionOCG}
    <div class="predict-disclaimer">
      <span class="predict-disclaimer-icon" aria-hidden="true">⚠</span>
      <p>{prediction?.disclaimer ?? 'Heuristic estimate only — not an official prediction.'}</p>
    </div>

    {#if !prediction || !prediction.has_data}
      <div class="empty-state">
        <div class="empty-icon" aria-hidden="true">⚠</div>
        <p class="empty-title">Not enough data to estimate {activeFormat} banlist risk</p>
        <p class="empty-sub">Import more decks to unlock this heuristic — it needs cards that are actually being played.</p>
      </div>
    {:else}
      <div class="banlist-meta">
        <span class="meta-date">
          Based on {prediction.total_decks_analyzed} deck{prediction.total_decks_analyzed !== 1 ? 's' : ''} in the database
        </span>
      </div>
      <div class="card-grid">
        {#each prediction.candidates as entry (entry.card_id)}
          <div
            class="card-item card-item--clickable"
            role="button" tabindex="0"
            onclick={() => openCardHistory({ card_id: entry.card_id, name: entry.name, image_url: entry.image_url })}
            onkeydown={(e) => e.key === 'Enter' && openCardHistory({ card_id: entry.card_id, name: entry.name, image_url: entry.image_url })}
            aria-label="View {entry.name} banlist history"
          >
            <div class="card-img-wrap">
              <img src={entry.image_url} alt={entry.name} class="card-img" loading="lazy" onerror={handleImgError} />
              <span class="risk-badge risk-badge--{entry.risk_label.toLowerCase().replace(' ', '-')}">{entry.risk_label}</span>
            </div>
            <p class="card-name">{entry.name}</p>
            <p class="risk-meta">
              {(entry.play_rate * 100).toFixed(0)}% play rate
              {#if entry.prior_hits > 0} · {entry.prior_hits} prior hit{entry.prior_hits > 1 ? 's' : ''}{/if}
              {#if entry.is_recent} · new{/if}
            </p>
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<!-- ── Card history panel ─────────────────────────────────────────────────── -->
{#if selectedCard}
  <!-- Overlay -->
  <div
    class="history-overlay"
    role="presentation"
    onclick={closeCardHistory}
    onkeydown={(e) => e.key === 'Escape' && closeCardHistory()}
  ></div>

  <!-- Panel -->
  <aside class="history-panel" aria-label="Banlist history">
    <!-- Header -->
    <div class="history-header">
      <div class="history-card-info">
        <div class="history-card-img-wrap">
          <img
            src={selectedCard.image_url}
            alt={selectedCard.name}
            class="history-card-img"
            onerror={handleImgError}
          />
        </div>
        <div class="history-card-meta">
          <p class="history-card-name">{selectedCard.name}</p>
          <p class="history-card-sub">Restriction history</p>
        </div>
      </div>
      <button class="history-close" onclick={closeCardHistory} aria-label="Close">×</button>
    </div>

    <!-- Format tabs -->
    <div class="history-tabs" role="tablist">
      {#each (['TCG', 'OCG'] as const) as fmt}
        {@const count = fmt === 'TCG' ? tcgHistory.length : ocgHistory.length}
        <button
          role="tab"
          class="history-tab"
          class:active={historyFormat === fmt}
          onclick={() => (historyFormat = fmt)}
          aria-selected={historyFormat === fmt}
        >
          {fmt}
          <span class="history-tab-count">{count}</span>
        </button>
      {/each}
    </div>

    <!-- Body -->
    <div class="history-body">
      {#if historyLoading}
        <div class="history-loading">
          <span class="history-spinner" aria-hidden="true"></span>
          <span>Loading…</span>
        </div>
      {:else if historyError}
        <p class="history-error">Failed to load: {historyError}</p>
      {:else if displayedHistory.length === 0}
        <div class="history-empty">
          <p class="history-empty-title">Never restricted in {historyFormat}</p>
          <p class="history-empty-sub">This card has always been Unlimited in {historyFormat}.</p>
        </div>
      {:else}
        <ul class="history-timeline" aria-label="{historyFormat} restriction history">
          {#each displayedHistory as entry, i (entry.banlist_id)}
            {@const isLast = i === displayedHistory.length - 1}
            <li class="history-entry">
              <div class="timeline-connector">
                <span class="timeline-dot timeline-dot--{entry.status}" aria-hidden="true"></span>
                {#if !isLast}<span class="timeline-line" aria-hidden="true"></span>{/if}
              </div>
              <div class="timeline-content">
                <span class="timeline-status timeline-status--{entry.status}">
                  {statusLabel(entry.status)}
                </span>
                <span class="timeline-date">
                  {entry.version_label ?? formatDate(entry.effective_date)}
                </span>
              </div>
            </li>
          {/each}
          <!-- Implied current status if last entry differs from "not on list" -->
          <li class="history-entry history-entry--implied">
            <div class="timeline-connector">
              <span class="timeline-dot timeline-dot--unlimited" aria-hidden="true"></span>
            </div>
            <div class="timeline-content">
              <span class="timeline-status timeline-status--unlimited">Before that</span>
              <span class="timeline-date timeline-date--dim">Unlimited</span>
            </div>
          </li>
        </ul>
      {/if}
    </div>
  </aside>
{/if}

<style>
  .page-body {
    padding-top: 2rem;
    padding-bottom: 5rem;
  }

  .page-header {
    margin-bottom: 2.5rem;
    padding-bottom: 2rem;
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .header-top {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .page-eyebrow {
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: var(--gold);
    opacity: 0.7;
    text-transform: uppercase;
  }

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.025em;
    line-height: 1.1;
  }

  .page-sub {
    font-size: 0.9rem;
    color: var(--text-tertiary);
  }

  /* Mode toggle */
  .mode-toggle {
    display: flex;
    gap: 0.375rem;
    width: fit-content;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 0.25rem;
  }

  .mode-btn {
    padding: 0.375rem 0.875rem;
    border-radius: calc(var(--radius-md) - 2px);
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-tertiary);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
  }

  .mode-btn:hover {
    color: var(--text-primary);
  }

  .mode-btn.active {
    background: var(--bg-elevated);
    color: var(--text-primary);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  }

  /* Format selector */
  .format-selector {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    max-width: 560px;
  }

  .format-btn {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.375rem;
    padding: 1rem 1.25rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    cursor: pointer;
    text-align: left;
    transition: border-color var(--duration-fast) var(--ease-out),
      background var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .format-btn:hover {
    border-color: var(--border-strong);
    background: var(--bg-elevated);
  }

  .format-btn.active {
    border-color: var(--gold);
    background: var(--bg-elevated);
    box-shadow: 0 0 0 1px rgba(201, 164, 73, 0.15), inset 0 1px 0 rgba(201, 164, 73, 0.06);
  }

  .format-btn-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.25rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--text-secondary);
    transition: color var(--duration-fast) var(--ease-out);
  }

  .format-btn.active .format-btn-label {
    color: var(--gold);
  }

  .format-btn-counts {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .fmt-forbidden { color: #f87171; }
  .fmt-limited   { color: #fb923c; }
  .fmt-semi      { color: #facc15; }
  .fmt-sep       { color: var(--text-tertiary); opacity: 0.5; font-weight: 400; }

  .format-btn-legend {
    font-size: 0.6875rem;
    color: var(--text-tertiary);
    opacity: 0.7;
  }

  /* Meta */
  .banlist-meta {
    margin-bottom: 2.5rem;
  }

  .meta-date {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
  }

  /* Sections */
  .ban-section {
    margin-bottom: 3rem;
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    margin-bottom: 1rem;
  }

  .section-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .dot-forbidden { background: #ef4444; }
  .dot-limited   { background: #f97316; }
  .dot-semi      { background: #eab308; }

  .section-title {
    font-size: 0.875rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-secondary);
  }

  .section-count {
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  .section-rule {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    opacity: 0.7;
  }

  /* Card grid */
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
    gap: 0.625rem;
  }

  @media (min-width: 640px) {
    .card-grid { grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); }
  }

  @media (min-width: 1024px) {
    .card-grid { grid-template-columns: repeat(auto-fill, minmax(106px, 1fr)); }
  }

  .card-item {
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
    transition: border-color var(--duration-fast) var(--ease-out),
      transform var(--duration-fast) var(--ease-out);
  }

  .card-item:hover .card-img-wrap {
    transform: translateY(-3px) scale(1.02);
    z-index: 1;
  }

  .card-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .status-strip {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 4px;
    pointer-events: none;
  }

  .strip-forbidden { background: rgba(239, 68, 68, 0.9); }
  .strip-limited   { background: rgba(249, 115, 22, 0.9); }
  .strip-semi      { background: rgba(234, 179, 8, 0.9); }

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

  /* ─── Predict mode ─── */
  .predict-disclaimer {
    display: flex;
    align-items: flex-start;
    gap: 0.625rem;
    padding: 0.875rem 1.125rem;
    margin-bottom: 1.5rem;
    background: rgba(234, 179, 8, 0.08);
    border: 1px solid rgba(234, 179, 8, 0.25);
    border-radius: var(--radius-md);
  }

  .predict-disclaimer-icon {
    font-size: 1rem;
    color: #eab308;
    flex-shrink: 0;
    line-height: 1.4;
  }

  .predict-disclaimer p {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    line-height: 1.55;
    margin: 0;
  }

  .risk-badge {
    position: absolute;
    top: 4px;
    left: 4px;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.5625rem;
    font-weight: 800;
    letter-spacing: 0.03em;
    line-height: 1.5;
    pointer-events: none;
  }

  .risk-badge--very-high { background: rgba(239, 68, 68, 0.92); color: #fff; }
  .risk-badge--high      { background: rgba(249, 115, 22, 0.92); color: #fff; }
  .risk-badge--moderate  { background: rgba(234, 179, 8, 0.92); color: #1a1a1a; }
  .risk-badge--low       { background: rgba(148, 163, 184, 0.92); color: #1a1a1a; }

  .risk-meta {
    font-size: 0.625rem;
    color: var(--text-tertiary);
    line-height: 1.3;
    text-align: center;
  }

  /* ─── Compare mode ─── */
  .compare-controls {
    display: flex;
    align-items: flex-end;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 2rem;
    padding: 1.25rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
  }

  .compare-selectors {
    display: flex;
    align-items: flex-end;
    gap: 0.75rem;
    flex-wrap: wrap;
    flex: 1;
  }

  .compare-field {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
    min-width: 180px;
    flex: 1;
  }

  .compare-label {
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .compare-select {
    padding: 0.5rem 0.75rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 0.875rem;
    cursor: pointer;
    width: 100%;
  }

  .compare-select:focus {
    outline: none;
    border-color: var(--gold);
    box-shadow: 0 0 0 2px rgba(201, 164, 73, 0.15);
  }

  .compare-arrow {
    font-size: 1.25rem;
    color: var(--text-tertiary);
    padding-bottom: 0.375rem;
    flex-shrink: 0;
  }

  .compare-run {
    flex-shrink: 0;
    align-self: flex-end;
  }

  .compare-same-warn {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    margin-bottom: 1rem;
  }

  /* Diff results */
  .diff-header {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    margin-bottom: 2rem;
    font-size: 0.875rem;
  }

  .diff-label {
    font-weight: 600;
    color: var(--text-primary);
  }

  .diff-arrow {
    color: var(--text-tertiary);
  }

  .diff-total {
    margin-left: auto;
    font-size: 0.75rem;
    color: var(--text-tertiary);
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 99px;
    padding: 0.125rem 0.625rem;
  }

  .diff-section {
    margin-bottom: 2.5rem;
  }

  .diff-sec-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.875rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .diff-sec-icon {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.6875rem;
    font-weight: 700;
    flex-shrink: 0;
  }

  .diff-section--hit .diff-sec-icon {
    background: rgba(239, 68, 68, 0.15);
    color: #f87171;
  }

  .diff-section--shift .diff-sec-icon {
    background: rgba(234, 179, 8, 0.15);
    color: #facc15;
  }

  .diff-section--free .diff-sec-icon {
    background: rgba(34, 197, 94, 0.15);
    color: #4ade80;
  }

  .diff-sec-title {
    font-size: 0.8125rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-secondary);
  }

  .diff-sec-count {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 99px;
    padding: 0.125rem 0.5rem;
  }

  .diff-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 0.5rem;
    list-style: none;
    padding: 0;
    margin: 0;
  }

  @media (min-width: 640px) {
    .diff-list { grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }
  }

  .diff-entry {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.625rem 0.75rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    transition: background var(--duration-fast) var(--ease-out);
  }

  .diff-entry:hover {
    background: var(--bg-elevated);
  }

  .diff-img-wrap {
    position: relative;
    width: 40px;
    flex-shrink: 0;
    aspect-ratio: 421 / 614;
    border-radius: 3px;
    overflow: hidden;
    background: var(--bg-elevated);
  }

  .diff-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .diff-strip {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 3px;
    pointer-events: none;
  }

  .diff-strip--hit   { background: rgba(239, 68, 68, 0.9); }
  .diff-strip--shift { background: rgba(234, 179, 8, 0.9); }
  .diff-strip--free  { background: rgba(34, 197, 94, 0.9); }

  .diff-info {
    min-width: 0;
    flex: 1;
  }

  .diff-name {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-primary);
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    margin-bottom: 0.25rem;
  }

  .diff-change {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.6875rem;
  }

  .diff-from {
    color: var(--text-tertiary);
  }

  .diff-ch-arrow {
    color: var(--text-tertiary);
    opacity: 0.5;
  }

  .diff-to--hit   { color: #f87171; font-weight: 600; }
  .diff-to--shift { color: #facc15; font-weight: 600; }
  .diff-to--free  { color: #4ade80; font-weight: 600; }

  /* Diff empty */
  .diff-empty {
    padding: 3rem 2rem;
    text-align: center;
    border: 1px dashed var(--border-default);
    border-radius: var(--radius-xl);
  }

  .diff-empty-title {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 0.375rem;
  }

  .diff-empty-sub {
    font-size: 0.875rem;
    color: var(--text-tertiary);
  }

  .diff-error {
    padding: 1rem;
    border-radius: var(--radius-sm);
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.25);
    color: #f87171;
    font-size: 0.875rem;
    margin-bottom: 1rem;
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
    max-width: 38ch;
    line-height: 1.6;
  }

  .empty-cta {
    margin-top: 1.75rem;
  }

  /* ── Clickable card/diff items ───────────────────────────────────────────── */
  .card-item--clickable {
    cursor: pointer;
  }

  .card-item--clickable:hover .card-img-wrap {
    transform: translateY(-3px) scale(1.02);
    border-color: var(--border-strong);
    box-shadow: 0 0 0 1px rgba(201, 164, 73, 0.25);
  }

  .card-item--clickable:focus-visible {
    outline: 2px solid var(--gold);
    outline-offset: 2px;
    border-radius: var(--radius-sm);
  }

  .diff-entry--clickable {
    cursor: pointer;
  }

  .diff-entry--clickable:hover {
    border-color: rgba(201, 164, 73, 0.3);
  }

  /* ── History panel ───────────────────────────────────────────────────────── */
  .history-overlay {
    position: fixed;
    inset: 0;
    z-index: 200;
    background: rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(2px);
  }

  .history-panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: 320px;
    z-index: 201;
    background: var(--bg-elevated);
    border-left: 1px solid var(--border-strong);
    display: flex;
    flex-direction: column;
    box-shadow: -8px 0 32px rgba(0, 0, 0, 0.4);
    animation: panel-in 0.2s var(--ease-out);
  }

  @keyframes panel-in {
    from { transform: translateX(100%); opacity: 0; }
    to   { transform: translateX(0);   opacity: 1; }
  }

  @media (max-width: 600px) {
    .history-panel {
      width: 100%;
      top: auto;
      height: 72vh;
      border-left: none;
      border-top: 1px solid var(--border-strong);
      border-radius: var(--radius-xl) var(--radius-xl) 0 0;
      animation: panel-up 0.2s var(--ease-out);
    }

    @keyframes panel-up {
      from { transform: translateY(100%); }
      to   { transform: translateY(0); }
    }
  }

  .history-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 1rem 1rem 0.75rem;
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .history-card-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    min-width: 0;
  }

  .history-card-img-wrap {
    width: 48px;
    aspect-ratio: 421 / 614;
    border-radius: var(--radius-sm);
    overflow: hidden;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .history-card-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .history-card-meta {
    min-width: 0;
  }

  .history-card-name {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.3;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .history-card-sub {
    font-size: 0.6875rem;
    color: var(--text-tertiary);
    margin-top: 0.125rem;
  }

  .history-close {
    width: 28px;
    height: 28px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-tertiary);
    font-size: 1.125rem;
    cursor: pointer;
    border-radius: 4px;
    padding: 0;
    line-height: 1;
    transition: color var(--duration-fast) var(--ease-out),
      background var(--duration-fast) var(--ease-out);
  }

  .history-close:hover {
    color: var(--text-primary);
    background: var(--bg-overlay);
  }

  /* Format tabs */
  .history-tabs {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .history-tab {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
    padding: 0.625rem 0.5rem;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--text-tertiary);
    cursor: pointer;
    transition: color var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out);
    margin-bottom: -1px;
  }

  .history-tab:hover {
    color: var(--text-secondary);
  }

  .history-tab.active {
    color: var(--gold);
    border-bottom-color: var(--gold);
  }

  .history-tab-count {
    font-size: 0.625rem;
    background: var(--bg-overlay);
    border-radius: 99px;
    padding: 0.0625rem 0.375rem;
    font-weight: 700;
  }

  /* Body */
  .history-body {
    flex: 1;
    overflow-y: auto;
    padding: 1.25rem 1rem;
  }

  .history-loading {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 2rem 0;
    color: var(--text-tertiary);
    font-size: 0.875rem;
  }

  .history-spinner {
    display: inline-block;
    width: 18px;
    height: 18px;
    border: 2px solid var(--border-default);
    border-top-color: var(--gold);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    flex-shrink: 0;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .history-error {
    font-size: 0.875rem;
    color: #f87171;
    padding: 1rem 0;
  }

  .history-empty {
    padding: 2rem 0;
    text-align: center;
  }

  .history-empty-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 0.375rem;
  }

  .history-empty-sub {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    line-height: 1.5;
  }

  /* Timeline */
  .history-timeline {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .history-entry {
    display: flex;
    gap: 0.875rem;
    min-height: 48px;
  }

  .timeline-connector {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
    padding-top: 3px;
  }

  .timeline-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .timeline-dot--forbidden    { background: #ef4444; box-shadow: 0 0 6px rgba(239,68,68,0.4); }
  .timeline-dot--limited      { background: #f97316; box-shadow: 0 0 6px rgba(249,115,22,0.4); }
  .timeline-dot--semi_limited { background: #eab308; box-shadow: 0 0 6px rgba(234,179,8,0.35); }
  .timeline-dot--unlimited    { background: var(--border-default); }

  .timeline-line {
    flex: 1;
    width: 1px;
    background: var(--border-subtle);
    margin: 3px 0;
    min-height: 20px;
  }

  .timeline-content {
    flex: 1;
    padding-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.1875rem;
  }

  .timeline-status {
    font-size: 0.8125rem;
    font-weight: 600;
    line-height: 1.2;
  }

  .timeline-status--forbidden    { color: #f87171; }
  .timeline-status--limited      { color: #fb923c; }
  .timeline-status--semi_limited { color: #facc15; }
  .timeline-status--unlimited    { color: var(--text-tertiary); font-weight: 400; }

  .timeline-date {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .timeline-date--dim {
    color: var(--text-tertiary);
    font-style: italic;
  }

  .history-entry--implied .timeline-content {
    padding-bottom: 0;
  }
</style>
