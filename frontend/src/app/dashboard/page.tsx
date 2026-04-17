"use client";

import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import Sidebar from "@/components/Sidebar";
import { useGeoSafe } from "@/context/GeoSafeContext";

export default function DashboardPage() {
  const router = useRouter();
  const { state, resetFlow } = useGeoSafe();
  const result = state.resultData;

  // Fallback data for when there's no result (direct navigation)
  const riskLevel = result?.riskLevel ?? "HIGH";
  const riskScore = result?.riskScore ?? 24;
  const llmInsight =
    result?.llmInsight ||
    '"This land is high risk because it overlaps with a primary flood zone and a protected forest buffer area, violating the Karnataka KGIS Act. Development here faces mandatory legal rejection."';

  const flags = result?.flags?.length
    ? result.flags
    : [
        {
          category: "Legal",
          severity: "CRITICAL" as const,
          title: "Government-acquired land",
          description: "Overlap detected with KIADB Phase III acquisition notification (Ref: 2021/B-04).",
          icon: "gavel",
        },
        {
          category: "Legal",
          severity: "WARNING" as const,
          title: "Encroachment detected",
          description: "Satellite delta shows 14% boundary deviation vs official land records.",
          icon: "grid_view",
        },
        {
          category: "Environmental",
          severity: "CRITICAL" as const,
          title: "Flood zone overlap",
          description: "Asset intersects with 100-year flood plain topography analysis.",
          icon: "water_drop",
        },
        {
          category: "Environmental",
          severity: "CRITICAL" as const,
          title: "Forest buffer zone",
          description: "Violation of 100m proximity rule to protected reserve forest area.",
          icon: "forest",
        },
      ];

  const featureImportance = result?.featureImportance?.length
    ? result.featureImportance
    : [
        { label: "Buffer Overlap", value: 88, color: "#3adffa" },
        { label: "Soil Stability", value: 12, color: "#c890ff" },
        { label: "Slope Gradient", value: 4, color: "#6f758b" },
      ];

  const metrics = result?.metrics?.length
    ? result.metrics
    : [
        { label: "Spectral Integrity", value: "99.42%", trend: "+0.2% vs previous pass", trendIcon: "trending_up" },
        { label: "Cloud Obscurity", value: "2.1%", trend: "CLEAR SKY OPTIMIZED", trendIcon: "verified" },
        { label: "KGIS Compliance", value: `${riskScore}/100`, trend: riskLevel === "LOW" ? "PASSED VALIDATION" : "FAILED VALIDATION", trendIcon: riskLevel === "LOW" ? "check_circle" : "report" },
      ];

  const legalFlags = flags.filter(
    (f) => f.category === "Legal" || f.category === "Boundary"
  );
  const envFlags = flags.filter(
    (f) => f.category === "Environmental" || f.category === "General" || !["Legal", "Boundary"].includes(f.category)
  );

  const severityBadge = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "bg-error-container text-on-error-container";
      case "WARNING":
        return "bg-tertiary/30 text-on-surface";
      default:
        return "bg-secondary/30 text-on-surface";
    }
  };

  const riskBadgeColor =
    riskLevel === "HIGH" || riskLevel === "CRITICAL"
      ? "text-error border-error/40 shadow-[0_0_30px_rgba(255,113,108,0.15)]"
      : riskLevel === "MEDIUM"
      ? "text-tertiary border-tertiary/40 shadow-[0_0_30px_rgba(200,144,255,0.15)]"
      : "text-primary border-primary/40 shadow-[0_0_30px_rgba(58,223,250,0.15)]";

  const coordsDisplay = state.selectedLocation
    ? `${state.selectedLocation.lat.toFixed(4)}° N, ${state.selectedLocation.lng.toFixed(4)}° E`
    : "12.9716° N, 77.5946° E";

  return (
    <>
      <Navbar />
      <Sidebar />

      {/* Background Map Layer */}
      <main className="ml-20 pt-16 min-h-screen relative overflow-hidden bg-black">
        <div className="absolute inset-0 z-0 grayscale opacity-20 pointer-events-none">
          <img
            alt="Satellite background"
            className="w-full h-full object-cover"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuBbwo7B207tVRQfA6x0pmxF7NmxThB6ZleQP4hFFbSM3a-A6K-dcR8rNHjnFRBtXLQd-vcAl-fNsofMQu1aDnkwzWUQ5SXGdXAxdZ1XxlJCN576qy6vd7TkVjwGJS0moIP5iiTdG0GmxiiDowGk1FZtJO7mEbxAPW78hAdJYwOlryNz5lmYkH3t8DuzO3ebv98ygpeMm42HJhldpJSWn-vwGURvNasfljikEfV9zcbmeCmQypLUkisYhApjfYaQdHlwTbyqPhURJqs"
          />
        </div>

        {/* Dashboard Overlay Canvas */}
        <div className="relative z-10 p-8 flex flex-col gap-8 min-h-[calc(100vh-64px)]">
          {/* Analysis Panel */}
          <div className="glass-panel rounded-xl p-8 flex flex-col gap-8">
            {/* Header Section */}
            <div className="flex flex-col lg:flex-row justify-between items-start gap-4">
              <div className="flex flex-col gap-1">
                <span className="text-primary font-label tracking-widest text-xs uppercase opacity-80">
                  Telemetry Intelligence
                </span>
                <h1 className="text-white font-headline text-4xl font-bold tracking-tight">
                  Analysis Report: {result?.reportId ? result.reportId.slice(-8) : "ID-294-B"}
                </h1>
                <div className="flex items-center gap-2 mt-2">
                  <span className="material-symbols-outlined text-outline text-sm">
                    location_on
                  </span>
                  <span className="text-on-surface-variant font-label text-sm">
                    Sector 7G: {coordsDisplay}
                  </span>
                </div>
              </div>
              {/* Risk Badge */}
              <div className="flex flex-col items-end gap-2">
                <div className={`bg-black/40 border px-6 py-3 rounded flex flex-col items-center ${riskBadgeColor}`}>
                  <span className="font-headline text-3xl font-extrabold tracking-tighter">
                    {riskLevel} RISK
                  </span>
                  <span className="text-on-surface-variant text-[10px] uppercase tracking-[0.2em] font-bold">
                    {riskLevel === "LOW" ? "Clear for Development" : "Priority Intervention"}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-tertiary/70">
                  <span className="material-symbols-outlined text-sm">sync</span>
                  <span className="text-[10px] font-label uppercase tracking-wider">
                    Model: Orbital-V4.2
                  </span>
                </div>
              </div>
            </div>

            {/* Main Grid Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              {/* Risk Breakdown (Left Column) */}
              <div className="lg:col-span-8 flex flex-col gap-6">
                {/* Legal & Boundary Flags */}
                {(legalFlags.length > 0 || envFlags.length === 0) && (
                  <div className="flex flex-col gap-4">
                    <h3 className="text-on-surface-variant font-headline text-sm font-semibold uppercase tracking-widest flex items-center gap-2">
                      <span className="w-2 h-2 bg-error rounded-full shadow-[0_0_10px_rgba(255,113,108,0.5)]" />
                      Legal &amp; Boundary Flags
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {(legalFlags.length > 0 ? legalFlags : flags.slice(0, 2)).map((flag, i) => (
                        <div key={i} className="bg-black/40 border border-white/5 p-5 rounded-lg hover:border-primary/40 transition-all group hover:bg-white/[0.03]">
                          <div className="flex justify-between mb-4">
                            <span className="material-symbols-outlined text-primary group-hover:scale-110 transition-transform">
                              {flag.icon}
                            </span>
                            <span className={`${severityBadge(flag.severity)} px-2 py-0.5 rounded text-[10px] font-bold`}>
                              {flag.severity}
                            </span>
                          </div>
                          <h4 className="text-white font-headline text-lg mb-1">
                            {flag.title}
                          </h4>
                          <p className="text-on-surface-variant text-sm leading-relaxed">
                            {flag.description}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Environmental Compliance */}
                {envFlags.length > 0 && (
                  <div className="flex flex-col gap-4">
                    <h3 className="text-on-surface-variant font-headline text-sm font-semibold uppercase tracking-widest flex items-center gap-2">
                      <span className="w-2 h-2 bg-primary rounded-full shadow-[0_0_10px_rgba(58,223,250,0.5)]" />
                      Environmental Compliance
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {envFlags.map((flag, i) => (
                        <div key={i} className="bg-black/40 border border-white/5 p-5 rounded-lg hover:border-primary/40 transition-all group hover:bg-white/[0.03]">
                          <div className="flex justify-between mb-4">
                            <span className="material-symbols-outlined text-primary group-hover:scale-110 transition-transform">
                              {flag.icon}
                            </span>
                            <span className={`${severityBadge(flag.severity)} px-2 py-0.5 rounded text-[10px] font-bold`}>
                              {flag.severity}
                            </span>
                          </div>
                          <h4 className="text-white font-headline text-lg mb-1">
                            {flag.title}
                          </h4>
                          <p className="text-on-surface-variant text-sm leading-relaxed">
                            {flag.description}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Explainability Panel (Right Column) */}
              <div className="lg:col-span-4 bg-white/[0.02] border border-white/5 rounded-lg p-6 flex flex-col gap-6">
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <span className="material-symbols-outlined text-tertiary">
                      psychology
                    </span>
                    <h3 className="text-white font-headline text-sm font-bold uppercase tracking-widest">
                      LLM INSIGHTS
                    </h3>
                  </div>
                  <div className="bg-black border-l-2 border-tertiary p-4 rounded shadow-[inset_0_0_20px_rgba(0,0,0,1)]">
                    <p className="text-on-surface leading-relaxed text-sm italic opacity-90">
                      {llmInsight}
                    </p>
                  </div>
                </div>
                <div className="flex flex-col gap-4">
                  <h4 className="text-on-surface-variant font-label text-[10px] uppercase tracking-widest font-bold">
                    Feature Importance
                  </h4>
                  <div className="flex flex-col gap-3">
                    {featureImportance.map((f, i) => (
                      <div key={i} className={`flex flex-col gap-1 ${f.value < 10 ? "opacity-40" : ""}`}>
                        <div className="flex justify-between text-xs font-label">
                          <span className="text-on-surface opacity-80">
                            {f.label}
                          </span>
                          <span className="font-bold" style={{ color: f.color }}>
                            {Math.round(f.value)}%
                          </span>
                        </div>
                        <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-700"
                            style={{ width: `${f.value}%`, backgroundColor: f.color, boxShadow: `0 0 8px ${f.color}50` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                {/* Feedback Indicator */}
                <div className="mt-auto pt-6 border-t border-white/5">
                  <div className="flex items-center justify-between group cursor-pointer">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-primary rounded-full animate-pulse shadow-[0_0_8px_rgba(58,223,250,0.8)]" />
                      <span className="text-[10px] font-label text-on-surface-variant uppercase tracking-widest">
                        Model Improvement Active
                      </span>
                    </div>
                    <span className="material-symbols-outlined text-sm text-outline group-hover:text-primary transition-colors">
                      info
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer Actions */}
            <div className="flex justify-between items-center gap-4 pt-6 border-t border-white/5">
              <button
                onClick={() => {
                  resetFlow();
                  router.push("/pipeline");
                }}
                className="flex items-center gap-2 text-slate-400 font-label text-sm border border-white/10 px-6 py-2 rounded-lg hover:bg-white/5 transition-all cursor-pointer"
              >
                <span className="material-symbols-outlined text-base">
                  arrow_back
                </span>
                New Analysis
              </button>
              <div className="flex gap-3">
                <button className="flex items-center gap-2 text-primary font-label text-sm font-bold border border-primary/20 px-6 py-2 rounded-lg hover:bg-primary/10 transition-all cursor-pointer">
                  <span className="material-symbols-outlined text-base">
                    share
                  </span>
                  Share Dashboard
                </button>
                <button className="flex items-center gap-2 bg-gradient-to-br from-primary to-primary-container text-on-primary font-bold px-8 py-2 rounded-lg text-sm tracking-tight active:opacity-80 transition-all shadow-[0_0_20px_rgba(58,223,250,0.2)] cursor-pointer">
                  <span className="material-symbols-outlined text-base">
                    picture_as_pdf
                  </span>
                  Download PDF Report
                </button>
              </div>
            </div>
          </div>

          {/* Contextual Data Strip */}
          <div className="flex gap-4 overflow-x-auto pb-4 no-scrollbar">
            {metrics.map((m, i) => (
              <div key={i} className="min-w-[240px] bg-white/[0.03] backdrop-blur-xl p-5 rounded-lg flex flex-col gap-1 border border-white/5 shadow-lg">
                <span className="text-[10px] font-label text-on-surface-variant uppercase tracking-widest">
                  {m.label}
                </span>
                <span className={`text-2xl font-headline font-bold ${
                  m.trendIcon === "report" ? "text-error" : "text-white"
                }`}>
                  {m.value}
                </span>
                <div className={`mt-2 text-[10px] flex items-center gap-1 font-bold ${
                  m.trendIcon === "report" ? "text-error" : "text-primary"
                }`}>
                  <span className="material-symbols-outlined text-xs">
                    {m.trendIcon}
                  </span>
                  {m.trend}
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Map Coordinate Overlay */}
      <div className="fixed bottom-6 right-6 z-50 bg-black/80 backdrop-blur-xl border border-white/10 p-4 rounded font-label text-[10px] tracking-[0.2em] text-primary flex flex-col gap-2 shadow-2xl">
        <div className="flex justify-between gap-6">
          <span>AZIMUTH: 242.4°</span>
          <span>ELEV: 402KM</span>
        </div>
        <div className="flex justify-between gap-6">
          <span>LAT: {state.selectedLocation?.lat.toFixed(4) ?? "12.9716"}</span>
          <span>LNG: {state.selectedLocation?.lng.toFixed(4) ?? "77.5946"}</span>
        </div>
      </div>
    </>
  );
}
