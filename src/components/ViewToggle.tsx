"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";

export default function ViewToggle({ current }: { current: "grid" | "list" }) {
  const router       = useRouter();
  const pathname     = usePathname();
  const searchParams = useSearchParams();

  function setView(view: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("nezet", view);
    router.push(`${pathname}?${params.toString()}`);
  }

  const base     = "px-3 py-1.5 rounded-lg text-sm font-semibold transition-all duration-200";
  const activeC  = `${base} bg-navy-600 text-white shadow-sm`;
  const inactiveC = `${base} text-slate-500 dark:text-slate-400 hover:text-navy-600 dark:hover:text-slate-200`;

  return (
    <div className="flex gap-1 border border-slate-200 dark:border-slate-700/60 rounded-xl p-1 bg-white dark:bg-slate-800 shadow-sm">
      <button onClick={() => setView("grid")} className={current === "grid" ? activeC : inactiveC} title="Rács nézet">⊞</button>
      <button onClick={() => setView("list")} className={current === "list" ? activeC : inactiveC} title="Lista nézet">☰</button>
    </div>
  );
}
