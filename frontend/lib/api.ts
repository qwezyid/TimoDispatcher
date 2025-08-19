export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export type City = { city_id: number; name_display: string };

export type Deal = {
  deal_id: number;
  created_at: string;
  city_from: number;
  city_to: number;
  city_from_name?: string;
  city_to_name?: string;
  cost_rub?: number;
  performer_id?: number;
  status?: string | null;
  payload?: any;
};

export async function searchCities(q: string, opts: RequestInit = {}): Promise<City[]> {
  return j<City[]>(await fetch(`${API_BASE}/cities?q=${encodeURIComponent(q)}`, { cache: "no-store", ...opts }));
}

export async function searchPerformers(payload: {
  from_city: number;
  to_city: number;
  mode: "exact" | "partial";
}): Promise<any[]> {
  return j<any[]>(
    await fetch(`${API_BASE}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  );
}

export async function getDeals(params: { limit?: number; offset?: number; performer_id?: number } = {}): Promise<Deal[]> {
  const usp = new URLSearchParams();
  if (params.limit) usp.set("limit", String(params.limit));
  if (params.offset) usp.set("offset", String(params.offset));
  if (params.performer_id) usp.set("performer_id", String(params.performer_id));
  return j<Deal[]>(await fetch(`${API_BASE}/deals?${usp.toString()}`, { cache: "no-store" }));
}
