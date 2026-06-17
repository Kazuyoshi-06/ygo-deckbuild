<script lang="ts">
  interface CardData {
    id: number;
    name: string;
    type: string;
    frame_type: string;
    race: string | null;
    attribute: string | null;
    archetype: string | null;
    level_rank_link: number | null;
    atk: number | null;
    def_: number | null;
    linkval: number | null;
    description: string | null;
    image_url: string;
  }

  interface Props {
    cardId: number | null;
    anchorX: number;
    anchorY: number;
  }

  let { cardId, anchorX, anchorY }: Props = $props();

  const cache = new Map<number, CardData>();
  let cardData: CardData | null = $state(null);
  let loading = $state(false);

  const PREVIEW_W = 260;
  const OFFSET = 16;
  const APPROX_H = 450;

  $effect(() => {
    const id = cardId;
    if (!id) {
      cardData = null;
      return;
    }
    if (cache.has(id)) {
      cardData = cache.get(id)!;
      return;
    }
    let cancelled = false;
    loading = true;
    cardData = null;
    fetch(`/api/v1/cards/${id}`)
      .then(r => (r.ok ? r.json() : null))
      .then(d => {
        if (cancelled || !d) return;
        cache.set(id, d);
        cardData = d;
        loading = false;
      })
      .catch(() => {
        if (!cancelled) loading = false;
      });
    return () => {
      cancelled = true;
      loading = false;
    };
  });

  let left = $derived(
    typeof window !== 'undefined'
      ? anchorX + OFFSET + PREVIEW_W > window.innerWidth - 8
        ? anchorX - OFFSET - PREVIEW_W
        : anchorX + OFFSET
      : anchorX + OFFSET
  );

  let top = $derived(
    typeof window !== 'undefined'
      ? Math.max(8, Math.min(anchorY - 80, window.innerHeight - APPROX_H - 8))
      : anchorY - 80
  );

  function typeInfo(card: CardData): string {
    const parts: string[] = [];
    if (card.attribute) parts.push(card.attribute);
    if (card.race) parts.push(card.race);
    if (card.level_rank_link !== null) {
      if (card.frame_type === 'link') parts.push(`Link ${card.linkval ?? card.level_rank_link}`);
      else if (card.frame_type === 'xyz' || card.frame_type.startsWith('xyz'))
        parts.push(`Rank ${card.level_rank_link}`);
      else parts.push(`Level ${card.level_rank_link}`);
    }
    return parts.join(' / ');
  }

  function statsLine(card: CardData): string {
    const parts: string[] = [];
    if (card.atk !== null) parts.push(`ATK ${card.atk === -1 ? '?' : card.atk}`);
    if (card.def_ !== null && card.frame_type !== 'link')
      parts.push(`DEF ${card.def_ === -1 ? '?' : card.def_}`);
    return parts.join(' / ');
  }

  function handleImgError(e: Event) {
    (e.target as HTMLImageElement).src = '/media/placeholder-card.svg';
  }
</script>

{#if cardId !== null}
  <div
    class="card-preview"
    style="left: {left}px; top: {top}px;"
    aria-hidden="true"
    role="tooltip"
  >
    {#if loading && !cardData}
      <div class="preview-loading">
        <span class="preview-spinner" aria-hidden="true"></span>
      </div>
    {:else if cardData}
      <div class="preview-img-wrap">
        <img
          src={cardData.image_url}
          alt={cardData.name}
          class="preview-img"
          onerror={handleImgError}
        />
      </div>
      <div class="preview-body">
        <p class="preview-name">{cardData.name}</p>
        {#if typeInfo(cardData)}
          <p class="preview-meta">{typeInfo(cardData)}</p>
        {/if}
        <p class="preview-type">{cardData.type}</p>
        {#if statsLine(cardData)}
          <p class="preview-stats">{statsLine(cardData)}</p>
        {/if}
        {#if cardData.archetype}
          <p class="preview-archetype">{cardData.archetype}</p>
        {/if}
        {#if cardData.description}
          <p class="preview-desc">{cardData.description}</p>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .card-preview {
    position: fixed;
    z-index: 9999;
    width: 260px;
    background: rgba(12, 13, 20, 0.98);
    border: 1px solid rgba(201, 164, 73, 0.35);
    border-radius: 10px;
    box-shadow:
      0 24px 64px rgba(0, 0, 0, 0.75),
      0 0 0 1px rgba(201, 164, 73, 0.12),
      inset 0 1px 0 rgba(255, 255, 255, 0.04);
    pointer-events: none;
    overflow: hidden;
    animation: preview-in 0.14s cubic-bezier(0.22, 1, 0.36, 1) both;
  }

  @keyframes preview-in {
    from {
      opacity: 0;
      transform: scale(0.94) translateY(6px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }

  /* Loading state */
  .preview-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 80px;
  }

  .preview-spinner {
    display: block;
    width: 20px;
    height: 20px;
    border: 2px solid rgba(201, 164, 73, 0.2);
    border-top-color: rgba(201, 164, 73, 0.8);
    border-radius: 50%;
    animation: spin 0.65s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* Card image: top portion shown (artwork + name area) */
  .preview-img-wrap {
    width: 100%;
    max-height: 200px;
    overflow: hidden;
    background: var(--bg-elevated, #1a1c26);
    border-bottom: 1px solid rgba(201, 164, 73, 0.18);
  }

  .preview-img {
    width: 100%;
    display: block;
    object-fit: cover;
    object-position: center top;
  }

  /* Info block */
  .preview-body {
    padding: 0.7rem 0.875rem 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .preview-name {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8125rem;
    font-weight: 700;
    color: #c9a449;
    line-height: 1.3;
    margin: 0;
  }

  .preview-meta {
    font-size: 0.6875rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.65);
    margin: 0;
    letter-spacing: 0.02em;
  }

  .preview-type {
    font-size: 0.625rem;
    color: rgba(255, 255, 255, 0.4);
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.07em;
  }

  .preview-stats {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.85);
    margin: 0.15rem 0 0;
    letter-spacing: 0.01em;
  }

  .preview-archetype {
    font-size: 0.5625rem;
    color: rgba(201, 164, 73, 0.55);
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin: 0.1rem 0 0;
  }

  .preview-desc {
    font-size: 0.6875rem;
    color: rgba(255, 255, 255, 0.55);
    line-height: 1.55;
    margin: 0.4rem 0 0;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 6;
    line-clamp: 6;
    -webkit-box-orient: vertical;
    padding-top: 0.4rem;
    border-top: 1px solid rgba(255, 255, 255, 0.07);
  }
</style>
