import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
  const [res1, res2] = await Promise.all([
    fetch(`/api/v1/decks/${params.id}/simulate?n=10000&hand=5`),
    fetch(`/api/v1/decks/${params.id}/simulate?n=10000&hand=6`),
  ]);
  if (res1.status === 404 || res2.status === 404) throw error(404, 'Deck not found');
  if (!res1.ok || !res2.ok) throw error(500, 'Failed to run simulation');
  const [initial1, initial2] = await Promise.all([res1.json(), res2.json()]);
  return { deckId: Number(params.id), initial1, initial2 };
};
