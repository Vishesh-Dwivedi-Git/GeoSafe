/**
 * GeoSafe API Service Layer
 * Handles all communication with the backend API
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ──────────────────────────────────
// Response Types
// ──────────────────────────────────

export interface AnalysisResponse {
  report_id: string;
  risk_classification: {
    risk_level: "LOW" | "MEDIUM" | "HIGH";
    risk_score: number;
    shap_features: Array<{
      feature: string;
      importance: number;
    }>;
  };
  flags: Array<{
    category: string;
    severity: "CRITICAL" | "WARNING" | "NOMINAL";
    flag_title: string;
    description: string;
    icon: string;
  }>;
  llm_explanation: {
    summary: string;
  };
  layer_validations: Array<{
    layer_name: string;
    layer_label: string;
    intersects: boolean;
    overlap_pct: number;
    spatial_score: number;
  }>;
  recommended_next_steps: string[];
  processing_time_ms: number;
  centroid_lat: number;
  centroid_lon: number;
  area_sqm: number;
  boundary_geojson: Record<string, unknown>;
  shareable_link: string;
}

interface BackendAnalysisResponse {
  risk: "LOW" | "MEDIUM" | "HIGH" | string;
  confidence: number;
  features?: Record<string, number>;
  reasoning?: string[];
  bhuvan_hits?: Record<string, boolean>;
  centroid_lat?: number;
  centroid_lon?: number;
  area_sqm?: number;
}

export interface ApiError {
  status: number;
  message: string;
  detail?: string;
}

export interface ApiState<T> {
  loading: boolean;
  data: T | null;
  error: ApiError | null;
}

function normalizeSeverity(severity?: string): "CRITICAL" | "WARNING" | "NOMINAL" {
  const value = (severity || "").toLowerCase();
  if (value === "critical" || value === "high") return "CRITICAL";
  if (value === "medium" || value === "warning") return "WARNING";
  return "NOMINAL";
}

function featureLabelToId(label: string): string {
  return label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function createReportId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `report-${Date.now()}`;
}

function scoreFeatureImportance(features: Record<string, number>) {
  const entries = Object.entries(features);
  const maxValue = Math.max(...entries.map(([, value]) => Math.abs(Number(value) || 0)), 1);

  return entries
    .filter(([, value]) => Number(value) > 0)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .map(([feature, value]) => ({
      feature: featureLabelToId(feature),
      importance: Math.min(Math.abs(Number(value) || 0) / maxValue, 1),
    }));
}

function buildLayerValidations(
  features: Record<string, number>,
  hits: Record<string, boolean>
): AnalysisResponse["layer_validations"] {
  const waterDistance = Number(features.distance_to_water ?? 999999);
  const waterHit = Number(features.water_present ?? 0) > 0 || waterDistance < 250;

  return [
    {
      layer_name: "water",
      layer_label: "Water Bodies",
      intersects: waterHit,
      overlap_pct: Number(features.water_present ?? 0) > 0 ? 100 : 0,
      spatial_score: waterDistance >= 999999 ? 0 : Math.max(0, Math.min(1, 1 - waterDistance / 500)),
    },
    {
      layer_name: "forest",
      layer_label: "Forest Layer",
      intersects: Boolean(hits.forest),
      overlap_pct: Boolean(hits.forest) ? 100 : 0,
      spatial_score: Number(features.forest_present ?? 0),
    },
    {
      layer_name: "esz",
      layer_label: "Eco-Sensitive Zone",
      intersects: Boolean(hits.esz),
      overlap_pct: Boolean(hits.esz) ? 100 : 0,
      spatial_score: Number(features.esz_present ?? 0),
    },
    {
      layer_name: "flood",
      layer_label: "Flood Risk",
      intersects: Boolean(hits.flood) || Number(features.flood_risk ?? 0) > 0,
      overlap_pct: Math.round(Number(features.flood_risk ?? 0) * 100),
      spatial_score: Number(features.flood_risk ?? 0),
    },
    {
      layer_name: "government_land",
      layer_label: "Government Land",
      intersects: Number(features.govt_land_present ?? 0) > 0,
      overlap_pct: Number(features.govt_land_present ?? 0) > 0 ? 100 : 0,
      spatial_score: Number(features.govt_land_present ?? 0),
    },
  ];
}

function buildFlags(
  risk: "LOW" | "MEDIUM" | "HIGH",
  features: Record<string, number>,
  hits: Record<string, boolean>,
  reasoning: string[]
): AnalysisResponse["flags"] {
  const flags: AnalysisResponse["flags"] = [];

  if (hits.esz || Number(features.esz_present ?? 0) > 0) {
    flags.push({
      category: "Environmental",
      severity: "CRITICAL",
      flag_title: "Eco-Sensitive Zone Hit",
      description: "The queried location intersects an ESZ layer from Bhuvan.",
      icon: "eco",
    });
  }

  if (hits.forest || Number(features.forest_present ?? 0) > 0) {
    flags.push({
      category: "Environmental",
      severity: "CRITICAL",
      flag_title: "Protected Forest Indicator",
      description: "The queried location matches a forest-protection thematic layer.",
      icon: "forest",
    });
  }

  if (Number(features.water_present ?? 0) > 0 || Number(features.distance_to_water ?? 999999) < 250) {
    flags.push({
      category: "Environmental",
      severity: risk === "HIGH" ? "CRITICAL" : "WARNING",
      flag_title: "Nearby Water Body",
      description: `Water-related features are present within ${Math.round(
        Number(features.distance_to_water ?? 0)
      )} m of the selected location.`,
      icon: "water_drop",
    });
  }

  if (Number(features.flood_risk ?? 0) > 0 || hits.flood) {
    flags.push({
      category: "Environmental",
      severity: "WARNING",
      flag_title: "Flood Exposure Signal",
      description: "Flood-related thematic signals were detected for this coordinate.",
      icon: "flood",
    });
  }

  if (Number(features.govt_land_present ?? 0) > 0) {
    flags.push({
      category: "Legal",
      severity: "WARNING",
      flag_title: "Government Land Indicator",
      description: "Government land presence is suggested by the available thematic layers.",
      icon: "gavel",
    });
  }

  if (flags.length === 0 && reasoning[0]) {
    flags.push({
      category: "General",
      severity: normalizeSeverity(risk),
      flag_title: "AI Land Risk Summary",
      description: reasoning[0],
      icon: "analytics",
    });
  }

  return flags;
}

function buildRecommendedSteps(
  risk: "LOW" | "MEDIUM" | "HIGH",
  features: Record<string, number>
): string[] {
  const steps: string[] = [];

  if (Number(features.esz_present ?? 0) > 0 || Number(features.forest_present ?? 0) > 0) {
    steps.push("Verify the parcel with the concerned forest or environmental authority before development.");
  }
  if (Number(features.water_present ?? 0) > 0 || Number(features.distance_to_water ?? 999999) < 250) {
    steps.push("Review drainage, setback, and lake-buffer constraints for the selected site.");
  }
  if (Number(features.govt_land_present ?? 0) > 0) {
    steps.push("Cross-check title and acquisition status against official land records.");
  }
  if (steps.length === 0) {
    steps.push(
      risk === "LOW"
        ? "Proceed with a detailed legal verification before finalizing the parcel."
        : "Run a deeper field and document verification before proceeding."
    );
  }

  return steps.slice(0, 3);
}

function mapBackendToAnalysisResponse(data: BackendAnalysisResponse): AnalysisResponse {
  const risk =
    data.risk === "LOW" || data.risk === "MEDIUM" || data.risk === "HIGH" ? data.risk : "MEDIUM";
  const features = data.features || {};
  const hits = data.bhuvan_hits || {};
  const reasoning = data.reasoning || [];
  const shapFeatures = scoreFeatureImportance(features);
  const flags = buildFlags(risk, features, hits, reasoning);
  const layerValidations = buildLayerValidations(features, hits);
  const recommendedNextSteps = buildRecommendedSteps(risk, features);

  return {
    report_id: createReportId(),
    risk_classification: {
      risk_level: risk,
      risk_score: Math.max(0, Math.min(100, Math.round((Number(data.confidence || 0) * 100)))),
      shap_features: shapFeatures,
    },
    flags,
    llm_explanation: {
      summary: reasoning.join(" ") || "Analysis completed with the currently available Bhuvan and water-layer signals.",
    },
    layer_validations: layerValidations,
    recommended_next_steps: recommendedNextSteps,
    processing_time_ms: 0,
    centroid_lat: Number(data.centroid_lat || 0),
    centroid_lon: Number(data.centroid_lon || 0),
    area_sqm: Number(data.area_sqm || 0),
    boundary_geojson: {},
    shareable_link: "",
  };
}

// ──────────────────────────────────
// API Functions
// ──────────────────────────────────

/**
 * Analyze a location using latitude and longitude
 * Sends coordinates to the backend for full pipeline processing
 * 
 * @param lat - Latitude coordinate
 * @param lng - Longitude coordinate
 * @param radiusM - Search radius in meters (default: 500)
 * @returns Promise<AnalysisResponse>
 * @throws ApiError
 */
