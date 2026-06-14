<script lang="ts">
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';

  interface ImportResult {
    deck_id: number;
    submission_id: number;
    title: string;
    main_count: number;
    extra_count: number;
    side_count: number;
    unknown_ids: number[];
  }

  type Phase = 'idle' | 'dragging' | 'loading' | 'success' | 'error';

  let phase: Phase = $state('idle');
  let result: ImportResult | null = $state(null);
  let errorMsg: string = $state('');
  let title: string = $state('');
  let fileInput: HTMLInputElement | null = $state(null);
  let selectedFile: File | null = $state(null);

  function onDragOver(e: DragEvent) {
    e.preventDefault();
    phase = 'dragging';
  }

  function onDragLeave() {
    if (phase === 'dragging') phase = 'idle';
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer?.files[0];
    if (file) {
      selectedFile = file;
      if (!title) title = file.name.replace(/\.ydk$/i, '');
    }
    phase = 'idle';
  }

  function onFileInputChange(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      selectedFile = file;
      if (!title) title = file.name.replace(/\.ydk$/i, '');
    }
  }

  async function submit() {
    if (!selectedFile) return;

    phase = 'loading';

    const form = new FormData();
    form.append('file', selectedFile, selectedFile.name);
    if (title.trim()) form.append('title', title.trim());

    try {
      const res = await fetch('/api/v1/decks/import/ydk', {
        method: 'POST',
        body: form,
      });
      const body = await res.json();

      if (!res.ok) {
        if (res.status === 401) { goto('/login'); return; }
        errorMsg = body.detail ?? 'Import failed';
        phase = 'error';
        return;
      }

      result = body as ImportResult;
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
    selectedFile = null;
    title = '';
    if (fileInput) fileInput.value = '';
  }

  function viewDeck() {
    if (result) goto(`/decks/${result.deck_id}`);
  }

  // Unknown IDs display
  let showAllUnknown = $state(false);
  const UNKNOWN_PREVIEW = 8;

  async function copyUnknownIds() {
    if (!result) return;
    await navigator.clipboard.writeText(result.unknown_ids.join('\n'));
  }
</script>

<svelte:head>
  <title>Import .ydk — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <header class="page-header">
    <div>
      <span class="label">Decks</span>
      <h1 class="page-title">Import .ydk</h1>
    </div>
    <a href="/decks" class="btn-ghost">← Back to decks</a>
  </header>

  {#if $auth.loaded && $auth.enabled && !$auth.user}
    <div class="auth-guard">
      <span class="auth-guard-icon" aria-hidden="true">⚿</span>
      <div class="auth-guard-text">
        <p class="auth-guard-title">Login required</p>
        <p class="auth-guard-sub">You must be logged in to import decks.</p>
      </div>
      <a href="/login" class="btn-primary auth-guard-btn">Login →</a>
    </div>
  {/if}

  {#if phase === 'success' && result}
    <!-- Success state -->
    <div class="result-card">
      <div class="result-icon success-icon" aria-hidden="true">✓</div>
      <h2 class="result-title">Deck imported</h2>
      <p class="result-deck-name">{result.title}</p>

      <div class="result-counts">
        <div class="result-count-item">
          <span class="result-count-value">{result.main_count}</span>
          <span class="result-count-label">Main</span>
        </div>
        <div class="result-count-sep" aria-hidden="true"></div>
        <div class="result-count-item">
          <span class="result-count-value">{result.extra_count}</span>
          <span class="result-count-label">Extra</span>
        </div>
        <div class="result-count-sep" aria-hidden="true"></div>
        <div class="result-count-item">
          <span class="result-count-value">{result.side_count}</span>
          <span class="result-count-label">Side</span>
        </div>
      </div>

      {#if result.unknown_ids.length > 0}
        <div class="unknown-block">
          <div class="unknown-block-header">
            <div class="unknown-block-title">
              <span class="unknown-icon" aria-hidden="true">⚠</span>
              <span>
                {result.unknown_ids.length} card{result.unknown_ids.length !== 1 ? 's' : ''} not found
              </span>
            </div>
            <button class="unknown-copy-btn" onclick={copyUnknownIds} title="Copy all IDs to clipboard">
              Copy IDs
            </button>
          </div>
          <p class="unknown-hint">
            These passcodes are in the .ydk file but missing from the database.
            They may be OCG pre-release cards —
            <a href="/admin" class="unknown-link">sync the EdoPro CDB</a> to add them.
          </p>
          <div class="unknown-ids-grid">
            {#each (showAllUnknown ? result.unknown_ids : result.unknown_ids.slice(0, UNKNOWN_PREVIEW)) as id}
              <code class="unknown-id-badge">{id}</code>
            {/each}
          </div>
          {#if result.unknown_ids.length > UNKNOWN_PREVIEW}
            <button class="unknown-toggle" onclick={() => (showAllUnknown = !showAllUnknown)}>
              {showAllUnknown ? '↑ Show less' : `↓ Show all ${result.unknown_ids.length} IDs`}
            </button>
          {/if}
        </div>
      {/if}

      <div class="result-actions">
        <button class="btn-primary" onclick={viewDeck}>View deck →</button>
        <button class="btn-ghost" onclick={reset}>Import another</button>
      </div>
    </div>

  {:else if phase === 'error'}
    <!-- Error state -->
    <div class="result-card error-card">
      <div class="result-icon error-icon" aria-hidden="true">✕</div>
      <h2 class="result-title">Import failed</h2>
      <p class="error-message">{errorMsg}</p>
      <button class="btn-ghost" onclick={reset}>Try again</button>
    </div>

  {:else}
    <!-- Import form -->
    <div class="import-layout">
      <!-- Drop zone -->
      <div
        class="drop-zone"
        class:dragging={phase === 'dragging'}
        class:has-file={selectedFile !== null}
        role="button"
        tabindex="0"
        aria-label="Drop .ydk file here or click to browse"
        ondragover={onDragOver}
        ondragleave={onDragLeave}
        ondrop={onDrop}
        onclick={() => fileInput?.click()}
        onkeydown={(e) => e.key === 'Enter' && fileInput?.click()}
      >
        <input
          bind:this={fileInput}
          type="file"
          accept=".ydk"
          class="file-input-hidden"
          onchange={onFileInputChange}
          tabindex="-1"
          aria-hidden="true"
        />

        {#if selectedFile}
          <div class="file-selected">
            <span class="file-icon" aria-hidden="true">◫</span>
            <span class="file-name">{selectedFile.name}</span>
            <span class="file-size">{(selectedFile.size / 1024).toFixed(1)} KB</span>
          </div>
        {:else}
          <div class="drop-prompt">
            <span class="drop-arrow" aria-hidden="true">↑</span>
            <span class="drop-label">Drop your .ydk file here</span>
            <span class="drop-sub">or click to browse</span>
          </div>
        {/if}
      </div>

      <!-- Title field -->
      <div class="field">
        <label class="field-label" for="deck-title">Deck name</label>
        <input
          id="deck-title"
          type="text"
          class="field-input"
          placeholder="e.g. Blue-Eyes Pure — June 2024"
          bind:value={title}
          disabled={phase === 'loading'}
        />
        <span class="field-hint">Optional — defaults to the filename</span>
      </div>

      <button
        class="btn-primary submit-btn"
        disabled={!selectedFile || phase === 'loading'}
        onclick={submit}
      >
        {#if phase === 'loading'}
          <span class="spinner" aria-hidden="true"></span>
          Importing…
        {:else}
          Import deck ↑
        {/if}
      </button>

      <!-- Instructions -->
      <div class="instructions card">
        <h3 class="instructions-title">Compatible formats</h3>
        <ul class="instructions-list">
          <li>YGOPRO / EDOPro (.ydk)</li>
          <li>Dueling Nexus export</li>
          <li>YGOSalvation / Untitled Tool exports</li>
          <li>Any standard #main / #extra / !side format</li>
        </ul>
      </div>
    </div>
  {/if}
</div>

<style>
  .page-body {
    padding-top: 3rem;
    padding-bottom: 5rem;
    max-width: 600px;
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

  .import-layout {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  /* Drop zone */
  .drop-zone {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 180px;
    border: 1.5px dashed var(--border-default);
    border-radius: var(--radius-xl);
    background: var(--bg-surface);
    cursor: pointer;
    transition:
      border-color var(--duration-base) var(--ease-out),
      background var(--duration-base) var(--ease-out);
    user-select: none;
    padding: 2rem;
  }

  .drop-zone:hover,
  .drop-zone:focus-visible {
    border-color: var(--gold);
    background: var(--gold-dim);
  }

  .drop-zone.dragging {
    border-color: var(--gold);
    background: var(--gold-dim);
    border-style: solid;
  }

  .drop-zone.has-file {
    border-color: var(--border-strong);
    border-style: solid;
  }

  .file-input-hidden {
    position: absolute;
    width: 0;
    height: 0;
    opacity: 0;
    pointer-events: none;
  }

  .drop-prompt {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    text-align: center;
  }

  .drop-arrow {
    font-size: 2rem;
    color: var(--text-tertiary);
    line-height: 1;
    margin-bottom: 0.25rem;
    transition:
      transform var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
  }

  .drop-zone:hover .drop-arrow,
  .drop-zone.dragging .drop-arrow {
    transform: translateY(-4px);
    color: var(--gold);
  }

  .drop-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .drop-sub {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
  }

  .file-selected {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.375rem;
    text-align: center;
  }

  .file-icon {
    font-size: 1.75rem;
    color: var(--gold);
    line-height: 1;
    margin-bottom: 0.25rem;
  }

  .file-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.875rem;
    color: var(--text-primary);
    word-break: break-all;
  }

  .file-size {
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  /* Field */
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

  .field-input {
    width: 100%;
    padding: 0.625rem 0.875rem;
    background: var(--bg-surface);
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

  .field-input::placeholder {
    color: var(--text-tertiary);
  }

  .field-input:focus {
    border-color: var(--gold);
    box-shadow: 0 0 0 3px rgba(201, 164, 73, 0.12);
  }

  .field-input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .field-hint {
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

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
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* Instructions */
  .instructions-title {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 0.75rem;
    font-family: 'Space Grotesk', sans-serif;
  }

  .instructions-list {
    margin: 0;
    padding: 0 0 0 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .instructions-list li {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    line-height: 1.4;
  }

  /* Result card */
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

  .result-deck-name {
    font-size: 1rem;
    color: var(--text-secondary);
    max-width: 32ch;
  }

  .result-counts {
    display: flex;
    align-items: center;
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .result-count-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.625rem 1.25rem;
    gap: 0.1rem;
  }

  .result-count-sep {
    width: 1px;
    height: 2.25rem;
    background: var(--border-subtle);
    flex-shrink: 0;
  }

  .result-count-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1;
  }

  .result-count-label {
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  /* Unknown IDs block */
  .unknown-block {
    align-self: stretch;
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
    padding: 1rem;
    background: rgba(232, 162, 59, 0.06);
    border: 1px solid rgba(232, 162, 59, 0.2);
    border-radius: var(--radius-md);
    text-align: left;
  }

  .unknown-block-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .unknown-block-title {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--warning);
  }

  .unknown-icon { font-size: 0.875rem; }

  .unknown-copy-btn {
    background: transparent;
    border: 1px solid rgba(232, 162, 59, 0.3);
    border-radius: var(--radius-sm);
    color: var(--warning);
    font-size: 0.6875rem;
    font-weight: 600;
    padding: 0.2rem 0.5rem;
    cursor: pointer;
    opacity: 0.7;
    transition: opacity var(--duration-fast) var(--ease-out);
    flex-shrink: 0;
  }

  .unknown-copy-btn:hover { opacity: 1; }

  .unknown-hint {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    line-height: 1.55;
  }

  .unknown-link {
    color: var(--gold);
    text-decoration: underline;
    text-underline-offset: 2px;
    transition: opacity var(--duration-fast) var(--ease-out);
  }

  .unknown-link:hover { opacity: 0.8; }

  .unknown-ids-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  .unknown-id-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6875rem;
    padding: 0.175rem 0.5rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    user-select: all;
    cursor: text;
  }

  .unknown-toggle {
    align-self: flex-start;
    background: transparent;
    border: none;
    color: var(--text-tertiary);
    font-size: 0.75rem;
    cursor: pointer;
    padding: 0;
    text-decoration: underline;
    text-underline-offset: 2px;
    transition: color var(--duration-fast) var(--ease-out);
  }

  .unknown-toggle:hover { color: var(--text-secondary); }

  .result-actions {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    justify-content: center;
  }

  .error-card {
    border-color: rgba(224, 84, 84, 0.2);
  }

  .error-message {
    font-size: 0.9rem;
    color: var(--text-secondary);
    max-width: 36ch;
  }
</style>
