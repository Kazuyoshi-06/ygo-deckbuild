<script lang="ts">
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';

  interface BulkImportItem {
    filename: string;
    deck_id: number | null;
    submission_id: number | null;
    title: string;
    main_count: number;
    extra_count: number;
    side_count: number;
    unknown_ids: number[];
    error: string | null;
  }

  interface BulkImportResult {
    imported: number;
    failed: number;
    items: BulkImportItem[];
  }

  interface ImportResult {
    deck_id: number;
    submission_id: number;
    title: string;
    main_count: number;
    extra_count: number;
    side_count: number;
    unknown_ids?: number[];
    unknown_names?: string[];
  }

  type Phase = 'idle' | 'dragging' | 'loading' | 'success' | 'error';
  type Tab = 'file' | 'url' | 'text' | 'bulk';

  let phase: Phase = $state('idle');
  let activeTab: Tab = $state('file');
  let result: ImportResult | null = $state(null);
  let errorMsg: string = $state('');

  // File tab state
  let title: string = $state('');
  let fileInput: HTMLInputElement | null = $state(null);
  let selectedFile: File | null = $state(null);

  // URL tab state
  let urlInput: string = $state('');
  let urlTitle: string = $state('');

  // Text tab state
  let textInput: string = $state('');
  let textTitle: string = $state('');

  // Bulk tab state
  let bulkFiles: File[] = $state([]);
  let bulkResult: BulkImportResult | null = $state(null);
  let bulkDragging: boolean = $state(false);
  let bulkFileInput: HTMLInputElement | null = $state(null);

  // ── File tab ────────────────────────────────────────────────────────────────
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

  async function submitFile() {
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

  // ── URL tab ─────────────────────────────────────────────────────────────────
  async function submitUrl() {
    if (!urlInput.trim()) return;
    phase = 'loading';

    try {
      const res = await fetch('/api/v1/decks/import/url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: urlInput.trim(),
          title: urlTitle.trim() || null,
        }),
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

  // ── Shared ──────────────────────────────────────────────────────────────────
  function reset() {
    phase = 'idle';
    result = null;
    errorMsg = '';
    selectedFile = null;
    title = '';
    urlInput = '';
    urlTitle = '';
    textInput = '';
    textTitle = '';
    bulkFiles = [];
    bulkResult = null;
    bulkDragging = false;
    if (fileInput) fileInput.value = '';
    if (bulkFileInput) bulkFileInput.value = '';
  }

  function viewDeck() {
    if (result) goto(`/decks/${result.deck_id}`);
  }

  // ── Bulk tab ─────────────────────────────────────────────────────────────────
  function addBulkFiles(fileList: FileList | null) {
    if (!fileList) return;
    const incoming = Array.from(fileList).filter(
      (f) => f.name.toLowerCase().endsWith('.ydk') || f.name.toLowerCase().endsWith('.zip')
    );
    const existingNames = new Set(bulkFiles.map((f) => f.name));
    bulkFiles = [...bulkFiles, ...incoming.filter((f) => !existingNames.has(f.name))];
  }

  function removeBulkFile(idx: number) {
    bulkFiles = bulkFiles.filter((_, i) => i !== idx);
  }

  function onBulkDragOver(e: DragEvent) {
    e.preventDefault();
    bulkDragging = true;
  }

  function onBulkDragLeave() {
    bulkDragging = false;
  }

  function onBulkDrop(e: DragEvent) {
    e.preventDefault();
    bulkDragging = false;
    addBulkFiles(e.dataTransfer?.files ?? null);
  }

  function onBulkFileInputChange(e: Event) {
    addBulkFiles((e.target as HTMLInputElement).files);
  }

  async function submitBulk() {
    if (!bulkFiles.length) return;
    phase = 'loading';

    const form = new FormData();
    for (const file of bulkFiles) {
      form.append('files', file, file.name);
    }

    try {
      const res = await fetch('/api/v1/decks/import/bulk', {
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
      bulkResult = body as BulkImportResult;
      phase = 'success';
    } catch {
      errorMsg = 'Network error — is the server running?';
      phase = 'error';
    }
  }

  let showAllUnknown = $state(false);
  const UNKNOWN_PREVIEW = 8;

  function getUnknownItems(r: ImportResult | null): string[] {
    if (!r) return [];
    return [
      ...(r.unknown_ids?.map(String) ?? []),
      ...(r.unknown_names ?? []),
    ];
  }

  let unknownItems: string[] = $derived(getUnknownItems(result));

  async function copyUnknownItems() {
    await navigator.clipboard.writeText(unknownItems.join('\n'));
  }

  async function submitText() {
    if (!textInput.trim()) return;
    phase = 'loading';

    try {
      const res = await fetch('/api/v1/decks/import/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textInput.trim(),
          title: textTitle.trim() || null,
        }),
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
</script>

<svelte:head>
  <title>Import — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <header class="page-header">
    <div>
      <span class="label">Decks</span>
      <h1 class="page-title">Import deck</h1>
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

  {#if phase === 'success' && bulkResult}
    <!-- Bulk success state -->
    <div class="result-card">
      <div
        class="result-icon"
        class:success-icon={bulkResult.failed === 0}
        class:warn-icon={bulkResult.failed > 0 && bulkResult.imported > 0}
        class:error-icon={bulkResult.imported === 0}
        aria-hidden="true"
      >
        {bulkResult.imported === 0 ? '✕' : bulkResult.failed === 0 ? '✓' : '⚠'}
      </div>
      <h2 class="result-title">
        {bulkResult.imported} deck{bulkResult.imported !== 1 ? 's' : ''} imported
      </h2>
      {#if bulkResult.failed > 0}
        <p class="result-deck-name">
          {bulkResult.failed} file{bulkResult.failed !== 1 ? 's' : ''} could not be imported
        </p>
      {/if}

      <div class="bulk-result-list">
        {#each bulkResult.items as item}
          <div class="bulk-result-item" class:bulk-item-error={!!item.error}>
            <span class="bulk-item-status" aria-hidden="true">{item.error ? '✕' : '✓'}</span>
            <div class="bulk-item-body">
              {#if item.error}
                <span class="bulk-item-name">{item.title}</span>
                <span class="bulk-item-errmsg">{item.error}</span>
              {:else}
                <a href="/decks/{item.deck_id}" class="bulk-deck-link">{item.title}</a>
                <span class="bulk-item-counts">
                  <span title="Main">{item.main_count}</span>
                  <span class="bulk-counts-sep" aria-hidden="true">/</span>
                  <span title="Extra">{item.extra_count}</span>
                  <span class="bulk-counts-sep" aria-hidden="true">/</span>
                  <span title="Side">{item.side_count}</span>
                </span>
              {/if}
            </div>
            {#if !item.error && item.unknown_ids.length > 0}
              <span
                class="bulk-item-unknown"
                title="{item.unknown_ids.length} unknown passcode{item.unknown_ids.length !== 1 ? 's' : ''}"
              >
                ⚠ {item.unknown_ids.length}
              </span>
            {/if}
          </div>
        {/each}
      </div>

      <div class="result-actions">
        <button class="btn-ghost" onclick={reset}>Import another batch</button>
      </div>
    </div>

  {:else if phase === 'success' && result}
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

      {#if unknownItems.length > 0}
        <div class="unknown-block">
          <div class="unknown-block-header">
            <div class="unknown-block-title">
              <span class="unknown-icon" aria-hidden="true">⚠</span>
              <span>
                {unknownItems.length} card{unknownItems.length !== 1 ? 's' : ''} not found
              </span>
            </div>
            <button class="unknown-copy-btn" onclick={copyUnknownItems} title="Copy to clipboard">
              Copy
            </button>
          </div>
          {#if result.unknown_names && result.unknown_names.length > 0}
            <p class="unknown-hint">
              These card names were not recognised. Check spelling or
              <a href="/admin" class="unknown-link">sync the card database</a>.
            </p>
          {:else}
            <p class="unknown-hint">
              These passcodes are missing from the database.
              They may be OCG pre-release cards —
              <a href="/admin" class="unknown-link">sync the EdoPro CDB</a> to add them.
            </p>
          {/if}
          <div class="unknown-ids-grid">
            {#each (showAllUnknown ? unknownItems : unknownItems.slice(0, UNKNOWN_PREVIEW)) as item}
              <code class="unknown-id-badge">{item}</code>
            {/each}
          </div>
          {#if unknownItems.length > UNKNOWN_PREVIEW}
            <button class="unknown-toggle" onclick={() => (showAllUnknown = !showAllUnknown)}>
              {showAllUnknown ? '↑ Show less' : `↓ Show all ${unknownItems.length}`}
            </button>
          {/if}
        </div>
      {/if}

      <div class="result-actions">
        <button class="btn-primary" onclick={viewDeck}>View deck →</button>
        <a href="/tournaments/new?deck_id={result.deck_id}" class="btn-ghost">Log result ⊞</a>
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
    <!-- Tab switcher -->
    <div class="tab-bar" role="tablist" aria-label="Import method">
      <button
        role="tab"
        aria-selected={activeTab === 'file'}
        class="tab-btn"
        class:active={activeTab === 'file'}
        onclick={() => { activeTab = 'file'; phase = 'idle'; }}
      >
        ◫ File (.ydk)
      </button>
      <button
        role="tab"
        aria-selected={activeTab === 'url'}
        class="tab-btn"
        class:active={activeTab === 'url'}
        onclick={() => { activeTab = 'url'; phase = 'idle'; }}
      >
        ⬡ URL / YDKE
      </button>
      <button
        role="tab"
        aria-selected={activeTab === 'text'}
        class="tab-btn"
        class:active={activeTab === 'text'}
        onclick={() => { activeTab = 'text'; phase = 'idle'; }}
      >
        ≡ Text list
      </button>
      <button
        role="tab"
        aria-selected={activeTab === 'bulk'}
        class="tab-btn"
        class:active={activeTab === 'bulk'}
        onclick={() => { activeTab = 'bulk'; phase = 'idle'; }}
      >
        ⊞ Bulk
      </button>
    </div>

    {#if activeTab === 'file'}
      <!-- File import form -->
      <div class="import-layout">
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
          onclick={submitFile}
        >
          {#if phase === 'loading'}
            <span class="spinner" aria-hidden="true"></span>
            Importing…
          {:else}
            Import deck ↑
          {/if}
        </button>

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

    {:else if activeTab === 'url'}
      <!-- URL / YDKE import form -->
      <div class="import-layout">
        <div class="field">
          <label class="field-label" for="deck-url">URL or YDKE link</label>
          <input
            id="deck-url"
            type="text"
            class="field-input url-input"
            placeholder="ydke://... or https://..."
            bind:value={urlInput}
            disabled={phase === 'loading'}
            spellcheck="false"
            autocomplete="off"
          />
          <span class="field-hint">Paste a ydke:// link, a direct .ydk URL, or a YGOProDeck deck page URL</span>
        </div>

        <div class="field">
          <label class="field-label" for="url-deck-title">Deck name</label>
          <input
            id="url-deck-title"
            type="text"
            class="field-input"
            placeholder="e.g. Snake-Eyes — YCS LA 2025"
            bind:value={urlTitle}
            disabled={phase === 'loading'}
          />
          <span class="field-hint">Optional — auto-detected from the page title if blank</span>
        </div>

        <button
          class="btn-primary submit-btn"
          disabled={!urlInput.trim() || phase === 'loading'}
          onclick={submitUrl}
        >
          {#if phase === 'loading'}
            <span class="spinner" aria-hidden="true"></span>
            Importing…
          {:else}
            Import deck ↑
          {/if}
        </button>

        <div class="instructions card">
          <h3 class="instructions-title">Supported URL types</h3>
          <ul class="instructions-list">
            <li>
              <strong class="hint-strong">ydke://</strong> — universal YDKE format
              <span class="hint-sub">(Omega, Dueling Nexus, YGOProDeck builder → Share → Copy YDKE Link)</span>
            </li>
            <li>
              <strong class="hint-strong">Direct .ydk URL</strong> — any URL ending in .ydk
              <span class="hint-sub">(GitHub raw, Dropbox, Google Drive direct links)</span>
            </li>
            <li>
              <strong class="hint-strong">YGOProDeck deck page</strong> — best effort
              <span class="hint-sub">(requires the page to contain a YDKE link or .ydk download button)</span>
            </li>
          </ul>
        </div>
      </div>

    {:else if activeTab === 'text'}
      <!-- Text list import form -->
      <div class="import-layout">
        <div class="field">
          <label class="field-label" for="text-deck-list">Deck list</label>
          <textarea
            id="text-deck-list"
            class="field-textarea"
            placeholder={"Main Deck\n3x Ash Blossom & Joyous Spring\n3 Effect Veiler\nDark Hole x3\n\nExtra Deck\n3x Salamangreat Sunlight Wolf\n\nSide Deck\n2 Nibiru, the Primal Being"}
            bind:value={textInput}
            disabled={phase === 'loading'}
            spellcheck="false"
            maxlength={50000}
          ></textarea>
          <span class="field-hint">
            {textInput.length.toLocaleString()} / 50,000 chars
          </span>
        </div>

        <div class="field">
          <label class="field-label" for="text-deck-title">Deck name</label>
          <input
            id="text-deck-title"
            type="text"
            class="field-input"
            placeholder="e.g. Purrely — YCS 2025"
            bind:value={textTitle}
            disabled={phase === 'loading'}
          />
          <span class="field-hint">Optional — defaults to "Imported Deck"</span>
        </div>

        <button
          class="btn-primary submit-btn"
          disabled={!textInput.trim() || phase === 'loading'}
          onclick={submitText}
        >
          {#if phase === 'loading'}
            <span class="spinner" aria-hidden="true"></span>
            Importing…
          {:else}
            Import deck ↑
          {/if}
        </button>

        <div class="instructions card">
          <h3 class="instructions-title">Accepted formats</h3>
          <ul class="instructions-list">
            <li><strong class="hint-strong">3x Card Name</strong> or <strong class="hint-strong">Card Name x3</strong> — with count</li>
            <li><strong class="hint-strong">3 Card Name</strong> — digit + space</li>
            <li><strong class="hint-strong">Card Name</strong> — bare name (counted as 1 copy)</li>
            <li>Section headers: <code class="inline-code">Main Deck</code>, <code class="inline-code">Extra Deck</code>, <code class="inline-code">Side Deck</code> (or <code class="inline-code">#main</code> / <code class="inline-code">#extra</code> / <code class="inline-code">!side</code>)</li>
            <li>Extra-deck monsters placed in the Main section are auto-detected and moved</li>
          </ul>
        </div>
      </div>
    {:else}
      <!-- Bulk import form -->
      <div class="import-layout">
        <div
          class="drop-zone"
          class:dragging={bulkDragging}
          class:has-file={bulkFiles.length > 0}
          role="button"
          tabindex="0"
          aria-label="Drop .ydk or .zip files here or click to browse"
          ondragover={onBulkDragOver}
          ondragleave={onBulkDragLeave}
          ondrop={onBulkDrop}
          onclick={() => bulkFileInput?.click()}
          onkeydown={(e) => e.key === 'Enter' && bulkFileInput?.click()}
        >
          <input
            bind:this={bulkFileInput}
            type="file"
            accept=".ydk,.zip"
            multiple
            class="file-input-hidden"
            onchange={onBulkFileInputChange}
            tabindex="-1"
            aria-hidden="true"
          />
          {#if bulkFiles.length > 0}
            <div class="drop-prompt">
              <span class="file-icon" aria-hidden="true">⊞</span>
              <span class="drop-label">
                {bulkFiles.length} file{bulkFiles.length !== 1 ? 's' : ''} selected
              </span>
              <span class="drop-sub">Drop more or click to add</span>
            </div>
          {:else}
            <div class="drop-prompt">
              <span class="drop-arrow" aria-hidden="true">↑</span>
              <span class="drop-label">Drop .ydk files or a .zip archive</span>
              <span class="drop-sub">or click to browse — multiple files supported</span>
            </div>
          {/if}
        </div>

        {#if bulkFiles.length > 0}
          <ul class="bulk-file-list" aria-label="Selected files">
            {#each bulkFiles as file, idx}
              <li class="bulk-file-item">
                <span class="bulk-file-icon" aria-hidden="true">
                  {file.name.toLowerCase().endsWith('.zip') ? '⊘' : '◫'}
                </span>
                <span class="bulk-file-name">{file.name}</span>
                <span class="bulk-file-size">{(file.size / 1024).toFixed(1)} KB</span>
                <button
                  class="bulk-file-remove"
                  onclick={() => removeBulkFile(idx)}
                  aria-label="Remove {file.name}"
                  title="Remove"
                >✕</button>
              </li>
            {/each}
          </ul>
        {/if}

        <button
          class="btn-primary submit-btn"
          disabled={bulkFiles.length === 0 || phase === 'loading'}
          onclick={submitBulk}
        >
          {#if phase === 'loading'}
            <span class="spinner" aria-hidden="true"></span>
            Importing…
          {:else}
            Import {bulkFiles.length > 0 ? bulkFiles.length : ''} deck{bulkFiles.length !== 1 ? 's' : ''} ↑
          {/if}
        </button>

        <div class="instructions card">
          <h3 class="instructions-title">How it works</h3>
          <ul class="instructions-list">
            <li>Select multiple <strong class="hint-strong">.ydk</strong> files — each becomes a separate deck</li>
            <li>Or upload a single <strong class="hint-strong">.zip</strong> archive containing .ydk files</li>
            <li>Deck title = filename (without extension)</li>
            <li>Up to <strong class="hint-strong">50 files</strong> per batch · 512 KB per .ydk · 10 MB per ZIP</li>
          </ul>
        </div>
      </div>
    {/if}
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

  /* ── Tab bar ──────────────────────────────────────────────────────────────── */
  .tab-bar {
    display: flex;
    gap: 0;
    margin-bottom: 2rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 3px;
  }

  .tab-btn {
    flex: 1;
    padding: 0.5rem 1rem;
    border: none;
    border-radius: calc(var(--radius-md) - 3px);
    background: transparent;
    color: var(--text-tertiary);
    font-size: 0.875rem;
    font-weight: 600;
    font-family: 'Space Grotesk', sans-serif;
    cursor: pointer;
    transition:
      background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
  }

  .tab-btn:hover {
    color: var(--text-secondary);
    background: var(--bg-elevated);
  }

  .tab-btn.active {
    background: var(--bg-elevated);
    color: var(--gold);
    border: 1px solid var(--border-default);
  }

  /* ── Import forms ─────────────────────────────────────────────────────────── */
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

  /* Fields */
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

  .url-input {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8125rem;
  }

  .field-textarea {
    width: 100%;
    min-height: 220px;
    padding: 0.625rem 0.875rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8125rem;
    line-height: 1.6;
    resize: vertical;
    transition:
      border-color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
    outline: none;
  }

  .field-textarea::placeholder {
    color: var(--text-tertiary);
    opacity: 0.6;
  }

  .field-textarea:focus {
    border-color: var(--gold);
    box-shadow: 0 0 0 3px rgba(201, 164, 73, 0.12);
  }

  .field-textarea:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* ── Warn icon ────────────────────────────────────────────────────────────── */
  .warn-icon {
    background: rgba(232, 162, 59, 0.12);
    color: var(--warning);
    border: 1px solid rgba(232, 162, 59, 0.25);
  }

  /* ── Bulk file list ──────────────────────────────────────────────────────── */
  .bulk-file-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    max-height: 200px;
    overflow-y: auto;
  }

  .bulk-file-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 0.75rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
  }

  .bulk-file-icon {
    font-size: 0.875rem;
    color: var(--gold);
    flex-shrink: 0;
  }

  .bulk-file-name {
    flex: 1;
    min-width: 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .bulk-file-size {
    font-size: 0.6875rem;
    color: var(--text-tertiary);
    flex-shrink: 0;
  }

  .bulk-file-remove {
    background: transparent;
    border: none;
    color: var(--text-tertiary);
    font-size: 0.6875rem;
    cursor: pointer;
    padding: 0.15rem 0.3rem;
    border-radius: var(--radius-sm);
    transition: color var(--duration-fast) var(--ease-out);
    flex-shrink: 0;
    line-height: 1;
  }

  .bulk-file-remove:hover { color: var(--error); }

  /* ── Bulk result list ────────────────────────────────────────────────────── */
  .bulk-result-list {
    align-self: stretch;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    max-height: 340px;
    overflow-y: auto;
  }

  .bulk-result-item {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    padding: 0.5rem 0.75rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
  }

  .bulk-item-error {
    background: rgba(224, 84, 84, 0.04);
    border-color: rgba(224, 84, 84, 0.18);
  }

  .bulk-item-status {
    font-size: 0.6875rem;
    font-weight: 700;
    flex-shrink: 0;
    width: 14px;
    text-align: center;
  }

  .bulk-result-item:not(.bulk-item-error) .bulk-item-status { color: var(--success); }
  .bulk-item-error .bulk-item-status { color: var(--error); }

  .bulk-item-body {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .bulk-deck-link {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-primary);
    text-decoration: none;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: color var(--duration-fast) var(--ease-out);
  }

  .bulk-deck-link:hover { color: var(--gold); }

  .bulk-item-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .bulk-item-counts {
    font-size: 0.6875rem;
    color: var(--text-tertiary);
    display: flex;
    gap: 0.25rem;
    align-items: center;
  }

  .bulk-counts-sep { opacity: 0.35; }

  .bulk-item-errmsg {
    font-size: 0.6875rem;
    color: var(--error);
    opacity: 0.8;
  }

  .bulk-item-unknown {
    font-size: 0.6875rem;
    color: var(--warning);
    flex-shrink: 0;
    opacity: 0.8;
  }

  .inline-code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    padding: 0.1rem 0.35rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
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
    to { transform: rotate(360deg); }
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
    gap: 0.5rem;
  }

  .instructions-list li {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    line-height: 1.4;
  }

  .hint-strong {
    color: var(--text-secondary);
    font-weight: 600;
  }

  .hint-sub {
    display: block;
    font-size: 0.75rem;
    color: var(--text-tertiary);
    margin-top: 0.1rem;
    opacity: 0.8;
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

  /* Unknown IDs */
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
