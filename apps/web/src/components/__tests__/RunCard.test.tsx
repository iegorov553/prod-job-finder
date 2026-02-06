import React from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RunCard } from "../RunCard";
import { copy } from "@/resources/en";

const defaultRun = {
  id: 1,
  status: "success" as const,
  started_at: "2026-02-04T10:00:00Z",
  finished_at: "2026-02-04T10:05:00Z",
  error: null,
  digest_md: "Digest",
  created_at: "2026-02-04T10:00:00Z",
};

describe("RunCard", () => {
  it("triggers onStart when button clicked", async () => {
    const onStart = vi.fn();
    const user = userEvent.setup();
    render(
      <RunCard
        lastRun={defaultRun}
        isRunning={false}
        onStart={onStart}
        disabled={false}
      />
    );

    await user.click(
      screen.getByRole("button", { name: copy.run.start })
    );

    expect(onStart).toHaveBeenCalledTimes(1);
  });

  it("disables button when running", () => {
    const onStart = vi.fn();
    render(
      <RunCard
        lastRun={{ ...defaultRun, status: "running" }}
        isRunning={true}
        onStart={onStart}
        disabled={true}
      />
    );

    const button = screen.getByRole("button", { name: copy.run.start });
    expect(button).toBeDisabled();
  });
});
