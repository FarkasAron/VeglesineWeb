"use client";

import { useRouter, usePathname } from "next/navigation";
import { TOPIC_LABELS } from "@/lib/supabase";

interface ActiveFilters {
  tema?: string;
  szint?: string;
  nehezseg?: string;
  ev?: string;
  nezet?: string;
}

const YEARS = Array.from({ length: 20 }, (_, i) => 2025 - i);

export default function FilterBar({ active }: { active: ActiveFilters }) {
  const router = useRouter();
  const pathname = usePathname();

  function update(key: string, value: string) {
    const params = new URLSearchParams();
    if (active.tema)      params.set("tema",      active.tema);
    if (active.szint)     params.set("szint",     active.szint);
    if (active.nehezseg)  params.set("nehezseg",  active.nehezseg);
    if (active.ev)        params.set("ev",        active.ev);
    if (active.nezet)     params.set("nezet",     active.nezet);

    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    router.push(`${pathname}?${params.toString()}`);
  }

  const hasFilters = Object.values(active).some(Boolean);

  return (
    <div className="flex flex-wrap gap-3 items-center">
      {/* Exam type */}
      <select
        value={active.szint ?? ""}
        onChange={(e) => update("szint", e.target.value)}
        className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
      >
        <option value="">Minden szint</option>
        <option value="kozep">Középszint</option>
        <option value="emelt">Emelt szint</option>
      </select>

      {/* Topic */}
      <select
        value={active.tema ?? ""}
        onChange={(e) => update("tema", e.target.value)}
        className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
      >
        <option value="">Minden témakör</option>
        {Object.entries(TOPIC_LABELS).map(([slug, label]) => (
          <option key={slug} value={slug}>{label}</option>
        ))}
      </select>

      {/* Difficulty */}
      <select
        value={active.nehezseg ?? ""}
        onChange={(e) => update("nehezseg", e.target.value)}
        className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
      >
        <option value="">Minden nehézség</option>
        <option value="konnyu">Könnyű</option>
        <option value="kozepes">Közepes</option>
        <option value="nehez">Nehéz</option>
      </select>

      {/* Year */}
      <select
        value={active.ev ?? ""}
        onChange={(e) => update("ev", e.target.value)}
        className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
      >
        <option value="">Minden év</option>
        {YEARS.map((y) => (
          <option key={y} value={y}>{y}</option>
        ))}
      </select>

      {/* Clear all */}
      {hasFilters && (
        <a
          href="/feladatok"
          className="text-sm text-red-600 hover:underline"
        >
          Szűrők törlése ✕
        </a>
      )}
    </div>
  );
}
