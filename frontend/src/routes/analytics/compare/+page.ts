import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, url }) => {
  const raw = url.searchParams.get('archetypes') ?? '';
  const labels = [...new Set(raw.split(',').map((s) => s.trim()).filter(Boolean))];

  const overviewRes = await fetch('/api/v1/analytics/overview');
  const overview = overviewRes.ok ? await overviewRes.json() : null;
  const topArchetypes: string[] = (overview?.top_archetypes ?? []).map(
    (a: { label: string }) => a.label
  );

  if (labels.length < 2) {
    return { compare: null, error: null, labels, topArchetypes };
  }

  const compareRes = await fetch(
    `/api/v1/analytics/compare?archetypes=${encodeURIComponent(labels.join(','))}`
  );
  if (!compareRes.ok) {
    const body = await compareRes.json().catch(() => null);
    return { compare: null, error: body?.detail ?? `Request failed (${compareRes.status})`, labels, topArchetypes };
  }

  return { compare: await compareRes.json(), error: null, labels, topArchetypes };
};
