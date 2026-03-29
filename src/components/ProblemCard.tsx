import Image from "next/image";
import { type Problem, TOPIC_LABELS, DIFFICULTY_LABELS } from "@/lib/supabase";

const SESSION_LABELS: Record<string, string> = {
  majus:   "május",
  oktober: "október",
  februar: "február",
};

const DIFFICULTY_STYLES: Record<string, string> = {
  konnyu:  "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400",
  kozepes: "bg-amber-100  text-amber-700  dark:bg-amber-900/40  dark:text-amber-400",
  nehez:   "bg-crimson-100 text-crimson-700 dark:bg-crimson-900/40 dark:text-crimson-400",
};

const DIFFICULTY_DOT: Record<string, string> = {
  konnyu:  "bg-emerald-400",
  kozepes: "bg-amber-400",
  nehez:   "bg-crimson-500",
};

export default function ProblemCard({ problem }: { problem: Problem }) {
  const session  = SESSION_LABELS[problem.exam_session] ?? problem.exam_session;
  const examType = problem.exam_type === "kozep" ? "Közép" : "Emelt";
  const subLabel = problem.sub_part ? ` / ${problem.sub_part}` : "";

  return (
    <article className="card flex flex-col overflow-hidden group">
      {/* Image area */}
      <div className="relative bg-slate-50 dark:bg-slate-900/50 overflow-hidden" style={{ minHeight: 160 }}>
        {problem.problem_image_url ? (
          <Image
            src={problem.problem_image_url}
            alt={`${problem.year} ${session} ${examType} ${problem.problem_number}. feladat${subLabel}`}
            width={800} height={400}
            className="w-full h-auto object-contain group-hover:scale-[1.02] transition-transform duration-500"
            unoptimized
          />
        ) : (
          <div className="w-full h-40 flex items-center justify-center text-slate-300 dark:text-slate-600 text-sm">
            Nincs kép
          </div>
        )}

        {/* Top-right exam type pill */}
        <div className="absolute top-2.5 right-2.5">
          <span className={`badge text-white shadow-sm ${
            problem.exam_type === "emelt"
              ? "bg-crimson-600"
              : "bg-navy-600"
          }`}>
            {examType}
          </span>
        </div>
      </div>

      {/* Thin color bar at bottom of image */}
      <div className={`h-0.5 w-full ${problem.exam_type === "emelt" ? "bg-gradient-to-r from-crimson-500 to-crimson-300" : "bg-gradient-to-r from-navy-500 to-navy-300"}`} />

      {/* Metadata */}
      <div className="p-4 flex flex-col gap-3 flex-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100 leading-snug">
            {problem.year} {session}
            <span className="text-slate-400 dark:text-slate-500 font-normal"> · </span>
            {problem.problem_number}. feladat{subLabel}
          </h3>
          {problem.max_points && (
            <span className="badge bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400 shrink-0">
              {problem.max_points} pt
            </span>
          )}
        </div>

        {problem.difficulty_level && (
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${DIFFICULTY_DOT[problem.difficulty_level]}`} />
            <span className={`badge ${DIFFICULTY_STYLES[problem.difficulty_level]}`}>
              {DIFFICULTY_LABELS[problem.difficulty_level]}
            </span>
          </div>
        )}

        {problem.topic_tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-auto pt-1">
            {problem.topic_tags.map((tag) => (
              <a key={tag} href={`/feladatok?tema=${tag}`}
                className="badge bg-navy-50 text-navy-600 hover:bg-navy-100
                           dark:bg-white/10 dark:text-slate-200 dark:hover:bg-white/15
                           transition-colors border border-navy-100/60 dark:border-white/10">
                {TOPIC_LABELS[tag] ?? tag}
              </a>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}
