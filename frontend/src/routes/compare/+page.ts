import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
  const res = await fetch('/api/v1/decks?limit=100&page=1');
  const data = res.ok ? await res.json() : { items: [] };
  return { decks: (data.items ?? []) as DeckSummary[] };
};

interface DeckSummary {
  id: number;
  title: string;
  archetype_label: string | null;
  tags: string[];
  created_at: string;
}
