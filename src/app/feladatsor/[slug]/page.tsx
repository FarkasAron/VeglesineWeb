import { supabase, type Problem } from "@/lib/supabase";
import ProblemCard from "@/components/ProblemCard";
import PrintButton from "@/components/PrintButton";
import Link from "next/link";

export const revalidate = 300;

const SESSION_LABELS: Record<string, string> = {
  majus:   "május",
  oktober: "október",
  februar: "február",
};

function parseSlug(slug: string) {
  const parts = slug.split("-");
  // parts[0] = year, parts[1] = exam_type, parts[2] = exam_session, parts[3] = exam_part (optional)
  const year         = parseInt(parts[0]);
  const exam_type    = parts[1] as "kozep" | "emelt";
  const exam_session = parts[2];
  const exam_part    = parts[3] ? parts[3].toUpperCase() : null;
  return { year, exam_type, exam_session, exam_part };
}

async function getProblems(slug: string): Promise<Problem[]> {
  const { year, exam_type, exam_session, exam_part } = parseSlug(slug);

  let query = supabase
    .from("problems")
    .select("id,year,exam_type,exam_session,exam_part,problem_number,sub_part,problem_image_url,max_points,difficulty_level,topic_tags,ocr_used")
    .eq("human_reviewed", true)
    .eq("year", year)
    .eq("exam_type", exam_type)
    .eq("exam_session", exam_session)
    .order("problem_number")
    .order("sub_part");

  if (exam_part) {
    query = query.eq("exam_part", exam_part);
  } else {
    query = query.is("exam_part", null);
  }

  const { data, error } = await query;
  if (error) throw error;
  return (data as Problem[]) ?? [];
}

export default async function FeladatsorDetailPage({ params }: { params: { slug: string } }) {
  const { slug } = params;
  const { year, exam_type, exam_session, exam_part } = parseSlug(slug);
  const problems = await getProblems(slug);

  const sessionLabel = SESSION_LABELS[exam_session] ?? exam_session;
  const typeLabel    = exam_type === "kozep" ? "Középszint" : "Emelt szint";
  const partLabel    = exam_part ? ` · ${exam_part}. rész` : "";
  const title        = `${year} ${sessionLabel} · ${typeLabel}${partLabel}`;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Link href="/feladatsor" className="no-print text-sm text-slate-400 hover:text-navy-600 dark:hover:text-white transition-colors">
              ← Feladatsorok
            </Link>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white print:text-black">{title}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{problems.length} feladat</p>
        </div>
        <div className="no-print flex items-center gap-2">
          <span className={`badge text-white shadow-sm text-sm py-1.5 px-3 ${
            exam_type === "emelt" ? "bg-crimson-600" : "bg-navy-600"
          }`}>
            {typeLabel}
          </span>
          <PrintButton />
        </div>
      </div>

      {problems.length === 0 ? (
        <div className="text-center py-16 text-slate-500 dark:text-slate-400">
          <p className="text-lg">Nincs elérhető feladat ehhez a feladatsorhoz.</p>
        </div>
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
