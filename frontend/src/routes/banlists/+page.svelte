<script lang="ts">
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

  let { data } = $props<{ data: { tcg: BanlistDetail | null; ocg: BanlistDetail | null } }>();

  let activeFormat: 'TCG' | 'OCG' = $state('TCG');

  let current = $derived(activeFormat === 'TCG' ? data.tcg : data.ocg);

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  }

  function handleImgError(e: Event) {
    const img = e.target as HTMLImageElement;
    img.src = '/media/placeholder-card.svg';
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

    <!-- Format selector — prominent, centered -->
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
          {#if fmtData}
            <span class="format-btn-counts">
              <span class="fmt-count fmt-forbidden">{fmtData.forbidden.length}</span>
              <span class="fmt-sep">/</span>
              <span class="fmt-count fmt-limited">{fmtData.limited.length}</span>
              <span class="fmt-sep">/</span>
              <span class="fmt-count fmt-semi">{fmtData.semi_limited.length}</span>
            </span>
            <span class="format-btn-legend">Forbidden / Limited / Semi</span>
          {:else}
            <span class="format-btn-empty">Not synced</span>
          {/if}
        </button>
      {/each}
    </div>
  </header>

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

    <!-- Forbidden -->
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
            <div class="card-item">
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

    <!-- Limited -->
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
            <div class="card-item">
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

    <!-- Semi-Limited -->
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
            <div class="card-item">
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
</div>

<style>
  .page-body {
    padding-top: 2rem;
    padding-bottom: 5rem;
  }

  .page-header {
    margin-bottom: 2.5rem;
    padding-bottom: 2rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .header-top {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
    margin-bottom: 1.75rem;
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

  /* Format selector — two large cards */
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

  .format-btn-empty {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    opacity: 0.6;
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
</style>
