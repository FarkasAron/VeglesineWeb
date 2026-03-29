import Link from "next/link";
import Image from "next/image";
import { TOPIC_LABELS } from "@/lib/supabase";

const FEATURED_TOPICS = [
  { slug: "geometria-sik",        icon: "△", delay: "stagger-1" },
  { slug: "egyenletek",           icon: "=", delay: "stagger-1" },
  { slug: "fuggvenyek",           icon: "f(x)", delay: "stagger-2" },
  { slug: "valoszinuseg",         icon: "P", delay: "stagger-2" },
  { slug: "trigonometria",        icon: "sin", delay: "stagger-3" },
  { slug: "kombinatorika",        icon: "n!", delay: "stagger-3" },
  { slug: "sorozatok",            icon: "aₙ", delay: "stagger-4" },
  { slug: "statisztika",          icon: "σ", delay: "stagger-4" },
  { slug: "exponencialis",        icon: "eˣ", delay: "stagger-1" },
  { slug: "koordinata-geometria", icon: "xy", delay: "stagger-2" },
  { slug: "differencialszamitas", icon: "∂", delay: "stagger-3" },
  { slug: "szovegfeladas",        icon: "✎", delay: "stagger-4" },
];

const STATS = [
  { value: "2 500+", label: "Feladat" },
  { value: "26",     label: "Témakör" },
  { value: "20+",    label: "Évjárat" },
  { value: "100+",   label: "Feladatsor" },
];

