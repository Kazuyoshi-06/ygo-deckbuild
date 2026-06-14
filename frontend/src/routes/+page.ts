import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
  try {
    const res = await fetch('/api/v1/analytics/overview');
    if (!res.ok) return { overview: null };
    return { overview: await res.json() };
  } catch {
    return { overview: null };
  }
};
