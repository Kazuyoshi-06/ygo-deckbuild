<script lang="ts">
  import { untrack } from 'svelte';

  interface SideCardInfo {
    card_id: number;
    name: string;
    frame_type: string;
    image_url: string;
    quantity: number;
    role: string | null;
    global_side_pct: number;
  }

  interface ArchetypeSideCard {
    card_id: number;
    name: string;
    frame_type: string;
    image_url: string;
    side_pct: number;
  }

  interface ArchetypeSideData {
    archetype_label: string;
    deck_count: number;
    top_side_cards: ArchetypeSideCard[];
  }

  interface OptimizerData {
    deck_id: number;
    deck_title: string;
    side_count: number;
    current_side: SideCardInfo[];
    suggestions: SideCardInfo[];
    total_other_decks: number;
    has_side_data: boolean;
    archetypes: ArchetypeSideData[];
  }

  interface MetaEntry {
    archetype: string;
    pct: number;
  }

  interface ScoredCard {
    card_id: number;
    name: string;
    frame_type: string;
    image_url: string;
    quantity: number;
    global_side_pct: number;
    weighted_score: number;           // Σ(side_pct_in_arch × meta_weight)
    archetype_coverage: Record<string, number>; // arch → side_pct
    in_current_side: boolean;
  }

  let { data } = $props<{ data: { deckId: number; optimizer: OptimizerData } }>();
  const d = untrack(() => data.optimizer);

  // ── Meta configuration ──────────────────────────────────────────────
  let metaEntries = $state<MetaEntry[]>(
    d.archetypes.slice(0, 4).map((a) => ({ archetype: a.archetype_label, pct: 25 }))
  );
  let newArch = $state('');

  const metaTotal = $derived(metaEntries.reduce((s, e) => s + e.pct, 0));
  const metaValid = $derived(metaTotal <= 100 && metaEntries.length > 0);

  function addArchetype() {
    const label = newArch.trim();
    if (!label) return;
    if (metaEntries.some((e) => e.archetype.toLowerCase() === label.toLowerCase())) return;
    const remaining = Math.max(0, Math.floor((100 - metaTotal) / 1));
    metaEntries = [...metaEntries, { archetype: label, pct: Math.min(remaining, 25) }];
    newArch = '';
  }

  function removeEntry(idx: number) {
    metaEntries = metaEntries.filter((_, i) => i !== idx);
  }

  function setQuickMeta() {
    const top = d.archetypes.slice(0, 3);
    const base = Math.floor(100 / Math.max(top.length, 1));
    metaEntries = top.map((a) => ({ archetype: a.archetype_label, pct: base }));
  }

  // ── Archetype lookup ────────────────────────────────────────────────
  const archLookup = $derived(
    Object.fromEntries(d.archetypes.map((a) => [a.archetype_label, a]))
  );

  // ── Score computation ───────────────────────────────────────────────
  function computeScore(cardId: number): { weighted: number; byArch: Record<string, number> } {
    if (!metaValid) return { weighted: 0, byArch: {} };
    let weighted = 0;
    const byArch: Record<string, number> = {};
    for (const entry of metaEntries) {
      const arch = archLookup[entry.archetype];
      if (!arch) continue;
      const cardData = arch.top_side_cards.find((c) => c.card_id === cardId);
      const pct = cardData ? cardData.side_pct : 0;
      byArch[entry.archetype] = pct;
      weighted += pct * (entry.pct / 100);
    }
    return { weighted, byArch };
  }

  const scoredCurrentSide = $derived<ScoredCard[]>(
    d.current_side.map((c) => {
      const { weighted, byArch } = computeScore(c.card_id);
      return { ...c, weighted_score: weighted, archetype_coverage: byArch, in_current_side: true };
    }).sort((a, b) => b.weighted_score - a.weighted_score)
  );

  const scoredSuggestions = $derived<ScoredCard[]>(
    d.suggestions.map((c) => {
      const { weighted, byArch } = computeScore(c.card_id);
      return { ...c, weighted_score: weighted, archetype_coverage: byArch, in_current_side: false };
    }).sort((a, b) => b.weighted_score - a.weighted_score).slice(0, 15)
  );

  const coverageScore = $derived(
    metaValid && scoredCurrentSide.length > 0
      ? Math.min(100, Math.round(
          scoredCurrentSide.reduce((s, c) => s + c.weighted_score, 0) * 100
        ))
      : null
  );

  // ── UI helpers ──────────────────────────────────────────────────────
  const ROLE_COLOR: Record<string, string> = {
    handtrap: '#f59e0b', tech: '#818cf8', starter: '#22c55e',
    extender: '#4ade80', garnet: '#ef4444', boss: '#fbbf24', other: '#94a3b8',
  };

  function frameColor(frame: string): string {
    if (frame === 'spell')  return '#1a7a4a';
    if (frame === 'trap')   return '#8b1a6b';
    if (frame === 'effect') return '#8b4a1a';
    if (frame === 'fusion') return '#4a1a8b';
    if (frame === 'synchro') return '#c8c8c8';
    if (frame === 'xyz')    return '#1a1a1a';
    if (frame === 'link')   return '#004a8b';
    return '#4a4a1a';
  }

  function pctBar(v: number, max = 1): string {
    return `width: ${Math.min(v / max, 1) * 100}%`;
  }

  function coverageLabel(score: number): string {
    if (score >= 70) return 'Excellent';
    if (score >= 50) return 'Bon';
    if (score >= 30) return 'Moyen';
    return 'Faible';
  }

  function coverageColor(score: number): string {
    if (score >= 70) return '#22c55e';
    if (score >= 50) return '#f59e0b';
    if (score >= 30) return '#f97316';
    return '#ef4444';
  }
