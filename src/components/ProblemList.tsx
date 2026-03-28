"use client";

import { useState } from "react";
import Image from "next/image";
import { type Problem, TOPIC_LABELS, DIFFICULTY_LABELS } from "@/lib/supabase";

const SESSION_LABELS: Record<string, string> = {
  majus:   "május",
  oktober: "október",
  februar: "február",
};

const DIFFICULTY_COLORS: Record<string, string> = {
  konnyu:  "bg-green-100 text-green-700",
  kozepes: "bg-yellow-100 text-yellow-700",
  nehez:   "bg-red-100 text-red-700",
};

function ProblemRow({ problem }: { problem: Problem }) {
  const [open, setOpen] = useState(false);

  const session  = SESSION_LABELS[problem.exam_session] ?? problem.exam_session;
  const examType = problem.exam_type === "kozep" ? "Középszint" : "Emelt szint";
  const subLabel = problem.sub_part ? ` / ${problem.sub_part}` : "";
  const title    = `${problem.year} ${session} · ${examType} · ${problem.problem_number}. feladat${subLabel}`;

  return (
    <div className="border-b border-gray-100 last:border-0">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 text-left transition-colors"
      >
        {/* Expand arrow */}
        <span className="text-gray-400 text-xs w-3 shrink-0">
          {open ? "▼" : "▶"}
        </span>

        {/* Title */}
        <span className="flex-1 text-sm font-medium text-gray-800">{title}</span>

        {/* Difficulty */}
        {problem.difficulty_level && (
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${DIFFICULTY_COLORS[problem.difficulty_level]}`}>
            {DIFFICULTY_LABELS[problem.difficulty_level]}
          </span>
        )}

        {/* Points */}
        {problem.max_points && (
          <span className="text-xs text-gray-400 shrink-0">{problem.max_points} pt</span>
        )}

        {/* Topic tags (first 2 only in collapsed state) */}
        <div className="hidden sm:flex gap-1 shrink-0">
          {problem.topic_tags.slice(0, 2).map((tag) => (
            <span key={tag} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
              {TOPIC_LABELS[tag] ?? tag}
            </span>
          ))}
          {problem.topic_tags.length > 2 && (
            <span className="text-xs text-gray-400">+{problem.topic_tags.length - 2}</span>
          )}
        </div>
      </button>

      {/* Expanded: problem image */}
      {open && (
        <div className="px-8 pb-4">
          {problem.problem_image_url ? (
            <Image
              src={problem.problem_image_url}
              alt={title}
              width={900}
              height={500}
              className="w-full max-w-2xl h-auto rounded border border-gray-200"
              unoptimized
            />
          ) : (
            <p className="text-sm text-gray-400">Nincs elérhető kép.</p>
          )}
          {/* All topic tags when expanded */}
          {problem.topic_tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-3">
              {problem.topic_tags.map((tag) => (
                <a
                  key={tag}
                  href={`/feladatok?tema=${tag}`}
                  className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full hover:bg-blue-100"
                >
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
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      {problems.map((p) => (
        <ProblemRow key={p.id} problem={p} />
      ))}
    </div>
  );
}
