"use client";

import { useState } from "react";
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
  nehez:   "bg-rose-100   text-rose-700   dark:bg-rose-900/40   dark:text-rose-400",
};

function ProblemRow({ problem }: { problem: Problem }) {
  const [open, setOpen] = useState(false);

  const session  = SESSION_LABELS[problem.exam_session] ?? problem.exam_session;
  const examType = problem.exam_type === "kozep" ? "Középszint" : "Emelt szint";
  const subLabel = problem.sub_part ? ` / ${problem.sub_part}` : "";
  const title    = `${problem.year} ${session} · ${examType} · ${problem.problem_number}. feladat${subLabel}`;

  return (
    <div className="border-b border-slate-100 dark:border-slate-800 last:border-0">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3.5
                   hover:bg-slate-50 dark:hover:bg-slate-800/50
                   text-left transition-colors group"
      >
        {/* Arrow */}
        <span className={`text-slate-300 dark:text-slate-600 transition-transform duration-200 text-xs ${open ? "rotate-90" : ""}`}>
          ▶
        </span>

        {/* Title */}
        <span className="flex-1 text-sm font-medium text-slate-800 dark:text-slate-200 group-hover:text-violet-600 dark:group-hover:text-violet-400 transition-colors">
          {title}
        </span>

        {/* Difficulty badge */}
        {problem.difficulty_level && (
          <span className={`badge shrink-0 ${DIFFICULTY_STYLES[problem.difficulty_level]}`}>
            {DIFFICULTY_LABELS[problem.difficulty_level]}
          </span>
        )}

        {/* Points */}
        {problem.max_points && (
          <span className="badge bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400 shrink-0">
            {problem.max_points} pt
          </span>
        )}

        {/* First 2 topic tags */}
        <div className="hidden sm:flex gap-1 shrink-0">
          {problem.topic_tags.slice(0, 2).map((tag) => (
            <span key={tag} className="badge bg-navy-50 text-navy-600 dark:bg-white/10 dark:text-slate-200 border border-navy-100/60 dark:border-white/10">
              {TOPIC_LABELS[tag] ?? tag}
            </span>
          ))}
          {problem.topic_tags.length > 2 && (
            <span className="badge bg-slate-100 text-slate-500 dark:bg-white/10 dark:text-slate-300">
              +{problem.topic_tags.length - 2}
            </span>
          )}
        </div>
      </button>

      {/* Expanded content */}
      {open && (
        <div className="px-10 pb-5 animate-fade-in">
          {problem.problem_image_url ? (
            <Image
              src={problem.problem_image_url}
              alt={title}
              width={900}
              height={500}
              className="w-full max-w-2xl h-auto rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm"
              unoptimized
            />
          ) : (
            <p className="text-sm text-slate-400">Nincs elérhető kép.</p>
          )}
          {problem.topic_tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
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
      )}
    </div>
  );
}

export default function ProblemList({ problems }: { problems: Problem[] }) {
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden shadow-sm">
      {problems.map((p) => (
        <ProblemRow key={p.id} problem={p} />
      ))}
    </div>
  );
}
