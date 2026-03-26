import { describe, expect, it, vi } from "vitest";

const redirectMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
}));

import Home from "@/app/page";

describe("Home", () => {
  it("redirects first-time visitors to the auth entry point", () => {
    Home();

    expect(redirectMock).toHaveBeenCalledWith("/auth");
  });
});