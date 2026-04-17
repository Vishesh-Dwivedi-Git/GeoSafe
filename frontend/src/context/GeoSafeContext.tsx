"use client";

import React, {
  createContext,
  useContext,
  useReducer,
  useCallback,
  useMemo,
  type ReactNode,
  type Dispatch,
} from "react";
import { validateLand } from "@/services/api";

// ────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────

export type PipelineStepStatus = "pending" | "active" | "done" | "error";

export interface PipelineStep {
  id: string;
  label: string;
  icon: string;
  status: PipelineStepStatus;
  description?: string;
  durationMs?: number;
}

export interface SelectedLocation {
  lat: number;
  lng: number;
}

export interface SurveyInputState {
  district: string;
  taluk: string;
  village: string;
  hobli?: string;
  villageCode?: string;
  surveyNumber: string;
  latitude?: string;
  longitude?: string;
}

export interface RiskFlag {
  category: string;
  severity: "CRITICAL" | "WARNING" | "NOMINAL";
  title: string;
  description: string;
  icon: string;
}

export interface LayerValidation {
  layerName: string;
  layerLabel: string;
  intersects: boolean;
  overlapPct: number;
  spatialScore: number;
}

export interface ResultData {
  reportId: string;
  riskLevel: string;
  riskScore: number;
  flags: RiskFlag[];
  llmInsight: string;
  recommendedNextSteps: string[];
  layerValidations: LayerValidation[];
  featureImportance: { label: string; value: number; color: string }[];
  metrics: { label: string; value: string; trend?: string; trendIcon?: string }[];
  shareableToken: string;
  boundaryGeoJSON?: Record<string, unknown>;
  centroidLat?: number;
  centroidLon?: number;
  areaSqm?: number;
}

export interface GeoSafeState {
  selectedLocation: SelectedLocation | null;
  surveyNumber: string;
  surveyInput: SurveyInputState;
  isProcessing: boolean;
  pipelineSteps: PipelineStep[];
  currentStepIndex: number;
  resultData: ResultData | null;
  error: string | null;
}

function normalizeRiskSeverity(severity: string | undefined): RiskFlag["severity"] {
  const value = (severity || "").toUpperCase();
  if (value === "CRITICAL" || value === "HIGH") return "CRITICAL";
  if (value === "WARNING" || value === "MEDIUM") return "WARNING";
  return "NOMINAL";
}

// ────────────────────────────────────────────────
// Default pipeline steps (mirrors the backend 7-stage flow)
// ────────────────────────────────────────────────

export const DEFAULT_PIPELINE_STEPS: PipelineStep[] = [
  { id: "geocoding", label: "Geocoding", icon: "location_on", status: "pending" },
  { id: "layer_fetch", label: "Layer Fetch", icon: "layers", status: "pending" },
  { id: "spatial_engine", label: "Spatial Engine", icon: "architecture", status: "pending" },
  { id: "risk_classifier", label: "Risk Classifier", icon: "security", status: "pending" },
  { id: "flag_mapping", label: "Flag Mapping", icon: "flag", status: "pending" },
  { id: "llm_layer", label: "LLM Layer", icon: "psychology", status: "pending" },
  { id: "safety_report", label: "Safety Report", icon: "description", status: "pending" },
];

// ────────────────────────────────────────────────
// Initial state
// ────────────────────────────────────────────────

const initialState: GeoSafeState = {
  selectedLocation: null,
  surveyNumber: "",
  surveyInput: {
    district: "Bengaluru (Urban)",
    taluk: "Bangalore-South",
    village: "Begur",
    hobli: "",
    villageCode: "",
    surveyNumber: "",
    latitude: "",
    longitude: "",
  },
  isProcessing: false,
  pipelineSteps: DEFAULT_PIPELINE_STEPS.map((s) => ({ ...s })),
  currentStepIndex: -1,
  resultData: null,
  error: null,
};

// ────────────────────────────────────────────────
// Action types
// ────────────────────────────────────────────────

