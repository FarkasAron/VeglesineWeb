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

export default function ProblemCard({ problem }: { problem: Problem }) {
  const session = SESSION_LABELS[problem.exam_session] ?? problem.exam_session;
  const examType = problem.exam_type === "kozep" ? "Közép" : "Emelt";
  const subLabel = problem.sub_part ? ` / ${problem.sub_part}` : "";

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow">
      {/* Problem image */}
      {problem.problem_image_url ? (
        <div className="relative w-full bg-gray-50" style={{ minHeight: 160 }}>
          <Image
            src={problem.problem_image_url}
            alt={`${problem.year} ${session} ${examType} ${problem.problem_number}. feladat${subLabel}`}
            width={800}
            height={400}
            className="w-full h-auto object-contain"
            unoptimized
          />
        </div>
      ) : (
        <div className="w-full h-40 bg-gray-100 flex items-center justify-center text-gray-400 text-sm">
          Nincs kép
        </div>
      )}

      {/* Metadata */}
      <div className="p-4 space-y-3">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-800">
            {problem.year} {session} · {examType} · {problem.problem_number}. feladat{subLabel}
          </span>
          {problem.max_points && (
            <span className="text-xs text-gray-500">{problem.max_points} pont</span>
          )}
        </div>

        {/* Difficulty */}
        {problem.difficulty_level && (
          <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${DIFFICULTY_COLORS[problem.difficulty_level] ?? ""}`}>
            {DIFFICULTY_LABELS[problem.difficulty_level]}
          </span>
        )}

        {/* Topic tags */}
        {problem.topic_tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {problem.topic_tags.map((tag) => (
              <a
                key={tag}
                href={`/feladatok?tema=${tag}`}
                className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full hover:bg-blue-100 transition-colors"
              >
                {TOPIC_LABELS[tag] ?? tag}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
