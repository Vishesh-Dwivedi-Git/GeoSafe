"use client";

import { usePathname } from "next/navigation";
import { useGeoSafe } from "@/context/GeoSafeContext";
import Link from "next/link";

const navItems = [
  { icon: "location_on", label: "Map", href: "/pipeline", id: "map" },
  { icon: "layers", label: "Layers", href: "/layers", id: "layers" },
  { icon: "bar_chart", label: "Analysis", href: "/analysis", id: "analysis" },
  { icon: "description", label: "Reports", href: "/reports", id: "reports" },
  { icon: "feedback", label: "Feedback", href: "/feedback", id: "feedback" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { state } = useGeoSafe();

  const isActive = (href: string) => {
    if (href === "/pipeline" && pathname === "/pipeline") return true;
    if (href === "/analysis" && pathname === "/analysis") return true;
    if (href === "/layers" && pathname === "/layers") return true;
    if (href === "/reports" && pathname === "/reports") return true;
    if (href === "/feedback" && pathname === "/feedback") return true;
    return false;
  };

  return (
    <aside className="fixed left-0 top-0 h-full flex flex-col items-center py-20 z-40 w-20 sidebar-glass">
      {/* User Profile */}
      <div className="flex flex-col items-center gap-2 mb-12">
        <div className="w-10 h-10 rounded-full overflow-hidden border border-primary/30 bg-surface-container-highest flex items-center justify-center hover:border-primary/60 transition-all duration-300 cursor-pointer">
          <span className="material-symbols-outlined text-primary text-xl">person</span>
        </div>
        <span className="text-[8px] text-primary font-headline uppercase tracking-[0.2em]">
          GEO-1
        </span>
      </div>

      {/* Navigation Items */}
      <div className="flex flex-col gap-1 w-full flex-1">
        {navItems.map((item) => {
          const active = isActive(item.href);
          const canNavigate =
            item.id === "map" ||
            (item.id === "layers" && !!state.selectedLocation) ||
            (item.id === "analysis" && !!state.resultData) ||
            (item.id === "reports" && !!state.resultData);

          // Disable navigation if not ready
          if (!canNavigate && item.href !== "/pipeline") {
            return (
              <div
                key={item.label}
                className="flex flex-col items-center py-4 cursor-not-allowed opacity-40 transition-all duration-150"
              >
                <span className="material-symbols-outlined mb-1 text-2xl text-slate-600">
                  {item.icon}
                </span>
                <span className="font-headline text-[10px] uppercase tracking-widest text-slate-600">
                  {item.label}
                </span>
              </div>
            );
          }

          return (
            <Link href={item.href} key={item.label}>
              <div
                className={`flex flex-col items-center py-4 cursor-pointer transition-all duration-150 relative group ${
                  active
                    ? "text-primary bg-primary/5 border-r-2 border-primary"
                    : "text-slate-500 hover:text-slate-200 hover:bg-white/5"
                }`}
              >
                {/* Active indicator glow */}
                {active && (
                  <div className="absolute inset-0 rounded-lg bg-primary/10 animate-pulse" />
                )}

                <span
                  className="material-symbols-outlined mb-1 text-2xl relative z-10 transition-all duration-300"
                  style={
                    active
                      ? { fontVariationSettings: "'FILL' 1", filter: "drop-shadow(0 0 8px rgba(58,223,250,0.6))" }
                      : { fontVariationSettings: "'FILL' 0" }
                  }
                >
                  {item.icon}
                </span>
                <span className="font-headline text-[10px] uppercase tracking-widest relative z-10">
                  {item.label}
                </span>

                {/* Tooltip */}
                <div className="absolute left-full ml-3 px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap font-label">
                  {item.label}
                  {!canNavigate && item.href !== "/pipeline" && (
                    <div className="text-slate-500 text-[10px] mt-1">
                      {item.id === "analysis" && "Requires completed processing"}
                      {item.id === "reports" && "Requires analysis"}
                      {item.id === "layers" && "Requires location"}
                    </div>
                  )}
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Settings */}
      <div className="mt-auto flex flex-col gap-1 w-full">
        <div className="flex flex-col items-center py-4 cursor-pointer text-slate-500 hover:text-slate-200 hover:bg-white/5 transition-all duration-150 group">
          <span className="material-symbols-outlined mb-1 text-2xl">settings</span>
          <span className="font-headline text-[10px] uppercase tracking-widest">Settings</span>

          {/* Tooltip */}
          <div className="absolute left-full ml-3 px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap font-label">
            Settings
          </div>
        </div>
      </div>
    </aside>
  );
}
