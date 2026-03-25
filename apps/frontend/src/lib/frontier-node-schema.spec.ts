import { describe, expect, it } from "vitest";

import { getNodePorts, resolveNodePortAlias } from "@/lib/frontier-node-schema";

const NODE_TYPES = [
  "frontier/trigger",
  "frontier/prompt",
  "frontier/agent",
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

  it("falls back safely when unknown alias is provided", () => {
    expect(resolveNodePortAlias("frontier/output", "input", "unknown_port")).toBe("in");
  });
});
