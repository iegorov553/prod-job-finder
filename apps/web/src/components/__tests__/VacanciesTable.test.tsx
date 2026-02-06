import React from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { VacanciesTable } from "../VacanciesTable";
import { copy } from "@/resources/en";

const vacancies = [
  {
    id: 1,
    title: "Product Manager",
    company: "Acme",
    status: "new" as const,
    is_relevant: true,
    post_id: 1,
    location: null,
    level: null,
    remote_type: "remote",
    created_at: null
  },
];

describe("VacanciesTable", () => {
  it("calls onStatusChange when status updated", async () => {
    const onStatusChange = vi.fn();
    const user = userEvent.setup();
    render(
      <VacanciesTable vacancies={vacancies} onStatusChange={onStatusChange} />
    );

    await user.selectOptions(
      screen.getByLabelText(
        copy.vacancies.aria.statusFor.replace("{title}", "Product Manager")
      ),
      "applied"
    );

    expect(onStatusChange).toHaveBeenCalledWith(1, "applied");
  });
});
