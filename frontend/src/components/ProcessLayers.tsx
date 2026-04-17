"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  BaseEdge,
  Background,
  Controls,
  Handle,
  Position,
  getSmoothStepPath,
  useEdgesState,
  useNodesState,
  type Edge,
  type EdgeProps,
  type EdgeTypes,
  type Node,
  type NodeProps,
  type ReactFlowInstance,
} from "@xyflow/react";
import { useGeoSafe, type PipelineStep, type PipelineStepStatus } from "@/context/GeoSafeContext";

interface ProcessLayersProps {
  resultData?: {
    riskScore?: number;
    riskLevel?: string;
    flags?: unknown[];
  } | null;
  onViewReport?: () => void;
}

type PipelineNodeData = {
  index: number;
  label: string;
  icon: string;
  status: PipelineStepStatus;
  durationMs?: number;
};

type PipelineEdgeData = {
  state: PipelineStepStatus;
  isTurn: boolean;
};

const CANVAS_WIDTH = 1160;
const CANVAS_HEIGHT = 520;
const NODE_WIDTH = 148;
const NODE_HEIGHT = 154;
const NODE_PADDING = 18;

const VIEW_EXTENT: [[number, number], [number, number]] = [
  [0, 0],
  [CANVAS_WIDTH, CANVAS_HEIGHT],
];

function PipelineNode({ data }: NodeProps<Node<PipelineNodeData>>) {
  const statusStyles: Record<PipelineStepStatus, string> = {
    pending: "border-slate-700 bg-slate-950/90 text-slate-400",
    active: "border-primary/80 bg-cyan-950/30 text-white pipeline-node-active",
    done: "border-emerald-500/70 bg-emerald-950/20 text-white pipeline-node-done",
    error: "border-red-500/80 bg-red-950/20 text-red-200",
  };

  return (
    <div className={`pipeline-node-card pipeline-node-appear ${statusStyles[data.status]}`}>
      <Handle type="target" position={Position.Left} className="pipeline-handle" />
      <Handle type="source" position={Position.Right} className="pipeline-handle" />

      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-mono text-slate-400 tracking-wide">STEP {data.index + 1}</span>
        <span
          className={`text-[10px] px-2 py-1 rounded-full font-bold tracking-wide ${
            data.status === "done"
              ? "bg-emerald-500/20 text-emerald-300"
              : data.status === "active"
                ? "bg-primary/20 text-primary"
                : data.status === "error"
                  ? "bg-red-500/20 text-red-300"
                  : "bg-slate-800 text-slate-500"
          }`}
        >
          {data.status.toUpperCase()}
        </span>
      </div>

      <div className="flex flex-col items-center text-center gap-2">
        <div
          className={`w-11 h-11 rounded-lg flex items-center justify-center ${
            data.status === "done"
              ? "bg-emerald-500/20 text-emerald-300"
              : data.status === "active"
                ? "bg-primary/20 text-primary"
                : data.status === "error"
                  ? "bg-red-500/20 text-red-300"
                  : "bg-slate-800 text-slate-500"
          }`}
        >
          <span className="material-symbols-outlined text-xl">{data.icon}</span>
        </div>

        <div>
          <p className="font-headline text-sm font-bold uppercase tracking-wide">{data.label}</p>
          <p className="text-[11px] text-slate-500 mt-1">Pipeline operation</p>
        </div>
      </div>

      <div className="mt-3 pt-2 border-t border-white/10 text-center text-xs font-mono text-slate-400">
        {data.durationMs || 1000}ms
      </div>
    </div>
  );
}

const nodeTypes = { pipelineNode: PipelineNode };

function TurnAwareEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps<Edge<PipelineEdgeData>>) {
  const turnDown = targetY > sourceY;

  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition: data?.isTurn ? (turnDown ? Position.Bottom : Position.Top) : sourcePosition,
    targetPosition: data?.isTurn ? (turnDown ? Position.Top : Position.Bottom) : targetPosition,
    borderRadius: data?.isTurn ? 40 : 24,
    offset: data?.isTurn ? 38 : 22,
  });

  const stateClass =
    data?.state === "active"
      ? "signal-edge-active"
      : data?.state === "done"
        ? "signal-edge-done"
        : data?.state === "error"
          ? "signal-edge-error"
          : "signal-edge-pending";

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      className={`signal-edge-path ${stateClass}`}
      style={{ strokeWidth: 2.2, strokeDasharray: "7 8" }}
    />
  );
}

