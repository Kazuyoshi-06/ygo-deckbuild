import { writable } from 'svelte/store';

export interface AuthState {
  user: string | null;
  enabled: boolean;
  loaded: boolean;
}

function createAuthStore() {
  const { subscribe, set, update } = writable<AuthState>({
    user: null,
    enabled: true,
    loaded: false,
  });

  return {
    subscribe,
    async init() {
      try {
        const res = await fetch('/api/v1/auth/me');
        if (res.ok) {
          const data = await res.json();
          set({ user: data.username, enabled: data.auth_enabled, loaded: true });
        } else {
          update((s) => ({ ...s, user: null, loaded: true }));
        }
      } catch {
        update((s) => ({ ...s, user: null, loaded: true }));
      }
    },
    setUser(username: string, enabled: boolean) {
      set({ user: username, enabled, loaded: true });
    },
    clear() {
      update((s) => ({ ...s, user: null }));
    },
  };
}

export const auth = createAuthStore();
