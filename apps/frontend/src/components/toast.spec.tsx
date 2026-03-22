import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ToastProvider, useToast } from "@/components/toast";

function TestConsumer() {
  const { addToast, removeToast } = useToast();
  return (
    <div>
      <button onClick={() => addToast("error", "Something broke")}>Add Error</button>
      <button onClick={() => addToast("success", "Saved!")}>Add Success</button>
      <button onClick={() => {
        const id = addToast("info", "Persistent note", { persistent: true });
        (window as unknown as Record<string, string>).__lastToastId = id;
      }}>Add Persistent</button>
      <button onClick={() => removeToast((window as unknown as Record<string, string>).__lastToastId)}>Remove</button>
    </div>
  );
}

describe("ToastProvider", () => {
  it("renders toast when addToast is called", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByText("Add Error"));

    expect(screen.getByText("Something broke")).toBeTruthy();
    expect(screen.getByRole("alert")).toBeTruthy();
  });

  it("can render multiple toasts", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByText("Add Error"));
    fireEvent.click(screen.getByText("Add Success"));

    expect(screen.getByText("Something broke")).toBeTruthy();
    expect(screen.getByText("Saved!")).toBeTruthy();
  });

  it("removes toast when dismiss button is clicked", async () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByText("Add Error"));
    expect(screen.getByText("Something broke")).toBeTruthy();

    fireEvent.click(screen.getByLabelText("Dismiss"));

    await waitFor(() => {
      expect(screen.queryByText("Something broke")).toBeNull();
    });
  });

  it("auto-dismisses non-persistent toasts", async () => {
    vi.useFakeTimers();

    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    );

    await act(async () => {
      fireEvent.click(screen.getByText("Add Success"));
    });
    expect(screen.getByText("Saved!")).toBeTruthy();

    await act(async () => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.queryByText("Saved!")).toBeNull();

    vi.useRealTimers();
  });

  it("does not auto-dismiss persistent toasts", async () => {
    vi.useFakeTimers();

    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    );

    await act(async () => {
      fireEvent.click(screen.getByText("Add Persistent"));
    });
    expect(screen.getByText("Persistent note")).toBeTruthy();

    await act(async () => {
      vi.advanceTimersByTime(30000);
    });

    // Still visible
    expect(screen.getByText("Persistent note")).toBeTruthy();

    vi.useRealTimers();
  });

  it("throws when useToast is used outside provider", () => {
    function BadConsumer() {
      useToast();
      return null;
    }

    expect(() => render(<BadConsumer />)).toThrow(/ToastProvider/);
  });
});
