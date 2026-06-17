import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
  const res = await fetch(`/api/v1/decks/${params.id}/tournament-prep`);
  if (res.status === 404) throw error(404, 'Deck not found');
  if (!res.ok) throw error(500, 'Failed to load tournament prep');
  const prep = await res.json();
  return { deckId: Number(params.id), prep };
};