type GeoSafeAction =
  | { type: "SET_LOCATION"; payload: SelectedLocation }
  | { type: "SET_SURVEY_NUMBER"; payload: string }
  | { type: "SET_SURVEY_FIELDS"; payload: Partial<SurveyInputState> }
  | { type: "START_PROCESSING" }
  | { type: "UPDATE_PIPELINE_STEP"; payload: { stepIndex: number; status: PipelineStepStatus; durationMs?: number } }
  | { type: "SET_RESULT_DATA"; payload: ResultData }
  | { type: "SET_ERROR"; payload: string }
  | { type: "RESET_FLOW" };

// ────────────────────────────────────────────────
// Reducer
// ────────────────────────────────────────────────

function geoSafeReducer(state: GeoSafeState, action: GeoSafeAction): GeoSafeState {
  switch (action.type) {
    case "SET_LOCATION":
      return { ...state, selectedLocation: action.payload, error: null };

    case "SET_SURVEY_NUMBER":
      return {
        ...state,
        surveyNumber: action.payload,
        surveyInput: {
          ...state.surveyInput,
          surveyNumber: action.payload,
        },
        error: null,
      };

    case "SET_SURVEY_FIELDS":
      return {
        ...state,
        surveyInput: {
          ...state.surveyInput,
          ...action.payload,
        },
        surveyNumber:
          action.payload.surveyNumber !== undefined
            ? action.payload.surveyNumber
            : state.surveyNumber,
        error: null,
      };

    case "START_PROCESSING":
      return {
        ...state,
        isProcessing: true,
        currentStepIndex: 0,
        resultData: null,
        error: null,
        pipelineSteps: state.pipelineSteps.map((step, i) => ({
          ...step,
          status: i === 0 ? "active" : "pending",
          durationMs: undefined,
        })),
      };

    case "UPDATE_PIPELINE_STEP": {
      const { stepIndex, status, durationMs } = action.payload;
      const updatedSteps = state.pipelineSteps.map((step, i) => {
        if (i === stepIndex) return { ...step, status, durationMs };
        // Activate the next step when this one completes
        if (i === stepIndex + 1 && status === "done") return { ...step, status: "active" as PipelineStepStatus };
        return step;
      });
      const newCurrentIndex = status === "done" ? stepIndex + 1 : stepIndex;
      const isStillProcessing = newCurrentIndex < state.pipelineSteps.length;
      return {
        ...state,
        pipelineSteps: updatedSteps,
        currentStepIndex: newCurrentIndex,
        isProcessing: isStillProcessing,
      };
    }

    case "SET_RESULT_DATA":
      return {
        ...state,
        resultData: action.payload,
        isProcessing: false,
        pipelineSteps: state.pipelineSteps.map((step) => ({ ...step, status: "done" as PipelineStepStatus })),
        currentStepIndex: state.pipelineSteps.length,
      };

    case "SET_ERROR":
      return {
        ...state,
        isProcessing: false,
        error: action.payload,
        pipelineSteps: state.pipelineSteps.map((step, i) =>
          i === state.currentStepIndex
            ? { ...step, status: "error" as PipelineStepStatus }
            : step
        ),
      };

    case "RESET_FLOW":
      return { ...initialState, pipelineSteps: DEFAULT_PIPELINE_STEPS.map((s) => ({ ...s })) };

    default:
      return state;
  }
}

// ────────────────────────────────────────────────
// Context shape (state + action dispatchers)
// ────────────────────────────────────────────────

export interface GeoSafeContextValue {
  state: GeoSafeState;
  dispatch: Dispatch<GeoSafeAction>;
  // Convenience actions
  setLocation: (lat: number, lng: number) => void;
  setSurveyNumber: (value: string) => void;
  setSurveyFields: (fields: Partial<SurveyInputState>) => void;
  startProcessing: () => void;
  updatePipelineStep: (stepIndex: number, status: PipelineStepStatus, durationMs?: number) => void;
  setResultData: (data: ResultData) => void;
  setError: (message: string) => void;
  resetFlow: () => void;
  // Orchestrated action: run full pipeline against backend
  runPipeline: (mode?: "auto" | "coordinates" | "survey") => Promise<void>;
}

const GeoSafeContext = createContext<GeoSafeContextValue | undefined>(undefined);

// ────────────────────────────────────────────────
// API base URL
// ────────────────────────────────────────────────

// ────────────────────────────────────────────────
// Provider
// ────────────────────────────────────────────────

