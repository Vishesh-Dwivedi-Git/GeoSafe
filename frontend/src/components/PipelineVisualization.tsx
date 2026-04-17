"use client";

import React, { useMemo } from "react";
import { useGeoSafe } from "@/context/GeoSafeContext";

// ──────────────────────────────────────────────
// Pipeline Step Node Component
// ──────────────────────────────────────────────

interface StepNodeProps {
  label: string;
  icon: string;
  status: "pending" | "active" | "done" | "error";
  index: number;
  description?: string;
  durationMs?: number;
}

function StepNode({ label, icon, status, index, description, durationMs }: StepNodeProps) {
  const getStatusColors = () => {
    switch (status) {
      case "pending":
        return {
          bgFrom: "from-slate-700",
          bgTo: "to-slate-800",
          border: "border-slate-600",
          text: "text-slate-400",
          glow: "",
        };
      case "active":
        return {
          bgFrom: "from-primary",
          bgTo: "to-primary-container",
          border: "border-primary",
          text: "text-white",
          glow: "shadow-[0_0_30px_rgba(58,223,250,0.6),inset_0_0_20px_rgba(58,223,250,0.2)]",
        };
      case "done":
        return {
          bgFrom: "from-emerald-600",
          bgTo: "to-emerald-700",
          border: "border-emerald-500",
          text: "text-white",
          glow: "shadow-[0_0_20px_rgba(16,185,129,0.4)]",
        };
      case "error":
        return {
          bgFrom: "from-red-600",
          bgTo: "to-red-700",
          border: "border-red-500",
          text: "text-white",
          glow: "shadow-[0_0_20px_rgba(239,68,68,0.4)]",
        };
    }
  };

  const colors = getStatusColors();

  return (
    <div className="relative flex flex-col items-center">
      {/* Step Number Badge */}
      <div
        className={`
          absolute -top-3 -right-3 w-6 h-6 rounded-full
          bg-linear-to-br ${colors.bgFrom} ${colors.bgTo}
          border ${colors.border}
          flex items-center justify-center
          text-xs font-bold text-white
          z-20 transition-all duration-300
        `}
      >
        {index + 1}
      </div>

      {/* Main Node Circle */}
      <div
        className={`
          relative w-24 h-24 rounded-full
          bg-linear-to-br ${colors.bgFrom} ${colors.bgTo}
          border-2 ${colors.border}
          flex flex-col items-center justify-center gap-1
          transition-all duration-500 cursor-pointer
          hover:scale-110
          ${colors.glow}
          ${status === "active" ? "animate-pulse" : ""}
        `}
      >
        {/* Icon */}
        <span className={`material-symbols-outlined text-3xl ${colors.text}`}>
          {icon}
        </span>

        {/* Animated rings for active state */}
        {status === "active" && (
          <>
            <div className="absolute inset-0 rounded-full border-2 border-primary animate-ping opacity-75" />
            <div className="absolute inset-1 rounded-full border border-primary opacity-50" />
          </>
        )}

        {/* Completed checkmark overlay */}
        {status === "done" && (
          <div className="absolute inset-0 rounded-full bg-emerald-500/20 flex items-center justify-center">
            <span className="material-symbols-outlined text-white text-xl">check_circle</span>
          </div>
        )}

        {/* Error X overlay */}
        {status === "error" && (
          <div className="absolute inset-0 rounded-full bg-red-500/20 flex items-center justify-center">
            <span className="material-symbols-outlined text-white text-xl">cancel</span>
          </div>
        )}
      </div>

      {/* Label */}
      <p className={`mt-4 text-center font-label text-sm font-bold ${colors.text} transition-colors duration-300`}>
        {label}
      </p>

      {/* Description */}
      {description && (
        <p className="mt-1 text-center font-label text-xs text-slate-500 max-w-30">
          {description}
        </p>
      )}

      {/* Duration Badge */}
      {durationMs && status === "done" && (
        <div className="mt-2 px-2 py-1 bg-emerald-900/40 border border-emerald-500/30 rounded-full">
          <p className="font-label text-xs text-emerald-300">{durationMs}ms</p>
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────
// Connector Line Component
// ──────────────────────────────────────────────

interface ConnectorProps {
  isCompleted: boolean;
  isActive: boolean;
  isError: boolean;
  vertical?: boolean;
}

function Connector({ isCompleted, isActive, isError, vertical = false }: ConnectorProps) {
  const getColor = () => {
    if (isError) return "from-red-500";
    if (isCompleted) return "from-emerald-500";
    if (isActive) return "from-primary via-primary-container";
    return "from-slate-600";
  };

  const lineClass = vertical ? "w-1 h-20" : "h-1 w-24";

  return (
    <div
      className={`
        ${lineClass}
        bg-gradient-to-${vertical ? "b" : "r"} ${getColor()} to-transparent
        transition-all duration-500
        ${isActive ? "animate-pulse" : ""}
        rounded-full
      `}
    />
  );
}

// ──────────────────────────────────────────────
// Main Pipeline Visualization Component
// ──────────────────────────────────────────────

export default function PipelineVisualization() {
  const { state } = useGeoSafe();
  const { pipelineSteps, currentStepIndex, isProcessing, error } = state;

  // Memoize status calculations
  const stepsWithStatus = useMemo(() => {
    return pipelineSteps.map((step, index) => {
      let status = step.status;

      // Override status based on processing state
      if (isProcessing && index < currentStepIndex) {
        status = "done";
      } else if (isProcessing && index === currentStepIndex) {
        status = "active";
      } else if (!isProcessing && error) {
        status = "error";
      } else if (!isProcessing && currentStepIndex >= pipelineSteps.length) {
        status = "done";
      }

      return {
        ...step,
        status,
      };
    });
  }, [pipelineSteps, currentStepIndex, isProcessing, error]);

  // Calculate step descriptions based on content
  const stepDescriptions: Record<string, string> = {
    geocoding: "Survey → Boundary polygon",
    layer_fetch: "KGIS Water, Forest, ESZ",
    spatial_engine: "PostGIS Validation",
    risk_classifier: "ML Risk Score",
    flag_mapping: "Legal Flags",
    llm_layer: "LLM Summary",
    safety_report: "Report Generated",
  };

  return (
    <div className="w-full h-full flex flex-col items-center justify-center p-12">
      {/* Header */}
      <div className="mb-12 text-center">
        <h2 className="font-headline text-3xl font-bold text-white mb-2">
          {isProcessing ? "analyzing_location" : "Pipeline Status"}
        </h2>
        <p className="font-label text-sm text-slate-400 uppercase tracking-widest">
          {isProcessing ? "Step " + (currentStepIndex + 1) + " of " + pipelineSteps.length : "Ready to analyze"}
        </p>
      </div>

      {/* Pipeline Visualization - Vertical Flow */}
      <div className="flex flex-col items-center gap-8">
        {stepsWithStatus.map((step, index) => (
          <React.Fragment key={step.id}>
            {/* Step Node */}
            <StepNode
              label={step.label}
              icon={step.icon}
              status={step.status}
              index={index}
              description={stepDescriptions[step.id] || step.description}
              durationMs={step.durationMs}
            />

            {/* Connector to Next Step */}
            {index < stepsWithStatus.length - 1 && (
              <Connector
                isCompleted={step.status === "done"}
                isActive={step.status === "active"}
                isError={step.status === "error"}
                vertical
              />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Status Bar at Bottom */}
      <div className="mt-16 w-full max-w-2xl">
        {/* Progress Bar */}
        <div className="relative h-2 bg-slate-700/50 rounded-full overflow-hidden border border-slate-600/50">
          <div
            className={`
              h-full rounded-full
              ${error ? "bg-red-500" : "bg-linear-to-r from-primary to-primary-container"}
              transition-all duration-500
            `}
            style={{
              width: `${((currentStepIndex + 1) / pipelineSteps.length) * 100}%`,
            }}
          />
        </div>

        {/* Info Row */}
        <div className="flex items-center justify-between mt-4 font-label text-xs uppercase tracking-widest">
          <span className="text-slate-400">
            {isProcessing
              ? `Processing: ${currentStepIndex + 1} of ${pipelineSteps.length}`
              : error
                ? "Analysis Failed"
                : "Ready"}
          </span>
          <span className="text-primary">
            {isProcessing ? `${Math.round(((currentStepIndex + 1) / pipelineSteps.length) * 100)}%` : "0%"}
          </span>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mt-8 p-4 bg-red-900/30 border border-red-500/50 rounded-lg max-w-lg">
          <p className="font-label text-sm text-red-300">
            <span className="font-bold">Error: </span>
            {error}
          </p>
        </div>
      )}

      {/* Completion Message */}
      {!isProcessing && currentStepIndex >= pipelineSteps.length - 1 && !error && state.resultData && (
        <div className="mt-8 p-6 bg-emerald-900/30 border border-emerald-500/50 rounded-lg max-w-lg text-center">
          <p className="font-headline text-lg font-bold text-emerald-300 mb-2">
            ✓ Analysis Complete
          </p>
          <p className="font-label text-sm text-emerald-200">
            Your safety report is ready. Risk Level: <span className="font-bold">{state.resultData.riskLevel}</span>
          </p>
        </div>
      )}
    </div>
  );
}
