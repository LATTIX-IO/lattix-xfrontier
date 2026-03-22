"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type NodeProps,
  type ReactFlowInstance,
} from "reactflow";
import { frontierCanvasNodes } from "@/lib/frontier-node-catalog";
import {
  getNodeDefaultConfig,
  getNodePorts,
  getNodeWidgets,
  normalizeNodeTypeForSchema,
  resolveNodePortAlias,
} from "@/lib/frontier-node-schema";
import "reactflow/dist/style.css";

type NodeType = string;

export type GraphNode = {
  id: string;
  title: string;
  type: NodeType;
  x: number;
  y: number;
  config?: Record<string, unknown>;
};

export type GraphLink = {
  from: string;
  to: string;
  from_port?: string;
  to_port?: string;
};

type Props = {
  nodes: GraphNode[];
  links: GraphLink[];
  height?: number;
  className?: string;
  readOnly?: boolean;
  extraNodeDefinitions?: Array<{
    key: `frontier/${string}`;
    title: string;
    color?: string;
    description?: string;
  }>;
  onGraphChange?: (graph: { nodes: GraphNode[]; links: GraphLink[] }) => void;
  onNodeSelected?: (node: GraphNode | null) => void;
  widgetOptionOverrides?: Record<string, Record<string, string[]>>;
  edgeType?: "default" | "straight" | "step" | "smoothstep" | "simplebezier";
  edgeAnimated?: boolean;
  onReady?: (api: {
    addNode: (node: { type: string; title?: string; x?: number; y?: number; config?: Record<string, unknown> }) => void;
    autoLayout: (options?: { fitView?: boolean }) => void;
    replaceGraph: (graph: { nodes: GraphNode[]; links: GraphLink[] }, options?: { fitView?: boolean }) => void;
    clear: () => void;
    serialize: () => { nodes: GraphNode[]; links: GraphLink[] };
  }) => void;
};

type WidgetSpec = {
  key: string;
  label: string;
  kind: "text" | "number" | "combo" | "toggle";
  defaultValue: string | number | boolean;
  options?: string[];
  multiline?: boolean;
  help?: string;
  placeholder?: string;
};

type PortSpec = {
  name: string;
  type: string;
};

type NodeDefinition = {
  key: `frontier/${string}`;
  type: string;
  title: string;
  color: string;
  description?: string;
};

type FrontierNodeData = {
  title: string;
  color: string;
  type: string;
  readOnly: boolean;
  config: Record<string, unknown>;
  widgets: WidgetSpec[];
  inputs: PortSpec[];
  outputs: PortSpec[];
  onConfigChange: (nodeId: string, key: string, value: unknown) => void;
};

