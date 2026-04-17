"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();
  const isHome = pathname === "/";

  return (
    <nav className="fixed top-0 w-full z-50 flex justify-between items-center px-8 h-16 nav-glass shadow-[0_0_50px_-12px_rgba(58,223,250,0.05)]">
      <div className="flex items-center gap-8">
        <Link
          href="/"
          className="text-2xl font-bold tracking-tighter text-primary font-headline uppercase"
        >
          GEOSAFE
        </Link>
        <div className="hidden md:flex items-center gap-6">
          <Link
            href="/"
            className={`font-medium font-label tracking-wider hover:bg-white/5 transition-all duration-300 px-3 py-1 text-xs uppercase ${
              isHome
                ? "text-primary font-bold border-b-2 border-primary pb-1"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Platform
          </Link>
          <Link
            href="/dashboard"
            className={`font-medium font-label tracking-wider hover:bg-white/5 transition-all duration-300 px-3 py-1 text-xs uppercase ${
              pathname === "/dashboard"
                ? "text-primary font-bold border-b-2 border-primary pb-1"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Insights
          </Link>
          <Link
            href="/pipeline"
            className={`font-medium font-label tracking-wider hover:bg-white/5 transition-all duration-300 px-3 py-1 text-xs uppercase ${
              pathname === "/pipeline"
                ? "text-primary font-bold border-b-2 border-primary pb-1"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Documentation
          </Link>
        </div>
      </div>
      <Link href="/pipeline">
        <button className="bg-gradient-to-br from-primary to-primary-container text-on-primary font-bold px-6 py-2 rounded-lg text-sm tracking-tight active:opacity-80 transition-all shadow-[0_0_20px_rgba(58,223,250,0.2)] hover:scale-105 cursor-pointer">
          Command Center
        </button>
      </Link>
    </nav>
  );
}
