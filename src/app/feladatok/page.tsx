import { supabase, TOPIC_LABELS, DIFFICULTY_LABELS, type Problem } from "@/lib/supabase";
import ProblemCard from "@/components/ProblemCard";
import ProblemList from "@/components/ProblemList";
import FilterBar from "@/components/FilterBar";
import ViewToggle from "@/components/ViewToggle";
import PrintButton from "@/components/PrintButton";
import { Suspense } from "react";

interface Props {
  searchParams: { tema?: string; szint?: string; nehezseg?: string; ev?: string; nezet?: string; tipus?: string };
}

export const revalidate = 300;

async function getProblems(filters: Props["searchParams"]): Promise<Problem[]> {
  let query = supabase
    .from("problems")
    .select("id,year,exam_type,exam_session,exam_part,problem_number,sub_part,problem_image_url,max_points,difficulty_level,topic_tags,ocr_used")
    .eq("human_reviewed", true)
    .order("year", { ascending: false })
    .order("exam_session")
    .order("problem_number")
    .order("sub_part")
    .limit(200);

  if (filters.szint)           query = query.eq("exam_type", filters.szint);
  if (filters.tema)            query = query.contains("topic_tags", [filters.tema]);
  if (filters.nehezseg)        query = query.eq("difficulty_level", filters.nehezseg);
  if (filters.ev)              query = query.eq("year", parseInt(filters.ev));
  if (filters.tipus === "rovid")  query = query.lte("problem_number", 4);
  if (filters.tipus === "hosszu") query = query.gte("problem_number", 5);

  const { data, error } = await query;
  if (error) throw error;
  return (data as Problem[]) ?? [];
}

export default async function FeladatokPage({ searchParams }: Props) {
  const problems = await getProblems(searchParams);
  const view = searchParams.nezet === "list" ? "list" : "grid";

  const activeFilters = {
    tema:     searchParams.tema,
    szint:    searchParams.szint,
    nehezseg: searchParams.nehezseg,
    ev:       searchParams.ev,
    nezet:    searchParams.nezet,
    tipus:    searchParams.tipus,
  };

  const topicLabel = searchParams.tema     ? TOPIC_LABELS[searchParams.tema]         : null;
  const examLabel  = searchParams.szint === "kozep" ? "Középszint"
                   : searchParams.szint === "emelt" ? "Emelt szint" : null;
  const diffLabel  = searchParams.nehezseg ? DIFFICULTY_LABELS[searchParams.nehezseg] : null;
  const tipusLabel = searchParams.tipus === "rovid" ? "Rövid (1–4)"
                   : searchParams.tipus === "hosszu" ? "Hosszú (5+)" : null;

  const titleParts = [topicLabel, examLabel, diffLabel, tipusLabel, searchParams.ev].filter(Boolean);
  const pageTitle  = titleParts.length > 0 ? titleParts.join(" · ") : "Összes feladat";

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white print:text-black">{pageTitle}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{problems.length} feladat</p>
        </div>
        <div className="flex items-center gap-2 no-print">
          <Suspense>
            <ViewToggle current={view} />
          </Suspense>
          <PrintButton />
        </div>
      </div>

      <FilterBar active={activeFilters} />

      {problems.length === 0 ? (
        <div className="text-center py-16 text-slate-500 dark:text-slate-400">
          <p className="text-lg">Nincs találat ezekkel a szűrőkkel.</p>
          <p className="text-sm mt-2">Próbálj kevesebb szűrőt alkalmazni.</p>
        </div>
      ) : view === "list" ? (
        <ProblemList problems={problems} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {problems.map((p) => (
            <ProblemCard key={p.id} problem={p} />
          ))}
        </div>
      )}
    </div>
  );
}