export default function HomePage() {
  return (
    <div className="space-y-24">

      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="relative rounded-3xl overflow-hidden min-h-[480px] flex items-center">
        {/* Background layers */}
        <div className="absolute inset-0 bg-gradient-to-br from-navy-700 via-navy-600 to-[#1a1040]" />
        <div className="absolute inset-0 dot-grid opacity-60" />
        {/* Red diagonal accent */}
        <div className="absolute -right-20 -top-20 w-96 h-96 bg-crimson-600/20 rounded-full blur-3xl" />
        <div className="absolute -left-10 bottom-0 w-64 h-64 bg-navy-500/30 rounded-full blur-3xl" />
        {/* Red stripe accent */}
        <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-crimson-500 via-crimson-600 to-transparent rounded-l-3xl" />

        <div className="relative z-10 px-8 sm:px-14 py-16 w-full flex flex-col lg:flex-row items-center gap-10">
          {/* Text content */}
          <div className="max-w-2xl space-y-7 flex-1">
            <div className="inline-flex items-center gap-2 bg-white/10 border border-white/15 rounded-full px-4 py-1.5 animate-fade-up">
              <span className="w-2 h-2 rounded-full bg-crimson-500 animate-pulse-slow" />
              <span className="text-white/75 text-xs font-medium tracking-wide uppercase">
                Boronkay György Technikum · Érettségi felkészítő
              </span>
            </div>

            <h1 className="text-4xl sm:text-5xl font-extrabold leading-tight animate-fade-up stagger-1">
              <span className="gradient-text">Matematika</span>
              <br />
              <span className="text-white">Feladatbank</span>
            </h1>

            <p className="text-slate-300 text-lg leading-relaxed animate-fade-up stagger-2">
              Középszintű és emelt szintű érettségi feladatok az eredeti vizsgalapokról,
              témakör és nehézség szerint szűrve.
            </p>

            <div className="flex flex-wrap gap-3 animate-fade-up stagger-3">
              <Link href="/feladatok" className="btn-primary inline-flex items-center gap-2">
                Feladatok böngészése <span className="text-crimson-200">→</span>
              </Link>
              <Link href="/feladatsor"
                className="inline-flex items-center gap-2 bg-white/10 border border-white/20 text-white
                           px-6 py-3 rounded-xl font-semibold hover:bg-white/20 active:scale-95 transition-all">
                Feladatsorok
              </Link>
            </div>
          </div>

          {/* Logo — stamp in, then float */}
          <div className="hidden lg:flex shrink-0 items-center justify-center animate-stamp" style={{ animationDelay: "0.3s" }}>
            <div className="relative animate-float" style={{ animationDelay: "1s" }}>
              {/* Glow ring */}
              <div className="absolute inset-0 rounded-full bg-crimson-600/20 blur-2xl scale-125" />
              <Image
                src="/boronkay-logo.png"
                alt="Boronkay György Technikum"
                width={200}
                height={200}
                className="relative drop-shadow-2xl hover:scale-105 transition-transform duration-500 cursor-default"
                priority
              />
            </div>
          </div>
        </div>
      </section>

      {/* ── Stats strip ───────────────────────────────────────────────── */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {STATS.map(({ value, label }) => (
          <div key={label}
            className="card p-5 text-center group hover:border-navy-200 dark:hover:border-navy-600">
            <div className="text-3xl font-extrabold text-navy-600 dark:text-navy-100 group-hover:text-crimson-600 dark:group-hover:text-crimson-400 transition-colors">
              {value}
            </div>
            <div className="text-sm text-slate-500 dark:text-slate-400 mt-1 font-medium">{label}</div>
          </div>
        ))}
      </section>

      {/* ── Level cards ───────────────────────────────────────────────── */}
      <section>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-5">Szint szerint</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Link href="/feladatok?szint=kozep"
            className="card p-6 flex items-center gap-5 group overflow-hidden relative">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-50 to-transparent dark:from-navy-600/10 opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative w-14 h-14 rounded-2xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-3xl group-hover:scale-110 transition-transform">
              📘
            </div>
            <div className="relative">
              <div className="font-bold text-slate-800 dark:text-slate-100 text-lg">Középszint</div>
              <div className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Kötelező érettségi, minden évből</div>
            </div>
            <span className="relative ml-auto text-2xl text-slate-200 dark:text-slate-700 group-hover:text-navy-500 dark:group-hover:text-navy-400 group-hover:translate-x-1 transition-all">→</span>
          </Link>

          <Link href="/feladatok?szint=emelt"
            className="card p-6 flex items-center gap-5 group overflow-hidden relative">
            <div className="absolute inset-0 bg-gradient-to-r from-crimson-50 to-transparent dark:from-crimson-900/10 opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative w-14 h-14 rounded-2xl bg-crimson-100 dark:bg-crimson-900/30 flex items-center justify-center text-3xl group-hover:scale-110 transition-transform">
              📗
            </div>
            <div className="relative">
              <div className="font-bold text-slate-800 dark:text-slate-100 text-lg">Emelt szint</div>
              <div className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Emelt érettségi és felvételi</div>
            </div>
            <span className="relative ml-auto text-2xl text-slate-200 dark:text-slate-700 group-hover:text-crimson-500 group-hover:translate-x-1 transition-all">→</span>
          </Link>
        </div>
      </section>

      {/* ── Quick links ───────────────────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Gyors elérés</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { href: "/feladatsor",  icon: "📋", title: "Feladatsorok",  desc: "Teljes érettségi vizsgalapok" },
            { href: "/statisztika", icon: "📊", title: "Statisztika",   desc: "Adatbázis összetétele" },
            { href: "/feladatok?tipus=rovid", icon: "⚡", title: "Rövid feladatok", desc: "Gyors 1–4. feladatok" },
          ].map(({ href, icon, title, desc }) => (
            <Link key={href} href={href}
              className="card p-5 flex items-center gap-4 group overflow-hidden relative">
              <div className="absolute inset-0 bg-gradient-to-r from-slate-50 to-transparent dark:from-white/5 opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="relative w-12 h-12 rounded-xl bg-slate-100 dark:bg-white/10 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform shrink-0">
                {icon}
              </div>
              <div className="relative">
                <div className="font-semibold text-slate-800 dark:text-slate-100">{title}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{desc}</div>
              </div>
              <span className="relative ml-auto text-xl text-slate-200 dark:text-slate-700 group-hover:text-navy-500 dark:group-hover:text-navy-400 group-hover:translate-x-1 transition-all shrink-0">→</span>
            </Link>
          ))}
        </div>
      </section>

      {/* ── Featured topics ───────────────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Témakörök</h2>
          <Link href="/temakoren-kint"
            className="text-sm font-semibold text-crimson-600 dark:text-crimson-400 hover:underline">
            Mind →
          </Link>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {FEATURED_TOPICS.map(({ slug, icon, delay }) => (
            <Link key={slug} href={`/feladatok?tema=${slug}`}
              className={`card p-4 flex items-center gap-3 group animate-fade-up ${delay}`}>
              <div className="w-10 h-10 rounded-xl bg-navy-50 dark:bg-white/10 border border-navy-100 dark:border-white/10
                              flex items-center justify-center font-bold text-navy-600 dark:text-slate-200
                              text-sm shrink-0 group-hover:bg-crimson-50 dark:group-hover:bg-crimson-900/30
                              group-hover:text-crimson-600 dark:group-hover:text-crimson-300
                              group-hover:border-crimson-200 dark:group-hover:border-crimson-600/40
                              transition-all duration-200">
                {icon}
              </div>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-100 leading-tight
                               group-hover:text-navy-700 dark:group-hover:text-white transition-colors">
                {TOPIC_LABELS[slug]}
              </span>
            </Link>
          ))}
        </div>
      </section>

    </div>
  );
}
