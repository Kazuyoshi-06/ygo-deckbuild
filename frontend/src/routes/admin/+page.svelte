<script lang="ts">
  import { onDestroy, untrack } from 'svelte';
  import { auth } from '$lib/stores/auth';

  interface SyncRun {
    id: number;
    sync_type: string;
    status: string;
    started_at: string;
    finished_at: string | null;
    summary_json: Record<string, unknown> | null;
    error_log: string | null;
  }

  let { data } = $props<{ data: { recentRuns: SyncRun[] } }>();

  let runs: SyncRun[] = $state(untrack(() => data.recentRuns));

  // Last run per type
  let lastCardRun    = $derived(runs.find(r => r.sync_type === 'cards')   ?? null);
  let lastBanlistRun = $derived(runs.find(r => r.sync_type === 'banlist') ?? null);
  let lastCdbRun     = $derived(runs.find(r => r.sync_type === 'cdb')     ?? null);

  // Poll state per sync type
  let cardPollId:    number | null = $state(null);
  let banlistPollId: number | null = $state(null);
  let cdbPollId:     number | null = $state(null);
  let cardTriggering    = $state(false);
  let banlistTriggering = $state(false);
  let cdbTriggering     = $state(false);

  // CDB path form — user provides one or more local .cdb file paths
  let cdbPaths: string[] = $state(['']);

  let cardPollTimer:    ReturnType<typeof setInterval> | null = null;
  let banlistPollTimer: ReturnType<typeof setInterval> | null = null;
  let cdbPollTimer:     ReturnType<typeof setInterval> | null = null;

  onDestroy(() => {
    if (cardPollTimer)    clearInterval(cardPollTimer);
    if (banlistPollTimer) clearInterval(banlistPollTimer);
    if (cdbPollTimer)     clearInterval(cdbPollTimer);
  });

  async function pollRun(id: number, type: 'cards' | 'banlist' | 'cdb') {
    try {
      const res = await fetch(`/api/v1/admin/sync/runs/${id}`);
      if (!res.ok) return;
      const run: SyncRun = await res.json();

      const idx = runs.findIndex(r => r.id === id);
      if (idx !== -1) runs[idx] = run;
      else runs = [run, ...runs];

      if (run.status !== 'running') {
        if (type === 'cards') {
          cardPollId = null;
          if (cardPollTimer) { clearInterval(cardPollTimer); cardPollTimer = null; }
        } else if (type === 'banlist') {
          banlistPollId = null;
          if (banlistPollTimer) { clearInterval(banlistPollTimer); banlistPollTimer = null; }
        } else {
          cdbPollId = null;
          if (cdbPollTimer) { clearInterval(cdbPollTimer); cdbPollTimer = null; }
        }
      }
    } catch { /* swallow */ }
  }

  function startPolling(runId: number, type: 'cards' | 'banlist' | 'cdb') {
    if (type === 'cards') {
      if (cardPollTimer) clearInterval(cardPollTimer);
      cardPollId = runId;
      cardPollTimer = setInterval(() => pollRun(runId, 'cards'), 2000);
    } else if (type === 'banlist') {
      if (banlistPollTimer) clearInterval(banlistPollTimer);
      banlistPollId = runId;
      banlistPollTimer = setInterval(() => pollRun(runId, 'banlist'), 2000);
    } else {
      if (cdbPollTimer) clearInterval(cdbPollTimer);
      cdbPollId = runId;
      cdbPollTimer = setInterval(() => pollRun(runId, 'cdb'), 2000);
    }
  }

  async function triggerSync(type: 'cards' | 'banlist') {
    if (type === 'cards') cardTriggering = true;
    else banlistTriggering = true;
    try {
      const res = await fetch(`/api/v1/admin/sync/${type}`, { method: 'POST' });
      if (!res.ok) {
        if (res.status === 401) { window.location.href = '/login'; return; }
        return;
      }
      const run: SyncRun = await res.json();
      runs = [run, ...runs];
      startPolling(run.id, type);
    } catch { /* silent */ }
    finally {
      if (type === 'cards') cardTriggering = false;
      else banlistTriggering = false;
    }
  }

  async function triggerCdbSync() {
    cdbTriggering = true;
    const paths = cdbPaths.map(p => p.trim()).filter(Boolean);
    try {
      const res = await fetch('/api/v1/admin/sync/cards/cdb', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(paths),
      });
      if (!res.ok) {
        if (res.status === 401) { window.location.href = '/login'; return; }
        return;
      }
      const run: SyncRun = await res.json();
      runs = [run, ...runs];
      startPolling(run.id, 'cdb');
    } catch { /* silent */ }
    finally {
      cdbTriggering = false;
    }
  }

  function addCdbPath() { cdbPaths = [...cdbPaths, '']; }

  function removeCdbPath(i: number) {
    if (cdbPaths.length === 1) { cdbPaths = ['']; return; }
    cdbPaths = cdbPaths.filter((_, idx) => idx !== i);
  }

  // Sources used in last successful CDB sync
  const lastCdbSources: string[] = $derived((() => {
    const s = lastCdbRun?.summary_json;
    if (!s || !Array.isArray(s.sources)) return [];
    return s.sources as string[];
  })());

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  }

  function formatDuration(start: string, end: string | null): string {
    if (!end) return '—';
    const ms = new Date(end).getTime() - new Date(start).getTime();
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
  }

  function summaryLabel(run: SyncRun): string {
    const s = run.summary_json;
    if (!s) return '';
    if (run.sync_type === 'cards' && typeof s.upserted === 'number') {
      return `${(s.upserted as number).toLocaleString('en-US')} cards`;
    }
    if (run.sync_type === 'banlist' && typeof s.entries === 'number') {
      return `${s.entries} entries`;
    }
    if (run.sync_type === 'cdb' && typeof s.new_inserted === 'number') {
      const pre = typeof s.prerelease_count === 'number' && (s.prerelease_count as number) > 0
        ? ` · ${s.prerelease_count} pre-release`
        : '';
      return `${s.new_inserted} new${pre}`;
    }
    return '';
  }

  const isCardRunning    = $derived(lastCardRun?.status    === 'running' || cardPollId    !== null);
  const isBanlistRunning = $derived(lastBanlistRun?.status === 'running' || banlistPollId !== null);
  const isCdbRunning     = $derived(lastCdbRun?.status     === 'running' || cdbPollId     !== null);
