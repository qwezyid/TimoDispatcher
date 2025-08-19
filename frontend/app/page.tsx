"use client";

import React, { useMemo, useState } from "react";
import useSWR from "swr";
import { Button, Card } from "@/components/ui";
import CityCombobox from "@/components/CityCombobox";
import { API_BASE, getDeals, searchPerformers } from "@/lib/api";

type Deal = {
  deal_id: number;
  created_at: string;
  city_from: number;
  city_to: number;
  cost_rub?: number;
};

export default function Page() {
  const [fromCity, setFrom] = useState<{ city_id: number; name_display: string } | null>(null);
  const [toCity, setTo] = useState<{ city_id: number; name_display: string } | null>(null);
  const [mode, setMode] = useState<"exact" | "partial">("exact");
  const [queryKey] = useState(0);

  // Уточняем тип данных от SWR
  const { data: deals } = useSWR<Deal[]>(
    ["deals", queryKey],
    () => getDeals({ limit: 25 }),
    { revalidateOnFocus: false }
  );

  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[] | null>(null);

  async function runSearch() {
    if (!fromCity || !toCity) return;
    setLoading(true);
    try {
      const r = await searchPerformers({
        from_city: fromCity.city_id,
        to_city: toCity.city_id,
        mode,
      });
      setResults(r as any[]);
    } finally {
      setLoading(false);
    }
  }

  const title = useMemo(
    () =>
      fromCity && toCity ? `${fromCity.name_display} → ${toCity.name_display}` : "Поиск исполнителей",
    [fromCity, toCity]
  );

  return (
    <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <div className="text-sm text-gray-700 mb-3">API</div>
          <div className="text-sm">{API_BASE}</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-700 mb-3">Найти исполнителя</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <CityCombobox label="Откуда" onSelect={setFrom} />
            <CityCombobox label="Куда" onSelect={setTo} />
          </div>
          <div className="flex items-center gap-3 mt-3">
            <div className="flex rounded-xl border p-1 bg-gray-50">
              <button
                onClick={() => setMode("exact")}
                className={`px-3 py-1 text-sm rounded-lg ${mode === "exact" ? "bg-white shadow" : ""}`}
              >
                Точное
              </button>
              <button
                onClick={() => setMode("partial")}
                className={`px-3 py-1 text-sm rounded-lg ${mode === "partial" ? "bg-white shadow" : ""}`}
              >
                Частичное
              </button>
            </div>
            <Button onClick={runSearch} disabled={!fromCity || !toCity || loading}>
              {loading ? "Ищу…" : "Найти"}
            </Button>
          </div>
        </Card>
        <Card className="md:col-span-2">
          <div className="text-sm text-gray-700 mb-2">Подсказка</div>
          <div className="text-sm text-gray-600">
            Выберите города из автодополнения. В режиме «Частичное» попадут водители с длинными маршрутами, проходящими
            через оба города в нужном порядке.
          </div>
        </Card>
      </div>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <div className="text-lg font-semibold">{title}</div>
            {results && (
              <div className="text-sm text-gray-600">
                Найдено: <b>{results.length}</b>
              </div>
            )}
          </div>
          {!results && <div className="text-sm text-gray-500">Выберите города и нажмите «Найти».</div>}
          {results && results.length === 0 && <div className="text-sm text-gray-500">Совпадений не найдено.</div>}
          {results && results.length > 0 && (
            <div className="grid sm:grid-cols-2 gap-3">
              {results.map((r: any) => (
                <div
                  key={`${r.performer_id}-${r.variant_id || "nv"}`}
                  className="p-4 rounded-2xl border hover:shadow-sm transition"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-semibold">{r.fio}</div>
                      <div className="text-sm text-gray-600">{r.phone_norm}</div>
                    </div>
                    {r.variant_id && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">
                        вариант #{r.variant_id}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <div className="text-lg font-semibold mb-2">Последние сделки</div>
          {!deals && <div className="text-sm text-gray-500">Загружаю…</div>}
          {Array.isArray(deals) && deals.length === 0 && (
            <div className="text-sm text-gray-500">Пока нет данных</div>
          )}
          <div className="space-y-2 max-h-[460px] overflow-auto pr-1">
            {Array.isArray(deals) &&
              deals.map((d) => (
                <div key={d.deal_id} className="p-3 rounded-xl border bg-white">
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-sm">#{d.deal_id}</div>
                    <div className="text-xs text-gray-500">{new Date(d.created_at).toLocaleDateString()}</div>
                  </div>
                  <div className="text-sm text-gray-700">
                    {d.city_from} → {d.city_to}
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-500">₽</span> {Number(d.cost_rub || 0).toLocaleString()}
                  </div>
                </div>
              ))}
          </div>
        </Card>
      </section>

      <footer className="text-xs text-gray-500">
        API: <code>NEXT_PUBLIC_API_URL</code>. Деплой: Vercel (frontend) + Railway/Timeweb (backend).
      </footer>
    </main>
  );
}
