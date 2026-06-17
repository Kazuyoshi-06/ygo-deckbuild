<script lang="ts">
  import { untrack } from 'svelte';
  interface ArchetypeAverages {
    sample_size: number;
    avg_main: number;
    avg_monster: number;
    avg_spell: number;
    avg_trap: number;
    avg_extra: number;
    avg_side: number;
  }

  interface AdviceItem {
    category: string;
    label: string;
    your_value: number;
    archetype_avg: number | null;
    archetype_sample: number;
    ref_ideal_min: number;
    ref_ideal_max: number;
    status: string;
    tip: string | null;
  }

  interface RatioAdviceData {
    deck_id: number;
    deck_title: string;
    archetype_label: string | null;
    main_count: number;
    monster_count: number;
    spell_count: number;
    trap_count: number;
    extra_count: number;
    side_count: number;
    role_counts: Record<string, number> | null;
    archetype_averages: ArchetypeAverages | null;
    advice: AdviceItem[];
  }

  let { data } = $props<{ data: { deckId: number; advice: RatioAdviceData } }>();
  const d = untrack(() => data.advice);

  // Split advice into type-ratios and role-ratios groups
  const TYPE_CATS = new Set(['main_count', 'monster', 'spell', 'trap', 'extra', 'side']);
  const typeItems = $derived(d.advice.filter((a: AdviceItem) => TYPE_CATS.has(a.category)));
  const roleItems = $derived(d.advice.filter((a: AdviceItem) => !TYPE_CATS.has(a.category)));

  function statusColor(s: string): string {
    if (s === 'critical') return '#ef4444';
    if (s === 'warning')  return '#f59e0b';
    return '#22c55e';
  }

  function statusIcon(s: string): string {
    if (s === 'critical') return '✕';
    if (s === 'warning')  return '⚠';
    return '✓';
  }

  // Bar width: normalise your_value to ref range with some margin
  function barPct(item: AdviceItem): number {
    const scale = item.ref_ideal_max * 1.4 || 60;
    return Math.min(100, (item.your_value / scale) * 100);
  }

  function avgBarPct(item: AdviceItem): number {
    if (item.archetype_avg === null) return 0;
    const scale = item.ref_ideal_max * 1.4 || 60;
    return Math.min(100, (item.archetype_avg / scale) * 100);
  }

  function idealRangePct(item: AdviceItem): { left: number; width: number } {
    const scale = item.ref_ideal_max * 1.4 || 60;
    const left = (item.ref_ideal_min / scale) * 100;
    const right = Math.min(100, (item.ref_ideal_max / scale) * 100);
    return { left, width: right - left };
  }

  // Global summary
  interface Summary { criticals: number; warnings: number; oks: number; verdict: string; color: string }
  let summary = $derived<Summary>((() => {
    const criticals = d.advice.filter((a: AdviceItem) => a.status === 'critical').length;
    const warnings  = d.advice.filter((a: AdviceItem) => a.status === 'warning').length;
    const oks       = d.advice.filter((a: AdviceItem) => a.status === 'ok').length;
    let verdict: string;
    let color: string;
    if (criticals > 0) {
      verdict = `${criticals} critical issue${criticals > 1 ? 's' : ''} detected. Fix ${criticals > 1 ? 'these' : 'this'} before taking the deck to a tournament.`;
      color = '#ef4444';
    } else if (warnings > 0) {
      verdict = `${warnings} metric${warnings > 1 ? 's are' : ' is'} slightly off. Your deck is playable but has room to improve.`;
      color = '#f59e0b';
    } else {
      verdict = `All ${oks} metrics are within competitive targets. Your ratios look solid.`;
      color = '#22c55e';
    }
    return { criticals, warnings, oks, verdict, color };
  })());
</script>

<svelte:head>
  <title>Ratio Advisor — {d.deck_title} — YGO Intel</title>
</svelte:head>

