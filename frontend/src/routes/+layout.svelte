<script lang="ts">
  import { onMount } from 'svelte';
  import '../app.css';
  import Nav from '$lib/components/Nav.svelte';
  import { navigating } from '$app/stores';
  import { dev } from '$app/environment';
  import { auth } from '$lib/stores/auth';

  let { children } = $props();

  onMount(() => {
    auth.init();

    // Skip in dev — the service worker's cache would otherwise fight with Vite's HMR.
    if (!dev && 'serviceWorker' in navigator) {
      navigator.serviceWorker.register('/service-worker.js').catch(() => {
        // Installability/offline support is a progressive enhancement — a failed
        // registration (unsupported browser, blocked by extension, etc.) shouldn't
        // surface as an error to the user.
      });
    }
  });

  const navLinks = [
    { href: '/decks', label: 'Decks' },
    { href: '/cards', label: 'Cards' },
    { href: '/analytics', label: 'Analytics' },
    { href: '/banlists', label: 'Banlists' },
    { href: '/import', label: 'Import' },
  ];
</script>

<Nav />

{#if $navigating}
  <div class="nav-loader" aria-hidden="true"></div>
{/if}

<div class="layout-content">
  {@render children()}
</div>

<footer class="site-footer">
  <div class="page-container footer-inner">
    <a href="/" class="footer-brand" aria-label="YGO Intel home">
      <span class="footer-mark" aria-hidden="true">◆</span>
      <span class="footer-name">YGO<span class="footer-accent">INTEL</span></span>
    </a>

    <nav class="footer-links" aria-label="Footer navigation">
      {#each navLinks as link}
        <a href={link.href} class="footer-link">{link.label}</a>
      {/each}
    </nav>

    <p class="footer-copy">Deck intelligence for competitive play</p>
  </div>
</footer>

<style>
  .layout-content {
    padding-top: 60px;
    min-height: calc(100dvh - 56px);
  }

  /* ── Navigation loader ──────────────────────────────────────────────────── */
  .nav-loader {
    position: fixed;
    top: 60px;
    left: 0;
    right: 0;
    height: 2px;
    z-index: 99;
    overflow: hidden;
  }

  .nav-loader::after {
    content: '';
    display: block;
    height: 100%;
    width: 40%;
    background: var(--gold);
    border-radius: 0 2px 2px 0;
    animation: navslide 1s var(--ease-out) infinite;
    opacity: 0.85;
  }

  @keyframes navslide {
    0% { transform: translateX(-150%); }
    60% { transform: translateX(200%); }
    100% { transform: translateX(350%); }
  }

  /* ── Footer ─────────────────────────────────────────────────────────────── */
  .site-footer {
    border-top: 1px solid var(--border-subtle);
    background: var(--bg-surface);
  }

  .footer-inner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
    padding-top: 1.25rem;
    padding-bottom: 1.25rem;
    flex-wrap: wrap;
  }

  .footer-brand {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    text-decoration: none;
    flex-shrink: 0;
  }

  .footer-mark {
    color: var(--gold);
    font-size: 0.75rem;
    line-height: 1;
    opacity: 0.7;
  }

  .footer-name {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 0.8125rem;
    letter-spacing: 0.04em;
    color: var(--text-tertiary);
  }

  .footer-accent {
    color: var(--gold);
    opacity: 0.7;
  }

  .footer-links {
    display: flex;
    align-items: center;
    gap: 0.125rem;
    flex-wrap: wrap;
  }

  .footer-link {
    padding: 0.25rem 0.625rem;
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    border-radius: var(--radius-sm);
    transition: color var(--duration-fast) var(--ease-out),
      background var(--duration-fast) var(--ease-out);
    text-decoration: none;
  }

  .footer-link:hover {
    color: var(--text-secondary);
    background: var(--bg-elevated);
  }

  .footer-copy {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    opacity: 0.6;
    white-space: nowrap;
  }

  @media (max-width: 640px) {
    .footer-links {
      display: none;
    }
  }
</style>
