import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
  const res = await fetch(`/api/v1/decks/${params.id}/probability`);
  if (res.status === 404) throw error(404, 'Deck not found');
  if (!res.ok) throw error(500, 'Failed to load probability data');
  const probability = await res.json();
  return { deckId: Number(params.id), probability };
};
