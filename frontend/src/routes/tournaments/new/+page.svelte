<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { auth } from '$lib/stores/auth';

  interface DeckOption {
    id: number;
    title: string;
    archetype_label: string | null;
  }

  interface ResultData {
    tournament: { id: number; name: string; event_date: string | null; format: string | null };
    player: { id: number; display_name: string; country: string | null };
    deck_id: number;
    submission_id: number;
    placement: number;
  }

  // ── Deck selector ───────────────────────────────────────────────────────────
  let decks: DeckOption[] = $state([]);
  let deckQuery: string = $state('');
  let selectedDeckId: number | null = $state(null);
  let showDropdown: boolean = $state(false);

  let filteredDecks: DeckOption[] = $derived(
    deckQuery.length === 0
      ? decks.slice(0, 12)
      : decks.filter(d => d.title.toLowerCase().includes(deckQuery.toLowerCase())).slice(0, 12)
  );

  function selectDeck(deck: DeckOption) {
    selectedDeckId = deck.id;
    deckQuery = deck.title;
    showDropdown = false;
  }

  function clearDeck() {
    selectedDeckId = null;
    deckQuery = '';
    showDropdown = false;
  }

  // ── Tournament fields ───────────────────────────────────────────────────────
  let tournamentName: string = $state('');
  let tournamentDate: string = $state('');
  let tournamentFormat: string = $state('TCG');
  let tournamentLocation: string = $state('');
  let tournamentParticipants: string = $state('');

  // ── Player fields ────────────────────────────────────────────────────────────
  let playerName: string = $state('');
  let playerCountry: string = $state('');

  // ── Result fields ────────────────────────────────────────────────────────────
  let placement: string = $state('');
  let wins: string = $state('');
  let losses: string = $state('');
  let draws: string = $state('');

  // ── State machine ────────────────────────────────────────────────────────────
  type Phase = 'idle' | 'loading' | 'success' | 'error';
  let phase: Phase = $state('idle');
  let result: ResultData | null = $state(null);
  let errorMsg: string = $state('');

  let isValid: boolean = $derived(
    !!selectedDeckId &&
    tournamentName.trim().length > 0 &&
    tournamentDate.length > 0 &&
    playerName.trim().length > 0 &&
    placement.trim().length > 0 &&
    parseInt(placement, 10) >= 1
  );

  // ── Helpers ──────────────────────────────────────────────────────────────────
  function ordinal(n: number): string {
    if (n >= 11 && n <= 13) return `${n}th`;
    const suffixes = ['th', 'st', 'nd', 'rd'];
    return `${n}${suffixes[n % 10] ?? 'th'}`;
  }

  function formatDate(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso + 'T00:00:00').toLocaleDateString('en-US', {
      year: 'numeric', month: 'long', day: 'numeric',
    });
  }

  // Track which tournament we're adding to (for back link)
  let fromTournamentId: number | null = $state(null);

  // ── Lifecycle ────────────────────────────────────────────────────────────────
  onMount(async () => {
    const res = await fetch('/api/v1/decks?limit=200&page=1');
    if (res.ok) {
      const body = await res.json();
      decks = body.items ?? [];
    }

    const params = new URLSearchParams(window.location.search);

    // Pre-fill deck from URL ?deck_id=N
    const rawDeckId = params.get('deck_id');
    if (rawDeckId) {
      const id = parseInt(rawDeckId, 10);
      if (!isNaN(id)) {
        const found = decks.find(d => d.id === id);
        if (found) { selectedDeckId = id; deckQuery = found.title; }
      }
    }

    // Pre-fill tournament fields from URL ?tournament_id=N
    const rawTId = params.get('tournament_id');
    if (rawTId) {
      const tid = parseInt(rawTId, 10);
      if (!isNaN(tid)) {
        fromTournamentId = tid;
        try {
          const tRes = await fetch(`/api/v1/tournaments/${tid}`);
          if (tRes.ok) {
            const t = await tRes.json();
            tournamentName = t.name ?? '';
            tournamentDate = t.event_date ?? '';
            tournamentFormat = t.format ?? 'TCG';
            tournamentLocation = t.location ?? '';
            tournamentParticipants = t.participants_count ? String(t.participants_count) : '';
          }
        } catch { /* ignore */ }
      }
    }
  });

  // ── Submit ───────────────────────────────────────────────────────────────────
  async function submit() {
    if (!isValid) return;
    phase = 'loading';

    try {
      const res = await fetch('/api/v1/tournaments/submit-result', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deck_id: selectedDeckId,
          tournament_name: tournamentName.trim(),
          tournament_date: tournamentDate,
          tournament_format: tournamentFormat,
          tournament_location: tournamentLocation.trim() || null,
          tournament_participants: tournamentParticipants ? parseInt(tournamentParticipants, 10) : null,
          player_name: playerName.trim(),
          player_country: playerCountry.trim() || null,
          placement: parseInt(placement, 10),
          wins: wins ? parseInt(wins, 10) : null,
          losses: losses ? parseInt(losses, 10) : null,
          draws: draws ? parseInt(draws, 10) : null,
        }),
      });
      const body = await res.json();
      if (!res.ok) {
        if (res.status === 401) { goto('/login'); return; }
        errorMsg = body.detail ?? 'Failed to submit result';
        phase = 'error';
        return;
      }
      result = body as ResultData;
      phase = 'success';
    } catch {
      errorMsg = 'Network error — is the server running?';
      phase = 'error';
    }
  }

  function reset() {
    phase = 'idle';
    result = null;
    errorMsg = '';
    selectedDeckId = null;
    deckQuery = '';
    tournamentName = '';
    tournamentDate = '';
    tournamentFormat = 'TCG';
    tournamentLocation = '';
    tournamentParticipants = '';
    playerName = '';
    playerCountry = '';
    placement = '';
    wins = '';
    losses = '';
    draws = '';
  }
