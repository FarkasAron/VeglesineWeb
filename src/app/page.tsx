import Link from "next/link";
import { TOPIC_LABELS } from "@/lib/supabase";

const FEATURED_TOPICS = [
  "geometria-sik",
  "egyenletek",
  "fuggvenyek",
  "valoszinuseg",
  "trigonometria",
  "kombinatorika",
  "sorozatok",
  "statisztika",
];

export default function HomePage() {
  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="text-center py-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Érettségi Matematika Feladatbank
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-8">
          Középszintű és emelt szintű érettségi feladatok témakör és nehézség szerint rendezve.
          Minden feladat az eredeti vizsgalapról van kivágva.
        </p>
        <Link
          href="/feladatok"
          className="inline-block bg-blue-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
        >
          Feladatok böngészése →
        </Link>
      </section>

      {/* Topic grid */}
      <section>
        <h2 className="text-2xl font-semibold text-gray-800 mb-6">Témakörök</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {FEATURED_TOPICS.map((slug) => (
            <Link
              key={slug}
              href={`/feladatok?tema=${slug}`}
              className="bg-white border border-gray-200 rounded-lg px-4 py-3 text-sm font-medium text-gray-700 hover:border-blue-400 hover:text-blue-700 hover:shadow-sm transition-all"
            >
              {TOPIC_LABELS[slug]}
            </Link>
          ))}
        </div>
        <div className="mt-4">
          <Link href="/temakoren-kint" className="text-sm text-blue-600 hover:underline">
            Összes témakör megtekintése →
          </Link>
        </div>
      </section>

      {/* Level cards */}
      <section>
        <h2 className="text-2xl font-semibold text-gray-800 mb-6">Szint szerint</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Link
            href="/feladatok?szint=kozep"
            className="bg-white border border-gray-200 rounded-xl p-6 hover:border-blue-400 hover:shadow-md transition-all"
          >
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Középszint</h3>
            <p className="text-sm text-gray-500">
              Kötelező érettségi feladatok, minden évből.
            </p>
          </Link>
          <Link
            href="/feladatok?szint=emelt"
            className="bg-white border border-gray-200 rounded-xl p-6 hover:border-blue-400 hover:shadow-md transition-all"
          >
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Emelt szint</h3>
            <p className="text-sm text-gray-500">
              Emelt szintű érettségi és felvételi felkészítő feladatok.
            </p>
          </Link>
        </div>
      </section>
    </div>
  );
}
