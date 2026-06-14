import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
  try {
    const [analyticsRes, decksRes] = await Promise.all([
      fetch(`/api/v1/analytics/archetypes/${encodeURIComponent(params.label)}`),
      fetch(`/api/v1/decks?archetype=${encodeURIComponent(params.label)}&limit=50`),
    ]);
    const analytics = analyticsRes.ok ? await analyticsRes.json() : null;
    const decksData = decksRes.ok ? await decksRes.json() : null;
    return { analytics, decks: decksData?.items ?? [], label: params.label };
  } catch {
    return { analytics: null, decks: [], label: params.label };
  }
};
