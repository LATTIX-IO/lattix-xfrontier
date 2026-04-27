import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { IntegrationsManager } from "@/components/integrations-manager";

const { getIntegrationsMock, saveIntegrationMock, testIntegrationMock, deleteIntegrationMock } = vi.hoisted(() => ({
  getIntegrationsMock: vi.fn(),
  saveIntegrationMock: vi.fn(),
  testIntegrationMock: vi.fn(),
  deleteIntegrationMock: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  getIntegrations: getIntegrationsMock,
  saveIntegration: saveIntegrationMock,
  testIntegration: testIntegrationMock,
  deleteIntegration: deleteIntegrationMock,
}));

describe("IntegrationsManager", () => {
  beforeEach(() => {
    getIntegrationsMock.mockReset();
    saveIntegrationMock.mockReset();
    testIntegrationMock.mockReset();
    deleteIntegrationMock.mockReset();

    getIntegrationsMock.mockResolvedValue([]);
    saveIntegrationMock.mockResolvedValue({ ok: true, id: "integration-1" });
    testIntegrationMock.mockResolvedValue({
      ok: true,
      id: "integration-1",
      status: "configured",
      message: "Connectivity verified",
      diagnostics: { warnings: ["TLS certificate is self-signed"] },
    });
    deleteIntegrationMock.mockResolvedValue({ ok: true });
  });

  it("saves integrations and refreshes the list", async () => {
    getIntegrationsMock
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: "integration-1",
          name: "CRM API",
          type: "http",
          status: "draft",
          base_url: "https://crm.example.com/v1",
          auth_type: "api_key",
          secret_ref: "secret/crm/token",
          metadata_json: {
            auth: { method: "api_key", location: "header", key_name: "x-api-key" },
          },
        },
      ]);

    render(<IntegrationsManager />);

    await screen.findByText(/no integrations configured yet/i);

    fireEvent.change(screen.getByLabelText(/^name$/i), { target: { value: "CRM API" } });
    fireEvent.change(screen.getByLabelText(/base url \/ dsn/i), { target: { value: "https://crm.example.com/v1" } });
    fireEvent.change(screen.getByLabelText(/auth type/i), { target: { value: "api_key" } });
    fireEvent.change(screen.getByLabelText(/secret reference/i), { target: { value: "secret/crm/token" } });
    fireEvent.click(screen.getByRole("button", { name: /save integration/i }));

    await waitFor(() => expect(saveIntegrationMock).toHaveBeenCalledTimes(1));
    expect(saveIntegrationMock).toHaveBeenCalledWith(expect.objectContaining({
      name: "CRM API",
      type: "http",
      base_url: "https://crm.example.com/v1",
      auth_type: "api_key",
      secret_ref: "secret/crm/token",
      metadata_json: {
        auth: {
          method: "api_key",
          location: "header",
          key_name: "x-api-key",
        },
      },
    }));
    expect(await screen.findByText("Integration saved.")).toBeInTheDocument();
    expect(await screen.findByText("CRM API")).toBeInTheDocument();
  });

  it("surfaces backend test failures", async () => {
    getIntegrationsMock.mockResolvedValue([
      {
        id: "integration-1",
        name: "CRM API",
        type: "http",
        status: "draft",
        base_url: "https://crm.example.com/v1",
        auth_type: "none",
        secret_ref: "",
        metadata_json: {},
      },
    ]);
    testIntegrationMock.mockRejectedValueOnce(new Error("503 integration backend unavailable"));

    render(<IntegrationsManager />);

    await screen.findByText("CRM API");
    fireEvent.click(screen.getByRole("button", { name: /^test$/i }));

    expect(await screen.findByText("503 integration backend unavailable")).toBeInTheDocument();
  });

  it("surfaces backend delete failures", async () => {
    getIntegrationsMock.mockResolvedValue([
      {
        id: "integration-1",
        name: "CRM API",
        type: "http",
        status: "draft",
        base_url: "https://crm.example.com/v1",
        auth_type: "none",
        secret_ref: "",
        metadata_json: {},
      },
    ]);
    deleteIntegrationMock.mockRejectedValueOnce(new Error("409 integration is still referenced"));

    render(<IntegrationsManager />);

    await screen.findByText("CRM API");
    fireEvent.click(screen.getByRole("button", { name: /^delete$/i }));

    expect(await screen.findByText("409 integration is still referenced")).toBeInTheDocument();
  });

  it("limits new integrations to auth modes the backend can currently exercise", async () => {
    render(<IntegrationsManager />);

    await screen.findByText(/no integrations configured yet/i);
    expect(screen.queryByRole("option", { name: /^oauth2$/i })).not.toBeInTheDocument();
    expect(screen.getByText(/interactive oauth2 is not wired through the backend test\/send path yet/i)).toBeInTheDocument();
  });
});
