"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";

export default function ViewToggle({ current }: { current: "grid" | "list" }) {
  const router      = useRouter();
  const pathname    = usePathname();
  const searchParams = useSearchParams();

  function setView(view: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("nezet", view);
    router.push(`${pathname}?${params.toString()}`);
  }

  return (
    <div className="flex gap-1 border border-gray-200 rounded-lg p-0.5 bg-white">
      <button
        onClick={() => setView("grid")}
        className={`px-3 py-1.5 rounded text-sm transition-colors ${
          current === "grid"
            ? "bg-gray-100 text-gray-900 font-medium"
            : "text-gray-500 hover:text-gray-700"
        }`}
        title="Rács nézet"
      >
        ⊞ Rács
      </button>
      <button
        onClick={() => setView("list")}
        className={`px-3 py-1.5 rounded text-sm transition-colors ${
          current === "list"
            ? "bg-gray-100 text-gray-900 font-medium"
            : "text-gray-500 hover:text-gray-700"
        }`}
        title="Lista nézet"
      >
        ☰ Lista
      </button>
    </div>
  );
}
