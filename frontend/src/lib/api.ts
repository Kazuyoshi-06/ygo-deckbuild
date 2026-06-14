const API_BASE = (import.meta.env.PUBLIC_API_URL as string | undefined) ?? 'http://localhost:8000';

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    throw new ApiError(res.status, `API ${res.status}: ${res.statusText}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string }>('/health'),

  cards: {
    list: (params?: { q?: string; page?: number; limit?: number }) => {
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      return request<{ items: unknown[]; total: number }>(`/api/v1/cards${qs ? `?${qs}` : ''}`);
    },
  },

  decks: {
    list: () => request<{ items: unknown[]; total: number }>('/api/v1/decks'),
  },
};

export { ApiError };
