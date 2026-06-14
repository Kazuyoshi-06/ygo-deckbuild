<script lang="ts">
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';

  interface DeckCard {
    card_id: number;
    external_card_id: number;
    name: string;
    section: string;
    quantity: number;
    image_url: string;
    tcg_date: string | null;
    ocg_date: string | null;
  }

  interface LegalityViolation {
    card_id: number;
    name: string;
    status: string;
    limit_value: number;
    actual_quantity: number;
  }

  interface RestrictedCard {
    card_id: number;
    name: string;
    status: string;
    limit_value: number;
  }

  interface Legality {
    deck_id: number;
    banlist_id: number | null;
    format: string;
    is_legal: boolean;
    violations: LegalityViolation[];
    restricted: RestrictedCard[];
  }

  function cardBadge(tcg_date: string | null, ocg_date: string | null): 'OCG' | 'TCG' | null {
    if (tcg_date && ocg_date) return null;
    if (ocg_date && !tcg_date) return 'OCG';
    if (tcg_date && !ocg_date) return 'TCG';
    return null;
  }

  const PRESET_TAGS = ['Top 8', 'Locals', 'Theory', 'Budget', 'Tested', 'Online', 'Casual'];

  interface Deck {
    id: number;
    title: string;
    archetype_label: string | null;
    source_type: string;
    notes: string | null;
    tags: string[];
    main: DeckCard[];
    extra: DeckCard[];
    side: DeckCard[];
    main_count: number;
    extra_count: number;
    side_count: number;
    created_at: string;
    updated_at: string;
  }

  let { data } = $props<{ data: { deck: Deck; legalityTCG: Legality | null; legalityOCG: Legality | null } }>();
  let deck = $derived(data.deck);

  let activeFormat: 'TCG' | 'OCG' = $state('TCG');
  let legality = $derived(activeFormat === 'TCG' ? data.legalityTCG : data.legalityOCG);

  // Map card_id → violation (cards exceeding limit) for O(1) lookup
  let violationMap: Record<number, LegalityViolation> = $derived(
    legality
      ? Object.fromEntries(legality.violations.map((v: LegalityViolation) => [v.card_id, v]))
      : {}
  );

  // Map card_id → restricted entry (ALL banlisted cards, including compliant ones)
  let restrictedMap: Record<number, RestrictedCard> = $derived(
    legality
      ? Object.fromEntries(legality.restricted.map((r: RestrictedCard) => [r.card_id, r]))
      : {}
  );

  const banLabel: Record<string, string> = {
    forbidden: 'BAN',
    limited: '×1',
    semi_limited: '×2',
  };

  const sourceLabel: Record<string, string> = {
    ydk_import: 'YDK Import',
    manual: 'Manual',
    scraped: 'Scraped',
    api_import: 'API Import',
  };

  // ── Edit state ─────────────────────────────────────────────────────────────
  let editing = $state(false);
  let editTitle = $state('');
  let editArchetype = $state('');
  let editNotes = $state('');
  let editTags = $state<string[]>([]);
  let saving = $state(false);
  let saveError = $state('');

  function startEdit() {
    editTitle = deck.title;
    editArchetype = deck.archetype_label ?? '';
    editNotes = deck.notes ?? '';
    editTags = [...deck.tags];
    editing = true;
    saveError = '';
  }

  function toggleEditTag(tag: string) {
    if (editTags.includes(tag)) {
      editTags = editTags.filter((t) => t !== tag);
    } else {
      editTags = [...editTags, tag];
    }
  }

  function cancelEdit() {
    editing = false;
    saveError = '';
  }

  async function saveEdit() {
    if (!editTitle.trim()) return;
    saving = true;
    saveError = '';
    try {
      const res = await fetch(`/api/v1/decks/${deck.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: editTitle.trim(),
          archetype_label: editArchetype.trim() || null,
          notes: editNotes.trim() || null,
          tags: editTags,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        saveError = body.detail ?? 'Save failed';
        return;
      }
      editing = false;
      // Reload the page to reflect updated data
      window.location.reload();
    } catch {
      saveError = 'Network error';
    } finally {
      saving = false;
    }
  }

  // ── Delete state ────────────────────────────────────────────────────────────
  let confirmDelete = $state(false);
  let deleting = $state(false);

  async function deleteDeck() {
    deleting = true;
    try {
      const res = await fetch(`/api/v1/decks/${deck.id}`, { method: 'DELETE' });
      if (!res.ok) return;
      goto('/decks');
    } catch {
      deleting = false;
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  }

  function handleImgError(e: Event) {
    const img = e.target as HTMLImageElement;
    img.src = '/media/placeholder-card.svg';
  }

  // ── Export ──────────────────────────────────────────────────────────────────
  function exportYdk() {
    const lines: string[] = ['#created by YGO Intel', '#main'];
    for (const c of deck.main)
      for (let i = 0; i < c.quantity; i++) lines.push(String(c.external_card_id));
    lines.push('#extra');
    for (const c of deck.extra)
      for (let i = 0; i < c.quantity; i++) lines.push(String(c.external_card_id));
    lines.push('!side');
    for (const c of deck.side)
      for (let i = 0; i < c.quantity; i++) lines.push(String(c.external_card_id));

    const filename = (deck.title.replace(/[^a-zA-Z0-9\s_-]/g, '').trim().replace(/\s+/g, '_') || 'deck') + '.ydk';
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  let copyFeedback = $state(false);

  async function copyAsText() {
    const parts: string[] = [];
    if (deck.main.length) {
      parts.push('# Main Deck');
      for (const c of deck.main) parts.push(`${c.quantity}x ${c.name}`);
    }
    if (deck.extra.length) {
      parts.push('', '# Extra Deck');
      for (const c of deck.extra) parts.push(`${c.quantity}x ${c.name}`);
    }
    if (deck.side.length) {
      parts.push('', '# Side Deck');
      for (const c of deck.side) parts.push(`${c.quantity}x ${c.name}`);
    }
    await navigator.clipboard.writeText(parts.join('\n'));
    copyFeedback = true;
    setTimeout(() => (copyFeedback = false), 2000);
  }
</script>

<svelte:head>
  <title>{deck.title} — YGO Intel</title>
</svelte:head>

<div class="page-container page-body">
  <!-- Breadcrumb -->
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="/decks" class="breadcrumb-link">Decks</a>
    <span class="breadcrumb-sep" aria-hidden="true">/</span>
    <span class="breadcrumb-current">{deck.title}</span>
  </nav>

  <!-- Header -->
  <header class="deck-header">
    <div class="deck-header-left">
      <span class="source-badge">{sourceLabel[deck.source_type] ?? deck.source_type}</span>

      {#if editing}
        <!-- Edit form -->
        <div class="edit-form">
          <input
            class="edit-input edit-input--title"
            type="text"
            placeholder="Deck title"
            bind:value={editTitle}
            maxlength="255"
            aria-label="Deck title"
          />
          <input
            class="edit-input edit-input--small"
            type="text"
            placeholder="Archetype (optional)"
            bind:value={editArchetype}
            maxlength="255"
            aria-label="Archetype"
          />
          <textarea
            class="edit-textarea"
            placeholder="Notes (optional)"
            bind:value={editNotes}
            rows="3"
            aria-label="Notes"
          ></textarea>
          <div class="edit-tags-label">Tags</div>
          <div class="edit-tags" role="group" aria-label="Select tags">
            {#each PRESET_TAGS as tag}
              <button
                type="button"
                class="edit-tag-btn"
                class:edit-tag-btn--active={editTags.includes(tag)}
                onclick={() => toggleEditTag(tag)}
              >{tag}</button>
            {/each}
          </div>
          {#if saveError}
            <p class="edit-error">{saveError}</p>
          {/if}
          <div class="edit-actions">
            <button class="btn-primary edit-save-btn" onclick={saveEdit} disabled={saving || !editTitle.trim()}>
              {saving ? 'Saving…' : 'Save changes'}
            </button>
            <button class="btn-ghost" onclick={cancelEdit} disabled={saving}>Cancel</button>
          </div>
        </div>
      {:else}
        <h1 class="deck-title">{deck.title}</h1>
        {#if deck.archetype_label}
          <a
            class="deck-archetype"
            href="/analytics/archetypes/{encodeURIComponent(deck.archetype_label)}"
          >{deck.archetype_label} →</a>
        {/if}
        {#if deck.tags.length > 0}
          <div class="deck-tags">
            {#each deck.tags as tag}<span class="deck-tag">{tag}</span>{/each}
          </div>
        {/if}
      {/if}
    </div>

    <div class="deck-meta">
      <div class="meta-row">
        <div class="meta-item">
          <span class="meta-label">Main</span>
          <span class="meta-value">{deck.main_count}</span>
        </div>
        <div class="meta-divider" aria-hidden="true"></div>
        <div class="meta-item">
          <span class="meta-label">Extra</span>
          <span class="meta-value">{deck.extra_count}</span>
        </div>
        <div class="meta-divider" aria-hidden="true"></div>
        <div class="meta-item">
          <span class="meta-label">Side</span>
          <span class="meta-value">{deck.side_count}</span>
        </div>
      </div>

      <div class="meta-actions">
        <a href="/decks/{deck.id}/analytics" class="btn-analytics">Analytics ↗</a>
        <a href="/decks/{deck.id}/probability" class="btn-analytics btn-probability">Probabilité ↗</a>
        <a href="/decks/{deck.id}/ratio-advice" class="btn-analytics btn-ratios">Ratios ↗</a>
        <a href="/decks/{deck.id}/simulate" class="btn-analytics btn-simulate">Simulateur ↗</a>
        <a href="/decks/{deck.id}/score" class="btn-analytics btn-score">Score ↗</a>
        <a href="/decks/{deck.id}/side-optimizer" class="btn-analytics btn-side">Side ↗</a>
        <a href="/decks/{deck.id}/matchups" class="btn-analytics btn-matchups">Matchups ↗</a>

        <div class="format-toggle" role="group" aria-label="Select format">
          {#each (['TCG', 'OCG'] as const) as fmt}
            <button
              class="format-btn"
              class:active={activeFormat === fmt}
              onclick={() => (activeFormat = fmt)}
              aria-pressed={activeFormat === fmt}
            >{fmt}</button>
          {/each}
        </div>

        {#if legality}
          <div class="legality-badge" class:legal={legality.is_legal} class:illegal={!legality.is_legal}>
            <span class="legality-dot" aria-hidden="true"></span>
            <span class="legality-label">
              {legality.is_legal ? `${activeFormat} Legal` : `${legality.violations.length} violation${legality.violations.length > 1 ? 's' : ''}`}
            </span>
          </div>
        {/if}

        <div class="deck-mgmt">
          <button class="btn-mgmt btn-mgmt--export" onclick={exportYdk} title="Download as .ydk file">
            ↓ Export .ydk
          </button>
          <button
            class="btn-mgmt btn-mgmt--copy"
            onclick={copyAsText}
            title="Copy deck list to clipboard"
            class:btn-mgmt--copied={copyFeedback}
          >
            {copyFeedback ? '✓ Copied' : '⎘ Copy list'}
          </button>
          {#if !$auth.enabled || $auth.user}
            {#if !editing}
              <button class="btn-mgmt" onclick={startEdit} title="Edit deck metadata">✎ Edit</button>
            {/if}
            {#if !confirmDelete}
              <button class="btn-mgmt btn-mgmt--danger" onclick={() => (confirmDelete = true)} title="Delete deck">
                ✕ Delete
              </button>
            {:else}
              <div class="delete-confirm">
                <span class="delete-confirm-label">Delete this deck?</span>
                <button class="btn-delete-confirm" onclick={deleteDeck} disabled={deleting}>
                  {deleting ? 'Deleting…' : 'Yes, delete'}
                </button>
                <button class="btn-ghost btn-cancel-delete" onclick={() => (confirmDelete = false)}>Cancel</button>
              </div>
            {/if}
          {:else if $auth.loaded}
            <a href="/login" class="btn-mgmt btn-mgmt--login">⚿ Login to edit</a>
          {/if}
        </div>

        <p class="deck-date">Imported {formatDate(deck.created_at)}</p>
        {#if deck.updated_at.slice(0, 10) !== deck.created_at.slice(0, 10)}
          <p class="deck-date deck-date--modified">Modified {formatDate(deck.updated_at)}</p>
        {/if}
      </div>
    </div>
  </header>

  {#if !editing && deck.notes}
    <p class="deck-notes">{deck.notes}</p>
  {/if}

  <!-- Sections -->
  {#each [
    { key: 'main', label: 'Main Deck', count: deck.main_count, cards: deck.main },
    { key: 'extra', label: 'Extra Deck', count: deck.extra_count, cards: deck.extra },
    { key: 'side', label: 'Side Deck', count: deck.side_count, cards: deck.side },
  ] as section (section.key)}
    {#if section.cards.length > 0}
      <section class="deck-section">
        <header class="section-header">
          <h2 class="section-title">{section.label}</h2>
          <span class="section-count">{section.count} cards</span>
        </header>
        <div class="card-grid">
          {#each section.cards as c (c.card_id)}
            {@const badge = cardBadge(c.tcg_date, c.ocg_date)}
            {@const violation = violationMap[c.card_id]}
            {@const restricted = restrictedMap[c.card_id]}
            <div class="card-slot" title="{c.name}{c.quantity > 1 ? ` ×${c.quantity}` : ''}{badge ? ` [${badge}]` : ''}{restricted ? ` · ${restricted.status}` : ''}">
              <div class="card-img-wrap"
                class:banned={violation?.status === 'forbidden'}
                class:limited={restricted?.status === 'limited' && !violation}
                class:limited-violation={violation?.status === 'limited'}
                class:semi={restricted?.status === 'semi_limited' && !violation}
                class:semi-violation={violation?.status === 'semi_limited'}
              >
                <img
                  src={c.image_url}
                  alt={c.name}
                  class="card-img"
                  loading="lazy"
                  onerror={handleImgError}
                />
                {#if badge}
                  <span class="format-badge format-badge--{badge.toLowerCase()}">{badge}</span>
                {/if}
                {#if restricted}
                  <span class="ban-badge ban-badge--{restricted.status}" class:is-violation={!!violation}>
                    {banLabel[restricted.status]}
                  </span>
                {/if}
                {#if c.quantity > 1}
                  <span class="qty-badge">×{c.quantity}</span>
                {/if}
              </div>
              <p class="card-name">{c.name}</p>
            </div>
          {/each}
        </div>
      </section>
    {/if}
  {/each}
</div>

<style>
  .page-body {
    padding-top: 2rem;
    padding-bottom: 5rem;
  }

  /* Breadcrumb */
  .breadcrumb {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 2rem;
    font-size: 0.8125rem;
  }
  .breadcrumb-link {
    color: var(--text-tertiary);
    transition: color var(--duration-fast) var(--ease-out);
  }
  .breadcrumb-link:hover {
    color: var(--text-secondary);
  }
  .breadcrumb-sep {
    color: var(--text-tertiary);
    opacity: 0.5;
  }
  .breadcrumb-current {
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 30ch;
  }

  /* Header */
  .deck-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 2rem;
    flex-wrap: wrap;
    margin-bottom: 2rem;
    padding-bottom: 2rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .deck-header-left {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .source-badge {
    display: inline-flex;
    align-self: flex-start;
    align-items: center;
    padding: 0.15rem 0.6rem;
    background: var(--gold-dim);
    border: 1px solid rgba(201, 164, 73, 0.2);
    border-radius: 99px;
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    color: var(--gold);
    text-transform: uppercase;
  }

  .deck-title {
    font-size: 1.875rem;
    font-weight: 700;
    letter-spacing: -0.025em;
    line-height: 1.15;
  }

  .deck-archetype {
    font-size: 0.9375rem;
    color: var(--gold);
    opacity: 0.75;
    font-family: 'Space Grotesk', sans-serif;
    text-decoration: none;
    transition: opacity var(--duration-fast) var(--ease-out);
  }

  .deck-archetype:hover {
    opacity: 1;
  }

  /* Tags display */
  .deck-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
    margin-top: 0.125rem;
  }

  .deck-tag {
    padding: 0.15rem 0.55rem;
    background: rgba(201, 164, 73, 0.1);
    border: 1px solid rgba(201, 164, 73, 0.25);
    border-radius: 99px;
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--gold);
    opacity: 0.9;
  }

  /* Tags in edit form */
  .edit-tags-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-tertiary);
    letter-spacing: 0.04em;
    margin-top: 0.25rem;
  }

  .edit-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
  }

  .edit-tag-btn {
    padding: 0.25rem 0.625rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: 99px;
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--text-tertiary);
    cursor: pointer;
    transition: background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out);
  }

  .edit-tag-btn:hover {
    color: var(--text-secondary);
    border-color: var(--border-strong);
  }

  .edit-tag-btn--active {
    background: rgba(201, 164, 73, 0.12);
    border-color: rgba(201, 164, 73, 0.4);
    color: var(--gold);
  }

  .deck-notes {
    font-size: 0.9rem;
    color: var(--text-secondary);
    line-height: 1.6;
    margin-bottom: 2rem;
    padding: 1rem 1.25rem;
    background: var(--bg-surface);
    border-left: 2px solid var(--border-strong);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  }

  .deck-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .meta-row {
    display: flex;
    align-items: center;
    gap: 0;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .meta-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.625rem 1.125rem;
    gap: 0.1rem;
  }

  .meta-divider {
    width: 1px;
    height: 2.5rem;
    background: var(--border-subtle);
    flex-shrink: 0;
  }

  .meta-label {
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .meta-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1875rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
  }

  .meta-actions {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.375rem;
  }

  /* Edit form */
  .edit-form {
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
    width: 100%;
    max-width: 420px;
  }

  .edit-input {
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.9375rem;
    outline: none;
    transition: border-color var(--duration-fast) var(--ease-out);
  }

  .edit-input--title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.125rem;
    font-weight: 600;
  }

  .edit-input--small {
    font-size: 0.875rem;
  }

  .edit-input:focus {
    border-color: var(--gold);
    box-shadow: 0 0 0 3px rgba(201, 164, 73, 0.1);
  }

  .edit-textarea {
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.875rem;
    outline: none;
    resize: vertical;
    transition: border-color var(--duration-fast) var(--ease-out);
  }

  .edit-textarea:focus {
    border-color: var(--gold);
    box-shadow: 0 0 0 3px rgba(201, 164, 73, 0.1);
  }

  .edit-error {
    font-size: 0.8125rem;
    color: var(--error);
  }

  .edit-actions {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    flex-wrap: wrap;
  }

  .edit-save-btn {
    font-size: 0.875rem;
    padding: 0.5rem 1rem;
  }

  .edit-save-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
    transform: none !important;
    box-shadow: none !important;
  }

  /* Deck management actions */
  .deck-mgmt {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    flex-wrap: wrap;
  }

  .btn-mgmt {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.25rem 0.625rem;
    background: transparent;
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--text-tertiary);
    cursor: pointer;
    transition: color var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out),
      background var(--duration-fast) var(--ease-out);
  }

  .btn-mgmt:hover {
    color: var(--text-secondary);
    border-color: var(--border-strong);
    background: var(--bg-elevated);
  }

  .btn-mgmt--danger:hover {
    color: var(--error);
    border-color: rgba(224, 84, 84, 0.4);
    background: rgba(224, 84, 84, 0.06);
  }

  .btn-mgmt--login {
    text-decoration: none;
    color: var(--gold);
    opacity: 0.6;
  }

  .btn-mgmt--login:hover {
    opacity: 1;
    border-color: rgba(201, 164, 73, 0.35);
  }

  .btn-mgmt--export:hover {
    color: var(--gold);
    border-color: rgba(201, 164, 73, 0.4);
    background: rgba(201, 164, 73, 0.06);
  }

  .btn-mgmt--copy:hover {
    color: var(--text-secondary);
    border-color: var(--border-strong);
    background: var(--bg-elevated);
  }

  .btn-mgmt--copied {
    color: #4ade80 !important;
    border-color: rgba(74, 222, 128, 0.35) !important;
    background: rgba(74, 222, 128, 0.06) !important;
  }

  .delete-confirm {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.75rem;
    background: rgba(224, 84, 84, 0.08);
    border: 1px solid rgba(224, 84, 84, 0.25);
    border-radius: var(--radius-md);
    flex-wrap: wrap;
  }

  .delete-confirm-label {
    font-size: 0.75rem;
    color: var(--error);
    font-weight: 500;
    white-space: nowrap;
  }

  .btn-delete-confirm {
    padding: 0.2rem 0.625rem;
    background: var(--error);
    color: #fff;
    border: none;
    border-radius: var(--radius-sm);
    font-size: 0.6875rem;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
    transition: opacity var(--duration-fast) var(--ease-out);
  }

  .btn-delete-confirm:hover:not(:disabled) {
    opacity: 0.85;
  }

  .btn-delete-confirm:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-cancel-delete {
    font-size: 0.6875rem;
    padding: 0.2rem 0.5rem;
  }

  /* Format toggle */
  .format-toggle {
    display: flex;
    align-items: center;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    overflow: hidden;
    flex-shrink: 0;
  }

  .format-btn {
    padding: 0.25rem 0.625rem;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: var(--text-tertiary);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: color var(--duration-fast) var(--ease-out),
      background var(--duration-fast) var(--ease-out);
  }

  .format-btn + .format-btn {
    border-left: 1px solid var(--border-default);
  }

  .format-btn.active {
    background: var(--gold-dim);
    color: var(--gold);
  }

  .format-btn:hover:not(.active) {
    color: var(--text-secondary);
    background: var(--bg-overlay);
  }

  .btn-analytics {
    display: inline-flex;
    align-items: center;
    padding: 0.375rem 0.875rem;
    border: 1px solid rgba(201, 164, 73, 0.3);
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--gold);
    opacity: 0.8;
    transition: opacity var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out);
  }

  .btn-analytics:hover {
    opacity: 1;
    border-color: var(--gold);
  }

  .btn-probability {
    border-color: rgba(34, 197, 94, 0.3);
    color: #22c55e;
  }
  .btn-probability:hover {
    border-color: #22c55e;
  }

  .btn-ratios {
    border-color: rgba(99, 102, 241, 0.3);
    color: #818cf8;
  }
  .btn-ratios:hover {
    border-color: #818cf8;
  }

  .btn-simulate {
    border-color: rgba(251, 191, 36, 0.3);
    color: #fbbf24;
  }
  .btn-simulate:hover {
    border-color: #fbbf24;
  }

  .btn-score {
    border-color: rgba(34, 211, 238, 0.3);
    color: #22d3ee;
  }
  .btn-score:hover {
    border-color: #22d3ee;
  }

  .btn-side {
    border-color: rgba(250, 204, 21, 0.3);
    color: #facc15;
  }
  .btn-side:hover {
    border-color: #facc15;
  }

  .btn-matchups {
    border-color: rgba(168, 85, 247, 0.3);
    color: #a855f7;
  }
  .btn-matchups:hover {
    border-color: #a855f7;
  }

  .deck-date {
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  .deck-date--modified {
    color: var(--text-tertiary);
    opacity: 0.7;
  }

  /* Deck sections */
  .deck-section {
    margin-bottom: 2.5rem;
  }

  .section-header {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .section-title {
    font-size: 0.875rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-secondary);
  }

  .section-count {
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  /* Card grid */
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
    gap: 0.625rem;
  }

  @media (min-width: 640px) {
    .card-grid {
      grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
    }
  }

  @media (min-width: 1024px) {
    .card-grid {
      grid-template-columns: repeat(auto-fill, minmax(106px, 1fr));
    }
  }

  .card-slot {
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
      transform var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .card-slot:hover .card-img-wrap {
    border-color: var(--gold);
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(201, 164, 73, 0.3);
    z-index: 1;
  }

  .card-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .format-badge {
    position: absolute;
    top: 4px;
    left: 4px;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.5625rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    line-height: 1.6;
    pointer-events: none;
  }

  .format-badge--ocg {
    background: rgba(210, 105, 30, 0.88);
    color: #fff;
  }

  .format-badge--tcg {
    background: rgba(37, 99, 180, 0.82);
    color: #fff;
  }

  /* Ban badges (bottom-left) */
  .ban-badge {
    position: absolute;
    bottom: 4px;
    left: 4px;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.5625rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    line-height: 1.6;
    pointer-events: none;
  }

  /* Ban badge — compliant (muted) */
  .ban-badge--forbidden {
    background: rgba(220, 38, 38, 0.88);
    color: #fff;
  }

  .ban-badge--limited {
    background: rgba(249, 115, 22, 0.55);
    color: #fff;
  }

  .ban-badge--semi_limited {
    background: rgba(234, 179, 8, 0.5);
    color: #000;
  }

  /* Ban badge — violation (fully opaque, pulsing outline) */
  .ban-badge.is-violation {
    outline: 1px solid rgba(255, 255, 255, 0.5);
    opacity: 1 !important;
  }

  .ban-badge--limited.is-violation {
    background: rgba(249, 115, 22, 0.95);
  }

  .ban-badge--semi_limited.is-violation {
    background: rgba(234, 179, 8, 0.95);
    color: #000;
  }

  /* Card border tint */
  .card-img-wrap.banned {
    border-color: rgba(220, 38, 38, 0.6);
    box-shadow: 0 0 0 1px rgba(220, 38, 38, 0.3);
  }

  .card-img-wrap.limited {
    border-color: rgba(249, 115, 22, 0.35);
  }

  .card-img-wrap.limited-violation {
    border-color: rgba(249, 115, 22, 0.6);
    box-shadow: 0 0 0 1px rgba(249, 115, 22, 0.25);
  }

  .card-img-wrap.semi {
    border-color: rgba(234, 179, 8, 0.3);
  }

  .card-img-wrap.semi-violation {
    border-color: rgba(234, 179, 8, 0.55);
    box-shadow: 0 0 0 1px rgba(234, 179, 8, 0.2);
  }

  /* Legality badge in header */
  .legality-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.65rem;
    border-radius: 99px;
    font-size: 0.6875rem;
    font-weight: 600;
  }

  .legality-badge.legal {
    background: rgba(34, 197, 94, 0.12);
    border: 1px solid rgba(34, 197, 94, 0.25);
    color: #4ade80;
  }

  .legality-badge.illegal {
    background: rgba(220, 38, 38, 0.12);
    border: 1px solid rgba(220, 38, 38, 0.3);
    color: #f87171;
  }

  .legality-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .legality-badge.legal .legality-dot {
    background: #4ade80;
  }

  .legality-badge.illegal .legality-dot {
    background: #f87171;
  }

  .qty-badge {
    position: absolute;
    bottom: 4px;
    right: 4px;
    padding: 0.1rem 0.35rem;
    background: rgba(0, 0, 0, 0.75);
    backdrop-filter: blur(4px);
    border-radius: 4px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.6875rem;
    font-weight: 700;
    color: var(--gold);
    letter-spacing: 0.02em;
  }

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
</style>
