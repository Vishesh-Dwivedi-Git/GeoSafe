"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import Sidebar from "@/components/Sidebar";
import ProcessLayers from "@/components/ProcessLayers";
import { useGeoSafe } from "@/context/GeoSafeContext";

export default function LayersPage() {
  const router = useRouter();
  const { state } = useGeoSafe();

  useEffect(() => {
    if (!state.selectedLocation && !state.isProcessing && !state.resultData) {
      router.replace("/pipeline");
      return;
    }

    if (state.resultData && !state.isProcessing) {
      const timeout = setTimeout(() => {
        router.push("/analysis");
      }, 500);

      return () => clearTimeout(timeout);
    }
  }, [state.selectedLocation, state.resultData, state.isProcessing, router]);

  return (
    <>
      <Navbar />
      <Sidebar />

      <main className="ml-20 pt-16 h-screen bg-black overflow-y-auto">
        <ProcessLayers resultData={state.resultData} onViewReport={() => router.push("/analysis")} />
      </main>
    </>
  );
}