</script>

<svelte:head>
  <title>Side Optimizer — {d.deck_title} — YGO Intel</title>
</svelte:head>

<div class="page">
  <div class="topbar">
    <a href="/decks/{d.deck_id}" class="back">← Deck</a>
    <h1>{d.deck_title}</h1>
    <span class="badge side-badge">Side {d.side_count}/15</span>
  </div>

  {#if !d.has_side_data}
    <div class="notice">
      Pas encore assez de données dans la base — importez d'autres decklists pour activer les suggestions basées sur la communauté.
    </div>
  {/if}

  <div class="layout">

    <!-- ── LEFT : Meta config ──────────────────────────────────────── -->
    <aside class="meta-panel">
      <div class="panel-header">
        <span class="panel-icon">⬡</span>
        <h2>Configuration méta</h2>
      </div>

      <p class="meta-hint">
        Définissez la distribution des archétypes que vous attendez en tournoi. Les scores de side sont pondérés en conséquence.
      </p>

      {#if d.archetypes.length > 0}
        <button class="btn-quick" onclick={setQuickMeta}>
          ↺ Top-{Math.min(3, d.archetypes.length)} auto
        </button>
      {/if}

      <div class="meta-entries">
        {#each metaEntries as entry, idx}
          <div class="meta-row">
            <span class="arch-name">{entry.archetype}</span>
            <input
              type="range" min="0" max="100" step="5"
              bind:value={entry.pct}
              class="meta-slider"
            />
            <span class="arch-pct">{entry.pct}%</span>
            <button class="remove-btn" onclick={() => removeEntry(idx)}>×</button>
          </div>
        {/each}
      </div>

      <div class="meta-total" class:over={metaTotal > 100}>
        Total : {metaTotal}% {#if metaTotal > 100}⚠ &gt; 100%{/if}
      </div>

      <div class="add-arch-row">
        <input
          type="text"
          placeholder="Archétype (ex: Snake-Eye)"
          bind:value={newArch}
          class="arch-input"
          onkeydown={(e) => { if (e.key === 'Enter') addArchetype(); }}
        />
        <button class="btn-add" onclick={addArchetype}>+</button>
      </div>

      {#if d.archetypes.length > 0}
        <div class="arch-chips">
          {#each d.archetypes.slice(0, 8) as a}
            {#if !metaEntries.some(e => e.archetype === a.archetype_label)}
              <button
                class="arch-chip"
                onclick={() => { newArch = a.archetype_label; addArchetype(); }}
              >
                {a.archetype_label}
                <span class="chip-count">{a.deck_count}</span>
              </button>
            {/if}
          {/each}
        </div>
      {/if}

      {#if coverageScore !== null}
        <div class="coverage-box">
          <div class="cov-label">Score de couverture</div>
          <div class="cov-score" style="color:{coverageColor(coverageScore)}">
            {coverageScore}<span class="cov-unit">/100</span>
          </div>
          <div class="cov-status" style="color:{coverageColor(coverageScore)}">
            {coverageLabel(coverageScore)}
          </div>
          <div class="cov-bar-track">
            <div class="cov-bar" style="width:{coverageScore}%;background:{coverageColor(coverageScore)}"></div>
          </div>
          <p class="cov-hint">Basé sur la présence de vos cartes de side dans les decks des archétypes sélectionnés.</p>
        </div>
      {/if}
    </aside>

    <!-- ── RIGHT : Cards ───────────────────────────────────────────── -->
    <div class="cards-col">

      <!-- Current side -->
      <section class="cards-section">
        <h2 class="section-title">
          Side actuel
          <span class="sec-count">{d.current_side.length} cartes</span>
        </h2>

        {#if d.current_side.length === 0}
          <div class="empty">Ce deck n'a pas de side deck.</div>
        {:else}
          <div class="card-list">
            {#each scoredCurrentSide as card}
              <div class="card-row">
                <div class="card-img-wrap" style="border-color:{frameColor(card.frame_type)}">
                  <img src={card.image_url} alt={card.name} class="card-img" loading="lazy" />
                  {#if card.quantity > 1}
                    <span class="qty-badge">×{card.quantity}</span>
                  {/if}
                </div>

                <div class="card-info">
                  <div class="card-name-row">
                    <span class="card-name">{card.name}</span>
                    {#if card.role}
                      <span class="role-tag" style="color:{ROLE_COLOR[card.role] ?? '#94a3b8'}">
                        {card.role}
                      </span>
                    {/if}
                  </div>

                  <div class="pop-row">
                    <span class="pop-label">Popularité DB</span>
                    <div class="pop-bar-track">
                      <div class="pop-bar" style={pctBar(card.global_side_pct)}></div>
                    </div>
                    <span class="pop-pct">{(card.global_side_pct * 100).toFixed(0)}%</span>
                  </div>

                  {#if metaValid && Object.keys(card.archetype_coverage).length > 0}
                    <div class="arch-cov-row">
                      {#each Object.entries(card.archetype_coverage) as [arch, pct]}
                        {#if pct > 0}
                          <span class="arch-dot" title="{arch}: {(pct * 100).toFixed(0)}%">
                            {arch.slice(0, 6)}…
                            <span class="arch-dot-pct">{(pct * 100).toFixed(0)}%</span>
                          </span>
                        {/if}
                      {/each}
                    </div>
                  {/if}
                </div>

                {#if metaValid}
                  <div class="score-col">
                    <span class="weighted-score" title="Score pondéré méta">
                      {(card.weighted_score * 100).toFixed(0)}
                    </span>
                    <span class="score-unit">pts</span>
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </section>

      <!-- Suggestions -->
      {#if d.has_side_data && d.suggestions.length > 0}
        <section class="cards-section">
          <h2 class="section-title">
            Suggestions
            <span class="sec-count hint-muted">cartes absentes de votre side, populaires dans la DB</span>
          </h2>

          <div class="card-list">
            {#each scoredSuggestions as card}
              <div class="card-row suggestion">
                <div class="card-img-wrap" style="border-color:{frameColor(card.frame_type)}">
                  <img src={card.image_url} alt={card.name} class="card-img" loading="lazy" />
                </div>

                <div class="card-info">
                  <div class="card-name-row">
                    <span class="card-name">{card.name}</span>
                  </div>

                  <div class="pop-row">
                    <span class="pop-label">Popularité DB</span>
                    <div class="pop-bar-track">
                      <div class="pop-bar suggestion-bar" style={pctBar(card.global_side_pct)}></div>
                    </div>
                    <span class="pop-pct">{(card.global_side_pct * 100).toFixed(0)}%</span>
                  </div>

                  {#if metaValid && Object.keys(card.archetype_coverage).length > 0}
                    <div class="arch-cov-row">
                      {#each Object.entries(card.archetype_coverage) as [arch, pct]}
                        {#if pct > 0}
                          <span class="arch-dot" title="{arch}: {(pct * 100).toFixed(0)}%">
                            {arch.slice(0, 6)}…
                            <span class="arch-dot-pct">{(pct * 100).toFixed(0)}%</span>
                          </span>
                        {/if}
                      {/each}
                    </div>
                  {/if}
                </div>

                {#if metaValid}
                  <div class="score-col">
                    <span class="weighted-score suggestion-score" title="Score pondéré méta">
                      {(card.weighted_score * 100).toFixed(0)}
                    </span>
                    <span class="score-unit">pts</span>
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </section>
      {/if}

    </div>
  </div>
</div>

<style>
  .page {
    max-width: 1100px;
    margin: 0 auto;
    padding: 1.5rem 1rem 4rem;
    color: #e2e8f0;
  }

  .topbar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
  }
  .back { color: #94a3b8; text-decoration: none; font-size: 0.875rem; }
  .back:hover { color: #e2e8f0; }
  h1 { font-size: 1.2rem; font-weight: 600; margin: 0; flex: 1; }

  .badge {
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .side-badge { background: #1e3a5f; color: #38bdf8; }

  .notice {
    background: #1e293b; border: 1px solid #334155;
    border-radius: 8px; padding: 0.75rem 1rem;
    font-size: 0.85rem; color: #94a3b8; margin-bottom: 1rem;
  }

  /* Layout */
  .layout {
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 1rem;
    align-items: start;
  }
  @media (max-width: 720px) {
    .layout { grid-template-columns: 1fr; }
  }

  /* Meta panel */
  .meta-panel {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 1.25rem;
    position: sticky;
    top: 1rem;
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }
  .panel-icon { font-size: 1rem; color: #818cf8; }
  h2 { font-size: 1rem; font-weight: 700; margin: 0; }

  .meta-hint {
    font-size: 0.78rem;
    color: #64748b;
    margin: 0 0 0.75rem;
    line-height: 1.5;
  }

  .btn-quick {
    width: 100%;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #94a3b8;
    font-size: 0.78rem;
    padding: 0.35rem 0.6rem;
    cursor: pointer;
    margin-bottom: 0.75rem;
  }
  .btn-quick:hover { color: #e2e8f0; border-color: #475569; }

  .meta-entries {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .meta-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  .arch-name {
    font-size: 0.75rem;
    color: #cbd5e1;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .meta-slider {
    width: 80px;
    flex-shrink: 0;
    accent-color: #818cf8;
  }
  .arch-pct {
    font-size: 0.72rem;
    color: #818cf8;
    width: 32px;
    text-align: right;
  }
  .remove-btn {
    background: none;
    border: none;
    color: #475569;
    cursor: pointer;
    font-size: 0.9rem;
    padding: 0;
    line-height: 1;
  }
  .remove-btn:hover { color: #ef4444; }

  .meta-total {
    font-size: 0.78rem;
    color: #475569;
    text-align: right;
    margin-bottom: 0.75rem;
  }
  .meta-total.over { color: #ef4444; }

  .add-arch-row {
    display: flex;
    gap: 0.4rem;
    margin-bottom: 0.6rem;
  }
  .arch-input {
    flex: 1;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #e2e8f0;
    font-size: 0.78rem;
    padding: 0.35rem 0.5rem;
  }
  .arch-input:focus { outline: none; border-color: #818cf8; }

  .btn-add {
    background: #818cf8;
    border: none;
    border-radius: 6px;
    color: white;
    font-size: 1rem;
    width: 30px;
    cursor: pointer;
    font-weight: 700;
  }
  .btn-add:hover { background: #6366f1; }

  .arch-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-bottom: 0.75rem;
  }
  .arch-chip {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 20px;
    color: #94a3b8;
    font-size: 0.7rem;
    padding: 0.15rem 0.5rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }
  .arch-chip:hover { border-color: #818cf8; color: #e2e8f0; }
  .chip-count {
    background: #0f172a;
    border-radius: 10px;
    padding: 0 4px;
    font-size: 0.65rem;
    color: #475569;
  }

  /* Coverage box */
  .coverage-box {
    background: #0a1628;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 0.875rem;
    margin-top: 0.75rem;
  }
  .cov-label { font-size: 0.72rem; color: #64748b; margin-bottom: 0.2rem; }
  .cov-score {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 0.15rem;
  }
  .cov-unit { font-size: 0.9rem; font-weight: 400; color: #475569; }
  .cov-status { font-size: 0.78rem; font-weight: 700; margin-bottom: 0.5rem; }
  .cov-bar-track {
    height: 4px;
    background: #1e293b;
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 0.5rem;
  }
  .cov-bar {
    height: 100%;
    border-radius: 2px;
    transition: width 0.4s;
  }
  .cov-hint { font-size: 0.7rem; color: #475569; margin: 0; line-height: 1.4; }

  /* Cards column */
  .cards-col { display: flex; flex-direction: column; gap: 0.75rem; }

  .cards-section {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 1rem;
  }

  .section-title {
    font-size: 0.95rem;
    font-weight: 700;
    margin: 0 0 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .sec-count { font-size: 0.75rem; color: #475569; font-weight: 400; }
  .hint-muted { font-size: 0.72rem; color: #334155; }

  .empty { font-size: 0.85rem; color: #475569; }

  .card-list { display: flex; flex-direction: column; gap: 0.5rem; }

  .card-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 0.75rem;
    border-radius: 10px;
    background: #0a1628;
    border: 1px solid #1e293b;
    transition: border-color 0.15s;
  }
  .card-row:hover { border-color: #334155; }
  .card-row.suggestion { border-style: dashed; }

  .card-img-wrap {
    flex-shrink: 0;
    width: 42px;
    height: 58px;
    border-radius: 4px;
    overflow: hidden;
    border: 2px solid;
    position: relative;
  }
  .card-img { width: 100%; height: 100%; object-fit: cover; }
  .qty-badge {
    position: absolute;
    bottom: 0; right: 0;
    background: #000000cc;
    color: #e2e8f0;
    font-size: 0.6rem;
    font-weight: 700;
    padding: 0 3px;
    border-radius: 2px 0 0 0;
  }

  .card-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.3rem; }

  .card-name-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
  }
  .card-name { font-size: 0.85rem; font-weight: 600; color: #e2e8f0; }
  .role-tag {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .pop-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.72rem;
  }
  .pop-label { color: #475569; flex-shrink: 0; }
  .pop-bar-track {
    flex: 1;
    height: 5px;
    background: #1e293b;
    border-radius: 3px;
    overflow: hidden;
  }
  .pop-bar { height: 100%; background: #38bdf8; border-radius: 3px; }
  .suggestion-bar { background: #818cf8; }
  .pop-pct { color: #64748b; width: 28px; text-align: right; }

  .arch-cov-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
  }
  .arch-dot {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    background: #1e293b;
    border-radius: 4px;
    padding: 0.1rem 0.35rem;
    font-size: 0.65rem;
    color: #64748b;
  }
  .arch-dot-pct { color: #818cf8; font-weight: 700; }

  .score-col {
    flex-shrink: 0;
    text-align: right;
    min-width: 40px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .weighted-score {
    font-size: 1.3rem;
    font-weight: 800;
    color: #38bdf8;
    line-height: 1;
  }
  .suggestion-score { color: #818cf8; }
  .score-unit { font-size: 0.6rem; color: #475569; }
</style>
