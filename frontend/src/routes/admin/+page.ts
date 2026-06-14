import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
  try {
    const res = await fetch('/api/v1/admin/sync/runs?limit=15');
    if (!res.ok) return { recentRuns: [] };
    const runs = await res.json();
    return { recentRuns: runs };
  } catch {
    return { recentRuns: [] };
  }
};
