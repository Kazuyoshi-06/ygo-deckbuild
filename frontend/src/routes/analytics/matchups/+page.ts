import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
  const res = await fetch('/api/v1/analytics/matchups');
  const matrix = res.ok ? await res.json() : null;
  return { matrix };
};