function formatWidgetValue(field: WidgetSpec, value: unknown): string {
  if (field.kind === "toggle") {
    return Boolean(value) ? "true" : "false";
  }
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function resolveInputPortType(node: Node<FrontierNodeData>, handleId: string | null | undefined): string | null {
  const normalizedHandle = resolveNodePortAlias(node.data.type, "input", handleId);
  const port = normalizedHandle ? node.data.inputs.find((input) => input.name === normalizedHandle) : node.data.inputs[0];
  return port?.type ?? null;
}

function resolveOutputPortType(node: Node<FrontierNodeData>, handleId: string | null | undefined): string | null {
  const normalizedHandle = resolveNodePortAlias(node.data.type, "output", handleId);
  const port = normalizedHandle ? node.data.outputs.find((output) => output.name === normalizedHandle) : node.data.outputs[0];
  return port?.type ?? null;
}

function arePortTypesCompatible(sourceType: string | null, targetType: string | null): boolean {
  if (!sourceType || !targetType) {
    return false;
  }

  return sourceType === targetType;
}

const HEADER_HEIGHT_PX = 24;
const PORT_SECTION_OFFSET_PX = 32;
const PORT_ROW_HEIGHT_PX = 18;
const PORT_ROW_CENTER_OFFSET_PX = 18;
const AUTO_LAYOUT_BASE_X = 120;
const AUTO_LAYOUT_BASE_Y = 120;
const AUTO_LAYOUT_X_GAP = 440;
const AUTO_LAYOUT_Y_GAP = 64;

function estimateNodeHeight(node: Node<FrontierNodeData>): number {
  const measuredHeight = typeof node.height === "number" && Number.isFinite(node.height) ? node.height : null;
  const portRows = Math.max(node.data.inputs.length, node.data.outputs.length, 1);
  const multilineWidgets = node.data.widgets.filter((widget) => widget.multiline).length;
  const singleLineWidgets = Math.max(0, node.data.widgets.length - multilineWidgets);

  const estimated =
    40 + // header + outer paddings
    14 + // ports header row
    portRows * PORT_ROW_HEIGHT_PX +
    20 + // ports panel paddings/margins
    singleLineWidgets * 28 +
    multilineWidgets * 96 +
    20;

  if (measuredHeight && measuredHeight > 0) {
    return Math.max(measuredHeight, estimated);
  }
  return estimated;
}

const defaultNodeColorByType: Record<string, string> = Object.fromEntries(
  frontierCanvasNodes.map((definition) => [definition.type, definition.color]),
);

function ensureReadableHeaderColor(color: string): string {
  const hex = color.replace("#", "").trim();
  const valid = /^[0-9a-fA-F]{6}$/.test(hex) ? hex : "4f5966";
  const r = parseInt(valid.slice(0, 2), 16);
  const g = parseInt(valid.slice(2, 4), 16);
  const b = parseInt(valid.slice(4, 6), 16);
  const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  if (luminance <= 0.45) {
    return `#${valid}`;
  }
  const darken = (channel: number) => Math.max(0, Math.floor(channel * 0.58));
  return `#${darken(r).toString(16).padStart(2, "0")}${darken(g).toString(16).padStart(2, "0")}${darken(b).toString(16).padStart(2, "0")}`;
}

function headerTitleTextColor(color: string): "#000000" | "#ffffff" {
  const hex = color.replace("#", "").trim();
  const valid = /^[0-9a-fA-F]{6}$/.test(hex) ? hex : "4f5966";
  const r = parseInt(valid.slice(0, 2), 16);
  const g = parseInt(valid.slice(2, 4), 16);
  const b = parseInt(valid.slice(4, 6), 16);
  const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  return luminance >= 0.6 ? "#000000" : "#ffffff";
}

function portsForNodeType(type: string): { inputs: PortSpec[]; outputs: PortSpec[] } {
  return getNodePorts(type);
}

function defaultConfigForNodeType(type: string): Record<string, unknown> {
  return getNodeDefaultConfig(type);
}

function widgetSpecsForNodeType(type: string, widgetOptionOverrides?: Record<string, Record<string, string[]>>): WidgetSpec[] {
  const widgets = getNodeWidgets(type);
  if (!widgetOptionOverrides) {
    return widgets;
  }

  const normalizedType = normalizeNodeTypeForSchema(type);
  const overrides = widgetOptionOverrides[normalizedType] ?? widgetOptionOverrides[type] ?? {};

  return widgets.map((widget) => {
    if (widget.kind !== "combo") {
      return widget;
    }
    const overrideOptions = overrides[widget.key];
    if (!overrideOptions) {
      return widget;
    }
    return {
      ...widget,
      options: overrideOptions,
    };
  });
}

function FrontierNodeView({ id, data }: NodeProps<FrontierNodeData>) {
  const titleColor = headerTitleTextColor(data.color);
  const portRows = Math.max(data.inputs.length, data.outputs.length, 1);

  return (
    <div className="min-w-[300px] border border-[var(--fx-border)] bg-[var(--fx-surface)] text-[var(--foreground)] shadow-[0_8px_20px_rgba(0,0,0,0.35)]">
      <div className="px-2 py-1 text-[11px] font-semibold" style={{ background: data.color, color: titleColor }}>
        {data.title}
      </div>
      <div className="space-y-1 p-2">
        <div className="mb-2 border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-2">
          <div className="mb-1 grid grid-cols-2 text-[9px] uppercase tracking-[0.08em] fx-muted">
            <span>Inputs</span>
            <span className="text-right">Outputs</span>
          </div>
          <div className="space-y-0.5">
            {Array.from({ length: portRows }).map((_, index) => {
              const input = data.inputs[index];
              const output = data.outputs[index];

              return (
                <div key={`port-row-${index}`} className="grid min-h-[18px] grid-cols-2 items-center gap-2 text-[10px]">
                  <span className="truncate text-[var(--foreground)]" title={input ? `${input.name} (${input.type})` : ""}>
                    {input ? `${input.name} · ${input.type}` : "—"}
                  </span>
                  <span className="truncate text-right text-[var(--foreground)]" title={output ? `${output.name} (${output.type})` : ""}>
                    {output ? `${output.name} · ${output.type}` : "—"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {data.widgets.map((field) => {
          const value = data.config[field.key] ?? field.defaultValue;
          const placeholder = field.placeholder ?? "literal value or var.currentUser";
          return (
            <label key={field.key} className="block text-[10px] fx-muted">
              <div className="mb-0.5 flex items-center gap-1">
                <span>{field.label}</span>
                {field.help ? (
                  <span
                    className="inline-flex h-3.5 w-3.5 cursor-help items-center justify-center rounded-full border border-[var(--fx-border)] text-[9px] font-semibold text-[var(--fx-primary)]"
                    title={field.help}
                    aria-label={`${field.label} help`}
                  >
                    i
                  </span>
                ) : null}
              </div>
              {field.kind === "combo" ? (
                data.readOnly ? (
                  <div className="border border-[var(--fx-border)] bg-[var(--fx-input)] px-1 py-0.5 text-[10px] text-[var(--fx-input-text)]">{formatWidgetValue(field, value)}</div>
                ) : (
                  <>
                    <input
                      className="nodrag fx-field w-full px-1 py-0.5 text-[10px]"
                      type="text"
                      list={`combo-${id}-${field.key}`}
                      value={String(value)}
                      onChange={(event) => data.onConfigChange(id, field.key, event.target.value)}
                      placeholder={placeholder}
                    />
                    <datalist id={`combo-${id}-${field.key}`}>
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option} />
                      ))}
                    </datalist>
                  </>
                )
              ) : field.kind === "number" ? (
                data.readOnly ? (
                  <div className="border border-[var(--fx-border)] bg-[var(--fx-input)] px-1 py-0.5 text-[10px] text-[var(--fx-input-text)]">{formatWidgetValue(field, value)}</div>
                ) : (
                  <input
                    className="nodrag fx-field w-full px-1 py-0.5 text-[10px]"
                    type="number"
                    value={Number(value)}
                    onChange={(event) => data.onConfigChange(id, field.key, Number(event.target.value))}
                  />
                )
              ) : field.kind === "toggle" ? (
                data.readOnly ? (
                  <div className="border border-[var(--fx-border)] bg-[var(--fx-input)] px-1 py-0.5 text-[10px] text-[var(--fx-input-text)]">{formatWidgetValue(field, value)}</div>
                ) : (
                  <input
                    className="nodrag"
                    type="checkbox"
                    checked={Boolean(value)}
                    onChange={(event) => data.onConfigChange(id, field.key, event.target.checked)}
                  />
                )
              ) : field.multiline ? (
                data.readOnly ? (
                  <pre className="max-h-24 overflow-auto whitespace-pre-wrap border border-[var(--fx-border)] bg-[var(--fx-input)] px-2 py-1 text-[10px] text-[var(--fx-input-text)]">
                    {formatWidgetValue(field, value) || "(empty)"}
                  </pre>
                ) : (
                  <textarea
                    className="nodrag fx-field min-h-20 w-full px-2 py-1 text-[10px]"
                    value={String(value)}
                    onChange={(event) => data.onConfigChange(id, field.key, event.target.value)}
                    placeholder="Type value (supports var.currentUser / {{var.currentUser}})"
                  />
                )
              ) : (
                data.readOnly ? (
                  <div className="border border-[var(--fx-border)] bg-[var(--fx-input)] px-1 py-0.5 text-[10px] text-[var(--fx-input-text)]">{formatWidgetValue(field, value)}</div>
                ) : (
                  <input
                    className="nodrag fx-field w-full px-1 py-0.5 text-[10px]"
                    type="text"
                    value={String(value)}
                    onChange={(event) => data.onConfigChange(id, field.key, event.target.value)}
                    placeholder={placeholder}
                  />
                )
              )}
            </label>
          );
        })}
      </div>

      {data.inputs.map((input, index) => (
        <Handle
          key={`in-${input.name}`}
          id={input.name}
          type="target"
          position={Position.Left}
          style={{
            top: HEADER_HEIGHT_PX + PORT_SECTION_OFFSET_PX + PORT_ROW_CENTER_OFFSET_PX + index * PORT_ROW_HEIGHT_PX,
            width: 8,
            height: 8,
            background: "#9aa0a6",
          }}
        />
      ))}

      {data.outputs.map((output, index) => (
        <Handle
          key={`out-${output.name}`}
          id={output.name}
          type="source"
          position={Position.Right}
          style={{
            top: HEADER_HEIGHT_PX + PORT_SECTION_OFFSET_PX + PORT_ROW_CENTER_OFFSET_PX + index * PORT_ROW_HEIGHT_PX,
            width: 8,
            height: 8,
            background: "#54d499",
          }}
        />
      ))}
    </div>
  );
}

const nodeTypes = { frontierNode: FrontierNodeView };

function ReactFlowCanvasImpl({
  nodes,
  links,
  height,
  className,
  readOnly = false,
  extraNodeDefinitions,
  onGraphChange,
  onNodeSelected,
  widgetOptionOverrides,
  edgeType = "smoothstep",
  edgeAnimated = false,
  onReady,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const flowRef = useRef<ReactFlowInstance | null>(null);
  const [menu, setMenu] = useState<{ x: number; y: number; clientX: number; clientY: number } | null>(null);

  const definitions = useMemo<NodeDefinition[]>(() => {
    const extraDefinitions = extraNodeDefinitions ?? [];
    const source = extraDefinitions.length > 0
      ? extraDefinitions.map((item) => ({
          key: item.key,
          type: item.key.replace("frontier/", ""),
          title: item.title,
          color: item.color ?? "#54d499",
          description: item.description,
        }))
      : frontierCanvasNodes;

    return source.reduce<NodeDefinition[]>((acc, item) => {
      if (!acc.some((existing) => existing.key === item.key)) {
        acc.push({ ...item, color: ensureReadableHeaderColor(item.color) });
      }
      return acc;
    }, []);
  }, [extraNodeDefinitions]);

  const definitionByType = useMemo(() => new Map(definitions.map((definition) => [definition.type, definition])), [definitions]);

  const normalizedEdgeType = edgeType === "default" ? "default" : edgeType;

  const edgeVisualStyle = useMemo(() => {
    if (normalizedEdgeType === "step") {
      return { stroke: "#7b8794", strokeWidth: 1.6, strokeLinecap: "square" as const };
    }
    if (normalizedEdgeType === "straight") {
      return { stroke: "#8b96a3", strokeWidth: 1.4 };
    }
    if (normalizedEdgeType === "simplebezier") {
      return { stroke: "#74a8ff", strokeWidth: 1.6 };
    }
    return { stroke: "#7b8794", strokeWidth: 1.5 };
  }, [normalizedEdgeType]);

  const toCanvasNode = useCallback(
    (graphNode: GraphNode): Node<FrontierNodeData> => {
      const definition = definitionByType.get(graphNode.type);
      const config = {
        ...defaultConfigForNodeType(graphNode.type),
        ...(graphNode.config ?? {}),
      };

      return {
        id: graphNode.id,
        type: "frontierNode",
        position: { x: graphNode.x, y: graphNode.y },
        data: {
          title: graphNode.title,
          color: ensureReadableHeaderColor(definition?.color ?? defaultNodeColorByType[graphNode.type] ?? "#4f5966"),
          type: graphNode.type,
          readOnly,
          config,
          widgets: widgetSpecsForNodeType(graphNode.type, widgetOptionOverrides),
          ...portsForNodeType(graphNode.type),
          onConfigChange: () => {
            // wired after initial node creation
          },
        },
      };
    },
    [definitionByType, readOnly, widgetOptionOverrides],
  );

  const buildCanvasEdges = useCallback((graphNodes: Node<FrontierNodeData>[], graphLinks: GraphLink[]): Edge[] => {
    const byId = new Map(graphNodes.map((node) => [node.id, node]));

    return graphLinks.reduce<Edge[]>((acc, link, index) => {
      const source = byId.get(link.from);
      const target = byId.get(link.to);
      if (!source || !target) {
        return acc;
      }

      const sourceHandle = resolveNodePortAlias(source.data.type, "output", link.from_port ?? source.data.outputs[0]?.name);
      const targetHandle = resolveNodePortAlias(target.data.type, "input", link.to_port ?? target.data.inputs[0]?.name);
      const sourceType = resolveOutputPortType(source, sourceHandle);
      const targetType = resolveInputPortType(target, targetHandle);

      if (!arePortTypesCompatible(sourceType, targetType)) {
        return acc;
      }

      acc.push({
        id: `${link.from}:${sourceHandle ?? "out"}->${link.to}:${targetHandle ?? "in"}:${index}`,
        source: link.from,
        target: link.to,
        sourceHandle,
        targetHandle,
        type: normalizedEdgeType,
        animated: edgeAnimated,
        style: edgeVisualStyle,
      });

      return acc;
    }, []);
  }, [edgeAnimated, edgeVisualStyle, normalizedEdgeType]);

  const [rfNodes, setRfNodes] = useState<Node<FrontierNodeData>[]>(() => nodes.map(toCanvasNode));
  const [rfEdges, setRfEdges] = useState<Edge[]>(() => buildCanvasEdges(nodes.map(toCanvasNode), links));

  const autoLayout = useCallback((options?: { fitView?: boolean }) => {
    setRfNodes((previous) => {
      if (previous.length <= 1) {
        return previous;
      }

      const nodeIds = previous.map((node) => node.id);
      const idSet = new Set(nodeIds);
      const indegree = new Map<string, number>(nodeIds.map((id) => [id, 0]));
      const adjacency = new Map<string, string[]>(nodeIds.map((id) => [id, []]));

      for (const edge of rfEdges) {
        if (!idSet.has(edge.source) || !idSet.has(edge.target) || edge.source === edge.target) {
          continue;
        }
        const targets = adjacency.get(edge.source);
        if (targets && !targets.includes(edge.target)) {
          targets.push(edge.target);
          indegree.set(edge.target, (indegree.get(edge.target) ?? 0) + 1);
        }
      }

      const nodeById = new Map(previous.map((node) => [node.id, node]));
      const sortStable = (a: string, b: string) => {
        const left = nodeById.get(a);
        const right = nodeById.get(b);
        if (!left || !right) {
          return a.localeCompare(b);
        }
        if (left.position.y !== right.position.y) {
          return left.position.y - right.position.y;
        }
        if (left.position.x !== right.position.x) {
          return left.position.x - right.position.x;
        }
        return a.localeCompare(b);
      };

      const queue = nodeIds.filter((id) => (indegree.get(id) ?? 0) === 0).sort(sortStable);
      const levelById = new Map<string, number>(nodeIds.map((id) => [id, 0]));
      const ordered: string[] = [];

      while (queue.length > 0) {
        const currentId = queue.shift() as string;
        ordered.push(currentId);
        const currentLevel = levelById.get(currentId) ?? 0;
        for (const nextId of adjacency.get(currentId) ?? []) {
          const nextLevel = Math.max(levelById.get(nextId) ?? 0, currentLevel + 1);
          levelById.set(nextId, nextLevel);

          const nextInDegree = (indegree.get(nextId) ?? 0) - 1;
          indegree.set(nextId, nextInDegree);
          if (nextInDegree === 0) {
            queue.push(nextId);
            queue.sort(sortStable);
          }
        }
      }

      if (ordered.length !== previous.length) {
        const remaining = nodeIds.filter((id) => !ordered.includes(id)).sort(sortStable);
        const maxLevel = Math.max(...Array.from(levelById.values()));
        remaining.forEach((id, index) => {
          levelById.set(id, maxLevel + 1 + index);
          ordered.push(id);
        });
      }

      const columns = new Map<number, string[]>();
      for (const id of ordered) {
        const level = levelById.get(id) ?? 0;
        const existing = columns.get(level) ?? [];
        existing.push(id);
        columns.set(level, existing);
      }

      for (const [level, ids] of columns.entries()) {
        ids.sort(sortStable);
        columns.set(level, ids);
      }

      const positions = new Map<string, { x: number; y: number }>();
      const sortedLevels = Array.from(columns.keys()).sort((a, b) => a - b);
      for (const level of sortedLevels) {
        const ids = columns.get(level) ?? [];
        const heights = ids.map((id) => {
          const candidate = nodeById.get(id);
          return candidate ? estimateNodeHeight(candidate) : 280;
        });

        const totalHeight = heights.reduce((sum, current) => sum + current, 0);
        const totalGap = Math.max(0, ids.length - 1) * AUTO_LAYOUT_Y_GAP;
        const stackHeight = totalHeight + totalGap;
        let currentTop = AUTO_LAYOUT_BASE_Y - stackHeight / 2;

        ids.forEach((id, index) => {
          const nodeHeight = heights[index] ?? 280;
          const centerY = currentTop + nodeHeight / 2;
          positions.set(id, {
            x: AUTO_LAYOUT_BASE_X + level * AUTO_LAYOUT_X_GAP,
            y: centerY,
          });
          currentTop += nodeHeight + AUTO_LAYOUT_Y_GAP;
        });
      }

      return previous.map((node) => {
        const next = positions.get(node.id);
        if (!next) {
          return node;
        }
        return {
          ...node,
          position: next,
        };
      });
    });

    if (options?.fitView !== false) {
      requestAnimationFrame(() => {
        flowRef.current?.fitView({ duration: 280, padding: 0.18 });
      });
    }
  }, [rfEdges]);

  const renderedEdges = useMemo(
    () =>
      rfEdges.map((edge) => ({
        ...edge,
        type: normalizedEdgeType,
        animated: edgeAnimated,
        style: edgeVisualStyle,
      })),
    [edgeAnimated, edgeVisualStyle, normalizedEdgeType, rfEdges],
  );

  const serializeGraph = useCallback((): { nodes: GraphNode[]; links: GraphLink[] } => {
    const graphNodes: GraphNode[] = rfNodes.map((node) => ({
      id: node.id,
      title: node.data.title,
      type: node.data.type,
      x: node.position.x,
      y: node.position.y,
      config: node.data.config,
    }));

    const graphLinks: GraphLink[] = rfEdges.map((edge) => ({
      from: edge.source,
      to: edge.target,
      from_port: edge.sourceHandle ?? undefined,
      to_port: edge.targetHandle ?? undefined,
    }));

    return { nodes: graphNodes, links: graphLinks };
  }, [rfEdges, rfNodes]);

  useEffect(() => {
    onGraphChange?.(serializeGraph());
  }, [onGraphChange, serializeGraph]);

  const updateNodeConfig = useCallback((nodeId: string, key: string, value: unknown) => {
    setRfNodes((previous) =>
      previous.map((node) => {
        if (node.id !== nodeId) {
          return node;
        }
        return {
          ...node,
          data: {
            ...node.data,
            config: {
              ...node.data.config,
              [key]: value,
            },
          },
        };
      }),
    );
  }, []);

  const hydratedNodes = useMemo(
    () =>
      rfNodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          readOnly,
          onConfigChange: updateNodeConfig,
        },
      })),
    [rfNodes, readOnly, updateNodeConfig],
  );

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    const allowedChanges = readOnly ? changes.filter((change) => change.type === "position" || change.type === "select") : changes;
    setRfNodes((previous) => applyNodeChanges(allowedChanges, previous));
  }, [readOnly]);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    if (readOnly) {
      return;
    }
    setRfEdges((previous) => applyEdgeChanges(changes, previous));
  }, [readOnly]);

  const isConnectionValid = useCallback(
    (connection: Connection | Edge): boolean => {
      const sourceId = connection.source;
      const targetId = connection.target;

      if (!sourceId || !targetId || sourceId === targetId) {
        return false;
      }

      if (readOnly) {
        return false;
      }

      const sourceNode = rfNodes.find((node) => node.id === sourceId);
      const targetNode = rfNodes.find((node) => node.id === targetId);
      if (!sourceNode || !targetNode) {
        return false;
      }

      const sourceType = resolveOutputPortType(sourceNode, connection.sourceHandle);
      const targetType = resolveInputPortType(targetNode, connection.targetHandle);

      return arePortTypesCompatible(sourceType, targetType);
    },
    [readOnly, rfNodes],
  );

  const onConnect = useCallback((connection: Connection) => {
    if (readOnly) {
      return;
    }

    if (!isConnectionValid(connection)) {
      return;
    }

    setRfEdges((previous) =>
      addEdge(
        {
          ...connection,
          id: `${connection.source}:${connection.sourceHandle ?? "out"}->${connection.target}:${connection.targetHandle ?? "in"}:${Date.now()}`,
          type: normalizedEdgeType,
          animated: edgeAnimated,
          style: edgeVisualStyle,
        },
        previous,
      ),
    );
  }, [edgeAnimated, edgeVisualStyle, isConnectionValid, normalizedEdgeType, readOnly]);

  const removeEdgeById = useCallback((edgeId: string) => {
    if (readOnly) {
      return;
    }
    setRfEdges((previous) => previous.filter((edge) => edge.id !== edgeId));
  }, [readOnly]);

  const handlePaneContextMenu = useCallback((event: React.MouseEvent) => {
    if (readOnly) {
      return;
    }

    event.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) {
      setMenu({ x: event.clientX, y: event.clientY, clientX: event.clientX, clientY: event.clientY });
      return;
    }

    const menuWidth = 288; // w-72
    const menuHeight = 320; // max-h-80
    const localX = Math.max(0, Math.min(event.clientX - rect.left, Math.max(0, rect.width - menuWidth - 4)));
    const localY = Math.max(0, Math.min(event.clientY - rect.top, Math.max(0, rect.height - menuHeight - 4)));
    setMenu({ x: localX, y: localY, clientX: event.clientX, clientY: event.clientY });
  }, [readOnly]);

  const addNode = useCallback(
    (type: string, title?: string, config?: Record<string, unknown>, x?: number, y?: number) => {
      const definition = definitionByType.get(type);
      const id = `${type}-${Date.now()}`;
      const position = flowRef.current && x !== undefined && y !== undefined
        ? (flowRef.current.screenToFlowPosition({ x, y }) as { x: number; y: number })
        : { x: 220, y: 140 };

      const newNode: Node<FrontierNodeData> = {
        id,
        type: "frontierNode",
        position,
        data: {
          title: title ?? definition?.title ?? type,
          color: ensureReadableHeaderColor(definition?.color ?? defaultNodeColorByType[type] ?? "#4f5966"),
          type,
          readOnly,
          config: {
            ...defaultConfigForNodeType(type),
            ...(config ?? {}),
          },
          widgets: widgetSpecsForNodeType(type, widgetOptionOverrides),
          ...portsForNodeType(type),
          onConfigChange: updateNodeConfig,
        },
      };

      setRfNodes((previous) => [...previous, newNode]);
      setMenu(null);
    },
    [definitionByType, readOnly, updateNodeConfig, widgetOptionOverrides],
  );

  useEffect(() => {
    onReady?.({
      addNode: ({ type, title, x, y, config }) => addNode(type, title, config, x, y),
      autoLayout,
      replaceGraph: (graph, options) => {
        const nextNodes = graph.nodes.map(toCanvasNode);
        setRfNodes(nextNodes);
        setRfEdges(buildCanvasEdges(nextNodes, graph.links));
        if (options?.fitView !== false) {
          requestAnimationFrame(() => {
            flowRef.current?.fitView({ duration: 220, padding: 0.18 });
          });
        }
      },
      clear: () => {
        setRfNodes([]);
        setRfEdges([]);
      },
      serialize: serializeGraph,
    });
  }, [addNode, autoLayout, buildCanvasEdges, onReady, serializeGraph, toCanvasNode]);

  return (
    <div ref={containerRef} className={`fx-panel relative overflow-hidden ${className ?? ""}`} style={{ height: height ? `${height}px` : "100%" }}>
      <ReactFlow
        nodes={hydratedNodes}
        edges={renderedEdges}
        nodeTypes={nodeTypes}
        isValidConnection={isConnectionValid}
        nodesConnectable={!readOnly}
        edgesUpdatable={!readOnly}
        connectOnClick={!readOnly}
        fitView
        minZoom={0.25}
        maxZoom={1.8}
        defaultEdgeOptions={{ type: normalizedEdgeType, animated: edgeAnimated, style: edgeVisualStyle }}
        onInit={(instance) => {
          flowRef.current = instance;
        }}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onEdgeDoubleClick={(_, edge) => {
          removeEdgeById(edge.id);
        }}
        onEdgeContextMenu={(event, edge) => {
          event.preventDefault();
          removeEdgeById(edge.id);
        }}
        onPaneContextMenu={handlePaneContextMenu}
        onPaneClick={() => {
          setMenu(null);
          onNodeSelected?.(null);
        }}
        onNodeClick={(_, node) => {
          setMenu(null);
          onNodeSelected?.({
            id: node.id,
            title: node.data.title,
            type: node.data.type,
            x: node.position.x,
            y: node.position.y,
            config: node.data.config,
          });
        }}
        style={{ background: "var(--background)" }}
      >
        <Background color="var(--fx-border)" gap={20} size={1} />
        <MiniMap position="bottom-left" pannable zoomable nodeColor="var(--fx-muted)" maskColor="rgba(0,0,0,0.35)" />
        <Controls showInteractive={false} />
      </ReactFlow>

      {menu && (
        <div
          className="fx-panel absolute z-40 max-h-80 w-72 overflow-auto p-1 shadow-[0_10px_30px_rgba(0,0,0,0.5)]"
          style={{ left: menu.x, top: menu.y }}
        >
          <div className="mb-1 px-1 text-[10px] uppercase tracking-[0.08em] fx-muted">Add Node • frontier</div>
          {definitions.map((definition) => (
            <button
              key={definition.key}
              className="mb-0.5 flex w-full items-center justify-between border border-transparent px-2 py-1 text-left text-[11px] text-[var(--foreground)] hover:border-[var(--fx-border)] hover:bg-[var(--fx-nav-hover)]"
              onClick={() => addNode(definition.type, definition.title, undefined, menu.clientX, menu.clientY)}
            >
              <span>{definition.title}</span>
              <span className="h-2 w-2 rounded-full" style={{ background: definition.color }} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function ReactFlowCanvas(props: Props) {
  return (
    <ReactFlowProvider>
      <ReactFlowCanvasImpl {...props} />
    </ReactFlowProvider>
  );
}
