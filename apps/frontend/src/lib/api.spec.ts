import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock fetch globally
const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

// Reset modules so each test gets a fresh copy of api.ts state
beforeEach(() => {
  fetchMock.mockReset();
  vi.unstubAllEnvs();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("getApiBase", () => {
  it("returns NEXT_PUBLIC_API_BASE_URL on client side", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://custom:9000");
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => [] });

    const { getPublishedWorkflows } = await import("@/lib/api");
    await getPublishedWorkflows();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("http://custom:9000"),
      expect.any(Object),
    );
  });

  it("defaults to the local gateway api path on client side", async () => {
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => [] });

    const { getPublishedWorkflows } = await import("@/lib/api");
    await getPublishedWorkflows();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/workflows/published"),
      expect.any(Object),
    );
  });
});

describe("safeFetch", () => {
  it("returns parsed JSON on success", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: "wf-1", name: "Test" }],
    });

    const { getPublishedWorkflows } = await import("@/lib/api");
    const result = await getPublishedWorkflows();

    expect(result).toEqual([{ id: "wf-1", name: "Test" }]);
  });

  it("returns fallback on network error", async () => {
    fetchMock.mockRejectedValue(new Error("Network failure"));

    const { getInbox } = await import("@/lib/api");
    const result = await getInbox();

    // Should return mock data (the fallback), not throw
    expect(Array.isArray(result)).toBe(true);
  });

  it("returns fallback on non-ok response", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500 });

    const { getArtifacts } = await import("@/lib/api");
    const result = await getArtifacts();

    expect(Array.isArray(result)).toBe(true);
  });
});

describe("strictFetch", () => {
  it("throws on non-ok response", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 422,
      text: async () => "Validation error",
    });

    const { saveWorkflowDefinition } = await import("@/lib/api");

    await expect(saveWorkflowDefinition({ id: "test" })).rejects.toThrow(/422/);
  });

  it("returns parsed JSON on success", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });

    const { saveWorkflowDefinition } = await import("@/lib/api");
    const result = await saveWorkflowDefinition({ id: "test" });

    expect(result).toEqual({ ok: true });
  });
});

describe("retry logic", () => {
  it("retries on 502 and succeeds", async () => {
    fetchMock
      .mockResolvedValueOnce({ ok: false, status: 502 })
      .mockResolvedValueOnce({ ok: true, json: async () => [] });

    const { getPublishedWorkflows } = await import("@/lib/api");
    const result = await getPublishedWorkflows();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result).toEqual([]);
  });

  it("retries on network error and succeeds", async () => {
    fetchMock
      .mockRejectedValueOnce(new Error("ECONNREFUSED"))
      .mockResolvedValueOnce({ ok: true, json: async () => ({ ok: true }) });

    const { saveWorkflowDefinition } = await import("@/lib/api");
    const result = await saveWorkflowDefinition({ id: "test" });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result).toEqual({ ok: true });
  });
});

describe("onApiStatusChange", () => {
  it("notifies listeners on connectivity change", async () => {
    const { onApiStatusChange, getPublishedWorkflows } = await import("@/lib/api");
    const listener = vi.fn();
    const unsub = onApiStatusChange(listener);

    // Force a network error to set connected=false
    fetchMock.mockRejectedValue(new Error("offline"));
    await getPublishedWorkflows();

    expect(listener).toHaveBeenCalledWith(false);

    // Restore connectivity
    fetchMock.mockResolvedValue({ ok: true, json: async () => [] });
    await getPublishedWorkflows();

    expect(listener).toHaveBeenCalledWith(true);

    unsub();
  });
});

describe("identity headers", () => {
  it("omits x-frontier-actor when no actor is configured", async () => {
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => [] });

    const { getPublishedWorkflows } = await import("@/lib/api");
    await getPublishedWorkflows();

    const callHeaders = fetchMock.mock.calls[0]?.[1]?.headers as Record<string, string>;
    expect(callHeaders["x-frontier-actor"]).toBeUndefined();
  });

  it("includes x-frontier-actor only when explicitly configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_FRONTIER_ACTOR", "frontend-user");
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => [] });

    const { getPublishedWorkflows } = await import("@/lib/api");
    await getPublishedWorkflows();

    const callHeaders = fetchMock.mock.calls[0]?.[1]?.headers as Record<string, string>;
    expect(callHeaders["x-frontier-actor"]).toBe("frontend-user");
  });

  it("never includes Authorization from browser env", async () => {
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => [] });

    const { getPublishedWorkflows } = await import("@/lib/api");
    await getPublishedWorkflows();

    const callHeaders = fetchMock.mock.calls[0]?.[1]?.headers as Record<string, string>;
    expect(callHeaders["Authorization"]).toBeUndefined();
  });
});
