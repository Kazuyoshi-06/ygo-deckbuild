<script lang="ts">
  import { onMount, untrack } from 'svelte';

  interface CardProbRow {
    card_id: number;
    external_card_id: number;
    name: string;
    frame_type: string;
    image_url: string;
    total_in_main: number;
    role: string | null;
    p_at_least_one_5: number;
    p_at_least_one_6: number;
    p_zero_5: number;
  }

  interface GroupStats {
    role: string;
    total_copies: number;
    p_at_least_one_5: number;
    p_at_least_one_6: number;
  }

  interface Recommendation {
    level: string;
    text: string;
  }

  interface ProbabilityData {
    deck_id: number;
    deck_title: string;
    main_count: number;
    cards: CardProbRow[];
    groups: GroupStats[];
    dead_hand_p5: number;
    dead_hand_p6: number;
    has_roles: boolean;
    recommendations: Recommendation[];
  }

  let { data } = $props<{ data: { deckId: number; probability: ProbabilityData } }>();

  // untrack prevents Svelte 5 from warning that data.probability is only captured once.
  // prob is independent state updated by reloadProb() after each role PATCH.
  let prob = $state<ProbabilityData>(untrack(() => data.probability));
  let loading = $state(false);
  let pendingRoles = $state<Record<number, string | null>>({});

  const ROLES: { key: string; label: string; color: string; desc: string }[] = [
    { key: 'starter',   label: 'S',  color: '#22c55e', desc: 'Starter' },
    { key: 'extender',  label: 'E',  color: '#3b82f6', desc: 'Extender' },
    { key: 'handtrap',  label: 'HT', color: '#f59e0b', desc: 'Handtrap' },
    { key: 'garnet',    label: 'G',  color: '#ef4444', desc: 'Garnet' },
    { key: 'tech',      label: 'T',  color: '#8b5cf6', desc: 'Tech' },
    { key: 'boss',      label: 'B',  color: '#ec4899', desc: 'Boss' },
    { key: 'other',     label: '?',  color: '#6b7280', desc: 'Other' },
  ];

  const ROLE_MAP = Object.fromEntries(ROLES.map(r => [r.key, r]));

  const FRAME_COLORS: Record<string, string> = {
    spell:    '#4ade80',
    trap:     '#c084fc',
    normal:   '#fbbf24',
    effect:   '#fb923c',
    fusion:   '#a855f7',
    synchro:  '#e2e8f0',
    xyz:      '#94a3b8',
    link:     '#60a5fa',
    ritual:   '#818cf8',
    token:    '#6b7280',
  };

  function frameColor(ft: string): string {
    return FRAME_COLORS[ft?.toLowerCase()] ?? '#64748b';
  }

  async function reloadProb() {
    const res = await fetch(`/api/v1/decks/${data.deckId}/probability`);
    if (res.ok) prob = await res.json();
  }

  async function setRole(cardId: number, role: string | null) {
    const current = prob.cards.find(c => c.card_id === cardId)?.role ?? null;
    const next = current === role ? null : role;

    pendingRoles[cardId] = next === undefined ? null : next;

    const res = await fetch(`/api/v1/decks/${data.deckId}/cards/${cardId}/role`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: next }),
    });

    if (res.ok) {
      await reloadProb();
    }
    delete pendingRoles[cardId];
  }

  function pct(v: number): string {
    return (v * 100).toFixed(1) + '%';
  }

  function deadHandColor(v: number): string {
    if (v > 0.30) return '#ef4444';
    if (v > 0.15) return '#f59e0b';
    return '#22c55e';
  }

  function recColor(level: string): string {
    if (level === 'critical') return '#ef4444';
    if (level === 'warning')  return '#f59e0b';
    return '#60a5fa';
  }

  function recIcon(level: string): string {
    if (level === 'critical') return '✕';
    if (level === 'warning')  return '⚠';
    return 'ℹ';
  }

  // Sort cards: first by role bucket, then untagged at end
  let sortedCards = $derived(
    [...prob.cards].sort((a, b) => {
      const ra = ROLES.findIndex(r => r.key === a.role);
      const rb = ROLES.findIndex(r => r.key === b.role);
      const ia = ra === -1 ? 99 : ra;
      const ib = rb === -1 ? 99 : rb;
      return ia !== ib ? ia - ib : a.name.localeCompare(b.name);
    })
  );
</script>

