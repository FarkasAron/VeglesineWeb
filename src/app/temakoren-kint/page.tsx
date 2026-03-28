import Link from "next/link";
import { TOPIC_LABELS } from "@/lib/supabase";

export default function TemakorokPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Összes témakör</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        {Object.entries(TOPIC_LABELS).map(([slug, label]) => (
          <Link
            key={slug}
            href={`/feladatok?tema=${slug}`}
            className="bg-white border border-gray-200 rounded-lg px-5 py-4 hover:border-blue-400 hover:text-blue-700 hover:shadow-sm transition-all"
          >
            <span className="font-medium">{label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
