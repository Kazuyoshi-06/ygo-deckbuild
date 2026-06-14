import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
  const [analyticsRes, deckRes] = await Promise.all([
    fetch(`/api/v1/analytics/decks/${params.id}`),
    fetch(`/api/v1/decks/${params.id}`),
  ]);

  const analytics = analyticsRes.ok ? await analyticsRes.json() : null;
  const deck = deckRes.ok ? await deckRes.json() : null;

  return { analytics, deck };
};
