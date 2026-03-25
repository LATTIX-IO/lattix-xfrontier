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
    getOperatorSessionMock.mockResolvedValue({
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
    });

    render(<AppShell><div>builder child</div></AppShell>);

    expect(await screen.findByText(/workflow studio/i)).toBeInTheDocument();
    expect(screen.getByText(/builder child/i)).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});