import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, url }) => {
  try {
    const q = url.searchParams.get('q') ?? '';
    const params = new URLSearchParams({ limit: '48', page: '1' });
    if (q) params.set('q', q);
    const res = await fetch(`/api/v1/cards?${params}`);
    if (!res.ok) return { initialCards: [], total: 0, initialQuery: q };
    const data = await res.json();
    return { initialCards: data.items ?? [], total: data.total ?? 0, initialQuery: q };
  } catch {
    return { initialCards: [], total: 0, initialQuery: '' };
  }
};
