<script lang="ts">
  import { page } from '$app/stores';
</script>

<svelte:head>
  <title>{$page.status === 404 ? '404 Not Found' : 'Error'} — YGO Intel</title>
</svelte:head>

<div class="page-container error-body">
  <div class="error-card">
    <div class="error-code" aria-hidden="true">{$page.status}</div>
    <h1 class="error-title">
      {#if $page.status === 404}
        Page not found
      {:else if $page.status === 500}
        Server error
      {:else if $page.status === 403}
        Access denied
      {:else}
        Something went wrong
      {/if}
    </h1>
    <p class="error-sub">
      {#if $page.status === 404}
        The page you're looking for doesn't exist or has been moved.
      {:else if $page.error?.message}
        {$page.error.message}
      {:else}
        An unexpected error occurred. Please try again.
      {/if}
    </p>
    <div class="error-actions">
      <a href="/" class="btn-ghost">← Home</a>
      <a href="/decks" class="btn-primary">Browse decks</a>
    </div>
  </div>
</div>

<style>
  .error-body {
    min-height: calc(100dvh - 60px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding-top: 2rem;
    padding-bottom: 4rem;
  }

  .error-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    max-width: 420px;
    width: 100%;
  }

  .error-code {
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(4rem, 12vw, 7rem);
    font-weight: 700;
    letter-spacing: -0.04em;
    color: var(--text-tertiary);
    opacity: 0.35;
    line-height: 1;
    margin-bottom: 1.5rem;
    user-select: none;
  }

  .error-title {
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: 0.75rem;
  }

  .error-sub {
    font-size: 0.9375rem;
    color: var(--text-secondary);
    line-height: 1.65;
    margin-bottom: 2rem;
    max-width: 34ch;
  }

  .error-actions {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    justify-content: center;
  }
</style>
