<script lang="ts">
  import { page } from '$app/stores';
  import { afterNavigate } from '$app/navigation';
  import SearchModal from './SearchModal.svelte';
  import { auth } from '$lib/stores/auth';

  const navLinks = [
    { href: '/decks', label: 'Decks' },
    { href: '/compare', label: 'Compare' },
    { href: '/cards', label: 'Cards' },
    { href: '/analytics', label: 'Analytics' },
    { href: '/banlists', label: 'Banlists' },
    { href: '/tournaments', label: 'Tournaments' },
  ];

  let menuOpen = $state(false);
  let searchOpen = $state(false);

  afterNavigate(() => {
    menuOpen = false;
  });

  function toggleMenu() {
    menuOpen = !menuOpen;
  }

  $effect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        searchOpen = true;
        return;
      }
      if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName ?? '')) {
        e.preventDefault();
        searchOpen = true;
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  });

  async function logout() {
    await fetch('/api/v1/auth/logout', { method: 'POST' });
    auth.clear();
  }
</script>

<header class="nav">
  <div class="nav-inner page-container">
    <a href="/" class="nav-logo" aria-label="YGO Intel home">
      <span class="logo-mark" aria-hidden="true">◆</span>
      <span class="logo-text">YGO<span class="logo-accent">INTEL</span></span>
    </a>

    <nav class="nav-links" aria-label="Main navigation">
      {#each navLinks as link}
        <a
          href={link.href}
          class="nav-link"
          class:active={$page.url.pathname.startsWith(link.href)}
        >
          {link.label}
        </a>
      {/each}
    </nav>

    <div class="nav-actions">
      <button
        class="nav-search-btn"
        onclick={() => (searchOpen = true)}
        aria-label="Search (Ctrl+K)"
        title="Search (Ctrl+K)"
        type="button"
      >
        <span class="nav-search-icon" aria-hidden="true">⌕</span>
        <span class="nav-search-hint">Ctrl+K</span>
      </button>
      <a href="/admin" class="nav-admin-link" title="Admin & sync">
        <span aria-hidden="true">⚙</span>
      </a>
      {#if $auth.loaded && $auth.enabled}
        {#if $auth.user}
          <span class="nav-user" title="Logged in as {$auth.user}">
            <span class="nav-user-dot" aria-hidden="true"></span>{$auth.user}
          </span>
          <button class="nav-logout-btn" onclick={logout} type="button" title="Log out">
            ⎋
          </button>
        {:else}
          <a href="/login" class="nav-login-btn">Login</a>
        {/if}
      {/if}
      <a href="/import" class="btn-primary nav-import-btn">
        Import .ydk
        <span aria-hidden="true" class="nav-import-icon">↑</span>
      </a>
      <button
        class="hamburger"
        aria-label={menuOpen ? 'Close menu' : 'Open menu'}
        aria-expanded={menuOpen}
        onclick={toggleMenu}
      >
        <span class="hamburger-line" class:open={menuOpen}></span>
        <span class="hamburger-line" class:open={menuOpen}></span>
        <span class="hamburger-line" class:open={menuOpen}></span>
      </button>
    </div>
  </div>
</header>

{#if searchOpen}
  <SearchModal onclose={() => (searchOpen = false)} />
{/if}

<!-- Mobile overlay -->
{#if menuOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="mobile-backdrop" onclick={() => (menuOpen = false)} aria-hidden="true"></div>
  <div class="mobile-menu" role="dialog" aria-modal="true" aria-label="Navigation menu">
    <div class="mobile-menu-header">
      <a href="/" class="nav-logo" onclick={() => (menuOpen = false)}>
        <span class="logo-mark" aria-hidden="true">◆</span>
        <span class="logo-text">YGO<span class="logo-accent">INTEL</span></span>
      </a>
      <button class="mobile-close" aria-label="Close menu" onclick={() => (menuOpen = false)}>
        ✕
      </button>
    </div>
    <nav class="mobile-nav" aria-label="Mobile navigation">
      {#each navLinks as link}
        <a
          href={link.href}
          class="mobile-nav-link"
          class:active={$page.url.pathname.startsWith(link.href)}
          onclick={() => (menuOpen = false)}
        >
          {link.label}
        </a>
      {/each}
      <a
        href="/admin"
        class="mobile-nav-link mobile-nav-link--admin"
        onclick={() => (menuOpen = false)}
      >
        <span aria-hidden="true">⚙</span> Admin
      </a>
    </nav>
    <div class="mobile-menu-footer">
      {#if $auth.loaded && $auth.enabled}
        {#if $auth.user}
          <div class="mobile-auth-row">
            <span class="mobile-auth-user">
              <span class="nav-user-dot" aria-hidden="true"></span>{$auth.user}
            </span>
            <button class="mobile-logout-btn" onclick={() => { logout(); menuOpen = false; }} type="button">
              Log out
            </button>
          </div>
        {:else}
          <a href="/login" class="mobile-login-btn" onclick={() => (menuOpen = false)}>
            Log in
          </a>
        {/if}
      {/if}
      <a href="/import" class="btn-primary mobile-import-btn" onclick={() => (menuOpen = false)}>
        Import .ydk ↑
      </a>
    </div>
  </div>
{/if}

<style>
  .nav {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 100;
    height: 60px;
    background: rgba(8, 9, 13, 0.85);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border-subtle);
  }

  .nav-inner {
    display: flex;
    align-items: center;
    height: 100%;
    gap: 2rem;
  }

  .nav-logo {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    text-decoration: none;
    flex-shrink: 0;
  }

  .logo-mark {
    color: var(--gold);
    font-size: 1rem;
    line-height: 1;
  }

  .logo-text {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 0.9375rem;
    letter-spacing: 0.04em;
    color: var(--text-primary);
  }

  .logo-accent {
    color: var(--gold);
  }

  .nav-links {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    flex: 1;
  }

  .nav-link {
    padding: 0.375rem 0.75rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
    border-radius: var(--radius-sm);
    transition: color var(--duration-fast) var(--ease-out),
      background var(--duration-fast) var(--ease-out);
    text-decoration: none;
  }

  .nav-link:hover {
    color: var(--text-primary);
    background: var(--bg-elevated);
  }

  .nav-link.active {
    color: var(--text-primary);
    background: var(--bg-elevated);
  }

  .nav-actions {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
  }

  /* Search button */
  .nav-search-btn {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.375rem 0.625rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-tertiary);
    font-family: inherit;
    font-size: 0.8125rem;
    cursor: pointer;
    transition: border-color var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .nav-search-btn:hover {
    border-color: var(--border-subtle);
    color: var(--text-secondary);
    box-shadow: 0 0 0 2px rgba(201, 164, 73, 0.08);
  }

  .nav-search-icon {
    font-size: 1rem;
    line-height: 1;
  }

  .nav-search-hint {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.625rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    opacity: 0.6;
  }

  .nav-admin-link {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    color: var(--text-tertiary);
    border-radius: var(--radius-sm);
    font-size: 1rem;
    transition: color var(--duration-fast) var(--ease-out),
      background var(--duration-fast) var(--ease-out);
  }

  .nav-admin-link:hover {
    color: var(--text-secondary);
    background: var(--bg-elevated);
  }

  .nav-import-btn {
    font-size: 0.8125rem;
    padding: 0.5rem 1rem;
  }

  .nav-import-icon {
    font-size: 0.75rem;
    opacity: 0.8;
  }

  /* Auth indicators */
  .nav-user {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 500;
  }

  .nav-user-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #4caf7d;
    flex-shrink: 0;
  }

  .nav-logout-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    background: transparent;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    color: var(--text-tertiary);
    font-size: 0.875rem;
    cursor: pointer;
    transition: color var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out),
      background var(--duration-fast) var(--ease-out);
  }

  .nav-logout-btn:hover {
    color: var(--text-secondary);
    border-color: var(--border-default);
    background: var(--bg-elevated);
  }

  .nav-login-btn {
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--text-secondary);
    padding: 0.375rem 0.75rem;
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    text-decoration: none;
    transition: color var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out);
  }

  .nav-login-btn:hover {
    color: var(--gold);
    border-color: rgba(201, 164, 73, 0.4);
  }

  /* Hamburger */
  .hamburger {
    display: none;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 5px;
    width: 34px;
    height: 34px;
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 4px;
    border-radius: var(--radius-sm);
    transition: background var(--duration-fast) var(--ease-out);
  }

  .hamburger:hover {
    background: var(--bg-elevated);
  }

  .hamburger-line {
    display: block;
    width: 18px;
    height: 1.5px;
    background: var(--text-secondary);
    border-radius: 2px;
    transition: transform var(--duration-base) var(--ease-out),
      opacity var(--duration-base) var(--ease-out);
    transform-origin: center;
  }

  .hamburger-line:nth-child(1).open {
    transform: translateY(6.5px) rotate(45deg);
  }

  .hamburger-line:nth-child(2).open {
    opacity: 0;
    transform: scaleX(0);
  }

  .hamburger-line:nth-child(3).open {
    transform: translateY(-6.5px) rotate(-45deg);
  }

  @media (max-width: 640px) {
    .nav-links {
      display: none;
    }

    .nav-search-btn {
      display: none;
    }

    .nav-admin-link {
      display: none;
    }

    .nav-import-btn {
      display: none;
    }

    .hamburger {
      display: flex;
    }
  }

  /* Mobile backdrop */
  .mobile-backdrop {
    position: fixed;
    inset: 0;
    z-index: 150;
    background: rgba(8, 9, 13, 0.7);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
  }

  /* Mobile menu drawer */
  .mobile-menu {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 200;
    width: min(320px, 88vw);
    background: var(--bg-surface);
    border-left: 1px solid var(--border-default);
    display: flex;
    flex-direction: column;
    animation: slideIn 200ms var(--ease-out);
  }

  @keyframes slideIn {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }

  .mobile-menu-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 1.25rem;
    height: 60px;
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .mobile-close {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    background: transparent;
    border: none;
    cursor: pointer;
    color: var(--text-tertiary);
    font-size: 0.875rem;
    border-radius: var(--radius-sm);
    transition: background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
  }

  .mobile-close:hover {
    background: var(--bg-elevated);
    color: var(--text-primary);
  }

  .mobile-nav {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 1rem 0;
    overflow-y: auto;
  }

  .mobile-nav-link {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    padding: 0.875rem 1.5rem;
    font-size: 1rem;
    font-weight: 500;
    color: var(--text-secondary);
    text-decoration: none;
    transition: color var(--duration-fast) var(--ease-out),
      background var(--duration-fast) var(--ease-out);
  }

  .mobile-nav-link:hover,
  .mobile-nav-link.active {
    color: var(--text-primary);
    background: var(--bg-elevated);
  }

  .mobile-nav-link.active {
    color: var(--gold);
  }

  .mobile-nav-link--admin {
    margin-top: auto;
    border-top: 1px solid var(--border-subtle);
    margin-top: 0.5rem;
    padding-top: 1rem;
    color: var(--text-tertiary);
    font-size: 0.9rem;
  }

  .mobile-menu-footer {
    padding: 1.25rem;
    border-top: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .mobile-import-btn {
    width: 100%;
    justify-content: center;
  }

  .mobile-auth-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
  }

  .mobile-auth-user {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.875rem;
    color: var(--text-tertiary);
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 500;
  }

  .mobile-logout-btn {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    background: transparent;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 0.25rem 0.625rem;
    cursor: pointer;
    transition: color var(--duration-fast) var(--ease-out);
  }

  .mobile-logout-btn:hover {
    color: var(--text-secondary);
  }

  .mobile-login-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    padding: 0.625rem;
    margin-bottom: 0.75rem;
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--text-secondary);
    text-decoration: none;
    transition: border-color var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
  }

  .mobile-login-btn:hover {
    color: var(--gold);
    border-color: rgba(201, 164, 73, 0.4);
  }
</style>
