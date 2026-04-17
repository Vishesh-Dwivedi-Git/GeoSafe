"use client";

import { useCallback, useMemo } from "react";
import { useGeoSafe, type GeoSafeContextValue, type PipelineStep, type ResultData, type RiskFlag } from "@/context/GeoSafeContext";

interface MockAnalysisResponse {
  report_id: string;
  risk_classification: {
    risk_level: "LOW" | "MEDIUM" | "HIGH";
    risk_score: number;
    shap_features: Array<{ feature: string; importance: number }>;
  };
  flags: Array<{
    category: string;
    severity: RiskFlag["severity"];
    flag_title: string;
    description: string;
    icon: string;
  }>;
  llm_explanation: {
    summary: string;
  };
  boundary_geojson: Record<string, unknown>;
  centroid_lat: number;
  centroid_lon: number;
  area_sqm: number;
  shareable_link: string;
}

// ──────────────────────────────────────────────
// Backend Simulation with setTimeout
// ──────────────────────────────────────────────

/**
 * Simulates backend processing for each pipeline step
 * Delays: 1-2 seconds per step
 * Updates step status sequentially: pending → active → done
 */
export async function simulateBackendProcessing(
  dispatch: GeoSafeContextValue["dispatch"],
  steps: PipelineStep[]
) {
  const stepDelays = [1200, 1500, 1000, 1800, 1200, 1600, 1400]; // ms per step

  for (let i = 0; i < steps.length; i++) {
    // Activate current step
    dispatch({
      type: "UPDATE_PIPELINE_STEP",
      payload: { stepIndex: i, status: "active" },
    });

    // Simulate processing
    await new Promise((resolve) => setTimeout(resolve, stepDelays[i]));

    // Complete current step
    dispatch({
      type: "UPDATE_PIPELINE_STEP",
      payload: {
        stepIndex: i,
        status: "done",
        durationMs: stepDelays[i],
      },
    });
  }
}

/**
 * Mock API response generator
 * Simulates backend returning analysis results
 */
export function generateMockAnalysisResponse(lat: number, lng: number): MockAnalysisResponse {
  const riskLevels: Array<"LOW" | "MEDIUM" | "HIGH"> = ["LOW", "MEDIUM", "HIGH"];
  const riskLevel = riskLevels[Math.floor(Math.random() * riskLevels.length)];
  const riskScore =
    riskLevel === "LOW" ? Math.random() * 33 :
    riskLevel === "MEDIUM" ? 33 + Math.random() * 33 :
    66 + Math.random() * 34;

  return {
    report_id: `REPORT-${Date.now()}`,
    risk_classification: {
      risk_level: riskLevel,
      risk_score: Math.round(riskScore * 10) / 10,
      shap_features: [
        { feature: "forest_proximity", importance: Math.random() },
        { feature: "water_body_overlap", importance: Math.random() },
        { feature: "population_density", importance: Math.random() },
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
      {
        category: "legal",
        severity: "NOMINAL",
        flag_title: "Legal Verification Required",
        description: "Requires approval from Revenue Department",
        icon: "gavel",
      },
    ],
    llm_explanation: {
      summary: `The parcel at ${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E shows ${riskLevel.toLowerCase()} risk for development. Key concerns include proximity to forest areas and potential flood vulnerability. A detailed environmental impact assessment is recommended before proceeding with development plans.`,
    },
    boundary_geojson: {
      type: "Polygon",
      coordinates: [
        [
          [lng - 0.001, lat - 0.001],
          [lng + 0.001, lat - 0.001],
          [lng + 0.001, lat + 0.001],
          [lng - 0.001, lat + 0.001],
          [lng - 0.001, lat - 0.001],
        ],
      ],
    },
    centroid_lat: lat,
    centroid_lon: lng,
    area_sqm: 5000 + Math.random() * 15000,
    shareable_link: `https://geosafe.io/reports/${Math.random().toString(36).substr(2, 9)}`,
  };
}

// ──────────────────────────────────────────────
// Flow Management Hook
// ──────────────────────────────────────────────

export function useFlowManagement() {
  const { state, dispatch, startProcessing, setResultData, setError } = useGeoSafe();

  // Screen state management
  const screen = useMemo(() => {
    if (!state.selectedLocation) return "initial"; // Show map
    if (state.isProcessing) return "processing"; // Show pipeline
    if (state.resultData) return "result"; // Show dashboard
    return "initial";
  }, [state.selectedLocation, state.isProcessing, state.resultData]);

  /**
   * Start the analysis pipeline with backend simulation
   */
  const startAnalysis = useCallback(async () => {
    if (!state.selectedLocation) return;

    try {
      // Start processing UI animation
      startProcessing();

      // Simulate backend processing with sequential step updates
      await simulateBackendProcessing(dispatch, state.pipelineSteps);

      // After all steps complete, simulate API response
      await new Promise((resolve) => setTimeout(resolve, 500));

      const mockResponse = generateMockAnalysisResponse(
        state.selectedLocation.lat,
        state.selectedLocation.lng
      );

      // Map response to ResultData format
      const resultData: ResultData = {
        reportId: mockResponse.report_id,
        riskLevel: mockResponse.risk_classification.risk_level,
        riskScore: mockResponse.risk_classification.risk_score,
        flags: mockResponse.flags.map((f: { category: string; severity: string; flag_title: string; description: string; icon: string; }): RiskFlag => ({
          category: f.category,
          severity: f.severity as RiskFlag["severity"],
          title: f.flag_title,
          description: f.description,
          icon: f.icon,
        })),
        llmInsight: mockResponse.llm_explanation.summary,
        recommendedNextSteps: ["Review the detected risks before proceeding with development."],
        layerValidations: [],
        featureImportance: mockResponse.risk_classification.shap_features.map(
          (f: { feature: string; importance: number }) => ({
            label: f.feature,
            value: f.importance * 100,
            color: f.importance > 0.5 ? "#3adffa" : "#c890ff",
          })
        ),
        metrics: [
          {
            label: "Environmental Integrity",
            value: `${(100 - mockResponse.risk_classification.risk_score).toFixed(1)}%`,
          },
          {
            label: "Legal Compliance",
            value: mockResponse.flags.length > 2 ? "At Risk" : "Clear",
          },
        ],
        shareableToken: mockResponse.shareable_link.split("/").pop() || "",
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

  return {
    screen,
    startAnalysis,
    isProcessing: state.isProcessing,
    hasLocation: !!state.selectedLocation,
    hasResult: !!state.resultData,
  };
}

export default function FlowManager() {
  return null; // This is just a hook provider
}
