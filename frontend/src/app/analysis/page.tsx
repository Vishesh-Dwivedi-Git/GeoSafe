"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import Sidebar from "@/components/Sidebar";
import Dashboard from "@/components/Dashboard";
import { useGeoSafe } from "@/context/GeoSafeContext";

export default function AnalysisPage() {
  const router = useRouter();
  const { state } = useGeoSafe();

  useEffect(() => {
    if (!state.selectedLocation) {
      router.replace("/pipeline");
    }
  }, [state.selectedLocation, router]);

  return (
    <>
      <Navbar />
      <Sidebar />

      <main className="ml-20 pt-16 h-screen bg-black overflow-hidden">
        {!state.resultData ? (
          <div className="w-full h-full flex items-center justify-center flex-col gap-4">
            <span className="material-symbols-outlined text-6xl text-slate-600">analytics</span>
            <p className="text-white font-semibold">Analysis is not ready yet</p>
            <p className="text-slate-400 text-sm">Complete Layers processing to view charts and report actions</p>
          </div>
        ) : (
          <Dashboard />
        )}
      </main>
    </>
  );
}
