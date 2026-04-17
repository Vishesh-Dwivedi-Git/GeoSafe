"use client";

import { useCallback, useState, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import Navbar from "@/components/Navbar";
import Sidebar from "@/components/Sidebar";
import {
  useGeoSafe,
  type GeoSafeContextValue,
  type PipelineStep,
  type ResultData,
  type RiskFlag,
} from "@/context/GeoSafeContext";

// Dynamic imports to avoid SSR issues
const InteractiveMap = dynamic(() => import("@/components/InteractiveMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-black/60 rounded-xl">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        <span className="text-primary font-label text-xs uppercase tracking-widest">Loading Map</span>
      </div>
    </div>
  ),
});

const Dashboard = dynamic(() => import("@/components/Dashboard"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        <span className="text-primary font-label text-xs uppercase tracking-widest">Loading Dashboard</span>
      </div>
    </div>
  ),
});

const ProcessLayers = dynamic(() => import("@/components/ProcessLayers"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        <span className="text-primary font-label text-xs uppercase tracking-widest">Loading Analysis Layers</span>
      </div>
    </div>
  ),
});

// ──────────────────────────────────────────────
// Backend Simulation
// ──────────────────────────────────────────────

async function simulateBackendProcessing(
  dispatch: GeoSafeContextValue["dispatch"],
  steps: PipelineStep[]
) {
  const stepDelays = [1200, 1500, 1000, 1800, 1200, 1600, 1400];

  for (let i = 0; i < steps.length; i++) {
    dispatch({
      type: "UPDATE_PIPELINE_STEP",
      payload: { stepIndex: i, status: "active" },
    });

    await new Promise((resolve) => setTimeout(resolve, stepDelays[i]));

    dispatch({
      type: "UPDATE_PIPELINE_STEP",
      payload: { stepIndex: i, status: "done", durationMs: stepDelays[i] },
    });
  }
}

function generateMockAnalysisResponse(lat: number, lng: number) {
  const riskLevels: Array<"LOW" | "MEDIUM" | "HIGH"> = ["LOW", "MEDIUM", "HIGH"];
  const riskLevel = riskLevels[Math.floor(Math.random() * riskLevels.length)];
  const riskScore =
    riskLevel === "LOW"
      ? Math.random() * 33
      : riskLevel === "MEDIUM"
        ? 33 + Math.random() * 33
        : 66 + Math.random() * 34;

  return {
    report_id: `REPORT-${Date.now()}`,
    risk_classification: {
      risk_level: riskLevel,
      risk_score: Math.round(riskScore * 10) / 10,
      shap_features: [
        { feature: "forest_proximity", importance: Math.random() },
        { feature: "water_body_overlap", importance: Math.random() },
      ],
    },
    flags: [
      {
        category: "environmental",
        severity: "WARNING",
        flag_title: "Forest Proximity Alert",
        description: "Land is within 500m of protected forest area",
        icon: "forest",
      },
      {
        category: "water",
        severity: riskLevel === "HIGH" ? "CRITICAL" : "WARNING",
        flag_title: "Water Body Risk",
        description: "Potential flood zone based on topography",
        icon: "water",
      },
    ],
    llm_explanation: {
      summary: `The parcel at ${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E shows ${riskLevel.toLowerCase()} risk for development.`,
    },
    boundary_geojson: { type: "Polygon", coordinates: [[]] },
    centroid_lat: lat,
    centroid_lon: lng,
    area_sqm: 5000 + Math.random() * 15000,
    shareable_link: `https://geosafe.io/reports/${Math.random().toString(36).substr(2, 9)}`,
  };
}

type MockAnalysisResponse = ReturnType<typeof generateMockAnalysisResponse>;