const edgeTypes: EdgeTypes = {
  turnEdge: TurnAwareEdge,
};

const getUTurnPosition = (index: number, total: number, cols: number) => {
  if (total <= 1) {
    return {
      x: CANVAS_WIDTH / 2 - NODE_WIDTH / 2,
      y: CANVAS_HEIGHT / 2 - NODE_HEIGHT / 2,
    };
  }

  const rowGap = NODE_HEIGHT + 52;
  const usableWidth = CANVAS_WIDTH - NODE_PADDING * 2;

  const row = Math.floor(index / cols);
  const col = index % cols;
  const rowCount = Math.ceil(total / cols);
  const rowUsableHeight = CANVAS_HEIGHT - NODE_PADDING * 2 - NODE_HEIGHT;
  const verticalStep = rowCount > 1 ? Math.min(rowGap, rowUsableHeight / (rowCount - 1)) : 0;

  const effectiveCol = row % 2 === 0 ? col : cols - 1 - col;
  const xStep = cols > 1 ? (usableWidth - NODE_WIDTH) / (cols - 1) : 0;
  const x = NODE_PADDING + effectiveCol * xStep;
  const y = 34 + row * verticalStep;

  const maxX = CANVAS_WIDTH - NODE_WIDTH - NODE_PADDING;
  const maxY = CANVAS_HEIGHT - NODE_HEIGHT - NODE_PADDING;

  return {
    x: Math.min(Math.max(x, NODE_PADDING), maxX),
    y: Math.min(Math.max(y, NODE_PADDING), maxY),
  };
};

const buildGraph = (steps: PipelineStep[], visibleCount: number) => {
  const total = Math.max(visibleCount, 1);
  const cols = Math.min(total, 4);

  const nodes: Node<PipelineNodeData>[] = steps.slice(0, visibleCount).map((step, index) => {
    const position = getUTurnPosition(index, total, cols);
    return {
      id: `node-${step.id}`,
      type: "pipelineNode",
      data: {
        index,
        label: step.label,
        icon: step.icon,
        status: step.status,
        durationMs: step.durationMs,
      },
      position,
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      draggable: false,
      selectable: false,
    };
  });

  const edges: Edge<PipelineEdgeData>[] = [];
  for (let index = 0; index < visibleCount - 1; index++) {
    const sourceStep = steps[index];
    const nextStep = steps[index + 1];
    const edgeState: PipelineStepStatus =
      sourceStep.status === "error" || nextStep.status === "error"
        ? "error"
        : sourceStep.status === "active"
          ? "active"
          : sourceStep.status === "done"
            ? "done"
            : "pending";

    const sourceRow = Math.floor(index / cols);
    const targetRow = Math.floor((index + 1) / cols);
    const isTurn = sourceRow !== targetRow;

    edges.push({
      id: `edge-${sourceStep.id}-${nextStep.id}`,
      source: `node-${sourceStep.id}`,
      target: `node-${nextStep.id}`,
      type: "turnEdge",
      animated: edgeState === "active" || edgeState === "done",
      data: {
        state: edgeState,
        isTurn,
      },
      zIndex: 0,
    });
  }

  return { nodes, edges };
};

