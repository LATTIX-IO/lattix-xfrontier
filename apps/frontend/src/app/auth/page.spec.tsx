import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { loginMock, registerMock, getSessionMock, routerReplaceMock, routerRefreshMock } = vi.hoisted(() => ({
  loginMock: vi.fn(),
  registerMock: vi.fn(),
  getSessionMock: vi.fn(),
  routerReplaceMock: vi.fn(),
  routerRefreshMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: routerReplaceMock,
    refresh: routerRefreshMock,
    push: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  loginWithLocalPassword: loginMock,
  registerWithLocalPassword: registerMock,
  getOperatorSession: getSessionMock,
}));

import { LattixAuthCard } from "@/components/auth/lattix-auth-card";

function renderCard(initialErrorCode?: string | null) {
  return render(<LattixAuthCard initialErrorCode={initialErrorCode ?? undefined} />);
}

describe("LattixAuthCard", () => {
  beforeEach(() => {
    loginMock.mockReset();
    registerMock.mockReset();
    getSessionMock.mockReset();
    routerReplaceMock.mockReset();
    routerRefreshMock.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the Lattix sign-in card with email, password, footer, and brand", () => {
    renderCard();

    expect(screen.getAllByText(/lattix/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/secure access/i)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /sign in/i })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /sign up/i })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByLabelText(/^email$/i)).toHaveAttribute("type", "email");
    expect(screen.getByLabelText(/^password$/i)).toHaveAttribute("type", "password");
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeInTheDocument();
    expect(screen.getByText(/encrypted channel/i)).toBeInTheDocument();
    expect(screen.getByText(/lattix technologies corp/i)).toBeInTheDocument();
  });

  it("renders a resolved error message from the auth_error search param", () => {
    renderCard("invalid_credentials");

    expect(
      screen.getByRole("alert"),
    ).toHaveTextContent(/email or password was not accepted/i);
  });

  it("toggles password visibility", () => {
    renderCard();

    const passwordInput = screen.getByLabelText(/^password$/i);
    expect(passwordInput).toHaveAttribute("type", "password");

    fireEvent.click(screen.getByRole("button", { name: /show password/i }));

    expect(passwordInput).toHaveAttribute("type", "text");
  });

  it("submits sign-in through Casdoor-backed /auth/login and routes to the default destination", async () => {
    loginMock.mockResolvedValueOnce({ ok: true, authenticated: true, provider: "casdoor", mode: "oidc" });
    getSessionMock.mockResolvedValueOnce({
      authenticated: true,
      capabilities: { can_builder: false, can_admin: false },
      default_mode: "user",
    });

    renderCard();

    fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: "operator@lattix.io" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "correct-horse" } });
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith({
        username: "operator@lattix.io",
        password: "correct-horse",
      });
    });
    await waitFor(() => expect(routerReplaceMock).toHaveBeenCalledWith("/inbox"));
  });

  it("routes builder-default operators to the builder workflows screen", async () => {
    loginMock.mockResolvedValueOnce({ ok: true, authenticated: true, provider: "casdoor", mode: "oidc" });
    getSessionMock.mockResolvedValueOnce({
      authenticated: true,
      capabilities: { can_builder: true, can_admin: true },
      default_mode: "builder",
    });

    renderCard();

    fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: "builder@lattix.io" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "hunter2hunter" } });
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    await waitFor(() => expect(routerReplaceMock).toHaveBeenCalledWith("/builder/workflows"));
  });

  it("surfaces the server error when credentials are rejected", async () => {
    loginMock.mockRejectedValueOnce(new Error("Request failed (401): Invalid credentials"));

    renderCard();

    fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: "bad@lattix.io" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "nope" } });
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/invalid credentials/i);
    expect(routerReplaceMock).not.toHaveBeenCalled();
  });

  it("falls back to the canonical copy when the server message is missing", async () => {
    loginMock.mockRejectedValueOnce(new Error(""));

    renderCard();

    fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: "bad@lattix.io" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "nope" } });
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/email or password was not accepted/i);
  });

  it("switches to sign-up mode, collects first/last/email/password + confirmation, and posts to /auth/register", async () => {
    registerMock.mockResolvedValueOnce({
      ok: true,
      authenticated: true,
      provider: "casdoor",
      mode: "oidc",
      created: true,
    });
    getSessionMock.mockResolvedValueOnce({
      authenticated: true,
      capabilities: { can_builder: false, can_admin: false },
      default_mode: "user",
    });

    renderCard();

    fireEvent.click(screen.getByRole("tab", { name: /sign up/i }));

    expect(screen.getByRole("tab", { name: /sign up/i })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: "New" } });
    fireEvent.change(screen.getByLabelText(/last name/i), { target: { value: "Operator" } });
    fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: "new@lattix.io" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "fresh-pass" } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: "fresh-pass" } });
    fireEvent.click(screen.getByRole("button", { name: /^create account$/i }));

    await waitFor(() => {
      expect(registerMock).toHaveBeenCalledWith({
        username: "new@lattix.io",
        email: "new@lattix.io",
        display_name: "New Operator",
        password: "fresh-pass",
      });
    });
    await waitFor(() => expect(routerReplaceMock).toHaveBeenCalledWith("/inbox"));
  });

  it("blocks sign-up submission when the password confirmation does not match", async () => {
    renderCard();

    fireEvent.click(screen.getByRole("tab", { name: /sign up/i }));

    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: "A" } });
    fireEvent.change(screen.getByLabelText(/last name/i), { target: { value: "B" } });
    fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: "c@lattix.io" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "one" } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: "two" } });
    fireEvent.click(screen.getByRole("button", { name: /^create account$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/passwords do not match/i);
    expect(registerMock).not.toHaveBeenCalled();
  });
});
