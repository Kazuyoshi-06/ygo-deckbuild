<script lang="ts">
  import { untrack } from 'svelte';

  interface MatchResultRow {
    id: number;
    opponent_arch: string;
    result: 'W' | 'L' | 'D';
    event_date: string | null;
    notes: string | null;
    created_at: string;
  }

  interface MatchupSummary {
    opponent_arch: string;
    wins: number;
    losses: number;
    draws: number;
    total: number;
    win_rate: number;
  }

  interface MatchupData {
    deck_id: number;
    deck_title: string;
    archetype_label: string | null;
    total_matches: number;
    overall_wins: number;
    overall_losses: number;
    overall_draws: number;
    overall_win_rate: number;
    matchup_stats: MatchupSummary[];
    recent_results: MatchResultRow[];
  }

  let { data } = $props<{ data: { deckId: number; matchups: MatchupData } }>();

  const deckId = untrack(() => data.deckId);
  let d = $state<MatchupData>(untrack(() => data.matchups));

  // ── Form state ──────────────────────────────────────────────────────
  let formArch = $state('');
  let formResult = $state<'W' | 'L' | 'D' | ''>('');
  let formDate = $state('');
  let formNotes = $state('');
  let submitting = $state(false);
  let formError = $state('');

  const formValid = $derived(formArch.trim().length > 0 && formResult !== '');

  async function submitMatch() {
    if (!formValid) return;
    submitting = true;
    formError = '';
    try {
      const res = await fetch(`/api/v1/decks/${deckId}/match-results`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          opponent_arch: formArch.trim(),
          result: formResult,
          event_date: formDate || null,
          notes: formNotes.trim() || null,
        }),
      });
      if (!res.ok) {
        formError = res.status === 401 ? 'Authentification requise.' : 'Erreur lors de l\'enregistrement.';
        return;
      }
      formArch = '';
      formResult = '';
      formDate = '';
      formNotes = '';
      await reload();
    } finally {
      submitting = false;
    }
  }

  async function deleteResult(id: number) {
    const res = await fetch(`/api/v1/decks/${deckId}/match-results/${id}`, { method: 'DELETE' });
    if (res.ok) await reload();
  }

  async function reload() {
    const res = await fetch(`/api/v1/decks/${deckId}/matchup-stats`);
    if (res.ok) d = await res.json();
  }

  // ── Display helpers ─────────────────────────────────────────────────
  function resultColor(r: string): string {
    if (r === 'W') return '#22c55e';
    if (r === 'L') return '#ef4444';
    return '#f59e0b';
  }

  function resultLabel(r: string): string {
    if (r === 'W') return 'Victoire';
    if (r === 'L') return 'Défaite';
    return 'Nul';
  }

  function wrColor(wr: number): string {
    if (wr >= 0.6) return '#22c55e';
    if (wr >= 0.4) return '#f59e0b';
    return '#ef4444';
  }

  function wrBar(wr: number): string {
    return `width:${Math.round(wr * 100)}%`;
  }

  function formatDate(s: string): string {
    return new Date(s).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  const COMMON_ARCHS = [
    'Snake-Eye', 'Tenpai Dragon', 'Yubel', 'Kashtira',
    'Branded Despia', 'Labrynth', 'Purrely', 'Mannadium',
  ];
</script>

<svelte:head>
  <title>Matchups — {d.deck_title} — YGO Intel</title>
</svelte:head>

<div class="page">
  <div class="topbar">
    <a href="/decks/{d.deck_id}" class="back">← Deck</a>
    <h1>{d.deck_title}</h1>
    {#if d.archetype_label}
      <span class="arch-badge">{d.archetype_label}</span>
    {/if}
  </div>

  <div class="layout">

    <!-- ── LEFT : Log form + overall stats ──────────────────────────── -->
    <aside class="left-col">

      <!-- Overall stats -->
      <div class="overall-card">
        <div class="overall-title">Bilan global</div>
        <div class="overall-wld">
          <span class="wld-num" style="color:#22c55e">{d.overall_wins}V</span>
          <span class="wld-sep">/</span>
          <span class="wld-num" style="color:#f59e0b">{d.overall_draws}N</span>
          <span class="wld-sep">/</span>
          <span class="wld-num" style="color:#ef4444">{d.overall_losses}D</span>
        </div>
        <div class="overall-total">{d.total_matches} match{d.total_matches > 1 ? 's' : ''}</div>
        {#if d.total_matches > 0}
          <div class="wr-row">
            <div class="wr-bar-track">
              <div class="wr-bar" style="width:{Math.round(d.overall_win_rate * 100)}%;background:{wrColor(d.overall_win_rate)}"></div>
            </div>
            <span class="wr-pct" style="color:{wrColor(d.overall_win_rate)}">
              {Math.round(d.overall_win_rate * 100)}%
            </span>
          </div>
        {/if}
      </div>

      <!-- Log form -->
      <div class="form-card">
        <div class="form-title">Enregistrer un match</div>

        <label class="field-label">Archétype adverse</label>
        <input
          type="text"
          bind:value={formArch}
          placeholder="ex: Snake-Eye"
          class="field-input"
          list="arch-suggestions"
        />
        <datalist id="arch-suggestions">
          {#each COMMON_ARCHS as a}
            <option value={a}></option>
          {/each}
          {#each d.matchup_stats as s}
            <option value={s.opponent_arch}></option>
          {/each}
        </datalist>

        <label class="field-label" style="margin-top:0.75rem">Résultat</label>
        <div class="result-btns">
          {#each [['W','V'],['D','N'],['L','D']] as [v, lbl]}
            <button
              class="result-btn"
              class:active={formResult === v}
              style="--rc:{resultColor(v)}"
              onclick={() => { formResult = v as 'W' | 'L' | 'D'; }}
            >{lbl}</button>
          {/each}
        </div>

        <label class="field-label" style="margin-top:0.75rem">Date <span class="opt">(optionnel)</span></label>
        <input type="date" bind:value={formDate} class="field-input" />

        <label class="field-label" style="margin-top:0.75rem">Notes <span class="opt">(optionnel)</span></label>
        <textarea bind:value={formNotes} class="field-textarea" rows="2" placeholder="contexte, format, etc."></textarea>

        {#if formError}
          <div class="form-error">{formError}</div>
        {/if}

        <button
          class="btn-submit"
          disabled={!formValid || submitting}
          onclick={submitMatch}
        >
          {submitting ? '…' : '+ Enregistrer'}
        </button>
      </div>

      <!-- Link to global matrix -->
      <a href="/analytics/matchups" class="matrix-link">
        ◎ Voir la matrice globale
      </a>
    </aside>

    <!-- ── RIGHT : Per-matchup stats + history ───────────────────────── -->
    <div class="right-col">

      <!-- Per-matchup stats -->
      {#if d.matchup_stats.length > 0}
        <section class="section-card">
          <h2 class="section-title">Par archétype</h2>
          <div class="matchup-list">
            {#each d.matchup_stats as m}
              <div class="matchup-row">
                <div class="matchup-arch">{m.opponent_arch}</div>
                <div class="matchup-wld">
                  <span style="color:#22c55e">{m.wins}V</span>
                  <span class="wld-sep">/</span>
                  <span style="color:#f59e0b">{m.draws}N</span>
                  <span class="wld-sep">/</span>
                  <span style="color:#ef4444">{m.losses}D</span>
                </div>
                <div class="matchup-bar-wrap">
                  <div class="matchup-bar-track">
                    <div class="matchup-bar" style={wrBar(m.win_rate) + ';background:' + wrColor(m.win_rate)}></div>
                  </div>
                  <span class="matchup-wr" style="color:{wrColor(m.win_rate)}">
                    {Math.round(m.win_rate * 100)}%
                  </span>
                </div>
                <span class="matchup-total">{m.total} match{m.total > 1 ? 's' : ''}</span>
              </div>
            {/each}
          </div>
        </section>
      {/if}

      <!-- Recent results -->
      {#if d.recent_results.length > 0}
        <section class="section-card">
          <h2 class="section-title">Historique récent</h2>
          <div class="history-list">
            {#each d.recent_results as r}
              <div class="history-row">
                <span class="hist-result" style="color:{resultColor(r.result)}">{resultLabel(r.result)}</span>
                <span class="hist-arch">vs {r.opponent_arch}</span>
                {#if r.event_date}
                  <span class="hist-date">{formatDate(r.event_date)}</span>
                {:else}
                  <span class="hist-date">{formatDate(r.created_at)}</span>
                {/if}
                {#if r.notes}
                  <span class="hist-notes" title={r.notes}>— {r.notes.slice(0, 40)}{r.notes.length > 40 ? '…' : ''}</span>
                {/if}
                <button class="delete-btn" title="Supprimer" onclick={() => deleteResult(r.id)}>×</button>
              </div>
            {/each}
          </div>
        </section>
      {:else if d.total_matches === 0}
        <div class="empty-state">
          <div class="empty-icon">◎</div>
          <p>Aucun match enregistré pour ce deck.</p>
          <p class="empty-hint">Utilisez le formulaire pour logger vos résultats de tournoi.</p>
        </div>
      {/if}

    </div>
  </div>
</div>

<style>
  .page {
    max-width: 1000px;
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
  .arch-badge {
    background: #1e293b; border: 1px solid #334155;
    border-radius: 20px; padding: 0.2rem 0.6rem;
    font-size: 0.75rem; color: #94a3b8;
  }

  .layout {
    display: grid;
    grid-template-columns: 260px 1fr;
    gap: 1rem;
    align-items: start;
  }
  @media (max-width: 680px) { .layout { grid-template-columns: 1fr; } }

  /* Left column */
  .left-col { display: flex; flex-direction: column; gap: 0.75rem; position: sticky; top: 1rem; }

  .overall-card, .form-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 1.125rem;
  }

  .overall-title { font-size: 0.75rem; color: #475569; margin-bottom: 0.5rem; }
  .overall-wld {
    display: flex;
    align-items: baseline;
    gap: 0.3rem;
    font-size: 1.5rem;
    font-weight: 800;
    margin-bottom: 0.1rem;
  }
  .wld-sep { color: #334155; font-weight: 400; font-size: 1rem; }
  .overall-total { font-size: 0.72rem; color: #475569; margin-bottom: 0.6rem; }

  .wr-row { display: flex; align-items: center; gap: 0.5rem; }
  .wr-bar-track { flex: 1; height: 6px; background: #1e293b; border-radius: 3px; overflow: hidden; }
  .wr-bar { height: 100%; border-radius: 3px; transition: width 0.4s; }
  .wr-pct { font-size: 0.8rem; font-weight: 700; width: 36px; text-align: right; }

  .form-title { font-size: 0.9rem; font-weight: 700; margin-bottom: 0.75rem; }
  .field-label { display: block; font-size: 0.75rem; color: #64748b; margin-bottom: 0.25rem; }
  .opt { color: #334155; }
  .field-input, .field-textarea {
    width: 100%;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #e2e8f0;
    font-size: 0.82rem;
    padding: 0.4rem 0.6rem;
    box-sizing: border-box;
  }
  .field-input:focus, .field-textarea:focus { outline: none; border-color: #a855f7; }
  .field-textarea { resize: vertical; font-family: inherit; }

  .result-btns { display: flex; gap: 0.4rem; }
  .result-btn {
    flex: 1;
    padding: 0.45rem;
    border-radius: 6px;
    border: 1px solid #334155;
    background: #1e293b;
    color: #475569;
    font-size: 1rem;
    font-weight: 800;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s, background 0.15s;
  }
  .result-btn:hover { border-color: var(--rc); color: var(--rc); }
  .result-btn.active { border-color: var(--rc); color: var(--rc); background: color-mix(in srgb, var(--rc) 12%, transparent); }

  .form-error { font-size: 0.78rem; color: #ef4444; margin-top: 0.5rem; }

  .btn-submit {
    width: 100%;
    margin-top: 0.875rem;
    padding: 0.55rem;
    border-radius: 8px;
    border: none;
    background: #a855f7;
    color: white;
    font-size: 0.875rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.15s;
  }
  .btn-submit:hover:not(:disabled) { background: #9333ea; }
  .btn-submit:disabled { opacity: 0.4; cursor: not-allowed; }

  .matrix-link {
    display: block;
    text-align: center;
    padding: 0.6rem;
    border: 1px dashed #334155;
    border-radius: 8px;
    font-size: 0.8rem;
    color: #475569;
    text-decoration: none;
    transition: color 0.15s, border-color 0.15s;
  }
  .matrix-link:hover { color: #94a3b8; border-color: #475569; }

  /* Right column */
  .right-col { display: flex; flex-direction: column; gap: 0.75rem; }

  .section-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 1rem;
  }
  .section-title { font-size: 0.95rem; font-weight: 700; margin: 0 0 0.75rem; }

  /* Per-matchup stats */
  .matchup-list { display: flex; flex-direction: column; gap: 0.4rem; }
  .matchup-row {
    display: grid;
    grid-template-columns: 1fr auto 200px auto;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0.625rem;
    border-radius: 8px;
    background: #0a1628;
  }
  @media (max-width: 580px) {
    .matchup-row { grid-template-columns: 1fr auto; }
    .matchup-bar-wrap, .matchup-total { display: none; }
  }
  .matchup-arch { font-size: 0.875rem; font-weight: 600; }
  .matchup-wld { font-size: 0.78rem; display: flex; gap: 0.2rem; white-space: nowrap; }
  .matchup-bar-wrap { display: flex; align-items: center; gap: 0.4rem; }
  .matchup-bar-track { flex: 1; height: 6px; background: #1e293b; border-radius: 3px; overflow: hidden; }
  .matchup-bar { height: 100%; border-radius: 3px; transition: width 0.4s; }
  .matchup-wr { font-size: 0.78rem; font-weight: 700; width: 34px; text-align: right; }
  .matchup-total { font-size: 0.7rem; color: #475569; white-space: nowrap; }

  /* History */
  .history-list { display: flex; flex-direction: column; gap: 0.35rem; }
  .history-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.5rem;
    border-radius: 6px;
    font-size: 0.8rem;
    background: #0a1628;
    flex-wrap: wrap;
  }
  .hist-result { font-weight: 700; flex-shrink: 0; }
  .hist-arch { flex: 1; min-width: 0; color: #e2e8f0; }
  .hist-date { color: #475569; font-size: 0.72rem; flex-shrink: 0; }
  .hist-notes { color: #64748b; font-size: 0.72rem; flex: 2; min-width: 0; }
  .delete-btn {
    background: none; border: none;
    color: #334155; cursor: pointer; font-size: 0.9rem;
    padding: 0; line-height: 1; flex-shrink: 0;
  }
  .delete-btn:hover { color: #ef4444; }

  /* Empty */
  .empty-state {
    text-align: center;
    padding: 3rem 1rem;
    background: #0f172a;
    border: 1px dashed #1e293b;
    border-radius: 14px;
  }
  .empty-icon { font-size: 2rem; color: #334155; margin-bottom: 0.75rem; }
  .empty-state p { color: #475569; font-size: 0.875rem; margin: 0 0 0.35rem; }
  .empty-hint { font-size: 0.78rem !important; color: #334155 !important; }
</style>