const ProcessLayers: React.FC<ProcessLayersProps> = ({ resultData, onViewReport }) => {
  const { state } = useGeoSafe();
  const pipelineSteps = state.pipelineSteps;

  const totalDuration = pipelineSteps.reduce((sum, step) => sum + (step.durationMs || 1000), 0);
  const completedCount = pipelineSteps.filter((step) => step.status === "done").length;

  const targetVisibleCount = useMemo(() => {
    const lastActivatedIndex = pipelineSteps.reduce((lastIndex, step, index) => {
      if (step.status !== "pending") return index;
      return lastIndex;
    }, -1);

    if (state.resultData && !state.isProcessing) return pipelineSteps.length;
    if (state.isProcessing && lastActivatedIndex < 0) return 1;
    return Math.max(0, lastActivatedIndex + 1);
  }, [pipelineSteps, state.resultData, state.isProcessing]);

  const [visibleCount, setVisibleCount] = useState(0);
  const [flowInstance, setFlowInstance] = useState<ReactFlowInstance | null>(null);
  const revealTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!state.selectedLocation && !state.isProcessing && !state.resultData) {
      revealTimerRef.current = setTimeout(() => setVisibleCount(0), 0);
      return;
    }

    if (targetVisibleCount < visibleCount) {
      revealTimerRef.current = setTimeout(() => setVisibleCount(targetVisibleCount), 0);
      return;
    }

    if (targetVisibleCount > visibleCount) {
      revealTimerRef.current = setTimeout(() => {
        setVisibleCount((prev) => Math.min(prev + 1, targetVisibleCount));
      }, 220);
    }

    return () => {
      if (revealTimerRef.current) {
        clearTimeout(revealTimerRef.current);
        revealTimerRef.current = null;
      }
    };
  }, [targetVisibleCount, visibleCount, state.selectedLocation, state.isProcessing, state.resultData]);

  const graph = useMemo(() => buildGraph(pipelineSteps, visibleCount), [pipelineSteps, visibleCount]);
  const [nodes, setNodes] = useNodesState<Node<PipelineNodeData>>(graph.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(graph.edges);

  useEffect(() => {
    setNodes(graph.nodes);
    setEdges(graph.edges);
  }, [graph, setNodes, setEdges]);

  useEffect(() => {
    if (!flowInstance || visibleCount === 0) return;
    const timeout = setTimeout(() => {
      flowInstance.fitView({
        padding: 0.18,
        duration: 280,
        minZoom: 0.8,
        maxZoom: 1.5,
      });
    }, 80);

    return () => clearTimeout(timeout);
  }, [flowInstance, visibleCount]);

  return (
    <div className="w-full min-h-screen bg-black px-6 py-12 overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        <div className="mb-10 text-center">
          <h2 className="font-headline text-4xl font-bold text-white mb-2">Pipeline Processing Layers</h2>
          <p className="text-slate-400 text-base">Controlled bounded flow with draggable nodes inside a fixed canvas</p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 md:p-8">
          <div
            className="mx-auto rounded-xl border border-white/10 bg-black/40 overflow-hidden"
            style={{ width: `${CANVAS_WIDTH}px`, height: `${CANVAS_HEIGHT}px` }}
          >
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              onInit={setFlowInstance}
              onEdgesChange={onEdgesChange}
              fitView
              fitViewOptions={{ padding: 0.18, minZoom: 0.8, maxZoom: 1.5 }}
              minZoom={0.8}
              maxZoom={1.5}
              panOnDrag={false}
              panOnScroll={false}
              zoomOnScroll={false}
              zoomOnPinch={false}
              zoomOnDoubleClick={false}
              nodeDragThreshold={4}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
              selectNodesOnDrag={false}
              selectionOnDrag={false}
              translateExtent={VIEW_EXTENT}
              preventScrolling={false}
              proOptions={{ hideAttribution: true }}
            >
              <Background gap={24} size={1} color="rgba(58,223,250,0.10)" />
              <Controls showInteractive={false} />
            </ReactFlow>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
            <div className="p-4 bg-black/40 rounded-lg border border-primary/20">
              <div className="text-xs text-slate-500 mb-2 font-mono">TOTAL STEPS</div>
              <div className="font-headline text-2xl font-bold text-primary">{pipelineSteps.length}</div>
            </div>
            <div className="p-4 bg-black/40 rounded-lg border border-emerald-500/20">
              <div className="text-xs text-slate-500 mb-2 font-mono">COMPLETED</div>
              <div className="font-headline text-2xl font-bold text-emerald-400">{completedCount}</div>
            </div>
            <div className="p-4 bg-black/40 rounded-lg border border-primary/20">
              <div className="text-xs text-slate-500 mb-2 font-mono">TOTAL TIME</div>
              <div className="font-headline text-2xl font-bold text-primary">{(totalDuration / 1000).toFixed(1)}s</div>
            </div>
            <div className="p-4 bg-black/40 rounded-lg border border-primary/20">
              <div className="text-xs text-slate-500 mb-2 font-mono">RISK SCORE</div>
              <div className="font-headline text-2xl font-bold text-primary">{resultData?.riskScore?.toFixed(1) ?? "N/A"}</div>
            </div>
          </div>
        </div>

        <div className="flex gap-4 justify-center mt-8 pb-6">
          <button
            onClick={onViewReport}
            disabled={!state.resultData}
            className={`px-8 py-3 font-semibold rounded-lg transition-all duration-300 flex items-center gap-2 ${
              state.resultData
                ? "bg-primary text-black hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/40"
                : "bg-slate-700 text-slate-300 cursor-not-allowed"
            }`}
          >
            <span className="material-symbols-outlined">arrow_forward</span>
            View Full Report
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProcessLayers;
