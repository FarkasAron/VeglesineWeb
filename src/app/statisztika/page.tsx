import { supabase, TOPIC_LABELS } from "@/lib/supabase";
import Link from "next/link";

export const revalidate = 300;

async function getTopicCounts(): Promise<{ slug: string; label: string; count: number }[]> {
  const { data, error } = await supabase
    .from("problems")
    .select("topic_tags, exam_type, difficulty_level")
    .eq("human_reviewed", true)
    .limit(2000);
  if (error) throw error;

  const counts: Record<string, number> = {};
  for (const row of data ?? []) {
    for (const tag of row.topic_tags ?? []) {
      counts[tag] = (counts[tag] || 0) + 1;
    }
  }

  return Object.entries(TOPIC_LABELS)
    .map(([slug, label]) => ({ slug, label, count: counts[slug] ?? 0 }))
    .sort((a, b) => b.count - a.count);
}

async function getSummary() {
  const { data } = await supabase
    .from("problems")
    .select("exam_type, difficulty_level")
    .eq("human_reviewed", true)
    .limit(2000);

  const rows = data ?? [];
  const total = rows.length;
  const kozep = rows.filter((r) => r.exam_type === "kozep").length;
  const emelt = rows.filter((r) => r.exam_type === "emelt").length;
  const konnyu  = rows.filter((r) => r.difficulty_level === "konnyu").length;
  const kozepes = rows.filter((r) => r.difficulty_level === "kozepes").length;
  const nehez   = rows.filter((r) => r.difficulty_level === "nehez").length;

  return { total, kozep, emelt, konnyu, kozepes, nehez };
}

export default async function StatisztikaPage() {
  const [topics, summary] = await Promise.all([getTopicCounts(), getSummary()]);
  const maxCount = topics[0]?.count ?? 1;

  return (
    <div className="space-y-10 animate-fade-in">

      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Statisztika</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">
          Az adatbázis összetétele témakör, szint és nehézség szerint.
        </p>
      </div>

      {/* Summary cards */}
      <section>
        <h2 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-4">Összesítés</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          {[
            { label: "Összes feladat", value: summary.total,   color: "text-navy-600 dark:text-navy-200" },
            { label: "Középszint",     value: summary.kozep,   color: "text-blue-600 dark:text-blue-300" },
            { label: "Emelt szint",    value: summary.emelt,   color: "text-crimson-600 dark:text-crimson-300" },
            { label: "Könnyű",         value: summary.konnyu,  color: "text-emerald-600 dark:text-emerald-300" },
            { label: "Közepes",        value: summary.kozepes, color: "text-amber-600 dark:text-amber-300" },
            { label: "Nehéz",          value: summary.nehez,   color: "text-rose-600 dark:text-rose-300" },
          ].map(({ label, value, color }) => (
            <div key={label} className="card p-4 text-center">
              <div className={`text-2xl font-extrabold ${color}`}>{value}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 font-medium">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Level pie-like bars */}
      <section>
        <h2 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-4">Szint arány</h2>
        <div className="card p-5 space-y-3">
          {[
            { label: "Középszint",  value: summary.kozep,  total: summary.total, barColor: "bg-navy-500" },
            { label: "Emelt szint", value: summary.emelt,  total: summary.total, barColor: "bg-crimson-500" },
          ].map(({ label, value, total, barColor }) => (
            <div key={label} className="flex items-center gap-3">
              <span className="w-28 text-sm font-medium text-slate-600 dark:text-slate-400 shrink-0">{label}</span>
              <div className="flex-1 bg-slate-100 dark:bg-slate-700 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full rounded-full ${barColor} transition-all duration-700`}
                  style={{ width: `${(value / total) * 100}%` }}
                />
              </div>
              <span className="text-sm font-semibold text-slate-700 dark:text-slate-300 w-10 text-right">{value}</span>
              <span className="text-xs text-slate-400 w-10">{Math.round((value / total) * 100)}%</span>
            </div>
          ))}
        </div>
      </section>

      {/* Topics */}
      <section>
        <h2 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-4">Feladatok témakörönként</h2>
        <div className="card divide-y divide-slate-100 dark:divide-slate-700/50">
          {topics.map(({ slug, label, count }, i) => (
            <Link
              key={slug}
              href={`/feladatok?tema=${slug}`}
              className="flex items-center gap-3 px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors group"
            >
              {/* Rank */}
              <span className="w-6 text-xs text-slate-400 dark:text-slate-600 font-mono shrink-0">{i + 1}</span>

              {/* Label */}
              <span className="w-52 text-sm font-medium text-slate-700 dark:text-slate-300 group-hover:text-navy-600 dark:group-hover:text-white transition-colors shrink-0 truncate">
                {label}
              </span>

              {/* Bar */}
              <div className="flex-1 bg-slate-100 dark:bg-slate-700 rounded-full h-2.5 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-navy-500 to-navy-400 dark:from-navy-400 dark:to-navy-300 transition-all duration-500 group-hover:from-crimson-500 group-hover:to-crimson-400"
                  style={{ width: count > 0 ? `${(count / maxCount) * 100}%` : "0%" }}
                />
              </div>

              {/* Count */}
              <span className="text-sm font-semibold text-slate-600 dark:text-slate-400 w-10 text-right shrink-0">
                {count}
              </span>
            </Link>
          ))}
        </div>
      </section>

    </div>
  );
}
