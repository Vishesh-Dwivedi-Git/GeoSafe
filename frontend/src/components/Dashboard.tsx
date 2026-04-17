"use client";

import React, { useMemo } from "react";
import { useGeoSafe } from "@/context/GeoSafeContext";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface InsightCardProps {
  icon: string;
  title: string;
  value: string;
  description: string;
  color: "green" | "yellow" | "red" | "blue";
}

function InsightCard({ icon, title, value, description, color }: InsightCardProps) {
  const colorClasses = {
    green: "bg-emerald-900/30 border-emerald-500/30 text-emerald-300",
    yellow: "bg-yellow-900/30 border-yellow-500/30 text-yellow-300",
    red: "bg-red-900/30 border-red-500/30 text-red-300",
    blue: "bg-blue-900/30 border-blue-500/30 text-blue-300",
  };

  return (
    <div className={`${colorClasses[color]} border rounded-lg p-4 transition-all duration-300`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="font-label text-xs uppercase tracking-widest text-slate-400 mb-1">{title}</p>
          <p className="font-headline text-2xl font-bold mb-2">{value}</p>
          <p className="font-label text-xs text-slate-500">{description}</p>
        </div>
        <span className="material-symbols-outlined text-3xl opacity-50">{icon}</span>
      </div>
    </div>
  );
}

const PIE_COLORS = ["#ef4444", "#f59e0b", "#3b82f6", "#10b981"];

export default function Dashboard() {
  const { state } = useGeoSafe();
  const { selectedLocation, resultData } = state;
  const safeLayers = useMemo(() => resultData?.layerValidations || [], [resultData?.layerValidations]);
  const safeFlags = useMemo(() => resultData?.flags || [], [resultData?.flags]);
  const safeImportance = resultData?.featureImportance || [];

  const overlapChartData = useMemo(
    () =>
      safeLayers.map((layer) => ({
        name: layer.layerLabel.length > 16 ? `${layer.layerLabel.slice(0, 16)}...` : layer.layerLabel,
        overlap: Number(layer.overlapPct.toFixed(2)),
        score: Number((layer.spatialScore * 100).toFixed(2)),
      })),
    [safeLayers]
  );

  const flagSeverityData = useMemo(() => {
    const counts = { CRITICAL: 0, WARNING: 0, NOMINAL: 0 };
    safeFlags.forEach((flag) => {
      counts[flag.severity] += 1;
    });
    return [
      { name: "Critical", value: counts.CRITICAL },
      { name: "Warning", value: counts.WARNING },
      { name: "Nominal", value: counts.NOMINAL },
    ].filter((item) => item.value > 0);
  }, [safeFlags]);

  if (!resultData || !selectedLocation) return null;

  const topFeature = safeImportance[0];
  const intersectingLayers = safeLayers.filter((l) => l.intersects).length;
  const highestOverlap = Math.max(0, ...safeLayers.map((l) => l.overlapPct));

  const handleDownloadReport = () => {
    const payload = {
      exportedAt: new Date().toISOString(),
      location: selectedLocation,
      report: resultData,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `geosafe-report-${resultData.reportId || "latest"}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  const handleShareReport = async () => {
    const shareText = `GeoSafe report ${resultData.reportId} | Risk ${resultData.riskLevel} (${resultData.riskScore.toFixed(1)}/100) at ${selectedLocation.lat.toFixed(5)}, ${selectedLocation.lng.toFixed(5)}`;
    if (navigator.share) {
      try {
        await navigator.share({ title: `GeoSafe Report ${resultData.reportId}`, text: shareText });
        return;
      } catch {
        // no-op
      }
    }
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(shareText);
    }
  };

  return (
    <div className="w-full h-full flex flex-col overflow-y-auto no-scrollbar">
      <div className="shrink-0 px-8 py-6 border-b border-white/5 bg-linear-to-b from-black to-black/50">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="font-headline text-3xl font-bold text-white mb-1">Safety Analysis Report</h1>
            <p className="font-label text-sm text-slate-400 uppercase tracking-widest">
              {selectedLocation.lat.toFixed(4)} N, {selectedLocation.lng.toFixed(4)} E
            </p>
          </div>
          <div className="text-right">
            <p className="font-label text-xs uppercase tracking-widest text-slate-400 mb-2">Risk Level</p>
            <div
              className={`inline-flex items-center px-4 py-2 rounded-lg font-headline font-bold text-lg gap-2 ${
                resultData.riskLevel === "LOW"
                  ? "bg-emerald-900/40 text-emerald-300 border border-emerald-500/30"
                  : resultData.riskLevel === "MEDIUM"
                    ? "bg-yellow-900/40 text-yellow-300 border border-yellow-500/30"
                    : "bg-red-900/40 text-red-300 border border-red-500/30"
              }`}
            >
              {resultData.riskLevel}
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-label text-xs uppercase tracking-widest text-slate-400">Risk Score</span>
            <span className="font-headline font-bold text-primary">{resultData.riskScore.toFixed(1)}/100</span>
          </div>
          <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden border border-slate-600/30">
            <div
              className={`h-full rounded-full transition-all duration-1000 ${
                resultData.riskScore < 33
                  ? "bg-linear-to-r from-emerald-500 to-emerald-400"
                  : resultData.riskScore < 66
                    ? "bg-linear-to-r from-yellow-500 to-yellow-400"
                    : "bg-linear-to-r from-red-500 to-red-400"
              }`}
              style={{ width: `${resultData.riskScore}%` }}
            />
          </div>
        </div>
      </div>

      <div className="flex-1 px-8 py-6 space-y-8">
        <section>
          <h2 className="font-headline text-xl font-bold text-white mb-4">Key Insights</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <InsightCard
              icon="warning"
              title="Highest Overlap"
              value={`${highestOverlap.toFixed(1)}%`}
              description="Maximum overlap across fetched layers"
              color={highestOverlap > 20 ? "red" : highestOverlap > 5 ? "yellow" : "green"}
            />
            <InsightCard
              icon="layers"
              title="Intersecting Layers"
              value={`${intersectingLayers}`}
              description="Layers intersecting your parcel"
              color={intersectingLayers > 2 ? "red" : intersectingLayers > 0 ? "yellow" : "green"}
            />
            <InsightCard
              icon="flag"
              title="Legal Flags"
              value={`${resultData.flags.length}`}
              description="Regulatory/environment flags mapped"
              color={resultData.flags.length > 2 ? "red" : resultData.flags.length > 0 ? "yellow" : "green"}
            />
            <InsightCard
              icon="analytics"
              title="Top Risk Factor"
              value={topFeature ? `${topFeature.value.toFixed(0)}%` : "N/A"}
              description={topFeature ? topFeature.label : "No SHAP factors available"}
              color="blue"
            />
          </div>
        </section>

        <section>
          <h2 className="font-headline text-xl font-bold text-white mb-4">Layer Overlap and Risk Scores</h2>
          <div className="bg-slate-900/40 border border-slate-700/50 rounded-lg p-6">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={overlapChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(71, 85, 105, 0.3)" />
                <XAxis dataKey="name" stroke="rgb(148, 163, 184)" />
                <YAxis stroke="rgb(148, 163, 184)" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "1px solid rgba(71, 85, 105, 0.5)",
                    borderRadius: "8px",
                  }}
                />
                <Bar dataKey="overlap" fill="#3adffa" radius={[6, 6, 0, 0]} />
                <Bar dataKey="score" fill="#c890ff" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h3 className="font-headline text-lg font-bold text-white mb-4">Flag Severity Split</h3>
              <div className="bg-slate-900/40 border border-slate-700/50 rounded-lg p-6">
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie data={flagSeverityData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label>
                      {flagSeverityData.map((entry, index) => (
                        <Cell key={`${entry.name}-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1e293b",
                        border: "1px solid rgba(71, 85, 105, 0.5)",
                        borderRadius: "8px",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div>
              <h3 className="font-headline text-lg font-bold text-white mb-4">Model Feature Importance</h3>
              <div className="bg-slate-900/40 border border-slate-700/50 rounded-lg p-6">
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart
                    data={safeImportance.map((item) => ({
                      feature: item.label,
                      importance: Number(item.value.toFixed(2)),
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(71, 85, 105, 0.3)" />
                    <XAxis dataKey="feature" stroke="rgb(148, 163, 184)" />
                    <YAxis stroke="rgb(148, 163, 184)" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1e293b",
                        border: "1px solid rgba(71, 85, 105, 0.5)",
                        borderRadius: "8px",
                      }}
                    />
                    <Bar dataKey="importance" fill="#3adffa" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </section>

        <section>
          <h2 className="font-headline text-xl font-bold text-white mb-4">Recommended Actions</h2>
          <div className="space-y-3">
            {(resultData.recommendedNextSteps.length > 0
              ? resultData.recommendedNextSteps
              : ["Review legal flags and consult local authority before proceeding."]
            ).map((action, idx) => (
              <div key={idx} className="flex items-center gap-4 p-4 bg-slate-900/40 border border-slate-700/50 rounded-lg">
                <span className="material-symbols-outlined text-primary text-2xl">check_circle</span>
                <p className="font-label text-sm text-slate-300">{action}</p>
              </div>
            ))}
          </div>
        </section>

        {resultData.flags.length > 0 && (
          <section>
            <h2 className="font-headline text-xl font-bold text-white mb-4">Regulatory Flags ({resultData.flags.length})</h2>
            <div className="space-y-3">
              {resultData.flags.slice(0, 8).map((flag, idx) => (
                <div
                  key={idx}
                  className={`p-4 rounded-lg border ${
                    flag.severity === "CRITICAL"
                      ? "bg-red-900/20 border-red-500/40"
                      : flag.severity === "WARNING"
                        ? "bg-yellow-900/20 border-yellow-500/40"
                        : "bg-blue-900/20 border-blue-500/40"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className="material-symbols-outlined text-lg">{flag.icon || "flag"}</span>
                    <div className="flex-1">
                      <p className="font-headline font-bold text-white mb-1">{flag.title}</p>
                      <p className="font-label text-xs text-slate-300">{flag.description}</p>
                    </div>
                    <span className="text-xs font-bold px-3 py-1 rounded-full bg-black/30">{flag.severity}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {resultData.llmInsight && (
          <section>
            <h2 className="font-headline text-xl font-bold text-white mb-4">AI Explanation</h2>
            <div className="bg-linear-to-r from-primary/10 to-primary-container/10 border border-primary/30 rounded-lg p-6">
              <p className="font-label text-sm leading-relaxed text-slate-300">{resultData.llmInsight}</p>
            </div>
          </section>
        )}

        <section className="pb-8">
          <div className="flex gap-3">
            <button
              onClick={handleDownloadReport}
              className="flex-1 px-6 py-3 bg-primary text-black font-label font-bold rounded-lg hover:bg-primary-container transition-all duration-300 flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined">download</span>
              Export Report
            </button>
            <button
              onClick={handleShareReport}
              className="flex-1 px-6 py-3 bg-slate-800 text-white font-label font-bold rounded-lg hover:bg-slate-700 transition-all duration-300 flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined">share</span>
              Share Report
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
