<script lang="ts">
  interface Overview {
    total_decks: number;
    total_cards_in_db: number;
    total_archetypes: number;
  }

  let { data }: { data: { overview: Overview | null } } = $props();

  const features = [
    {
      icon: '◈',
      title: 'Card Database',
      description:
        'Full catalog synced from YGOProDeck — 12,000+ cards with metadata. Images loaded on demand and cached locally.',
    },
    {
      icon: '⇪',
      title: '.ydk Import',
      description:
        'Paste or upload tournament decklists instantly. Main, Extra and Side decks parsed and matched automatically.',
    },
    {
      icon: '⊘',
      title: 'Banlist Tracking',
      description:
        'Every banlist version stored with history. Check any deck\'s legality at any point in time across all formats.',
    },
    {
      icon: '◎',
      title: 'Analytics Engine',
      description:
        'Frequency analysis, core card detection, flex spots identification and meta trends across tournament results.',
    },
  ];

  function fmt(n: number) { return n.toLocaleString('en-US'); }

  const stats = $derived([
    {
      value: data.overview ? fmt(data.overview.total_cards_in_db) : '—',
      label: 'Cards catalogued',
    },
    {
      value: data.overview ? fmt(data.overview.total_decks) : '—',
      label: 'Decks analyzed',
    },
    {
      value: data.overview ? fmt(data.overview.total_archetypes) : '—',
      label: 'Archetypes tracked',
    },
    { value: 'TCG · OCG', label: 'Formats covered' },
  ]);
</script>

<svelte:head>
  <title>YGO Intel — Deck Intelligence for Competitive Play</title>
</svelte:head>

<!-- ─── Hero ──────────────────────────────────────────────────────────── -->
<section class="hero">
  <div class="hero-grid-bg" aria-hidden="true"></div>
  <div class="hero-glow" aria-hidden="true"></div>

  <div class="hero-content page-container">
    <div class="hero-badge">
      <span class="hero-badge-dot"></span>
      Deck Intelligence Platform
    </div>

    <h1 class="hero-heading">
      Analyze your<br />
      <span class="hero-heading-accent">competitive edge</span>
    </h1>

    <p class="hero-sub">
      Transform raw decklists into strategic insight. Import, compare and optimize your
      Yu&#8209;Gi&#8209;Oh! strategy with precision analytics and real-time banlist awareness.
    </p>

    <div class="hero-cta">
      <a href="/import" class="btn-primary hero-cta-primary">
        Import .ydk file
        <span aria-hidden="true">→</span>
      </a>
      <a href="/decks" class="btn-ghost">Browse decks</a>
    </div>
  </div>

  <!-- Decorative card shapes -->
  <div class="hero-deco" aria-hidden="true">
    <div class="deco-card deco-card-1"></div>
    <div class="deco-card deco-card-2"></div>
    <div class="deco-card deco-card-3"></div>
  </div>
</section>