<div class="page">
  <div class="topbar">
    <a href="/decks/{data.deckId}" class="back">← Deck</a>
    <h1>{prob.deck_title}</h1>
    <span class="badge">{prob.main_count} cartes main</span>
  </div>

  <!-- ── Recommendations ─────────────────────────────────────── -->
  {#if prob.recommendations.length > 0}
    <section class="recs">
      {#each prob.recommendations as rec}
        <div class="rec" style="border-left-color:{recColor(rec.level)}">
          <span class="rec-icon" style="color:{recColor(rec.level)}">{recIcon(rec.level)}</span>
          <p>{rec.text}</p>
        </div>
      {/each}
    </section>
  {/if}

  <!-- ── Dead hand & Groups ──────────────────────────────────── -->
  {#if prob.has_roles}
    <section class="stats-grid">
      <div class="stat-card dead-hand">
        <h2>Main morte</h2>
        <p class="stat-sub">P(0 starter · 0 handtrap)</p>
        <div class="dead-bars">
          <div class="dead-row">
            <span class="hand-label">Main 5 cartes</span>
            <div class="bar-track">
              <div class="bar-fill" style="width:{prob.dead_hand_p5 * 100}%;background:{deadHandColor(prob.dead_hand_p5)}"></div>
            </div>
            <span class="hand-pct" style="color:{deadHandColor(prob.dead_hand_p5)}">{pct(prob.dead_hand_p5)}</span>
          </div>
          <div class="dead-row">
            <span class="hand-label">Main 6 cartes</span>
            <div class="bar-track">
              <div class="bar-fill" style="width:{prob.dead_hand_p6 * 100}%;background:{deadHandColor(prob.dead_hand_p6)}"></div>
            </div>
            <span class="hand-pct" style="color:{deadHandColor(prob.dead_hand_p6)}">{pct(prob.dead_hand_p6)}</span>
          </div>
        </div>
      </div>

      <div class="stat-card groups">
        <h2>Par rôle</h2>
        <table>
          <thead>
            <tr>
              <th>Rôle</th>
              <th>Copies</th>
              <th title="P(≥1) en main de 5">P≥1 (5)</th>
              <th title="P(≥1) en main de 6">P≥1 (6)</th>
            </tr>
          </thead>
          <tbody>
            {#each prob.groups as g}
              {@const roleInfo = ROLE_MAP[g.role]}
              <tr>
                <td>
                  <span class="role-chip" style="background:{roleInfo?.color ?? '#6b7280'}22;color:{roleInfo?.color ?? '#6b7280'};border-color:{roleInfo?.color ?? '#6b7280'}44">
                    {roleInfo?.label ?? g.role}
                    <span class="role-full">{roleInfo?.desc ?? g.role}</span>
                  </span>
                </td>
                <td class="num">{g.total_copies}</td>
                <td class="num prob">{pct(g.p_at_least_one_5)}</td>
                <td class="num prob">{pct(g.p_at_least_one_6)}</td>
              </tr>
            {/each}
            {#if prob.groups.length === 0}
              <tr><td colspan="4" class="empty">Aucun rôle assigné</td></tr>
            {/if}
          </tbody>
        </table>
      </div>
    </section>
  {/if}

  <!-- ── Card tagger ─────────────────────────────────────────── -->
  <section class="tagger">
    <div class="tagger-header">
      <h2>Cartes main deck</h2>
      <div class="legend">
        {#each ROLES as r}
          <span class="leg-chip" style="background:{r.color}22;color:{r.color};border-color:{r.color}44">{r.label} = {r.desc}</span>
        {/each}
      </div>
    </div>

    <div class="card-list">
      {#each sortedCards as card (card.card_id)}
        {@const isPending = card.card_id in pendingRoles}
        <div class="card-row" class:pending={isPending}>
          <div class="card-img-wrap" style="border-color:{frameColor(card.frame_type)}44">
            <img
              src={card.image_url}
              alt={card.name}
              class="card-img"
              loading="lazy"
              onerror={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          </div>

          <div class="card-info">
            <span class="card-name" style="border-left:3px solid {frameColor(card.frame_type)}">{card.name}</span>
            <span class="card-count">×{card.total_in_main}</span>
          </div>

          <div class="role-btns">
            {#each ROLES as r}
              <button
                type="button"
                class="role-btn"
                class:active={card.role === r.key}
                style="--rc:{r.color}"
                title={r.desc}
                onclick={() => setRole(card.card_id, r.key)}
                disabled={isPending}
              >
                {r.label}
              </button>
            {/each}
            <button
              type="button"
              class="role-btn clear-btn"
              title="Effacer le rôle"
              onclick={() => setRole(card.card_id, null)}
              disabled={isPending || card.role === null}
            >
              ∅
            </button>
          </div>

          {#if prob.has_roles && card.role}
            <div class="card-probs">
              <span title="P(≥1) en 5 cartes" class="prob-val">{pct(card.p_at_least_one_5)}</span>
              <span class="prob-sep">/</span>
              <span title="P(≥1) en 6 cartes" class="prob-val dim">{pct(card.p_at_least_one_6)}</span>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  </section>
</div>

<style>
  .page {
    max-width: 960px;
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
  .back {
    color: #94a3b8;
    text-decoration: none;
    font-size: 0.875rem;
  }
  .back:hover { color: #e2e8f0; }
  h1 {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0;
    flex: 1;
  }
  .badge {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 999px;
    padding: 0.2rem 0.75rem;
    font-size: 0.8rem;
    color: #94a3b8;
  }

  /* Recommendations */
  .recs {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
  }
  .rec {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-left-width: 3px;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
  }
  .rec p { margin: 0; color: #cbd5e1; }
  .rec-icon { font-size: 1rem; flex-shrink: 0; margin-top: 1px; }

  /* Stats grid */
  .stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }
  @media (max-width: 640px) {
    .stats-grid { grid-template-columns: 1fr; }
  }
  .stat-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 1.25rem;
  }
  .stat-card h2 {
    font-size: 0.875rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 0.25rem;
  }
  .stat-sub {
    font-size: 0.75rem;
    color: #475569;
    margin: 0 0 1rem;
  }

  .dead-bars { display: flex; flex-direction: column; gap: 0.75rem; }
  .dead-row { display: flex; align-items: center; gap: 0.75rem; }
  .hand-label { font-size: 0.8rem; color: #94a3b8; width: 110px; flex-shrink: 0; }
  .bar-track {
    flex: 1;
    height: 8px;
    background: #1e293b;
    border-radius: 4px;
    overflow: hidden;
  }
  .bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
  .hand-pct { font-size: 0.8rem; font-weight: 600; width: 44px; text-align: right; flex-shrink: 0; }

  .groups table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  .groups th {
    text-align: left;
    color: #475569;
    font-weight: 500;
    padding: 0.25rem 0.5rem 0.5rem;
    border-bottom: 1px solid #1e293b;
    font-size: 0.75rem;
  }
  .groups td { padding: 0.4rem 0.5rem; border-bottom: 1px solid #0f172a; }
  .groups .num { text-align: right; }
  .groups .prob { font-weight: 600; }
  .empty { color: #475569; text-align: center; padding: 1rem; }

  .role-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    border: 1px solid;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.05em;
  }
  .role-full { font-weight: 400; opacity: 0.8; }

  /* Card tagger */
  .tagger { background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 1.25rem; }
  .tagger-header { display: flex; align-items: flex-start; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
  .tagger-header h2 {
    font-size: 0.875rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0;
    flex-shrink: 0;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }
  .leg-chip {
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    border: 1px solid;
    font-size: 0.7rem;
    font-weight: 600;
  }

  .card-list { display: flex; flex-direction: column; gap: 0.5rem; }

  .card-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem;
    border-radius: 8px;
    background: #020617;
    border: 1px solid #1e293b;
    transition: border-color 0.2s, opacity 0.2s;
  }
  .card-row.pending { opacity: 0.5; }
  .card-row:hover { border-color: #334155; }

  .card-img-wrap {
    width: 36px;
    height: 52px;
    flex-shrink: 0;
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid;
    background: #0f172a;
  }
  .card-img { width: 100%; height: 100%; object-fit: cover; display: block; }

  .card-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    flex: 1;
    min-width: 0;
  }
  .card-name {
    font-size: 0.85rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding-left: 0.5rem;
  }
  .card-count {
    font-size: 0.75rem;
    color: #475569;
    padding-left: 0.5rem;
  }

  .role-btns {
    display: flex;
    gap: 0.25rem;
    flex-shrink: 0;
    flex-wrap: wrap;
  }

  .role-btn {
    width: 28px;
    height: 28px;
    border-radius: 5px;
    border: 1px solid #334155;
    background: #0f172a;
    color: #94a3b8;
    font-size: 0.7rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .role-btn:hover:not(:disabled) {
    border-color: var(--rc, #94a3b8);
    color: var(--rc, #94a3b8);
    background: color-mix(in srgb, var(--rc, #94a3b8) 15%, transparent);
  }
  .role-btn.active {
    background: color-mix(in srgb, var(--rc, #94a3b8) 25%, transparent);
    border-color: var(--rc, #94a3b8);
    color: var(--rc, #94a3b8);
  }
  .role-btn:disabled { opacity: 0.3; cursor: default; }
  .clear-btn { --rc: #6b7280; }

  .card-probs {
    display: flex;
    align-items: center;
    gap: 0.2rem;
    flex-shrink: 0;
    width: 90px;
    justify-content: flex-end;
  }
  .prob-val { font-size: 0.8rem; font-weight: 600; color: #22c55e; }
  .prob-val.dim { color: #4ade80; font-weight: 400; }
  .prob-sep { color: #334155; }
</style>
