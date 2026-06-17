import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
  const [cardRes, historyRes] = await Promise.all([
    fetch(`/api/v1/cards/${params.id}`),
    fetch(`/api/v1/banlists/cards/${params.id}/history`),
  ]);
  if (cardRes.status === 404) throw error(404, 'Card not found');
  if (!cardRes.ok) throw error(500, 'Failed to load card');
  const card = await cardRes.json();
  const history = historyRes.ok ? await historyRes.json() : [];

  const formatsToCheck: ('TCG' | 'OCG')[] = (['TCG', 'OCG'] as const).filter(
    (fmt) => card.current_banlist_status?.[fmt.toLowerCase()] === 'forbidden'
  );

  const replacements: Record<string, unknown> = {};
  if (formatsToCheck.length > 0) {
    const results = await Promise.all(
      formatsToCheck.map((fmt) =>
        fetch(`/api/v1/banlists/cards/${params.id}/replacements?format=${fmt}`).then((r) =>
          r.ok ? r.json() : null
        )
      )
    );
    formatsToCheck.forEach((fmt, i) => {
      replacements[fmt] = results[i];
    });
  }

  return { card, history, replacements };
};
