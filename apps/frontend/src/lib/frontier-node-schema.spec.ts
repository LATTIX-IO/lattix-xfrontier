import { describe, expect, it } from "vitest";

import { getNodePorts, resolveNodePortAlias } from "@/lib/frontier-node-schema";

const NODE_TYPES = [
  "frontier/trigger",
  "frontier/prompt",
  "frontier/goal",
  "frontier/evidence",
  "frontier/agent",
  "frontier/assembly",
  "frontier/commitment",
  "frontier/tool-call",
  "frontier/retrieval",
  "frontier/memory",
  "frontier/guardrail",
  "frontier/human-review",
  "frontier/manifold",
  "frontier/output",
] as const;

describe("frontier-node-schema canonical ports", () => {
  it.each(NODE_TYPES)("%s has control-plane ports", (nodeType) => {
    const ports = getNodePorts(nodeType);
    const inputNames = ports.inputs.map((item) => item.name);
    const outputNames = ports.outputs.map((item) => item.name);

    expect(inputNames.length).toBeGreaterThan(0);
    expect(outputNames.length).toBeGreaterThan(0);
    expect(outputNames).toContain("out");
  });

  it("agent defines expected canonical data ports", () => {
    const ports = getNodePorts("frontier/agent");
    const inputNames = ports.inputs.map((item) => item.name);
    const outputNames = ports.outputs.map((item) => item.name);

    expect(inputNames).toEqual(expect.arrayContaining(["in", "prompt", "context", "retrieval", "memory", "tool_result", "guardrail"]));
    expect(outputNames).toEqual(expect.arrayContaining(["out", "response", "retrieval_query", "tool_request", "state_delta", "memory", "guardrail"]));
  });

  it("guardrail defines expected canonical ports", () => {
    const ports = getNodePorts("frontier/guardrail");
    const inputNames = ports.inputs.map((item) => item.name);
    const outputNames = ports.outputs.map((item) => item.name);

    expect(inputNames).toEqual(expect.arrayContaining(["in", "candidate_output", "context"]));
    expect(outputNames).toEqual(expect.arrayContaining(["out", "approved_output", "violations", "decision"]));
  });

  it("cognitive MVP nodes define expected canonical ports", () => {
    expect(getNodePorts("frontier/goal").outputs.map((item) => item.name)).toEqual(expect.arrayContaining(["out", "goal"]));
    expect(getNodePorts("frontier/evidence").outputs.map((item) => item.name)).toEqual(expect.arrayContaining(["out", "evidence"]));
    expect(getNodePorts("frontier/assembly").inputs.map((item) => item.name)).toEqual(expect.arrayContaining(["in", "goal", "evidence"]));
    expect(getNodePorts("frontier/assembly").outputs.map((item) => item.name)).toEqual(expect.arrayContaining(["out", "synthesis", "commitment", "dissent"]));
    expect(getNodePorts("frontier/commitment").inputs.map((item) => item.name)).toEqual(expect.arrayContaining(["in", "commitment"]));
    expect(getNodePorts("frontier/commitment").outputs.map((item) => item.name)).toEqual(expect.arrayContaining(["out", "result"]));
  });
});

describe("frontier-node-schema alias resolution", () => {
  it("maps output aliases for agent", () => {
    expect(resolveNodePortAlias("frontier/agent", "output", "tool_api")).toBe("tool_request");
    expect(resolveNodePortAlias("frontier/agent", "output", "query")).toBe("retrieval_query");
  });

  it("maps input aliases for tool-call and output nodes", () => {
    expect(resolveNodePortAlias("frontier/tool-call", "input", "tool_input")).toBe("request");
    expect(resolveNodePortAlias("frontier/output", "input", "approved_output")).toBe("result");
    expect(resolveNodePortAlias("frontier/output", "input", "payload")).toBe("result");
  });

  it("maps aliases for cognitive MVP nodes", () => {
    expect(resolveNodePortAlias("frontier/goal", "output", "belief")).toBe("goal");
    expect(resolveNodePortAlias("frontier/evidence", "output", "claims")).toBe("evidence");
    expect(resolveNodePortAlias("frontier/assembly", "output", "proposal")).toBe("commitment");
    expect(resolveNodePortAlias("frontier/commitment", "input", "proposal")).toBe("commitment");
    expect(resolveNodePortAlias("frontier/commitment", "output", "published")).toBe("result");
  });

  it("falls back safely when unknown alias is provided", () => {
    expect(resolveNodePortAlias("frontier/output", "input", "unknown_port")).toBe("in");
  });
});