export default function FlowPage() {
  const { state, dispatch, setResultData, setError, startProcessing } = useGeoSafe();
  const [activeTab, setActiveTab] = useState<"map" | "layers" | "dashboard">("map");
  const dashboardSwitchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-switch to dashboard when processing completes
  useEffect(() => {
    if (dashboardSwitchTimeoutRef.current) {
      clearTimeout(dashboardSwitchTimeoutRef.current);
      dashboardSwitchTimeoutRef.current = null;
    }

    if (state.resultData && !state.isProcessing) {
      const timeoutId = setTimeout(() => {
        setActiveTab("dashboard");
      }, 500);
      dashboardSwitchTimeoutRef.current = timeoutId;
    }

    return () => {
      if (dashboardSwitchTimeoutRef.current) {
        clearTimeout(dashboardSwitchTimeoutRef.current);
        dashboardSwitchTimeoutRef.current = null;
      }
    };
  }, [state.resultData, state.isProcessing]);

  // Start analysis with backend simulation
  const handleStartAnalysis = useCallback(async () => {
    if (!state.selectedLocation) return;

    try {
      setActiveTab("layers");
      startProcessing();

      // Simulate backend processing
      await simulateBackendProcessing(dispatch, state.pipelineSteps);
      await new Promise((resolve) => setTimeout(resolve, 500));

      const mockResponse = generateMockAnalysisResponse(
        state.selectedLocation.lat,
        state.selectedLocation.lng
      );

      const flags: RiskFlag[] = mockResponse.flags.map((f: MockAnalysisResponse["flags"][number]) => ({
        category: f.category,
        severity: (f.severity as RiskFlag["severity"]) || "WARNING",
        title: f.flag_title || "Unknown",
        description: f.description || "",
        icon: f.icon || "warning",
      }));

      const resultData: ResultData = {
        reportId: mockResponse.report_id,
        riskLevel: mockResponse.risk_classification.risk_level,
        riskScore: mockResponse.risk_classification.risk_score,
        flags,
        llmInsight: mockResponse.llm_explanation.summary,
        recommendedNextSteps: ["Review the detected risks before proceeding with development."],
        layerValidations: [],
        featureImportance: mockResponse.risk_classification.shap_features.map((f) => ({
          label: f.feature || "Feature",
          value: (f.importance || 0) * 100,
          color: (f.importance || 0) > 0.5 ? "#3adffa" : "#c890ff",
        })),
        metrics: [],
        shareableToken: "",
        boundaryGeoJSON: mockResponse.boundary_geojson,
        centroidLat: mockResponse.centroid_lat,
        centroidLon: mockResponse.centroid_lon,
        areaSqm: mockResponse.area_sqm,
      };

      setResultData(resultData);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Analysis failed";
      setError(message);
    }
  }, [state.selectedLocation, state.pipelineSteps, dispatch, startProcessing, setResultData, setError]);

  const tabs = [
    { id: "map" as const, label: "📍 Map", description: "Select Location" },
    { id: "layers" as const, label: "🔍 Layers", description: "Processing Steps" },
    { id: "dashboard" as const, label: "📊 Dashboard", description: "Results & Analysis" },
  ];

  const isMapLocked = state.isProcessing;
  const isLayersDisabled = !state.selectedLocation;
  const isDashboardDisabled = !state.resultData || state.isProcessing;

  return (
    <>
      <Navbar />
      <Sidebar />

      <main className="ml-20 pt-16 h-screen bg-black flex flex-col overflow-hidden">
        {/* Tab Navigation */}
        <div className="border-b border-white/10 bg-black/50 backdrop-blur-sm px-6">
          <div className="flex items-center gap-1 h-16">
            {tabs.map((tab, idx) => (
              <div key={tab.id}>
                <button
                  onClick={() => {
                    if (tab.id === "map" && isMapLocked) return;
                    if (tab.id === "layers" && isLayersDisabled) return;
                    if (tab.id === "dashboard" && isDashboardDisabled) return;
                    setActiveTab(tab.id);
                  }}
                  disabled={
                    (tab.id === "map" && isMapLocked) ||
                    (tab.id === "layers" && isLayersDisabled) ||
                    (tab.id === "dashboard" && isDashboardDisabled)
                  }
                  className={`relative px-6 py-3 flex flex-col items-center gap-1 font-semibold transition-all duration-300 ${
                    activeTab === tab.id
                      ? "text-primary"
                      : (tab.id === "map" && isMapLocked) ||
                          (tab.id === "layers" && isLayersDisabled) ||
                          (tab.id === "dashboard" && isDashboardDisabled)
                        ? "text-slate-600 cursor-not-allowed"
                        : "text-slate-400 hover:text-white"
                  }`}
                >
                  <span className="text-lg">{tab.label}</span>
                  <span className="text-xs font-label text-slate-500">{tab.description}</span>
                  {activeTab === tab.id && (
                    <div className="absolute bottom-0 left-0 right-0 h-1 bg-linear-to-r from-primary to-primary-container" />
                  )}
                </button>

                {/* Connector between tabs */}
                {idx < tabs.length - 1 && (
                  <div className={`w-1 h-8 mx-2 ${activeTab === tab.id || activeTab === tabs[idx + 1].id ? "bg-primary/50" : "bg-slate-700/30"} transition-colors duration-300`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden relative">
          {/* Map Tab */}
          <div
            className={`absolute inset-0 transition-all duration-500 ${
              activeTab === "map" ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
            }`}
          >
            <InteractiveMap onAnalyze={handleStartAnalysis} useFlowMode={true} />
          </div>

          {/* Layers Tab - Shows processing animation */}
          <div
            className={`absolute inset-0 overflow-auto transition-all duration-500 ${
              activeTab === "layers" ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
            }`}
          >
            {!state.selectedLocation ? (
              <div className="w-full h-full flex items-center justify-center flex-col gap-4">
                <span className="material-symbols-outlined text-6xl text-primary">location_off</span>
                <p className="text-white font-semibold">No location selected</p>
                <p className="text-slate-400 text-sm">Go to Map tab to select a location first</p>
              </div>
            ) : (
              <ProcessLayers resultData={state.resultData} onViewReport={() => setActiveTab("dashboard")} />
            )}
          </div>

          {/* Dashboard Tab - Shows results */}
          <div
            className={`absolute inset-0 overflow-auto transition-all duration-500 ${
              activeTab === "dashboard" ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
            }`}
          >
            {!state.resultData ? (
              <div className="w-full h-full flex items-center justify-center flex-col gap-4">
                <span className="material-symbols-outlined text-6xl text-slate-600">dashboard</span>
                <p className="text-white font-semibold">No results yet</p>
                <p className="text-slate-400 text-sm">Complete the analysis to see results</p>
              </div>
            ) : (
              <Dashboard />
            )}
          </div>
        </div>
      </main>
    </>
  );
}
