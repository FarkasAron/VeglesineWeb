"use client";

export default function PrintButton() {
  return (
    <button
      onClick={() => window.print()}
      className="no-print inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold
                 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800
                 text-slate-600 dark:text-slate-300 hover:border-navy-300 dark:hover:border-navy-600
                 hover:text-navy-700 dark:hover:text-white transition-all shadow-sm"
      title="Nyomtatás"
    >
      <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 9V2h12v7M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2M6 14h12v8H6v-8z" />
      </svg>
      Nyomtatás
    </button>
  );
}