<!-- ─── Stats ─────────────────────────────────────────────────────────── -->
<section class="stats-section">
  <div class="page-container">
    <div class="stats-bar">
      {#each stats as stat, i}
        {#if i > 0}
          <div class="stats-divider"></div>
        {/if}
        <div class="stat">
          <span class="stat-value">{stat.value}</span>
          <span class="stat-label">{stat.label}</span>
        </div>
      {/each}
    </div>
  </div>
</section>

<!-- ─── Features ──────────────────────────────────────────────────────── -->
<section class="features-section">
  <div class="page-container">
    <div class="section-header">
      <span class="label">Platform capabilities</span>
      <h2 class="section-title">Everything for competitive deckbuilding</h2>
    </div>

    <div class="features-grid">
      {#each features as feat}
        <article class="feature-card">
          <div class="feature-icon" aria-hidden="true">{feat.icon}</div>
          <h3 class="feature-title">{feat.title}</h3>
          <p class="feature-desc">{feat.description}</p>
        </article>
      {/each}
    </div>
  </div>
</section>

<!-- ─── CTA Banner ────────────────────────────────────────────────────── -->
<section class="cta-banner-section">
  <div class="page-container">
    <div class="cta-banner">
      <div class="cta-banner-glow" aria-hidden="true"></div>
      <div class="cta-banner-content">
        <h2 class="cta-banner-title">Ready to analyze your first deck?</h2>
        <p class="cta-banner-sub">
          Start by syncing the card database, then import a .ydk file.
        </p>
      </div>
      <div class="cta-banner-actions">
        <a href="/admin" class="btn-ghost">Sync card database</a>
        <a href="/import" class="btn-primary">Import .ydk →</a>
      </div>
    </div>
  </div>
</section>

<style>
  /* ─── Hero ─────────────────────────────────────────────────────────── */
  .hero {
    position: relative;
    min-height: calc(100dvh - 60px);
    display: flex;
    align-items: center;
    overflow: hidden;
  }

  .hero-grid-bg {
    position: absolute;
    inset: 0;
    background-image: linear-gradient(var(--border-subtle) 1px, transparent 1px),
      linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px);
    background-size: 56px 56px;
    mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black 30%, transparent 100%);
  }

  .hero-glow {
    position: absolute;
    top: 20%;
    right: 10%;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(201, 164, 73, 0.06) 0%, transparent 70%);
    pointer-events: none;
  }

  .hero-content {
    position: relative;
    z-index: 1;
    padding-top: 5rem;
    padding-bottom: 5rem;
    max-width: 680px;
  }

  .hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 0.875rem;
    background: var(--gold-dim);
    border: 1px solid rgba(201, 164, 73, 0.25);
    border-radius: 99px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 2rem;
  }

  .hero-badge-dot {
    width: 6px;
    height: 6px;
    background: var(--gold);
    border-radius: 50%;
    animation: pulse 2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.4;
    }
  }

  .hero-heading {
    font-size: clamp(2.5rem, 5vw, 4rem);
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.08;
    margin-bottom: 1.5rem;
  }

  .hero-heading-accent {
    color: var(--gold);
  }

  .hero-sub {
    font-size: 1.0625rem;
    line-height: 1.7;
    color: var(--text-secondary);
    margin-bottom: 2.5rem;
    max-width: 540px;
  }

  .hero-cta {
    display: flex;
    align-items: center;
    gap: 0.875rem;
    flex-wrap: wrap;
  }

  .hero-cta-primary {
    font-size: 0.9375rem;
    padding: 0.75rem 1.5rem;
  }

  /* Decorative card shapes */
  .hero-deco {
    position: absolute;
    right: 6%;
    top: 50%;
    transform: translateY(-50%);
    width: 320px;
    height: 420px;
    pointer-events: none;
  }

  .deco-card {
    position: absolute;
    width: 160px;
    height: 230px;
    border-radius: 10px;
    border: 1px solid var(--border-default);
    background: linear-gradient(135deg, var(--bg-surface) 0%, var(--bg-elevated) 100%);
  }

  .deco-card-1 {
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate(-8deg);
    opacity: 0.5;
  }

  .deco-card-2 {
    top: 50%;
    left: 50%;
    transform: translate(-40%, -45%) rotate(4deg);
    opacity: 0.35;
    border-color: rgba(201, 164, 73, 0.15);
  }

  .deco-card-3 {
    top: 50%;
    left: 50%;
    transform: translate(-60%, -55%) rotate(-18deg);
    opacity: 0.2;
  }

  @media (max-width: 900px) {
    .hero-deco {
      display: none;
    }
    .hero-content {
      max-width: 100%;
    }
  }

  /* ─── Stats ─────────────────────────────────────────────────────────── */
  .stats-section {
    border-top: 1px solid var(--border-subtle);
    border-bottom: 1px solid var(--border-subtle);
    background: var(--bg-surface);
    padding: 2rem 0;
  }

  .stats-bar {
    display: flex;
    align-items: center;
    gap: 3rem;
    flex-wrap: wrap;
  }

  .stats-divider {
    width: 1px;
    height: 2.5rem;
    background: var(--border-subtle);
    flex-shrink: 0;
  }

  .stat {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .stat-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
  }

  .stat-label {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
  }

  /* ─── Features ──────────────────────────────────────────────────────── */
  .features-section {
    padding: 6rem 0;
  }

  .section-header {
    margin-bottom: 3rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .section-title {
    font-size: clamp(1.5rem, 3vw, 2rem);
    font-weight: 600;
  }

  .features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1rem;
  }

  .feature-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 1.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
    transition: border-color var(--duration-base) var(--ease-out),
      background var(--duration-base) var(--ease-out);
  }

  .feature-card:hover {
    border-color: var(--border-default);
    background: var(--bg-elevated);
  }

  .feature-icon {
    font-size: 1.25rem;
    color: var(--gold);
    line-height: 1;
  }

  .feature-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .feature-desc {
    font-size: 0.875rem;
    line-height: 1.65;
    color: var(--text-secondary);
  }

  /* ─── CTA Banner ────────────────────────────────────────────────────── */
  .cta-banner-section {
    padding: 0 0 6rem;
  }

  .cta-banner {
    position: relative;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    padding: 3rem;
    display: flex;
    align-items: center;
    gap: 2rem;
    flex-wrap: wrap;
    overflow: hidden;
  }

  .cta-banner-glow {
    position: absolute;
    top: -50%;
    left: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(201, 164, 73, 0.05) 0%, transparent 70%);
    pointer-events: none;
  }

  .cta-banner-content {
    flex: 1;
    min-width: 240px;
  }

  .cta-banner-title {
    font-size: 1.375rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  .cta-banner-sub {
    font-size: 0.9rem;
    color: var(--text-secondary);
  }

  .cta-banner-actions {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
    flex-wrap: wrap;
  }
</style>