export async function analyzeLocation(
  lat: number,
  lng: number,
  radiusM: number = 500
): Promise<AnalysisResponse> {
  try {
    const requestBody = {
      input_type: "coordinates",
      coordinates_input: {
        latitude: lat,
        longitude: lng,
        buffer_m: radiusM,
      },
    };

    const response = await fetch(`${API_BASE}/analyze-land`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const error: ApiError = {
        status: response.status,
        message: `API Error: ${response.status}`,
        detail: errorData.detail || "Unknown error occurred",
      };
      throw error;
    }

    const data = await response.json();
    return mapBackendToAnalysisResponse(data as BackendAnalysisResponse);
  } catch (err) {
    if (err instanceof Error) {
      if ("status" in err) {
        throw err as ApiError;
      }
      throw {
        status: 0,
        message: "Network Error",
        detail: err.message,
      } as ApiError;
    }
    throw {
      status: 0,
      message: "Unknown Error",
      detail: "An unexpected error occurred",
    } as ApiError;
  }
}

export async function validateLand(input: {
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
}): Promise<AnalysisResponse> {
  try {
    const response = await fetch(`${API_BASE}/analyze-land`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw {
        status: response.status,
        message: `API Error: ${response.status}`,
        detail: errorData.detail || "Unknown error occurred",
      } as ApiError;
    }

    const data = await response.json();
    return mapBackendToAnalysisResponse(data as BackendAnalysisResponse);
  } catch (err) {
    if (err instanceof Error) {
      throw {
        status: 0,
        message: "Network Error",
        detail: err.message,
      } as ApiError;
    }
    throw err as ApiError;
  }
}