export function GeoSafeProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(geoSafeReducer, initialState);

  // ── Convenience dispatchers ────────────────
  const setLocation = useCallback(
    (lat: number, lng: number) => dispatch({ type: "SET_LOCATION", payload: { lat, lng } }),
    []
  );

  const setSurveyNumber = useCallback(
    (value: string) => dispatch({ type: "SET_SURVEY_NUMBER", payload: value }),
    []
  );
  const setSurveyFields = useCallback(
    (fields: Partial<SurveyInputState>) => dispatch({ type: "SET_SURVEY_FIELDS", payload: fields }),
    []
  );

  const startProcessing = useCallback(() => dispatch({ type: "START_PROCESSING" }), []);

  const updatePipelineStep = useCallback(
    (stepIndex: number, status: PipelineStepStatus, durationMs?: number) =>
      dispatch({ type: "UPDATE_PIPELINE_STEP", payload: { stepIndex, status, durationMs } }),
    []
  );

  const setResultData = useCallback(
    (data: ResultData) => dispatch({ type: "SET_RESULT_DATA", payload: data }),
    []
  );

  const setError = useCallback(
    (message: string) => dispatch({ type: "SET_ERROR", payload: message }),
    []
  );

  const resetFlow = useCallback(() => dispatch({ type: "RESET_FLOW" }), []);

  // ── Orchestrated pipeline runner ───────────
  const runPipeline = useCallback(async (mode: "auto" | "coordinates" | "survey" = "auto") => {
    // Build request body
    const hasCoordinates = Boolean(state.selectedLocation?.lat && state.selectedLocation?.lng);
    const hasSurvey = state.surveyInput.surveyNumber.trim().length > 0;
    const useSurvey = mode === "survey" || (mode === "auto" && hasSurvey);
    const useCoordinates = mode === "coordinates" || (mode === "auto" && !useSurvey && hasCoordinates);

    if (!useCoordinates && !useSurvey) {
      dispatch({ type: "SET_ERROR", payload: "Please enter coordinates or a survey number." });
      return;
    }

    if (useSurvey && !state.selectedLocation) {
      // Keep flow pages stable even before geocoding returns parcel centroid.
      dispatch({ type: "SET_LOCATION", payload: { lat: 12.9716, lng: 77.5946 } });
    }

    dispatch({ type: "START_PROCESSING" });

    // Simulate step-by-step progression with realistic timings
    const stepDelays = [800, 1200, 1500, 1000, 800, 2000, 600]; // ms per step

    try {
      // Kick off the real API call in parallel with UI step animation
      const requestBody = useSurvey
        ? {
            input_type: "survey_number",
            survey_input: {
              survey_number: state.surveyInput.surveyNumber.trim(),
              district: state.surveyInput.district.trim(),
              taluk: state.surveyInput.taluk.trim(),
              village: state.surveyInput.village.trim(),
              hobli: state.surveyInput.hobli?.trim() || undefined,
              village_code: state.surveyInput.villageCode?.trim() || undefined,
              latitude:
                state.surveyInput.latitude && !Number.isNaN(Number(state.surveyInput.latitude))
                  ? Number(state.surveyInput.latitude)
                  : undefined,
              longitude:
                state.surveyInput.longitude && !Number.isNaN(Number(state.surveyInput.longitude))
                  ? Number(state.surveyInput.longitude)
                  : undefined,
            },
          }
        : {
            input_type: "coordinates",
            coordinates_input: {
              latitude: state.selectedLocation!.lat,
              longitude: state.selectedLocation!.lng,
              buffer_m: 500,
            },
          };

      // Animate steps while the API is processing
      const apiPromise = validateLand(
        requestBody as {
          input_type: "coordinates" | "survey_number";
          coordinates_input?: { latitude: number; longitude: number; buffer_m?: number };
          survey_input?: {
            district: string;
            taluk: string;
            village: string;
            survey_number: string;
            hobli?: string;
            village_code?: string;
            latitude?: number;
            longitude?: number;
          };
        }
      );

      // Animate pipeline steps with staggered delays
      for (let i = 0; i < stepDelays.length; i++) {
        dispatch({
          type: "UPDATE_PIPELINE_STEP",
          payload: { stepIndex: i, status: "active" },
        });
        await new Promise((r) => setTimeout(r, stepDelays[i]));
        dispatch({
          type: "UPDATE_PIPELINE_STEP",
          payload: { stepIndex: i, status: "done", durationMs: stepDelays[i] },
        });
      }

      // Wait for the actual API response
      const data = await apiPromise;

      // Map backend response into our ResultData shape
      const result: ResultData = {
        reportId: data.report_id || "REPORT-" + Date.now(),
        riskLevel: data.risk_classification?.risk_level || "UNKNOWN",
        riskScore: data.risk_classification?.risk_score ?? 0,
        flags: (data.flags || []).map((f: Record<string, unknown>) => ({
          category: (f.category as string) || "General",
          severity: normalizeRiskSeverity(f.severity as string | undefined),
          title: (f.flag_title as string) || (f.title as string) || "Unknown Flag",
          description: (f.description as string) || "",
          icon: (f.icon as string) || "warning",
        })),
        llmInsight:
          typeof data.llm_explanation === "string"
            ? data.llm_explanation
            : data.llm_explanation?.summary || "",
        recommendedNextSteps: data.recommended_next_steps || [],
        layerValidations: (data.layer_validations || []).map((layer) => ({
          layerName: layer.layer_name,
          layerLabel: layer.layer_label,
          intersects: layer.intersects,
          overlapPct: layer.overlap_pct,
          spatialScore: layer.spatial_score,
        })),
        featureImportance: (data.risk_classification?.shap_features || []).map(
          (f: Record<string, unknown>) => ({
            label: (f.feature as string) || "",
            value: ((f.importance as number) ?? 0) * 100,
            color: ((f.importance as number) ?? 0) > 0.5 ? "#3adffa" : "#c890ff",
          })
        ),
        metrics: [
          { label: "Parcel Area", value: `${(data.area_sqm || 0).toFixed(0)} m²`, trendIcon: "square_foot" },
          {
            label: "Layers Checked",
            value: `${(data.layer_validations || []).length}`,
            trendIcon: "layers",
          },
          {
            label: "KGIS Compliance",
            value: `${data.risk_classification?.risk_score ?? 0}/100`,
            trend: data.risk_classification?.risk_level === "LOW" ? "PASSED" : "FAILED",
            trendIcon: data.risk_classification?.risk_level === "LOW" ? "check_circle" : "report",
          },
          {
            label: "Processing Time",
            value: `${((data.processing_time_ms || 0) / 1000).toFixed(2)}s`,
            trendIcon: "schedule",
          },
        ],
        shareableToken: data.shareable_link?.split("/").pop() || "",
        boundaryGeoJSON: data.boundary_geojson,
        centroidLat: data.centroid_lat,
        centroidLon: data.centroid_lon,
        areaSqm: data.area_sqm,
      };

      dispatch({ type: "SET_RESULT_DATA", payload: result });
    } catch (err) {
      const apiLikeError = err as { message?: string; detail?: string } | undefined;
      const message =
        apiLikeError?.detail ||
        apiLikeError?.message ||
        (err instanceof Error ? err.message : "Pipeline execution failed");
      dispatch({ type: "SET_ERROR", payload: message });
    }
  }, [state.selectedLocation, state.surveyInput]);

  // ── Memoize context ────────────────────────
  const value = useMemo<GeoSafeContextValue>(
    () => ({
      state,
      dispatch,
      setLocation,
      setSurveyNumber,
      setSurveyFields,
      startProcessing,
      updatePipelineStep,
      setResultData,
      setError,
      resetFlow,
      runPipeline,
    }),
    [state, setLocation, setSurveyNumber, setSurveyFields, startProcessing, updatePipelineStep, setResultData, setError, resetFlow, runPipeline]
  );

  return <GeoSafeContext.Provider value={value}>{children}</GeoSafeContext.Provider>;
}

// ────────────────────────────────────────────────
// Hook
// ────────────────────────────────────────────────

export function useGeoSafe(): GeoSafeContextValue {
  const context = useContext(GeoSafeContext);
  if (!context) {
    throw new Error("useGeoSafe must be used within a <GeoSafeProvider>");
  }
  return context;
}