<div class="page">
  <div class="topbar">
    <a href="/decks/{d.deck_id}" class="back">← Deck</a>
    <h1>{d.deck_title}</h1>
    {#if d.archetype_label}
      <span class="archetype-badge">{d.archetype_label}</span>
    {/if}
  </div>

  <!-- ── Context bar ──────────────────────────────────────────── -->
  <div class="context-bar">
    <div class="ctx-item">
      <span class="ctx-label">Main</span>
      <span class="ctx-val">{d.main_count}</span>
    </div>
    <div class="ctx-item">
      <span class="ctx-label">Monsters</span>
      <span class="ctx-val">{d.monster_count}</span>
    </div>
    <div class="ctx-item">
      <span class="ctx-label">Spells</span>
      <span class="ctx-val">{d.spell_count}</span>
    </div>
    <div class="ctx-item">
      <span class="ctx-label">Traps</span>
      <span class="ctx-val">{d.trap_count}</span>
    </div>
    <div class="ctx-item">
      <span class="ctx-label">Extra</span>
      <span class="ctx-val">{d.extra_count}</span>
    </div>
    <div class="ctx-item">
      <span class="ctx-label">Side</span>
      <span class="ctx-val">{d.side_count}</span>
    </div>
    {#if d.archetype_averages}
      <div class="ctx-divider"></div>
      <div class="ctx-item ctx-arch">
        <span class="ctx-label">Archétype</span>
        <span class="ctx-val arch-val">{d.archetype_label}</span>
      </div>
      <div class="ctx-item ctx-arch">
        <span class="ctx-label">Échantillon</span>
        <span class="ctx-val arch-val">{d.archetype_averages.sample_size} deck{d.archetype_averages.sample_size > 1 ? 's' : ''}</span>
      </div>
    {:else if d.archetype_label}
      <div class="ctx-divider"></div>
      <span class="no-arch-data">Pas assez de decks {d.archetype_label} en base pour calculer les moyennes.</span>
    {:else}
      <div class="ctx-divider"></div>
      <span class="no-arch-data">Aucun archétype renseigné — comparaison archétype indisponible.</span>
    {/if}
  </div>

  <!-- ── Global summary ────────────────────────────────────────── -->
  <div class="summary-banner" style="border-left-color:{summary.color}">
    <span class="summary-icon" style="color:{summary.color}">
      {#if summary.criticals > 0}✕{:else if summary.warnings > 0}⚠{:else}✓{/if}
    </span>
    <div class="summary-body">
      <p class="summary-verdict">{summary.verdict}</p>
      <div class="summary-counts">
        {#if summary.criticals > 0}
          <span class="sc sc--critical">{summary.criticals} critical</span>
        {/if}
        {#if summary.warnings > 0}
          <span class="sc sc--warning">{summary.warnings} warning{summary.warnings > 1 ? 's' : ''}</span>
        {/if}
        {#if summary.oks > 0}
          <span class="sc sc--ok">{summary.oks} ok</span>
        {/if}
      </div>
    </div>
  </div>

  <!-- ── Legend ──────────────────────────────────────────────── -->
  <div class="legend">
    <div class="leg-item">
      <div class="leg-dot" style="background:#6366f1"></div>
      <span>Votre deck</span>
    </div>
    {#if d.archetype_averages}
      <div class="leg-item">
        <div class="leg-dot" style="background:#f59e0b"></div>
        <span>Moy. archétype</span>
      </div>
    {/if}
    <div class="leg-item">
      <div class="leg-zone"></div>
      <span>Fourchette idéale TCG 2025-2026</span>
    </div>
  </div>

  <!-- ── Type ratios ─────────────────────────────────────────── -->
  <section class="advice-section">
    <h2>Composition du deck</h2>
    <div class="advice-list">
      {#each typeItems as item (item.category)}
        {@const range = idealRangePct(item)}
        <div class="advice-row">
          <div class="row-header">
            <span class="row-label">{item.label}</span>
            <div class="status-badge" style="color:{statusColor(item.status)}">
              {statusIcon(item.status)}
              <span class="status-val">{item.your_value}</span>
              <span class="status-range">/ idéal {item.ref_ideal_min}–{item.ref_ideal_max}</span>
            </div>
          </div>

          <!-- Visual bar -->
          <div class="bar-track">
            <!-- Ideal range zone -->
            <div
              class="ideal-zone"
              style="left:{range.left}%;width:{range.width}%"
            ></div>
            <!-- Archetype average marker -->
            {#if item.archetype_avg !== null}
              <div
                class="avg-marker"
                style="left:{avgBarPct(item)}%"
                title="Moy. archétype: {item.archetype_avg}"
              ></div>
            {/if}
            <!-- Your value bar -->
            <div
              class="your-bar"
              style="width:{barPct(item)}%;background:{statusColor(item.status)}"
            ></div>
          </div>

          <!-- Archetype comparison -->
          {#if item.archetype_avg !== null}
            {@const delta = item.your_value - item.archetype_avg}
            <div class="arch-compare">
              <span class="arch-avg-label">Moy. archétype ({item.archetype_sample} decks) :</span>
              <span class="arch-avg-val">{item.archetype_avg.toFixed(1)}</span>
              <span class="delta" class:positive={delta > 0} class:negative={delta < 0}>
                {delta > 0 ? '+' : ''}{delta.toFixed(1)}
              </span>
            </div>
          {/if}

          <!-- Tip -->
          {#if item.tip}
            <p class="tip" style="border-left-color:{statusColor(item.status)}">{item.tip}</p>
          {/if}
        </div>
      {/each}
    </div>
  </section>

  <!-- ── Role ratios ─────────────────────────────────────────── -->
  {#if roleItems.length > 0}
    <section class="advice-section">
      <h2>Rôles des cartes</h2>
      <p class="section-sub">Basé sur les rôles que vous avez tagués dans le <a href="/decks/{d.deck_id}/probability">Calculateur de probabilités</a>.</p>
      <div class="advice-list">
        {#each roleItems as item (item.category)}
          {@const range = idealRangePct(item)}
          <div class="advice-row">
            <div class="row-header">
              <span class="row-label">{item.label}</span>
              <div class="status-badge" style="color:{statusColor(item.status)}">
                {statusIcon(item.status)}
                <span class="status-val">{item.your_value}</span>
                <span class="status-range">/ idéal {item.ref_ideal_min}–{item.ref_ideal_max}</span>
              </div>
            </div>
            <div class="bar-track">
              <div class="ideal-zone" style="left:{range.left}%;width:{range.width}%"></div>
              <div class="your-bar" style="width:{barPct(item)}%;background:{statusColor(item.status)}"></div>
            </div>
            {#if item.tip}
              <p class="tip" style="border-left-color:{statusColor(item.status)}">{item.tip}</p>
            {/if}
          </div>
        {/each}
      </div>
    </section>
  {:else if !d.role_counts}
    <section class="advice-section">
      <div class="cta-roles">
        <p>
          Taguez vos cartes dans le
          <a href="/decks/{d.deck_id}/probability">Calculateur de probabilités</a>
          pour débloquer l'analyse des rôles (starters, handtraps, garnets…).
        </p>
      </div>
    </section>
  {/if}

  <!-- ── Reference table ─────────────────────────────────────── -->
  <section class="advice-section ref-section">
    <h2>Référentiel compétitif TCG 2025-2026</h2>
    <table class="ref-table">
      <thead>
        <tr>
          <th>Catégorie</th>
          <th>Fourchette idéale</th>
          <th>Signal d'alarme</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>Main deck</td><td>40–42</td><td>&lt;40 ou &gt;60</td></tr>
        <tr><td>Monsters</td><td>20–24</td><td>&lt;18 ou &gt;26</td></tr>
        <tr><td>Spells</td><td>10–14</td><td>&lt;8 ou &gt;16</td></tr>
        <tr><td>Traps</td><td>3–8</td><td>&gt;12</td></tr>
        <tr><td>Extra deck</td><td>12–15</td><td>&lt;10</td></tr>
        <tr class="sep"><td>Starters</td><td>9–15</td><td>&lt;6</td></tr>
        <tr><td>Extenders</td><td>3–8</td><td>&lt;2</td></tr>
        <tr><td>Handtraps</td><td>6–12</td><td>&lt;4</td></tr>
        <tr><td>Garnets</td><td>0–3</td><td>&gt;3</td></tr>
        <tr><td>Tech cards</td><td>1–6</td><td>&gt;8</td></tr>
      </tbody>
    </table>
    <p class="ref-note">Basé sur l'analyse de Top 8 YCS/Regional/National 2024-2026.</p>
  </section>
</div>

<style>
  .page {
    max-width: 800px;
    margin: 0 auto;
    padding: 1.5rem 1rem 4rem;
    color: #e2e8f0;
  }

  .topbar {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
  }
  .back { color: #94a3b8; text-decoration: none; font-size: 0.875rem; }
  .back:hover { color: #e2e8f0; }
  h1 { font-size: 1.25rem; font-weight: 600; margin: 0; flex: 1; }
  .archetype-badge {
    background: #1e293b;
    border: 1px solid #6366f144;
    color: #818cf8;
    border-radius: 999px;
    padding: 0.2rem 0.75rem;
    font-size: 0.8rem;
  }

  /* Global summary banner */
  .summary-banner {
    display: flex;
    align-items: flex-start;
    gap: 0.875rem;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-left-width: 3px;
    border-radius: 10px;
    padding: 0.875rem 1.125rem;
    margin-bottom: 1rem;
  }
  .summary-icon {
    font-size: 1rem;
    flex-shrink: 0;
    margin-top: 0.1rem;
    font-weight: 700;
  }
  .summary-body { display: flex; flex-direction: column; gap: 0.375rem; }
  .summary-verdict {
    font-size: 0.875rem;
    color: #e2e8f0;
    margin: 0;
    line-height: 1.5;
  }
  .summary-counts { display: flex; gap: 0.5rem; flex-wrap: wrap; }
  .sc {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    padding: 0.1rem 0.45rem;
    border-radius: 4px;
    text-transform: uppercase;
  }
  .sc--critical { background: #ef444418; color: #ef4444; border: 1px solid #ef444430; }
  .sc--warning  { background: #f59e0b18; color: #f59e0b; border: 1px solid #f59e0b30; }
  .sc--ok       { background: #22c55e18; color: #22c55e; border: 1px solid #22c55e30; }

  /* Context bar */
  .context-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 1.25rem;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 0.875rem 1.25rem;
    margin-bottom: 1rem;
  }
  .ctx-item { display: flex; flex-direction: column; align-items: center; }
  .ctx-label { font-size: 0.7rem; color: #475569; text-transform: uppercase; letter-spacing: 0.06em; }
  .ctx-val { font-size: 1rem; font-weight: 600; }
  .arch-val { color: #818cf8; }
  .ctx-divider { width: 1px; height: 32px; background: #1e293b; margin: 0 0.25rem; }
  .ctx-arch { align-items: flex-start; }
  .no-arch-data { font-size: 0.8rem; color: #475569; font-style: italic; }

  /* Legend */
  .legend {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 1.5rem;
    font-size: 0.8rem;
    color: #94a3b8;
  }
  .leg-item { display: flex; align-items: center; gap: 0.4rem; }
  .leg-dot { width: 10px; height: 10px; border-radius: 50%; }
  .leg-zone {
    width: 24px;
    height: 10px;
    border-radius: 3px;
    background: #6366f122;
    border: 1px solid #6366f144;
  }

  /* Sections */
  .advice-section {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
  }
  .advice-section h2 {
    font-size: 0.875rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 1rem;
  }
  .section-sub { font-size: 0.8rem; color: #475569; margin: -0.5rem 0 1rem; }
  .section-sub a { color: #818cf8; text-decoration: none; }
  .section-sub a:hover { text-decoration: underline; }

  /* Advice rows */
  .advice-list { display: flex; flex-direction: column; gap: 1.25rem; }

  .advice-row { display: flex; flex-direction: column; gap: 0.4rem; }

  .row-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .row-label { font-size: 0.9rem; font-weight: 500; }

  .status-badge {
    display: flex;
    align-items: baseline;
    gap: 0.25rem;
    font-size: 0.85rem;
    font-weight: 700;
  }
  .status-val { font-size: 1rem; }
  .status-range { font-weight: 400; font-size: 0.75rem; color: #475569; }

  /* Bars */
  .bar-track {
    position: relative;
    height: 12px;
    background: #1e293b;
    border-radius: 6px;
    overflow: hidden;
  }
  .ideal-zone {
    position: absolute;
    top: 0;
    height: 100%;
    background: #6366f118;
    border-left: 1px solid #6366f144;
    border-right: 1px solid #6366f144;
    pointer-events: none;
  }
  .avg-marker {
    position: absolute;
    top: 0;
    width: 2px;
    height: 100%;
    background: #f59e0b;
    z-index: 2;
    transform: translateX(-50%);
  }
  .your-bar {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    border-radius: 6px;
    opacity: 0.85;
    transition: width 0.5s ease;
    z-index: 1;
  }

  /* Archetype comparison */
  .arch-compare {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8rem;
  }
  .arch-avg-label { color: #475569; }
  .arch-avg-val { font-weight: 600; color: #f59e0b; }
  .delta { font-weight: 700; font-size: 0.85rem; }
  .delta.positive { color: #22c55e; }
  .delta.negative { color: #f87171; }

  /* Tips */
  .tip {
    font-size: 0.8rem;
    color: #cbd5e1;
    border-left: 2px solid;
    padding-left: 0.625rem;
    margin: 0.25rem 0 0;
    line-height: 1.5;
  }

  /* CTA roles */
  .cta-roles {
    text-align: center;
    padding: 0.5rem 0;
    font-size: 0.875rem;
    color: #94a3b8;
  }
  .cta-roles a { color: #818cf8; text-decoration: none; }
  .cta-roles a:hover { text-decoration: underline; }

  /* Reference table */
  .ref-section h2 { margin-bottom: 0.75rem; }
  .ref-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }
  .ref-table th {
    text-align: left;
    color: #475569;
    font-weight: 500;
    padding: 0.3rem 0.75rem;
    border-bottom: 1px solid #1e293b;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .ref-table td {
    padding: 0.4rem 0.75rem;
    border-bottom: 1px solid #0f172a;
    color: #cbd5e1;
  }
  .ref-table tr.sep td { border-top: 1px solid #1e293b; color: #94a3b8; }
  .ref-note { font-size: 0.75rem; color: #334155; margin-top: 0.75rem; font-style: italic; }
</style>