/**
 * Geocode a location (faster preview without full analysis)
 * Useful for map previews before committing to full validation
 * 
 * @param lat - Latitude coordinate
 * @param lng - Longitude coordinate
 * @param radiusM - Search radius in meters (default: 500)
 * @returns Promise with geocoding results
 * @throws ApiError
 */
export async function geocodeLocation(
  lat: number,
  lng: number,
  radiusM: number = 500
) {
  try {
    const requestBody = {
      input_type: "coordinates",
      coordinates_input: {
        latitude: lat,
        longitude: lng,
        buffer_m: radiusM,
      },
    };

    const response = await fetch(`${API_BASE}/geocode`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw {
        status: response.status,
        message: `Geocoding failed: ${response.status}`,
        detail: errorData.detail || "Could not geocode location",
      } as ApiError;
    }

    return await response.json();
  } catch (err) {
    if (err instanceof Error) {
      if ("status" in err) {
        throw err as ApiError;
      }
      throw {
        status: 0,
        message: "Network Error",
        detail: err.message,
      } as ApiError;
    }
    throw {
      status: 0,
      message: "Unknown Error",
      detail: "An unexpected error occurred",
    } as ApiError;
  }
}

/**
 * Health check - verify backend is running
 * @returns Promise<boolean> - true if backend is healthy
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`, {
      method: "GET",
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Get a report by shareable token
 * @param token - Report token from previous analysis
 * @returns Promise<AnalysisResponse>
 * @throws ApiError
 */
export async function getReport(token: string): Promise<AnalysisResponse> {
  try {
    const response = await fetch(`${API_BASE}/reports/${token}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw {
        status: response.status,
        message: "Report not found",
        detail: "The requested report could not be retrieved",
      } as ApiError;
    }

    const data = await response.json();
    return mapBackendToAnalysisResponse(data as BackendAnalysisResponse);
  } catch (err) {
    if (err instanceof Error) {
      if ("status" in err) {
        throw err as ApiError;
      }
      throw {
        status: 0,
        message: "Network Error",
        detail: err.message,
      } as ApiError;
    }
    throw {
      status: 0,
      message: "Unknown Error",
      detail: "An unexpected error occurred",
    } as ApiError;
  }
}
