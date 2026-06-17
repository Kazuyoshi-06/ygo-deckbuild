import type { PageLoad } from './$types';

interface BanlistEntry {
  card_id: number;
  external_card_id: number;
  name: string;
  image_url: string;
  status: string;
  limit_value: number;
}

interface BanlistDetail {
  id: number;
  format: string;
  effective_date: string;
  version_label: string | null;
  forbidden: BanlistEntry[];
  limited: BanlistEntry[];
  semi_limited: BanlistEntry[];
}

interface BanlistSummary {
  id: number;
  format: string;
  effective_date: string;
  version_label: string | null;
  forbidden_count: number;
  limited_count: number;
  semi_limited_count: number;
}

interface LatestBanlists {
  tcg: BanlistSummary | null;
  ocg: BanlistSummary | null;
}

export const load: PageLoad = async ({ fetch }) => {
  const [latest, allBanlists] = await Promise.all([
    fetch('/api/v1/banlists/latest').then((r) => r.json() as Promise<LatestBanlists>),
    fetch('/api/v1/banlists').then((r) => r.json() as Promise<BanlistSummary[]>),
  ]);

  const [tcg, ocg, predictionTCG, predictionOCG] = await Promise.all([
    latest.tcg ? fetch(`/api/v1/banlists/${latest.tcg.id}`).then((r) => r.json() as Promise<BanlistDetail>) : Promise.resolve(null),
    latest.ocg ? fetch(`/api/v1/banlists/${latest.ocg.id}`).then((r) => r.json() as Promise<BanlistDetail>) : Promise.resolve(null),
    fetch('/api/v1/banlists/prediction?format=TCG').then((r) => (r.ok ? r.json() : null)),
    fetch('/api/v1/banlists/prediction?format=OCG').then((r) => (r.ok ? r.json() : null)),
  ]);

  return { tcg, ocg, allBanlists, predictionTCG, predictionOCG };
};