</script>

<svelte:head>
  <title>Log tournament result — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <header class="page-header">
    <div>
      <span class="label">Tournaments</span>
      <h1 class="page-title">Log result</h1>
    </div>
    {#if fromTournamentId}
      <a href="/tournaments/{fromTournamentId}" class="btn-ghost">← Back to tournament</a>
    {:else}
      <a href="/tournaments" class="btn-ghost">← Tournaments</a>
    {/if}
  </header>

  {#if $auth.loaded && $auth.enabled && !$auth.user}
    <div class="auth-guard">
      <span class="auth-guard-icon" aria-hidden="true">⚿</span>
      <div>
        <p class="auth-guard-title">Login required</p>
        <p class="auth-guard-sub">You must be logged in to log tournament results.</p>
      </div>
      <a href="/login" class="btn-primary" style="flex-shrink:0;font-size:.875rem;padding:.5rem 1rem">Login →</a>
    </div>
  {/if}

  {#if phase === 'success' && result}
    <div class="result-card">
      <div class="result-icon success-icon" aria-hidden="true">✓</div>
      <h2 class="result-title">Result logged</h2>

      <div class="result-placement-badge">
        <span class="result-placement-num">{ordinal(result.placement)}</span>
        <span class="result-placement-label">Place</span>
      </div>

      <div class="result-meta">
        <div class="meta-row">
          <span class="meta-key">Tournament</span>
          <span class="meta-val">{result.tournament.name}</span>
        </div>
        <div class="meta-row">
          <span class="meta-key">Date</span>
          <span class="meta-val">{formatDate(result.tournament.event_date)}</span>
        </div>
        {#if result.tournament.format}
          <div class="meta-row">
            <span class="meta-key">Format</span>
            <span class="meta-val">{result.tournament.format}</span>
          </div>
        {/if}
        <div class="meta-row">
          <span class="meta-key">Player</span>
          <span class="meta-val">
            {result.player.display_name}{result.player.country ? ` · ${result.player.country}` : ''}
          </span>
        </div>
      </div>

      <div class="result-actions">
        <a href="/decks/{result.deck_id}" class="btn-primary">View deck →</a>
        {#if fromTournamentId}
          <a href="/tournaments/{fromTournamentId}" class="btn-ghost">View tournament</a>
        {/if}
        <button class="btn-ghost" onclick={reset}>Log another</button>
      </div>
    </div>

  {:else if phase === 'error'}
    <div class="result-card error-card">
      <div class="result-icon error-icon" aria-hidden="true">✕</div>
      <h2 class="result-title">Submission failed</h2>
      <p class="error-message">{errorMsg}</p>
      <button class="btn-ghost" onclick={() => { phase = 'idle'; errorMsg = ''; }}>Try again</button>
    </div>

  {:else}
    <form class="form-layout" onsubmit={(e) => { e.preventDefault(); submit(); }}>

      <!-- ── Deck ─────────────────────────────────────────────────────────── -->
      <section class="form-section card">
        <h2 class="form-section-title">◫ Deck</h2>

        <div class="field">
          <label class="field-label" for="deck-search">Select deck</label>
          <div class="deck-combobox">
            <input
              id="deck-search"
              type="text"
              class="field-input"
              class:selected={!!selectedDeckId}
              placeholder="Search by title…"
              bind:value={deckQuery}
              onfocus={() => (showDropdown = true)}
              onblur={() => setTimeout(() => (showDropdown = false), 150)}
              oninput={() => { selectedDeckId = null; showDropdown = true; }}
              autocomplete="off"
              spellcheck="false"
              disabled={phase === 'loading'}
            />
            {#if selectedDeckId}
              <button
                type="button"
                class="deck-clear"
                onclick={clearDeck}
                aria-label="Clear deck selection"
                tabindex="-1"
              >✕</button>
            {/if}
            {#if showDropdown && filteredDecks.length > 0}
              <ul class="deck-dropdown" role="listbox">
                {#each filteredDecks as deck}
                  <li
                    role="option"
                    aria-selected={deck.id === selectedDeckId}
                    class="deck-option"
                    class:deck-option-active={deck.id === selectedDeckId}
                    onmousedown={(e) => { e.preventDefault(); selectDeck(deck); }}
                  >
                    <span class="deck-option-title">{deck.title}</span>
                    {#if deck.archetype_label}
                      <span class="deck-option-arch">{deck.archetype_label}</span>
                    {/if}
                  </li>
                {/each}
              </ul>
            {:else if showDropdown && deckQuery.length > 0 && filteredDecks.length === 0}
              <div class="deck-dropdown deck-no-match">No decks match "{deckQuery}"</div>
            {/if}
          </div>
          {#if selectedDeckId}
            <span class="field-hint field-hint-ok">✓ Deck selected (ID {selectedDeckId})</span>
          {:else}
            <span class="field-hint">Start typing to search your imported decks</span>
          {/if}
        </div>
      </section>

      <!-- ── Tournament ────────────────────────────────────────────────────── -->
      <section class="form-section card">
        <h2 class="form-section-title">⊞ Tournament</h2>

        <div class="field">
          <label class="field-label" for="t-name">Tournament name</label>
          <input
            id="t-name"
            type="text"
            class="field-input"
            placeholder="e.g. YCS Las Vegas 2025"
            bind:value={tournamentName}
            required
            disabled={phase === 'loading'}
          />
        </div>

        <div class="field-grid-2">
          <div class="field">
            <label class="field-label" for="t-date">Date</label>
            <input
              id="t-date"
              type="date"
              class="field-input"
              bind:value={tournamentDate}
              required
              disabled={phase === 'loading'}
            />
          </div>
          <div class="field">
            <label class="field-label" for="t-format">Format</label>
            <select
              id="t-format"
              class="field-input field-select"
              bind:value={tournamentFormat}
              disabled={phase === 'loading'}
            >
              <option value="TCG">TCG</option>
              <option value="OCG">OCG</option>
              <option value="Speed Duel">Speed Duel</option>
              <option value="Master Duel">Master Duel</option>
              <option value="Goat">Goat Format</option>
              <option value="Edison">Edison Format</option>
              <option value="Other">Other</option>
            </select>
          </div>
        </div>

        <div class="field-grid-2">
          <div class="field">
            <label class="field-label" for="t-location">Location <span class="optional">(optional)</span></label>
            <input
              id="t-location"
              type="text"
              class="field-input"
              placeholder="e.g. Las Vegas, NV"
              bind:value={tournamentLocation}
              disabled={phase === 'loading'}
            />
          </div>
          <div class="field">
            <label class="field-label" for="t-participants">Participants <span class="optional">(optional)</span></label>
            <input
              id="t-participants"
              type="number"
              class="field-input"
              placeholder="e.g. 512"
              min="2"
              bind:value={tournamentParticipants}
              disabled={phase === 'loading'}
            />
          </div>
        </div>
      </section>

      <!-- ── Player ────────────────────────────────────────────────────────── -->
      <section class="form-section card">
        <h2 class="form-section-title">◎ Player</h2>

        <div class="field-grid-2">
          <div class="field">
            <label class="field-label" for="p-name">Player name</label>
            <input
              id="p-name"
              type="text"
              class="field-input"
              placeholder="e.g. John Doe"
              bind:value={playerName}
              required
              disabled={phase === 'loading'}
            />
            <span class="field-hint">A new profile is created automatically if the name is new</span>
          </div>
          <div class="field">
            <label class="field-label" for="p-country">Country <span class="optional">(optional)</span></label>
            <input
              id="p-country"
              type="text"
              class="field-input"
              placeholder="e.g. US"
              maxlength="100"
              bind:value={playerCountry}
              disabled={phase === 'loading'}
            />
          </div>
        </div>
      </section>

      <!-- ── Result ────────────────────────────────────────────────────────── -->
      <section class="form-section card">
        <h2 class="form-section-title">⊛ Result</h2>

        <div class="field-grid-4">
          <div class="field">
            <label class="field-label" for="r-placement">Placement</label>
            <input
              id="r-placement"
              type="number"
              class="field-input"
              placeholder="1"
              min="1"
              bind:value={placement}
              required
              disabled={phase === 'loading'}
            />
            <span class="field-hint">1 = 1st, 2 = 2nd…</span>
          </div>
          <div class="field">
            <label class="field-label" for="r-wins">Wins <span class="optional">(opt)</span></label>
            <input
              id="r-wins"
              type="number"
              class="field-input"
              placeholder="—"
              min="0"
              bind:value={wins}
              disabled={phase === 'loading'}
            />
          </div>
          <div class="field">
            <label class="field-label" for="r-losses">Losses <span class="optional">(opt)</span></label>
            <input
              id="r-losses"
              type="number"
              class="field-input"
              placeholder="—"
              min="0"
              bind:value={losses}
              disabled={phase === 'loading'}
            />
          </div>
          <div class="field">
            <label class="field-label" for="r-draws">Draws <span class="optional">(opt)</span></label>
            <input
              id="r-draws"
              type="number"
              class="field-input"
              placeholder="—"
              min="0"
              bind:value={draws}
              disabled={phase === 'loading'}
            />
          </div>
        </div>
      </section>

      <button
        type="submit"
        class="btn-primary submit-btn"
        disabled={!isValid || phase === 'loading'}
      >
        {#if phase === 'loading'}
          <span class="spinner" aria-hidden="true"></span>
          Submitting…
        {:else}
          Log result ↑
        {/if}
      </button>
    </form>
  {/if}
</div>

<style>
  .page-body {
    padding-top: 3rem;
    padding-bottom: 5rem;
    max-width: 680px;
  }

  .page-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1.5rem;
    margin-bottom: 2.5rem;
    flex-wrap: wrap;
  }

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    margin-top: 0.375rem;
  }

  .auth-guard {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 1.25rem;
    margin-bottom: 2rem;
    background: rgba(201, 164, 73, 0.05);
    border: 1px solid rgba(201, 164, 73, 0.2);
    border-radius: var(--radius-md);
    flex-wrap: wrap;
  }

  .auth-guard-icon { font-size: 1.25rem; color: var(--gold); opacity: 0.7; }
  .auth-guard-title { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.125rem; }
  .auth-guard-sub { font-size: 0.8125rem; color: var(--text-tertiary); }

  /* ── Form layout ─────────────────────────────────────────────────────────── */
  .form-layout {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .form-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1.25rem 1.5rem;
  }

  .form-section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8125rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 0.25rem;
  }

  /* ── Fields ──────────────────────────────────────────────────────────────── */
  .field {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .field-label {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .optional {
    font-weight: 400;
    color: var(--text-tertiary);
    font-size: 0.75rem;
  }

  .field-input {
    width: 100%;
    padding: 0.625rem 0.875rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.9375rem;
    transition:
      border-color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
    outline: none;
  }

  .field-input.selected {
    border-color: var(--gold);
  }

  .field-input::placeholder { color: var(--text-tertiary); }

  .field-input:focus {
    border-color: var(--gold);
    box-shadow: 0 0 0 3px rgba(201, 164, 73, 0.12);
  }

  .field-input:disabled { opacity: 0.5; cursor: not-allowed; }

  .field-select {
    cursor: pointer;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23888' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 0.875rem center;
    padding-right: 2.25rem;
  }

  .field-hint {
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  .field-hint-ok { color: var(--success); }

  .field-grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.875rem;
  }

  .field-grid-4 {
    display: grid;
    grid-template-columns: 1.5fr 1fr 1fr 1fr;
    gap: 0.875rem;
  }

  @media (max-width: 520px) {
    .field-grid-2 { grid-template-columns: 1fr; }
    .field-grid-4 { grid-template-columns: 1fr 1fr; }
  }

  /* ── Deck combobox ───────────────────────────────────────────────────────── */
  .deck-combobox {
    position: relative;
  }

  .deck-clear {
    position: absolute;
    right: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    background: transparent;
    border: none;
    color: var(--text-tertiary);
    font-size: 0.75rem;
    cursor: pointer;
    padding: 0.25rem;
    line-height: 1;
    transition: color var(--duration-fast) var(--ease-out);
  }

  .deck-clear:hover { color: var(--text-primary); }

  .deck-dropdown {
    position: absolute;
    z-index: 50;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    max-height: 240px;
    overflow-y: auto;
    list-style: none;
    margin: 0;
    padding: 0.25rem;
  }

  .deck-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.5rem 0.75rem;
    border-radius: calc(var(--radius-md) - 2px);
    cursor: pointer;
    transition: background var(--duration-fast) var(--ease-out);
  }

  .deck-option:hover,
  .deck-option-active {
    background: var(--bg-elevated);
  }

  .deck-option-title {
    font-size: 0.875rem;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 1;
    min-width: 0;
  }

  .deck-option-arch {
    font-size: 0.6875rem;
    color: var(--text-tertiary);
    white-space: nowrap;
    flex-shrink: 0;
    background: var(--bg-elevated);
    padding: 0.1rem 0.4rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-subtle);
  }

  .deck-no-match {
    padding: 0.75rem;
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    text-align: center;
  }

  /* ── Submit ──────────────────────────────────────────────────────────────── */
  .submit-btn {
    width: 100%;
    justify-content: center;
    padding: 0.75rem;
    font-size: 0.9375rem;
  }

  .submit-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
    transform: none !important;
    box-shadow: none !important;
  }

  .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(0, 0, 0, 0.3);
    border-top-color: #000;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
    margin-right: 0.25rem;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Result card ─────────────────────────────────────────────────────────── */
  .result-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 1rem;
    padding: 3rem 2rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
  }

  .result-icon {
    width: 52px;
    height: 52px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.375rem;
    font-weight: 700;
  }

  .success-icon {
    background: rgba(74, 186, 122, 0.12);
    color: var(--success);
    border: 1px solid rgba(74, 186, 122, 0.25);
  }

  .error-icon {
    background: rgba(224, 84, 84, 0.12);
    color: var(--error);
    border: 1px solid rgba(224, 84, 84, 0.25);
  }

  .result-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-primary);
    font-family: 'Space Grotesk', sans-serif;
  }

  .result-placement-badge {
    display: flex;
    flex-direction: column;
    align-items: center;
    background: var(--gold-dim);
    border: 1px solid rgba(201, 164, 73, 0.3);
    border-radius: var(--radius-md);
    padding: 0.625rem 1.5rem;
  }

  .result-placement-num {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: var(--gold);
    line-height: 1;
  }

  .result-placement-label {
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-top: 0.2rem;
  }

  .result-meta {
    align-self: stretch;
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 0.875rem 1rem;
    text-align: left;
  }

  .meta-row {
    display: flex;
    align-items: baseline;
    gap: 0.625rem;
  }

  .meta-key {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-tertiary);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    min-width: 80px;
    flex-shrink: 0;
  }

  .meta-val {
    font-size: 0.875rem;
    color: var(--text-primary);
  }

  .result-actions {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    justify-content: center;
  }

  .error-card { border-color: rgba(224, 84, 84, 0.2); }

  .error-message {
    font-size: 0.9rem;
    color: var(--text-secondary);
    max-width: 36ch;
  }
</style>
