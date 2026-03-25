import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

const replaceMock = vi.fn();

const {
  getOperatorSessionMock,
  pathnameState,
} = vi.hoisted(() => ({
  getOperatorSessionMock: vi.fn(),
  pathnameState: { current: "/inbox" },
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: ReactNode; href: string }) => <a href={href} {...props}>{children}</a>,
}));

vi.mock("next/navigation", () => ({
  usePathname: () => pathnameState.current,
  useRouter: () => ({
    replace: replaceMock,
  }),
}));

vi.mock("@/components/api-status-banner", () => ({
  ApiStatusBanner: () => <div data-testid="api-status-banner" />,
}));

vi.mock("@/lib/api", () => ({
  getOperatorSession: getOperatorSessionMock,
}));

import { AppShell } from "@/components/app-shell";

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const guestSession = {
  authenticated: false,
  actor: "guest",
  principal_id: "guest",
  principal_type: "user",
  display_name: "Guest",
  subject: "guest",
  roles: [],
  auth_mode: "jwt",
  provider: "casdoor",
  capabilities: { can_admin: false, can_builder: false },
  allowed_modes: ["user"],
  default_mode: "user",
  oidc: { configured: true, issuer: "http://casdoor.localhost", audience: "frontier-ui", provider: "casdoor", validation_error: "" },
} as const;

const builderSession = {
  authenticated: true,
  actor: "frontier-admin",
  principal_id: "frontier-admin",
  principal_type: "user",
  display_name: "Frontier Admin",
  subject: "frontier-admin",
  roles: ["builder-admin"],
  auth_mode: "oidc",
  provider: "casdoor",
  capabilities: { can_admin: true, can_builder: true },
  allowed_modes: ["user", "builder"],
  default_mode: "builder",
  oidc: { configured: true, issuer: "http://casdoor.localhost", audience: "frontier-ui", provider: "casdoor", validation_error: "" },
} as const;

describe("AppShell", () => {
  it("redirects authenticated non-builders away from builder routes", async () => {
    pathnameState.current = "/builder/workflows";
    replaceMock.mockReset();
    getOperatorSessionMock.mockResolvedValue({
      authenticated: true,
      actor: "member-user",
      principal_id: "member-user",
      principal_type: "user",
      display_name: "Member User",
      subject: "member-user",
      roles: ["member"],
      auth_mode: "jwt",
      provider: "casdoor",
      capabilities: { can_admin: false, can_builder: false },
      allowed_modes: ["user"],
      default_mode: "user",
      oidc: { configured: true, issuer: "http://casdoor.localhost", audience: "frontier-ui", provider: "casdoor", validation_error: "" },
    });

    render(<AppShell><div>builder child</div></AppShell>);

    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/inbox"));
  });

  it("shows builder navigation when the operator session allows builder mode", async () => {
    pathnameState.current = "/builder/workflows";
    replaceMock.mockReset();
    getOperatorSessionMock.mockResolvedValue(builderSession);

    render(<AppShell><div>builder child</div></AppShell>);

    expect(await screen.findByText(/workflow studio/i)).toBeInTheDocument();
    expect(screen.getByText(/builder child/i)).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("does not let a stale session request resolve a later navigation", async () => {
    pathnameState.current = "/builder/workflows";
    replaceMock.mockReset();

    const firstRequest = deferred<typeof guestSession>();
    const secondRequest = deferred<typeof builderSession>();

    getOperatorSessionMock
      .mockImplementationOnce(() => firstRequest.promise)
      .mockImplementationOnce(() => secondRequest.promise);

    const view = render(<AppShell><div>builder child</div></AppShell>);

    pathnameState.current = "/builder/agents";
    view.rerender(<AppShell><div>builder child</div></AppShell>);

    secondRequest.resolve(builderSession);

    expect(await screen.findByText(/agent studio/i)).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();

    firstRequest.resolve(guestSession);

    await waitFor(() => expect(replaceMock).not.toHaveBeenCalled());
  });
});
