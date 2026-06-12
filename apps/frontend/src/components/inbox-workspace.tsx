"use client";

import { TaskKickoffComposer } from "@/components/task-kickoff-composer";

export function InboxWorkspace() {
  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Inbox</h1>
        <p className="fx-muted text-sm">
          Your chats live in the left nav under <span className="text-[var(--foreground)]">Chats</span> —
          grouped, foldered, and right-clickable for edit actions. Kick off a new task below.
        </p>
      </header>

      <TaskKickoffComposer />

      <p className="fx-muted text-xs">
        Select a chat from the nav to open it, or start a new task above.
      </p>
    </section>
  );
}
