import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
  const res = await fetch('/api/v1/cards?limit=24');
  if (!res.ok) return { initialCards: [] };
  const data = await res.json();
  return { initialCards: data.items ?? [] };
};
