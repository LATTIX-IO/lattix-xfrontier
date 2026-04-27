import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { getOperatorSessionMock } = vi.hoisted(() => ({
  getOperatorSessionMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: vi.fn(),
    refresh: vi.fn(),
    push: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  getOperatorSession: getOperatorSessionMock,
}));

import AuthPage from "@/app/auth/page";

const anonymousSession = {
  authenticated: false,
  actor: "anonymous",
  principal_id: "anonymous",
  principal_type: "user",
  display_name: "",
  subject: "",
  email: "",
  preferred_username: "",
  auth_mode: "shared-token",
  provider: "",
  roles: [],
  capabilities: { can_admin: false, can_builder: false },
  allowed_modes: ["user"],
  default_mode: "user",
  oidc: {
    configured: false,
    issuer: "",
    audience: "",
    provider: "",
    validation_error: "",
    browser_flow_configured: false,
    browser_flow_error: "",
  },
} as const;

describe("AuthPage", () => {
  const originalEnv = { ...process.env };

  afterEach(() => {
    process.env = { ...originalEnv };
    getOperatorSessionMock.mockReset();
  });

  it("renders Casdoor-backed sign-in and sign-up actions", async () => {
    getOperatorSessionMock.mockResolvedValue({
      ...anonymousSession,
      auth_mode: "oidc",
      provider: "casdoor",
      oidc: {
        configured: true,
        issuer: "http://127.0.0.1:8081",
        audience: "frontier-ui",
        provider: "casdoor",
        validation_error: "",
        browser_flow_configured: true,
        browser_flow_error: "",
      },
    });
    process.env.FRONTIER_AUTH_OIDC_CLIENT_ID = "frontier-web";
    process.env.FRONTIER_AUTH_OIDC_SIGNIN_URL = "http://127.0.0.1:8081/login/oauth/authorize";
    process.env.FRONTIER_AUTH_OIDC_SIGNUP_URL = "http://127.0.0.1:8081/signup";
    process.env.FRONTIER_AUTH_OIDC_SCOPES = "openid profile email";

    render(await AuthPage());

    expect(screen.getByRole("heading", { name: /sign in to xfrontier/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText("username")).toBeInTheDocument();
    expect(screen.queryByPlaceholderText("james")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /local sign-in/i })).toBeInTheDocument();
    expect(screen.getByText(/configured against http:\/\/127\.0\.0\.1:8081/i)).toBeInTheDocument();
  });

  it("shows setup guidance when oidc is incomplete", async () => {
    getOperatorSessionMock.mockResolvedValue({
      ...anonymousSession,
      auth_mode: "oidc",
      provider: "oidc",
      oidc: {
        configured: false,
        issuer: "",
        audience: "",
        provider: "oidc",
        validation_error: "",
        browser_flow_configured: false,
        browser_flow_error: "",
      },
    });
    process.env.FRONTIER_AUTH_OIDC_SIGNIN_URL = "";
    process.env.FRONTIER_AUTH_OIDC_SIGNUP_URL = "";

    render(await AuthPage());

    expect(screen.getAllByText(/oidc issuer must be a valid absolute http\(s\) url/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /sign in with oidc provider/i })).toBeDisabled();
  });

  it("disables interactive auth actions when redirect URLs do not match the configured issuer", async () => {
    getOperatorSessionMock.mockResolvedValue({
      ...anonymousSession,
      auth_mode: "oidc",
      provider: "oidc",
      oidc: {
        configured: true,
        issuer: "https://issuer.example.com",
        audience: "",
        provider: "oidc",
        validation_error: "",
        browser_flow_configured: true,
        browser_flow_error: "",
      },
    });
    process.env.FRONTIER_AUTH_OIDC_SIGNIN_URL = "https://evil.example.com/login";
    process.env.FRONTIER_AUTH_OIDC_SIGNUP_URL = "https://issuer.example.com/signup";

    render(await AuthPage());

    expect(screen.getAllByText(/sign-in url must belong to the configured oidc issuer origin/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /sign in with oidc provider/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /create account/i })).toBeDisabled();
  });

  it("explains shared-token fallback when interactive login is disabled", async () => {
    getOperatorSessionMock.mockResolvedValue(anonymousSession);

    render(await AuthPage());

    expect(screen.getByText(/shared operator token/i)).toBeInTheDocument();
    expect(screen.getAllByText(/using the shared-token fallback/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /sign in with oidc provider/i })).toBeDisabled();
  });

  it("does not offer a direct console bypass link", async () => {
    getOperatorSessionMock.mockResolvedValue({
      ...anonymousSession,
      auth_mode: "oidc",
      provider: "casdoor",
      oidc: {
        configured: true,
        issuer: "http://127.0.0.1:8081",
        audience: "",
        provider: "casdoor",
        validation_error: "",
        browser_flow_configured: true,
        browser_flow_error: "",
      },
    });
    process.env.FRONTIER_AUTH_OIDC_SIGNIN_URL = "http://127.0.0.1:8081/login/oauth/authorize";
    process.env.FRONTIER_AUTH_OIDC_SIGNUP_URL = "http://127.0.0.1:8081/signup";

    render(await AuthPage());

    expect(screen.queryByRole("link", { name: /continue to the console/i })).not.toBeInTheDocument();
  });

  it("offers browser sign-in for non-local oidc issuers once the callback flow is configured", async () => {
    getOperatorSessionMock.mockResolvedValue({
      ...anonymousSession,
      auth_mode: "oidc",
      provider: "oidc",
      oidc: {
        configured: true,
        issuer: "https://issuer.example.com",
        audience: "",
        provider: "oidc",
        validation_error: "",
        browser_flow_configured: true,
        browser_flow_error: "",
      },
    });
    process.env.FRONTIER_AUTH_OIDC_SIGNIN_URL = "https://issuer.example.com/login";
    process.env.FRONTIER_AUTH_OIDC_SIGNUP_URL = "https://issuer.example.com/signup";

    render(await AuthPage());

    expect(screen.getByRole("link", { name: /sign in with oidc provider/i })).toHaveAttribute(
      "href",
      "/api/auth/oidc/start?intent=signin",
    );
    expect(screen.getByRole("link", { name: /create account/i })).toHaveAttribute(
      "href",
      "/api/auth/oidc/start?intent=signup",
    );
    expect(screen.getByText(/start browser sign-in and finish the callback flow in xfrontier/i)).toBeInTheDocument();
  });

  it("surfaces backend oidc validation errors from auth session", async () => {
    getOperatorSessionMock.mockResolvedValue({
      ...anonymousSession,
      auth_mode: "oidc",
      provider: "oidc",
      oidc: {
        configured: false,
        issuer: "https://issuer.example.com",
        audience: "frontier-ui",
        provider: "oidc",
        validation_error: "OIDC configuration is invalid.",
        browser_flow_configured: false,
        browser_flow_error: "OIDC browser sign-in is invalid.",
      },
    });
    process.env.FRONTIER_AUTH_OIDC_SIGNIN_URL = "https://issuer.example.com/login";
    process.env.FRONTIER_AUTH_OIDC_SIGNUP_URL = "https://issuer.example.com/signup";

    render(await AuthPage());

    expect(screen.getAllByText(/oidc configuration is invalid/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /sign in with oidc provider/i })).toBeDisabled();
  });

  it("surfaces callback errors returned to the auth page", async () => {
    getOperatorSessionMock.mockResolvedValue(anonymousSession);

    render(await AuthPage({ searchParams: { error: "Unable to complete browser sign-in." } }));

    expect(screen.getByText(/unable to complete browser sign-in/i)).toBeInTheDocument();
  });
});
