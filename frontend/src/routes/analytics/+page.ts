import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
  const [overviewRes, metaWinRes, trendingRes, ocgTcgRes] = await Promise.all([
    fetch('/api/v1/analytics/overview'),
    fetch('/api/v1/analytics/meta-vs-win-share'),
    fetch('/api/v1/analytics/trending'),
    fetch('/api/v1/analytics/ocg-tcg-pipeline'),
  ]);
  return {
    overview: overviewRes.ok ? await overviewRes.json() : null,
    metaWinShare: metaWinRes.ok ? await metaWinRes.json() : null,
    trending: trendingRes.ok ? await trendingRes.json() : null,
    ocgTcgPipeline: ocgTcgRes.ok ? await ocgTcgRes.json() : null,
  };
};
