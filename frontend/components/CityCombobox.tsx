"use client";

import React, { useState, useEffect, useMemo } from "react";
import { Input } from "./ui";
import { searchCities } from "@/lib/api";

type City = { city_id: number; name_display: string };

export default function CityCombobox({
  label,
  onSelect,
}: {
  label: string;
  onSelect: (c: City | null) => void;
}) {
  const [q, setQ] = useState("");
  const [options, setOptions] = useState<City[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  // простейший дебаунс
  const debounced = useMemo(() => q, [q]);

  useEffect(() => {
    if (!debounced) {
      setOptions([]);
      return;
    }

    const ctrl = new AbortController();
    setLoading(true);

    searchCities(debounced, { signal: ctrl.signal })
      .then(setOptions)
      .catch(() => {})
      .finally(() => setLoading(false));

    return () => ctrl.abort();
  }, [debounced]);

  return (
    <div className="relative">
      <div className="mb-2 text-sm text-gray-700">{label}</div>
      <Input
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        placeholder="Начните вводить город…"
      />
      {open && (loading || options.length > 0) && (
        <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg max-h-64 overflow-auto">
          {loading && (
            <div className="px-3 py-2 text-sm text-gray-500">Загрузка…</div>
          )}
          {!loading &&
            options.map((c) => (
              <div
                key={c.city_id}
                onClick={() => {
                  onSelect(c);
                  setQ(c.name_display);
                  setOpen(false);
                }}
                className="px-3 py-2 text-sm hover:bg-blue-50 cursor-pointer"
              >
                {c.name_display}
              </div>
            ))}
        </div>
      )}
    </div>
  );
} 