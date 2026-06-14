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

interface LatestBanlists {
  tcg: { id: number; format: string; effective_date: string; forbidden_count: number; limited_count: number; semi_limited_count: number } | null;
  ocg: { id: number; format: string; effective_date: string; forbidden_count: number; limited_count: number; semi_limited_count: number } | null;
}

export const load: PageLoad = async ({ fetch }) => {
  const latest: LatestBanlists = await fetch('/api/v1/banlists/latest').then((r) => r.json());

  const [tcg, ocg] = await Promise.all([
    latest.tcg ? fetch(`/api/v1/banlists/${latest.tcg.id}`).then((r) => r.json() as Promise<BanlistDetail>) : Promise.resolve(null),
    latest.ocg ? fetch(`/api/v1/banlists/${latest.ocg.id}`).then((r) => r.json() as Promise<BanlistDetail>) : Promise.resolve(null),
  ]);

  return { tcg, ocg };
};