</script>

<svelte:head>
  <title>Admin — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <header class="page-header">
    <div>
      <span class="label">System</span>
      <h1 class="page-title">Admin Panel</h1>
    </div>
    <a href="/decks" class="btn-ghost">← Back to decks</a>
  </header>

  {#if $auth.loaded && $auth.enabled && !$auth.user}
    <div class="auth-guard">
      <span class="auth-guard-icon" aria-hidden="true">⚿</span>
      <div class="auth-guard-text">
        <p class="auth-guard-title">Admin access requires authentication</p>
        <p class="auth-guard-sub">Sync and write operations will fail until you log in.</p>
      </div>
      <a href="/login" class="btn-primary auth-guard-btn">Login →</a>
    </div>
  {/if}

  <!-- Top row: Card catalog + Banlist -->
  <div class="sync-grid">

    <!-- Card catalog -->
    <div class="sync-card">
      <div class="sync-card-top">
        <div class="sync-icon-wrap" aria-hidden="true">◈</div>
        <div class="sync-card-info">
          <h2 class="sync-card-title">Card Catalog</h2>
          <p class="sync-card-desc">Sync all cards and metadata from YGOProDeck</p>
        </div>
      </div>

      <div class="sync-status-row">
        {#if !lastCardRun}
          <span class="status-pill status-never">Never synced</span>
        {:else if lastCardRun.status === 'running'}
          <span class="status-pill status-running">
            <span class="status-dot running-dot" aria-hidden="true"></span>
            Running…
          </span>
        {:else if lastCardRun.status === 'completed'}
          <span class="status-pill status-ok">Completed</span>
          {#if summaryLabel(lastCardRun)}<span class="status-detail">{summaryLabel(lastCardRun)}</span>{/if}
          <span class="status-date">{formatDate(lastCardRun.started_at)}</span>
        {:else}
          <span class="status-pill status-error">Failed</span>
          <span class="status-date">{formatDate(lastCardRun.started_at)}</span>
        {/if}
      </div>

      {#if lastCardRun?.error_log}
        <pre class="error-log">{lastCardRun.error_log}</pre>
      {/if}

      <button
        class="btn-primary sync-btn"
        onclick={() => triggerSync('cards')}
        disabled={isCardRunning || cardTriggering}
        aria-busy={isCardRunning}
      >
        {#if isCardRunning || cardTriggering}
          <span class="spinner" aria-hidden="true"></span>
          Syncing cards…
        {:else}
          Sync card catalog
        {/if}
      </button>
    </div>

    <!-- Banlist -->
    <div class="sync-card">
      <div class="sync-card-top">
        <div class="sync-icon-wrap" aria-hidden="true">⊘</div>
        <div class="sync-card-info">
          <h2 class="sync-card-title">Banlist</h2>
          <p class="sync-card-desc">Sync current TCG &amp; OCG forbidden/limited lists</p>
        </div>
      </div>

      <div class="sync-status-row">
        {#if !lastBanlistRun}
          <span class="status-pill status-never">Never synced</span>
        {:else if lastBanlistRun.status === 'running'}
          <span class="status-pill status-running">
            <span class="status-dot running-dot" aria-hidden="true"></span>
            Running…
          </span>
        {:else if lastBanlistRun.status === 'completed'}
          <span class="status-pill status-ok">Completed</span>
          {#if summaryLabel(lastBanlistRun)}<span class="status-detail">{summaryLabel(lastBanlistRun)}</span>{/if}
          <span class="status-date">{formatDate(lastBanlistRun.started_at)}</span>
        {:else}
          <span class="status-pill status-error">Failed</span>
          <span class="status-date">{formatDate(lastBanlistRun.started_at)}</span>
        {/if}
      </div>

      {#if lastBanlistRun?.error_log}
        <pre class="error-log">{lastBanlistRun.error_log}</pre>
      {/if}

      <button
        class="btn-primary sync-btn"
        onclick={() => triggerSync('banlist')}
        disabled={isBanlistRunning || banlistTriggering}
        aria-busy={isBanlistRunning}
      >
        {#if isBanlistRunning || banlistTriggering}
          <span class="spinner" aria-hidden="true"></span>
          Syncing banlist…
        {:else}
          Sync banlists
        {/if}
      </button>
    </div>

  </div><!-- /sync-grid -->

  <!-- Full-width CDB card -->
  <div class="sync-card sync-card--cdb">
    <div class="cdb-top-row">
      <div class="sync-card-top">
        <div class="sync-icon-wrap" aria-hidden="true">◉</div>
        <div class="sync-card-info">
          <h2 class="sync-card-title">EdoPro — OCG Pre-release</h2>
          <p class="sync-card-desc">
            Sync OCG-exclusive and pre-release cards from local EdoPro <code class="inline-code">.cdb</code> files.
            Supports merging base + delta + pre-release CDB files in order.
            Includes OCG exclusives and pre-release cards — Rush Duel and anime cards are automatically filtered.
          </p>
        </div>
      </div>

      <div class="cdb-status-col">
        <div class="sync-status-row">
          {#if !lastCdbRun}
            <span class="status-pill status-never">Never synced</span>
          {:else if lastCdbRun.status === 'running'}
            <span class="status-pill status-running">
              <span class="status-dot running-dot" aria-hidden="true"></span>
              Running…
            </span>
          {:else if lastCdbRun.status === 'completed'}
            <span class="status-pill status-ok">Completed</span>
            {#if summaryLabel(lastCdbRun)}<span class="status-detail">{summaryLabel(lastCdbRun)}</span>{/if}
            <span class="status-date">{formatDate(lastCdbRun.started_at)}</span>
          {:else}
            <span class="status-pill status-error">Failed</span>
            <span class="status-date">{formatDate(lastCdbRun.started_at)}</span>
          {/if}
        </div>

        {#if lastCdbSources.length > 0}
          <div class="cdb-last-sources">
            <span class="cdb-sources-label">Last synced from</span>
            {#each lastCdbSources as src}
              <code class="cdb-source-path">{src}</code>
            {/each}
          </div>
        {/if}

        {#if lastCdbRun?.error_log}
          <pre class="error-log">{lastCdbRun.error_log}</pre>
        {/if}
      </div>
    </div>

    <!-- Path form -->
    <div class="cdb-form">
      <div class="cdb-form-header">
        <span class="cdb-paths-label">CDB file paths</span>
        <span class="cdb-paths-hint">One path per row — later files override earlier ones on ID conflict</span>
      </div>
      <div class="cdb-path-list">
        {#each cdbPaths as path, i}
          <div class="cdb-path-row">
            <span class="cdb-path-index">{i + 1}</span>
            <input
              type="text"
              class="cdb-path-input"
              placeholder="C:\EdoPro\expansions\cards.cdb"
              value={path}
              oninput={(e) => { cdbPaths[i] = (e.target as HTMLInputElement).value; }}
              aria-label={`CDB path ${i + 1}`}
            />
            <button
              class="cdb-remove-btn"
              onclick={() => removeCdbPath(i)}
              aria-label="Remove path"
              title="Remove"
              tabindex={cdbPaths.length === 1 ? -1 : 0}
              style={cdbPaths.length === 1 ? 'opacity: 0; pointer-events: none;' : ''}
            >✕</button>
          </div>
        {/each}
      </div>
      <div class="cdb-form-actions">
        <button class="cdb-add-btn" onclick={addCdbPath}>+ Add path</button>
        <button
          class="btn-primary sync-btn cdb-sync-btn"
          onclick={triggerCdbSync}
          disabled={isCdbRunning || cdbTriggering}
          aria-busy={isCdbRunning}
        >
          {#if isCdbRunning || cdbTriggering}
            <span class="spinner" aria-hidden="true"></span>
            Syncing…
          {:else}
            Sync EdoPro CDB
          {/if}
        </button>
      </div>
    </div>
  </div>

  <!-- Recent runs -->
  {#if runs.length > 0}
    <section class="runs-section">
      <h2 class="runs-title">Recent Activity</h2>
      <div class="runs-table">
        <div class="runs-header">
          <span>Type</span>
          <span>Status</span>
          <span>Started</span>
          <span>Duration</span>
          <span>Result</span>
        </div>
        {#each runs as run (run.id)}
          <div class="runs-row">
            <span class="run-type-badge run-type--{run.sync_type}">{run.sync_type}</span>
            <span class="run-status run-status--{run.status}">
              {#if run.status === 'running'}
                <span class="status-dot running-dot" aria-hidden="true"></span>
              {/if}
              {run.status}
            </span>
            <span class="run-date-cell">{formatDate(run.started_at)}</span>
            <span class="run-duration">{formatDuration(run.started_at, run.finished_at)}</span>
            <span class="run-result">{summaryLabel(run) || '—'}</span>
          </div>
        {/each}
      </div>
    </section>
  {/if}
</div>

<style>
  .page-body {
    padding-top: 3rem;
    padding-bottom: 5rem;
  }

  .page-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1.5rem;
    margin-bottom: 2.5rem;
    flex-wrap: wrap;
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

  .auth-guard-icon {
    font-size: 1.25rem;
    color: var(--gold);
    opacity: 0.7;
    flex-shrink: 0;
  }

  .auth-guard-text { flex: 1; min-width: 160px; }

  .auth-guard-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.125rem;
  }

  .auth-guard-sub {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
  }

  .auth-guard-btn {
    font-size: 0.875rem;
    padding: 0.5rem 1rem;
    flex-shrink: 0;
  }

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    margin-top: 0.375rem;
  }

  /* ── Sync grid (top row) ───────────────────────────────────────────────── */
  .sync-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .sync-card {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    padding: 1.75rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
  }

  /* ── CDB card (full-width below grid) ─────────────────────────────────── */
  .sync-card--cdb {
    margin-bottom: 3rem;
  }

  .cdb-top-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    align-items: start;
  }

  .cdb-status-col {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .inline-code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8em;
    background: var(--bg-elevated);
    padding: 0.1em 0.35em;
    border-radius: 3px;
    border: 1px solid var(--border-subtle);
  }

  .cdb-last-sources {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    padding: 0.625rem 0.75rem;
    background: var(--bg-elevated);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-subtle);
  }

  .cdb-sources-label {
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 0.25rem;
  }

  .cdb-source-path {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6875rem;
    color: var(--text-secondary);
    word-break: break-all;
  }

  /* ── Path form ─────────────────────────────────────────────────────────── */
  .cdb-form {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--border-subtle);
  }

  .cdb-form-header {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .cdb-paths-label {
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .cdb-paths-hint {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    opacity: 0.7;
  }

  .cdb-path-list {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .cdb-path-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .cdb-path-index {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6875rem;
    color: var(--text-tertiary);
    width: 1rem;
    text-align: right;
    flex-shrink: 0;
  }

  .cdb-path-input {
    flex: 1;
    height: 36px;
    padding: 0 0.75rem;
    background: var(--bg-base);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    transition: border-color var(--duration-fast) var(--ease-out);
    outline: none;
  }

  .cdb-path-input::placeholder {
    color: var(--text-tertiary);
    opacity: 0.45;
  }

  .cdb-path-input:focus {
    border-color: var(--gold);
    box-shadow: 0 0 0 2px rgba(201, 164, 73, 0.1);
  }

  .cdb-remove-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    flex-shrink: 0;
    background: transparent;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    color: var(--text-tertiary);
    font-size: 0.625rem;
    cursor: pointer;
    transition: border-color var(--duration-fast) var(--ease-out),
                color var(--duration-fast) var(--ease-out);
  }

  .cdb-remove-btn:hover {
    border-color: var(--error);
    color: var(--error);
  }

  .cdb-form-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .cdb-add-btn {
    background: transparent;
    border: 1px dashed var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-tertiary);
    font-size: 0.8125rem;
    padding: 0.375rem 0.875rem;
    cursor: pointer;
    transition: border-color var(--duration-fast) var(--ease-out),
                color var(--duration-fast) var(--ease-out);
  }

  .cdb-add-btn:hover {
    border-color: var(--gold);
    color: var(--gold);
  }

  .cdb-sync-btn {
    gap: 0.5rem;
  }

  /* ── Shared sync card styles ───────────────────────────────────────────── */
  .sync-card-top {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
  }

  .sync-icon-wrap {
    font-size: 1.25rem;
    color: var(--gold);
    opacity: 0.75;
    line-height: 1;
    flex-shrink: 0;
    padding-top: 0.125rem;
  }

  .sync-card-title {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
  }

  .sync-card-desc {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    line-height: 1.55;
  }

  .sync-status-row {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    flex-wrap: wrap;
  }

  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.2rem 0.625rem;
    border-radius: 99px;
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.04em;
  }

  .status-never   { background: var(--bg-elevated); color: var(--text-tertiary); border: 1px solid var(--border-subtle); }
  .status-running { background: rgba(201,164,73,.1); color: var(--gold);         border: 1px solid rgba(201,164,73,.25); }
  .status-ok      { background: rgba(74,186,122,.1); color: var(--success);      border: 1px solid rgba(74,186,122,.25); }
  .status-error   { background: rgba(224,84,84,.1);  color: var(--error);        border: 1px solid rgba(224,84,84,.25); }

  .status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
  .running-dot { background: var(--gold); animation: pulse 1.4s ease-in-out infinite; }

  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

  .status-detail { font-size: 0.8125rem; color: var(--text-secondary); font-weight: 500; }
  .status-date   { font-size: 0.75rem; color: var(--text-tertiary); }

  .error-log {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--error);
    background: rgba(224,84,84,.06);
    border: 1px solid rgba(224,84,84,.15);
    border-radius: var(--radius-sm);
    padding: 0.75rem;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 100px;
  }

  .sync-btn {
    width: 100%;
    justify-content: center;
    gap: 0.5rem;
  }

  .sync-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none !important;
    box-shadow: none !important;
  }

  .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(0, 0, 0, 0.2);
    border-top-color: rgba(0, 0, 0, 0.6);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Recent Activity table ─────────────────────────────────────────────── */
  .runs-section { margin-top: 1rem; }

  .runs-title {
    font-size: 0.8125rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 1rem;
  }

  .runs-table {
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .runs-header {
    display: grid;
    grid-template-columns: 80px 90px 1fr 80px 160px;
    gap: 1rem;
    padding: 0.625rem 1.25rem;
    background: var(--bg-elevated);
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .runs-row {
    display: grid;
    grid-template-columns: 80px 90px 1fr 80px 160px;
    gap: 1rem;
    align-items: center;
    padding: 0.75rem 1.25rem;
    border-top: 1px solid var(--border-subtle);
    transition: background var(--duration-fast) var(--ease-out);
  }

  .runs-row:hover { background: var(--bg-surface); }

  .run-type-badge {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--text-secondary);
    text-transform: capitalize;
  }

  /* Color-coded type badges */
  .run-type--cards   { color: var(--gold); }
  .run-type--banlist { color: var(--error); }
  .run-type--cdb     { color: #7c9cf8; }

  .run-status {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: capitalize;
  }

  .run-status--completed { color: var(--success); }
  .run-status--running   { color: var(--gold); }
  .run-status--failed    { color: var(--error); }

  .run-date-cell { font-size: 0.8125rem; color: var(--text-secondary); }
  .run-duration  { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-tertiary); }
  .run-result    { font-size: 0.8125rem; color: var(--text-secondary); }

  /* ── Responsive ────────────────────────────────────────────────────────── */
  @media (max-width: 900px) {
    .cdb-top-row { grid-template-columns: 1fr; gap: 1.25rem; }
  }

  @media (max-width: 768px) {
    .runs-header,
    .runs-row { grid-template-columns: 80px 80px 1fr 70px; }
    .runs-header span:last-child, .run-result { display: none; }
  }

  @media (max-width: 480px) {
    .runs-header,
    .runs-row { grid-template-columns: 80px 80px 1fr; }
    .runs-header span:nth-child(4), .run-duration { display: none; }
  }
</style>
