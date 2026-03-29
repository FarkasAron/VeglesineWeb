import Link from "next/link";
import { TOPIC_LABELS } from "@/lib/supabase";

export default function TemakorokPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Témakörök</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">
          Válassz témakört a feladatok szűréséhez.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        {Object.entries(TOPIC_LABELS).map(([slug, label]) => (
          <Link key={slug} href={`/feladatok?tema=${slug}`}
            className="card px-5 py-4 flex items-center justify-between group">
            <span className="font-medium text-slate-700 dark:text-slate-200 group-hover:text-violet-600 dark:group-hover:text-violet-400 transition-colors">
              {label}
            </span>
            <span className="text-slate-300 dark:text-slate-600 group-hover:text-violet-400 transition-colors">→</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
