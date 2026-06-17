import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
  const [deckRes, tcgRes, ocgRes, banlistsRes] = await Promise.all([
    fetch(`/api/v1/decks/${params.id}`),
    fetch(`/api/v1/decks/${params.id}/legality?format=TCG`),
    fetch(`/api/v1/decks/${params.id}/legality?format=OCG`),
    fetch('/api/v1/banlists'),
  ]);
  if (deckRes.status === 404) throw error(404, 'Deck not found');
  if (!deckRes.ok) throw error(500, 'Failed to load deck');
  const deck = await deckRes.json();
  const legalityTCG = tcgRes.ok ? await tcgRes.json() : null;
  const legalityOCG = ocgRes.ok ? await ocgRes.json() : null;
  const allBanlists = banlistsRes.ok ? await banlistsRes.json() : [];
  return { deck, legalityTCG, legalityOCG, allBanlists };
};
