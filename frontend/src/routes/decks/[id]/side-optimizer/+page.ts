import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
  const res = await fetch(`/api/v1/decks/${params.id}/side-optimizer`);
  if (res.status === 404) throw error(404, 'Deck not found');
  if (!res.ok) throw error(500, 'Failed to load side optimizer');
  const optimizer = await res.json();
  return { deckId: Number(params.id), optimizer };
};
