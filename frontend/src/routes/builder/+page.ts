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

function buildBanMap(bl: BanlistDetail | null): Record<number, string> {
  if (!bl) return {};
  const m: Record<number, string> = {};
  for (const e of bl.forbidden) m[e.card_id] = 'forbidden';
  for (const e of bl.limited) m[e.card_id] = 'limited';
  for (const e of bl.semi_limited) m[e.card_id] = 'semi_limited';
  return m;
}

export const load: PageLoad = async ({ fetch }) => {
  const [cardsRes, latestRes] = await Promise.all([
    fetch('/api/v1/cards?limit=24'),
    fetch('/api/v1/banlists/latest'),
  ]);

  const [cardsData, latest] = await Promise.all([
    cardsRes.ok ? cardsRes.json() : Promise.resolve({ items: [] }),
    latestRes.ok ? latestRes.json() : Promise.resolve({ tcg: null, ocg: null }),
  ]);

  const [tcgDetail, ocgDetail] = await Promise.all([
    latest.tcg
      ? fetch(`/api/v1/banlists/${latest.tcg.id}`).then((r) =>
          r.ok ? (r.json() as Promise<BanlistDetail>) : null
        )
      : Promise.resolve(null),
    latest.ocg
      ? fetch(`/api/v1/banlists/${latest.ocg.id}`).then((r) =>
          r.ok ? (r.json() as Promise<BanlistDetail>) : null
        )
      : Promise.resolve(null),
  ]);

  return {
    initialCards: cardsData.items ?? [],
    tcgBan: buildBanMap(tcgDetail),
    ocgBan: buildBanMap(ocgDetail),
  };
};
