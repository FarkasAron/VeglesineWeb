"use client";

import { useRouter, usePathname } from "next/navigation";
import { TOPIC_LABELS } from "@/lib/supabase";

interface ActiveFilters {
  tema?: string; szint?: string; nehezseg?: string; ev?: string; nezet?: string; tipus?: string;
}

const YEARS = Array.from({ length: 20 }, (_, i) => 2025 - i);

const SELECT_CLS = `
  border border-slate-200 dark:border-slate-700/60
  rounded-xl px-3 py-2 text-sm font-medium
  bg-white dark:bg-slate-800
  text-slate-700 dark:text-slate-200
  focus:outline-none focus:ring-2 focus:ring-navy-400 dark:focus:ring-navy-500
  hover:border-navy-300 dark:hover:border-navy-600
  transition-colors cursor-pointer shadow-sm
`.replace(/\s+/g, " ").trim();

export default function FilterBar({ active }: { active: ActiveFilters }) {
  const router   = useRouter();
  const pathname = usePathname();

  function update(key: string, value: string) {
    const params = new URLSearchParams();
    if (active.tema)     params.set("tema",     active.tema);
    if (active.szint)    params.set("szint",    active.szint);
    if (active.nehezseg) params.set("nehezseg", active.nehezseg);
    if (active.ev)       params.set("ev",       active.ev);
    if (active.nezet)    params.set("nezet",    active.nezet);
    if (active.tipus)    params.set("tipus",    active.tipus);
    if (value) params.set(key, value); else params.delete(key);
    router.push(`${pathname}?${params.toString()}`);
  }

  const hasFilters = [active.tema, active.szint, active.nehezseg, active.ev, active.tipus].some(Boolean);

  return (
    <div className="flex flex-wrap gap-2 items-center">
      <select value={active.szint ?? ""}    onChange={(e) => update("szint", e.target.value)}    className={SELECT_CLS}>
        <option value="">Minden szint</option>
        <option value="kozep">Középszint</option>
        <option value="emelt">Emelt szint</option>
      </select>

      <select value={active.tema ?? ""}     onChange={(e) => update("tema", e.target.value)}     className={SELECT_CLS}>
        <option value="">Minden témakör</option>
        {Object.entries(TOPIC_LABELS).map(([slug, label]) => (
          <option key={slug} value={slug}>{label}</option>
        ))}
      </select>

      <select value={active.nehezseg ?? ""} onChange={(e) => update("nehezseg", e.target.value)} className={SELECT_CLS}>
        <option value="">Minden nehézség</option>
        <option value="konnyu">Könnyű</option>
        <option value="kozepes">Közepes</option>
        <option value="nehez">Nehéz</option>
      </select>

      <select value={active.ev ?? ""}       onChange={(e) => update("ev", e.target.value)}       className={SELECT_CLS}>
        <option value="">Minden év</option>
        {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
      </select>

      <select value={active.tipus ?? ""}     onChange={(e) => update("tipus", e.target.value)}     className={SELECT_CLS}>
        <option value="">Minden típus</option>
        <option value="rovid">Rövid feladatok (1–4)</option>
        <option value="hosszu">Hosszú feladatok (5+)</option>
      </select>

      {hasFilters && (
        <a href="/feladatok"
          className="px-3 py-2 rounded-xl text-sm font-semibold text-crimson-600 dark:text-crimson-400
                     hover:bg-crimson-50 dark:hover:bg-crimson-900/20 transition-colors">
          Törlés ✕
        </a>
      )}
    </div>
  );
}
