import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import AuthPage from "@/app/auth/page";

describe("AuthPage", () => {
  const originalEnv = { ...process.env };

  afterEach(() => {
    process.env = { ...originalEnv };
  });

  it("renders Casdoor-backed sign-in and sign-up actions", () => {
    process.env.FRONTIER_AUTH_MODE = "oidc";
    process.env.FRONTIER_AUTH_OIDC_PROVIDER = "casdoor";
    process.env.FRONTIER_AUTH_OIDC_ISSUER = "http://casdoor.localhost";
    process.env.FRONTIER_AUTH_OIDC_AUDIENCE = "frontier-ui";
    process.env.FRONTIER_AUTH_OIDC_CLIENT_ID = "frontier-web";
    process.env.FRONTIER_AUTH_OIDC_SIGNIN_URL = "http://casdoor.localhost/login/oauth/authorize";
    process.env.FRONTIER_AUTH_OIDC_SIGNUP_URL = "http://casdoor.localhost/signup";
    process.env.FRONTIER_AUTH_OIDC_SCOPES = "openid profile email";

    render(<AuthPage />);

    expect(screen.getByRole("heading", { name: /one frontier, whichever iam your team already trusts/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign in with casdoor/i })).toHaveAttribute("href", "http://casdoor.localhost/login/oauth/authorize");
    expect(screen.getByRole("link", { name: /create account/i })).toHaveAttribute("href", "http://casdoor.localhost/signup");
    expect(screen.getByText(/configured against http:\/\/casdoor\.localhost/i)).toBeInTheDocument();
  });

  it("shows setup guidance when oidc is incomplete", () => {
    process.env.FRONTIER_AUTH_MODE = "oidc";
    process.env.FRONTIER_AUTH_OIDC_PROVIDER = "oidc";
    process.env.FRONTIER_AUTH_OIDC_ISSUER = "";
    process.env.FRONTIER_AUTH_OIDC_SIGNIN_URL = "";
    process.env.FRONTIER_AUTH_OIDC_SIGNUP_URL = "";

    render(<AuthPage />);

    expect(screen.getByText(/oidc issuer must be a valid absolute http\(s\) url/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign in with oidc provider/i })).toHaveAttribute("href", "#auth-not-configured");
  });

  it("disables interactive auth actions when redirect URLs do not match the configured issuer", () => {
    process.env.FRONTIER_AUTH_MODE = "oidc";
    process.env.FRONTIER_AUTH_OIDC_PROVIDER = "oidc";
    process.env.FRONTIER_AUTH_OIDC_ISSUER = "https://issuer.example.com";
    process.env.FRONTIER_AUTH_OIDC_SIGNIN_URL = "https://evil.example.com/login";
    process.env.FRONTIER_AUTH_OIDC_SIGNUP_URL = "https://issuer.example.com/signup";

    render(<AuthPage />);

    expect(screen.getByText(/sign-in url must belong to the configured oidc issuer origin/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign in with oidc provider/i })).toHaveAttribute("href", "#auth-not-configured");
    expect(screen.getByRole("link", { name: /create account/i })).toHaveAttribute("href", "#auth-not-configured");
  });

  it("explains shared-token fallback when interactive login is disabled", () => {
    process.env.FRONTIER_AUTH_MODE = "shared-token";
    process.env.FRONTIER_AUTH_OIDC_PROVIDER = "";

    render(<AuthPage />);

    expect(screen.getByText(/shared operator token/i)).toBeInTheDocument();
    expect(screen.getByText(/using the shared-token fallback/i)).toBeInTheDocument();
  });

  it("does not offer a direct console bypass link", () => {
    process.env.FRONTIER_AUTH_MODE = "oidc";
    process.env.FRONTIER_AUTH_OIDC_PROVIDER = "casdoor";
    process.env.FRONTIER_AUTH_OIDC_ISSUER = "http://casdoor.localhost";
    process.env.FRONTIER_AUTH_OIDC_SIGNIN_URL = "http://casdoor.localhost/login/oauth/authorize";
    process.env.FRONTIER_AUTH_OIDC_SIGNUP_URL = "http://casdoor.localhost/signup";

    render(<AuthPage />);

    expect(screen.queryByRole("link", { name: /continue to the console/i })).not.toBeInTheDocument();
  });
});
