<script lang="ts">
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';

  let username = $state('');
  let password = $state('');
  let error = $state('');
  let loading = $state(false);

  async function submit() {
    if (!username.trim() || !password) return;
    loading = true;
    error = '';
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      if (res.ok) {
        const data = await res.json();
        auth.setUser(data.username, data.auth_enabled);
        goto('/');
      } else {
        const body = await res.json().catch(() => ({}));
        error = body.detail ?? 'Invalid credentials';
      }
    } catch {
      error = 'Network error — make sure the backend is running';
    } finally {
      loading = false;
    }
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter') submit();
  }
</script>

<svelte:head>
  <title>Login — YGO Intel</title>
</svelte:head>

<div class="login-page">
  <div class="login-card">
    <div class="login-header">
      <a href="/" class="login-logo" aria-label="YGO Intel home">
        <span class="logo-mark" aria-hidden="true">◆</span>
        <span class="logo-text">YGO<span class="logo-accent">INTEL</span></span>
      </a>
      <h1 class="login-title">Sign in</h1>
      <p class="login-sub">Access protected features</p>
    </div>

    <form class="login-form" onsubmit={(e) => { e.preventDefault(); submit(); }}>
      <div class="field">
        <label class="field-label" for="username">Username</label>
        <input
          id="username"
          class="field-input"
          type="text"
          autocomplete="username"
          placeholder="admin"
          bind:value={username}
          onkeydown={onKeyDown}
          disabled={loading}
        />
      </div>

      <div class="field">
        <label class="field-label" for="password">Password</label>
        <input
          id="password"
          class="field-input"
          type="password"
          autocomplete="current-password"
          placeholder="••••••••"
          bind:value={password}
          onkeydown={onKeyDown}
          disabled={loading}
        />
      </div>

      {#if error}
        <p class="login-error" role="alert">{error}</p>
      {/if}

      <button
        class="btn-primary login-btn"
        type="submit"
        disabled={loading || !username.trim() || !password}
      >
        {loading ? 'Signing in…' : 'Sign in'}
      </button>
    </form>

    <p class="login-footer">
      <a href="/" class="login-back">← Back to home</a>
    </p>
  </div>
</div>

<style>
  .login-page {
    min-height: calc(100dvh - 60px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem 1rem;
  }

  .login-card {
    width: 100%;
    max-width: 380px;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    padding: 2.5rem 2rem;
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .login-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .login-logo {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    text-decoration: none;
    margin-bottom: 1.5rem;
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

  .login-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.375rem;
  }

  .login-sub {
    font-size: 0.875rem;
    color: var(--text-tertiary);
  }

  .login-form {
    display: flex;
    flex-direction: column;
    gap: 1.125rem;
  }

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
    background: var(--bg-base);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.9375rem;
    transition: border-color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
    box-sizing: border-box;
  }

  .field-input:focus {
    outline: none;
    border-color: var(--gold);
    box-shadow: 0 0 0 3px rgba(201, 164, 73, 0.12);
  }

  .field-input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .login-error {
    font-size: 0.8125rem;
    color: var(--danger, #e05c5c);
    background: rgba(224, 92, 92, 0.08);
    border: 1px solid rgba(224, 92, 92, 0.2);
    border-radius: var(--radius-sm);
    padding: 0.5rem 0.75rem;
    margin: 0;
  }

  .login-btn {
    width: 100%;
    justify-content: center;
    padding: 0.75rem;
    font-size: 0.9375rem;
    margin-top: 0.25rem;
  }

  .login-footer {
    text-align: center;
    margin-top: 1.5rem;
  }

  .login-back {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    transition: color var(--duration-fast) var(--ease-out);
    text-decoration: none;
  }

  .login-back:hover {
    color: var(--text-secondary);
  }
</style>
