import { supabase } from "@/lib/supabase";
import Link from "next/link";

export const revalidate = 300;

const SESSION_LABELS: Record<string, string> = {
  majus:   "május",
  oktober: "október",
  februar: "február",
};

interface ExamGroup {
  year: number;
  exam_type: "kozep" | "emelt";
  exam_session: string;
  exam_part: string | null;
  count: number;
}

function toSlug(g: ExamGroup): string {
  const base = `${g.year}-${g.exam_type}-${g.exam_session}`;
  return g.exam_part ? `${base}-${g.exam_part.toLowerCase()}` : base;
}

async function getExamGroups(): Promise<ExamGroup[]> {
  const { data, error } = await supabase
    .from("problems")
    .select("year,exam_type,exam_session,exam_part")
    .eq("human_reviewed", true)
    .order("year", { ascending: false })
    .order("exam_session")
    .order("exam_type")
    .limit(2000);

  if (error) throw error;

  const map = new Map<string, ExamGroup>();
  for (const row of data ?? []) {
    const key = `${row.year}-${row.exam_type}-${row.exam_session}-${row.exam_part ?? ""}`;
    if (map.has(key)) {
      map.get(key)!.count++;
    } else {
      map.set(key, {
        year: row.year,
        exam_type: row.exam_type,
        exam_session: row.exam_session,
        exam_part: row.exam_part,
        count: 1,
      });
    }
  }

  return Array.from(map.values()).sort((a, b) => {
    if (b.year !== a.year) return b.year - a.year;
    const sessOrder = ["majus", "oktober", "februar"];
    const sA = sessOrder.indexOf(a.exam_session);
    const sB = sessOrder.indexOf(b.exam_session);
    if (sA !== sB) return sA - sB;
    if (a.exam_type !== b.exam_type) return a.exam_type === "kozep" ? -1 : 1;
    return (a.exam_part ?? "").localeCompare(b.exam_part ?? "");
  });
}

export default async function FeladatsorPage() {
  const groups = await getExamGroups();

  // Group by year for display
  const byYear = new Map<number, ExamGroup[]>();
  for (const g of groups) {
    if (!byYear.has(g.year)) byYear.set(g.year, []);
    byYear.get(g.year)!.push(g);
  }

  return (
    <div className="space-y-10 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Feladatsorok</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">
          Teljes érettségi feladatsorok — az eredeti vizsgalap sorrendjében.
        </p>
      </div>

      {Array.from(byYear.entries()).map(([year, yearGroups]) => (
        <section key={year}>
          <h2 className="text-xl font-bold text-slate-800 dark:text-slate-200 mb-3">{year}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {yearGroups.map((g) => {
              const sessionLabel = SESSION_LABELS[g.exam_session] ?? g.exam_session;
              const typeLabel = g.exam_type === "kozep" ? "Középszint" : "Emelt szint";
              const partLabel = g.exam_part ? ` · ${g.exam_part}. rész` : "";
              const slug = toSlug(g);

              return (
                <Link
                  key={slug}
                  href={`/feladatsor/${slug}`}
                  className="card p-5 flex items-center justify-between gap-3 group overflow-hidden relative"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-navy-50 to-transparent dark:from-navy-900/20 opacity-0 group-hover:opacity-100 transition-opacity" />

                  <div className="relative flex-1 min-w-0">
                    <div className="font-semibold text-slate-800 dark:text-slate-100 leading-snug">
                      {sessionLabel}{partLabel}
                    </div>
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className={`badge text-white text-[10px] ${
                        g.exam_type === "emelt" ? "bg-crimson-600" : "bg-navy-600"
                      }`}>
                        {typeLabel}
                      </span>
                      <span className="text-xs text-slate-400 dark:text-slate-500">{g.count} feladat</span>
                    </div>
                  </div>

                  <span className="relative text-xl text-slate-200 dark:text-slate-700 group-hover:text-navy-500 dark:group-hover:text-navy-400 group-hover:translate-x-1 transition-all shrink-0">→</span>
                </Link>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
