"use client";

import { useCallback, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import Sidebar from "@/components/Sidebar";
import { useGeoSafe } from "@/context/GeoSafeContext";

const InteractiveMap = dynamic(() => import("@/components/InteractiveMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-black/60 rounded-xl">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        <span className="text-primary font-label text-xs uppercase tracking-widest">Loading Orbital View</span>
      </div>
    </div>
  ),
});

export default function PipelinePage() {
  const router = useRouter();
  const { state, runPipeline, setSurveyFields } = useGeoSafe();
  const [inputMode, setInputMode] = useState<"coordinates" | "survey">("coordinates");

  const handleAnalyzeCoordinates = useCallback(async () => {
    router.push("/layers");
    await runPipeline("coordinates");
  }, [router, runPipeline]);

  const canAnalyzeSurvey = useMemo(() => {
    const s = state.surveyInput;
    return Boolean(s.district.trim() && s.taluk.trim() && s.village.trim() && s.surveyNumber.trim());
  }, [state.surveyInput]);

  const handleSurveyAnalyze = useCallback(async () => {
    if (!canAnalyzeSurvey) return;
    router.push("/layers");
    await runPipeline("survey");
  }, [canAnalyzeSurvey, router, runPipeline]);

  const useMapPointForSurvey = useCallback(() => {
    if (!state.selectedLocation) return;
    setSurveyFields({
      latitude: state.selectedLocation.lat.toFixed(6),
      longitude: state.selectedLocation.lng.toFixed(6),
    });
  }, [setSurveyFields, state.selectedLocation]);

  return (
    <>
      <Navbar />
      <Sidebar />

      <main className="ml-20 pt-16 h-screen bg-black flex flex-col overflow-hidden">
        <div className="shrink-0 px-8 py-4 border-b border-white/5">
          <h1 className="font-headline text-2xl font-bold text-white">Map and Survey Input</h1>
          <p className="font-label text-xs text-slate-400 uppercase tracking-widest">
            Choose map coordinates or survey details to start processing
          </p>
        </div>

        <div className="shrink-0 px-8 py-4 border-b border-white/5 bg-black/40">
          <div className="inline-flex rounded-lg border border-white/10 overflow-hidden mb-4">
            <button
              type="button"
              onClick={() => setInputMode("coordinates")}
              className={`px-4 py-2 text-xs font-bold uppercase tracking-widest ${
                inputMode === "coordinates" ? "bg-primary text-black" : "bg-transparent text-slate-300"
              }`}
            >
              Coordinates
            </button>
            <button
              type="button"
              onClick={() => setInputMode("survey")}
              className={`px-4 py-2 text-xs font-bold uppercase tracking-widest ${
                inputMode === "survey" ? "bg-primary text-black" : "bg-transparent text-slate-300"
              }`}
            >
              Survey
            </button>
          </div>

          {inputMode === "survey" && (
            <div className="rounded-xl border border-white/10 bg-black/50 p-4">
              <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-4 gap-3">
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] uppercase tracking-widest text-slate-400">District *</span>
                  <input
                    className="px-3 py-2 rounded-md bg-slate-900 border border-white/10 text-white text-sm"
                    placeholder="Bengaluru (Urban)"
                    value={state.surveyInput.district}
                    onChange={(e) => setSurveyFields({ district: e.target.value })}
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] uppercase tracking-widest text-slate-400">Taluk *</span>
                  <input
                    className="px-3 py-2 rounded-md bg-slate-900 border border-white/10 text-white text-sm"
                    placeholder="Bangalore-South"
                    value={state.surveyInput.taluk}
                    onChange={(e) => setSurveyFields({ taluk: e.target.value })}
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] uppercase tracking-widest text-slate-400">Village *</span>
                  <input
                    className="px-3 py-2 rounded-md bg-slate-900 border border-white/10 text-white text-sm"
                    placeholder="Begur"
                    value={state.surveyInput.village}
                    onChange={(e) => setSurveyFields({ village: e.target.value })}
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] uppercase tracking-widest text-slate-400">Survey Number *</span>
                  <input
                    className="px-3 py-2 rounded-md bg-slate-900 border border-white/10 text-white text-sm"
                    placeholder="1 or 45/1"
                    value={state.surveyInput.surveyNumber}
                    onChange={(e) => setSurveyFields({ surveyNumber: e.target.value })}
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] uppercase tracking-widest text-slate-400">Hobli (optional)</span>
                  <input
                    className="px-3 py-2 rounded-md bg-slate-900 border border-white/10 text-white text-sm"
                    placeholder="Kasaba"
                    value={state.surveyInput.hobli || ""}
                    onChange={(e) => setSurveyFields({ hobli: e.target.value })}
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] uppercase tracking-widest text-slate-400">Village Code (optional)</span>
                  <input
                    className="px-3 py-2 rounded-md bg-slate-900 border border-white/10 text-white text-sm"
                    placeholder="0201020003"
                    value={state.surveyInput.villageCode || ""}
                    onChange={(e) => setSurveyFields({ villageCode: e.target.value })}
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] uppercase tracking-widest text-slate-400">Latitude (optional)</span>
                  <input
                    className="px-3 py-2 rounded-md bg-slate-900 border border-white/10 text-white text-sm"
                    placeholder="12.863388"
                    value={state.surveyInput.latitude || ""}
                    onChange={(e) => setSurveyFields({ latitude: e.target.value })}
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] uppercase tracking-widest text-slate-400">Longitude (optional)</span>
                  <input
                    className="px-3 py-2 rounded-md bg-slate-900 border border-white/10 text-white text-sm"
                    placeholder="77.613011"
                    value={state.surveyInput.longitude || ""}
                    onChange={(e) => setSurveyFields({ longitude: e.target.value })}
                  />
                </label>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={useMapPointForSurvey}
                  disabled={!state.selectedLocation}
                  className={`px-3 py-2 rounded-md text-xs font-bold uppercase tracking-widest ${
                    state.selectedLocation
                      ? "bg-slate-800 text-slate-100 hover:bg-slate-700"
                      : "bg-slate-800/50 text-slate-500 cursor-not-allowed"
                  }`}
                >
                  Use Map Point
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setSurveyFields({
                      district: "Bengaluru (Urban)",
                      taluk: "Bangalore-South",
                      village: "Begur",
                      hobli: "",
                      villageCode: "",
                      surveyNumber: "",
                      latitude: "",
                      longitude: "",
                    })
                  }
                  className="px-3 py-2 rounded-md text-xs font-bold uppercase tracking-widest bg-slate-900 text-slate-300 hover:bg-slate-800"
                >
                  Reset Survey Form
                </button>
                <button
                  type="button"
                  onClick={handleSurveyAnalyze}
                  disabled={!canAnalyzeSurvey}
                  className={`ml-auto px-4 py-2 rounded-md text-xs font-bold uppercase tracking-widest ${
                    canAnalyzeSurvey
                      ? "bg-primary text-black hover:bg-primary/90"
                      : "bg-slate-700 text-slate-400 cursor-not-allowed"
                  }`}
                >
                  Analyze Survey
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="flex-1 p-4">
          <div className="w-full h-full rounded-xl overflow-hidden border border-white/5 shadow-[0_0_60px_rgba(0,0,0,0.8)]">
            <InteractiveMap onAnalyze={handleAnalyzeCoordinates} useFlowMode={true} />
          </div>
        </div>
      </main>
    </>
  );
}
