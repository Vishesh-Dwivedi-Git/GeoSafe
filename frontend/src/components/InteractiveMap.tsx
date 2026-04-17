"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useGeoSafe } from "@/context/GeoSafeContext";
import { analyzeLocation, type ApiError, type AnalysisResponse } from "@/services/api";

// We dynamically import Leaflet to avoid SSR issues in Next.js
let L: typeof import("leaflet") | null = null;
type LeafletContainer = HTMLDivElement & {
  _leaflet_map?: { remove: () => void };
} & Record<string, unknown>;

interface InteractiveMapProps {
  onAnalyze?: () => void | Promise<void>;
  useFlowMode?: boolean;
}

export default function InteractiveMap({ onAnalyze, useFlowMode = false }: InteractiveMapProps) {
  const router = useRouter();
  const { state, setLocation, setResultData, startProcessing } = useGeoSafe();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);
  const pulseMarkerRef = useRef<L.CircleMarker | null>(null);
  const initAttemptedRef = useRef(false); // Track if init was already attempted
  const [isMapReady, setIsMapReady] = useState(false);
  const [hoveredCoords, setHoveredCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Initialize map
  useEffect(() => {
    if (mapInstanceRef.current || !mapContainerRef.current) return;
    initAttemptedRef.current = true;

    const initMap = async () => {
      // Dynamic import to avoid SSR
      const leaflet = await import("leaflet");
      L = leaflet;

      const container = mapContainerRef.current as LeafletContainer | null;
      if (!container) return;

      // CRITICAL: Clear any existing Leaflet instance from DOM before initialization
      // This handles React 18 Strict Mode double-mounting
      if (container._leaflet_map) {
        try {
          const existingMap = container._leaflet_map;
          existingMap.remove();
        } catch {
          // Ignore errors
        }
        delete container._leaflet_map;
      }

      // Clear all internal Leaflet properties
      for (const key in container) {
        if (key.startsWith('_leaflet')) {
          delete container[key];
        }
      }

      // Fix default marker icon paths for webpack/next.js
      delete (leaflet.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
      leaflet.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
        iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
        shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
      });

      const map = leaflet.map(mapContainerRef.current!, {
        center: [12.9716, 77.5946], // Bangalore, India default
        zoom: 12,
        zoomControl: false,
        attributionControl: false,
      });

      // Dark satellite tile layer for the orbital aesthetic
      leaflet
        .tileLayer(
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          { maxZoom: 19 }
        )
        .addTo(map);

      // Add zoom control to bottom-right
      leaflet.control.zoom({ position: "bottomright" }).addTo(map);

      // Click handler
      map.on("click", (e: L.LeafletMouseEvent) => {
        const { lat, lng } = e.latlng;
        placeMarker(leaflet, map, lat, lng);
        setLocation(lat, lng);
      });

      // Mouse move for hover coordinates
      map.on("mousemove", (e: L.LeafletMouseEvent) => {
        setHoveredCoords({ lat: e.latlng.lat, lng: e.latlng.lng });
      });

      map.on("mouseout", () => {
        setHoveredCoords(null);
      });

      mapInstanceRef.current = map;
      setIsMapReady(true);

      // If we already have a selected location, place marker
      if (state.selectedLocation) {
        placeMarker(leaflet, map, state.selectedLocation.lat, state.selectedLocation.lng);
      }
    };

    initMap().catch((err) => {
      console.warn("Map initialization warning:", err instanceof Error ? err.message : String(err));
      mapInstanceRef.current = null;
      setIsMapReady(true);
    });

    return () => {
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.remove();
        } catch {
          // Ignore cleanup errors
        }
        mapInstanceRef.current = null;
      }
      setIsMapReady(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update marker when selectedLocation changes externally
  useEffect(() => {
    if (!L || !mapInstanceRef.current || !state.selectedLocation) return;
    placeMarker(L, mapInstanceRef.current, state.selectedLocation.lat, state.selectedLocation.lng);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.selectedLocation]);

  const placeMarker = useCallback(
    (leaflet: typeof import("leaflet"), map: L.Map, lat: number, lng: number) => {
      // Remove existing markers
      if (markerRef.current) {
        map.removeLayer(markerRef.current);
      }
      if (pulseMarkerRef.current) {
        map.removeLayer(pulseMarkerRef.current);
      }

      // Cyan pulsing circle (outer)
      const pulseCircle = leaflet.circleMarker([lat, lng], {
        radius: 20,
        color: "#3adffa",
        fillColor: "#3adffa",
        fillOpacity: 0.15,
        weight: 2,
        opacity: 0.6,
        className: "map-pulse-marker",
      });
      pulseCircle.addTo(map);
      pulseMarkerRef.current = pulseCircle;

      // Custom cyan marker icon
      const customIcon = leaflet.divIcon({
        className: "custom-marker-icon",
        html: `
          <div style="position:relative; display:flex; align-items:center; justify-content:center;">
            <div style="width:16px; height:16px; border-radius:50%; background:#3adffa; box-shadow: 0 0 20px rgba(58,223,250,0.8), 0 0 40px rgba(58,223,250,0.4); border: 2px solid rgba(255,255,255,0.9);"></div>
            <div style="position:absolute; width:32px; height:32px; border-radius:50%; border:2px solid rgba(58,223,250,0.4); animation: markerPing 2s infinite;"></div>
          </div>
        `,
        iconSize: [40, 40],
        iconAnchor: [20, 20],
      });

      const marker = leaflet.marker([lat, lng], { icon: customIcon });
      marker.addTo(map);
      markerRef.current = marker;

      // Smooth fly to location
      map.flyTo([lat, lng], Math.max(map.getZoom(), 14), {
        duration: 1.2,
      });
    },
    []
  );

  // Handle analyze location button click
  const handleAnalyzeArea = useCallback(async () => {
    if (!state.selectedLocation) return;

    setIsAnalyzing(true);
    setAnalysisError(null);

    // If using flow mode with custom callback, use that
    if (useFlowMode && onAnalyze) {
      try {
        await onAnalyze();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Analysis failed";
        setAnalysisError(message);
      } finally {
        setIsAnalyzing(false);
      }
      return;
    }

    // Otherwise use direct API call mode (legacy)
    try {
      startProcessing();
      router.push("/analysis");

      const response: AnalysisResponse = await analyzeLocation(
        state.selectedLocation.lat,
        state.selectedLocation.lng,
        500 // 500m radius
      );

      const resultData = {
        reportId: response.report_id || "REPORT-" + Date.now(),
        riskLevel: response.risk_classification?.risk_level || "UNKNOWN",
        riskScore: response.risk_classification?.risk_score ?? 0,
        flags: (response.flags || []).map((f) => ({
          category: f.category || "General",
          severity: f.severity || "WARNING",
          title: f.flag_title || "Unknown Flag",
          description: f.description || "",
          icon: f.icon || "warning",
        })),
        llmInsight: response.llm_explanation?.summary || "",
        recommendedNextSteps: response.recommended_next_steps || [],
        layerValidations: (response.layer_validations || []).map((layer) => ({
          layerName: layer.layer_name,
          layerLabel: layer.layer_label,
          intersects: layer.intersects,
          overlapPct: layer.overlap_pct,
          spatialScore: layer.spatial_score,
        })),
        featureImportance: (response.risk_classification?.shap_features || []).map((f) => ({
          label: f.feature || "",
          value: (f.importance ?? 0) * 100,
          color: (f.importance ?? 0) > 0.5 ? "#3adffa" : "#c890ff",
        })),
        metrics: [
          { label: "Spectral Integrity", value: "99.42%", trend: "+0.2%", trendIcon: "trending_up" },
          { label: "Cloud Obscurity", value: "2.1%", trend: "CLEAR", trendIcon: "verified" },
          {
            label: "KGIS Compliance",
            value: `${response.risk_classification?.risk_score ?? 0}/100`,
            trend: response.risk_classification?.risk_level === "LOW" ? "PASSED" : "FAILED",
            trendIcon: response.risk_classification?.risk_level === "LOW" ? "check_circle" : "report",
          },
        ],
        shareableToken: response.shareable_link?.split("/").pop() || "",
        boundaryGeoJSON: response.boundary_geojson,
        centroidLat: response.centroid_lat,
        centroidLon: response.centroid_lon,
        areaSqm: response.area_sqm,
      };

      setResultData(resultData);
      setIsAnalyzing(false);
    } catch (err) {
      const apiError = err as ApiError;
      setAnalysisError(apiError.detail || apiError.message || "Analysis failed");
      setIsAnalyzing(false);
      setTimeout(() => setAnalysisError(null), 5000);
    }
  }, [state.selectedLocation, setResultData, startProcessing, router, useFlowMode, onAnalyze]);

  return (
    <div className="relative w-full h-full rounded-xl overflow-hidden group">
      {/* Map Container */}
      <div ref={mapContainerRef} className="w-full h-full z-0" />

      {/* Loading State */}
      {!isMapReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-20">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-primary font-label text-xs uppercase tracking-widest">
              Initializing Orbital View
            </span>
          </div>
        </div>
      )}

      {/* Hover Coordinate Display */}
      {hoveredCoords && (
        <div className="absolute top-4 left-4 z-30 bg-black/80 backdrop-blur-xl border border-white/10 px-4 py-2 rounded-lg pointer-events-none">
          <div className="flex items-center gap-3 font-label text-[10px] tracking-widest uppercase">
            <span className="text-primary">
              LAT: {hoveredCoords.lat.toFixed(6)}
            </span>
            <span className="text-primary">
              LNG: {hoveredCoords.lng.toFixed(6)}
            </span>
          </div>
        </div>
      )}

      {/* Selected Location Badge */}
      {state.selectedLocation && (
        <div className="absolute bottom-4 left-4 z-30 bg-black/80 backdrop-blur-xl border border-primary/30 px-4 py-3 rounded-lg shadow-[0_0_20px_rgba(58,223,250,0.1)]">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(58,223,250,0.8)]" />
            <span className="text-primary font-label text-[10px] uppercase tracking-widest font-bold">
              Target Acquired
            </span>
          </div>
          <div className="font-label text-xs text-white mb-3">
            {state.selectedLocation.lat.toFixed(6)}° N, {state.selectedLocation.lng.toFixed(6)}° E
          </div>
          
          {/* Analyze Button */}
          <button
            onClick={handleAnalyzeArea}
            disabled={isAnalyzing}
            className={`w-full py-3 px-4 rounded-lg font-label font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-lg ${
              isAnalyzing
                ? "bg-primary/20 text-primary/50 cursor-not-allowed shadow-primary/20"
                : "bg-linear-to-r from-cyan-500 to-blue-500 hover:shadow-[0_0_25px_rgba(58,223,250,0.6)] hover:from-cyan-400 hover:to-blue-400 active:scale-95 text-white cursor-pointer shadow-lg shadow-primary/50"
            }`}
          >
            {isAnalyzing ? (
              <>
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-base">analytics</span>
                <span>Analyze Area</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Click Prompt */}
      {!state.selectedLocation && isMapReady && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 bg-black/70 backdrop-blur-xl border border-white/10 px-6 py-3 rounded-full pointer-events-none animate-pulse">
          <span className="text-on-surface-variant font-label text-xs uppercase tracking-widest">
            Click anywhere to select a parcel
          </span>
        </div>
      )}

      {/* Scan Grid Overlay */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.04] z-10">
        <div
          className="w-full h-full"
          style={{
            backgroundImage:
              "linear-gradient(#3adffa 1px, transparent 1px), linear-gradient(90deg, #3adffa 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />
      </div>

      {/* Crosshair Center */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10 opacity-20">
        <div className="relative">
          <div className="absolute w-12 h-px bg-primary -translate-x-full" />
          <div className="absolute w-12 h-px bg-primary translate-x-0" />
          <div className="absolute h-12 w-px bg-primary -translate-y-full -translate-x-[0.5px]" />
          <div className="absolute h-12 w-px bg-primary translate-y-0 -translate-x-[0.5px]" />
        </div>
      </div>

      {/* Analysis Error Display */}
      {analysisError && (
        <div className="absolute top-4 right-4 z-40 bg-red-900/90 backdrop-blur-xl border border-red-500/50 px-4 py-3 rounded-lg shadow-[0_0_20px_rgba(239,68,68,0.2)] max-w-xs animate-in fade-in slide-in-from-top-2">
          <div className="flex items-start gap-3">
            <span className="text-red-400 text-lg">⚠️</span>
            <div>
              <p className="font-label text-xs uppercase tracking-widest text-red-300 font-bold mb-1">
                Analysis Failed
              </p>
              <p className="font-label text-xs text-red-200">
                {analysisError}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
