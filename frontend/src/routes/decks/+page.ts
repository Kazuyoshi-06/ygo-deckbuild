import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
  const res = await fetch('/api/v1/decks?limit=50');
  if (!res.ok) return { items: [], total: 0 };
  return res.json();
};
