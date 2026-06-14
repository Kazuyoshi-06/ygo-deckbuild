import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
  const res = await fetch(
    `/api/v1/analytics/archetypes/${encodeURIComponent(params.label)}/evolution?months=12`
  );
  const evolution = res.ok ? await res.json() : null;
  return { label: params.label, evolution };
};
