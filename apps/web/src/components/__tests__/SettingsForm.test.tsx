import React from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SettingsForm } from "../SettingsForm";
import { copy } from "@/resources/en";

const settings = {
  id: "1",
  channels: ["@a", "@b"],
  scheduler_enabled: true,
  scheduler_time_utc: "09:00",
  llm_model_name: "gpt-4.1-mini",
  llm_temperature: 0.7,
  llm_timeout: 60,
  llm_retry_max: 2,
  llm_retry_backoff: 2.0,
  max_posts_per_batch: 10,
  max_posts_per_run: 30,
  hours_lookback: 24,
  custom_prompt: "Prompt",
  jobspy_enabled: false,
  jobspy_sites: ["indeed", "google"],
  jobspy_search_terms: [],
  jobspy_location: null,
  jobspy_country: "USA",
  jobspy_results_wanted: 20,
  jobspy_hours_old: 24,
  jobspy_job_type: null,
  jobspy_is_remote: null,
};

describe("SettingsForm", () => {
  it("submits updated values", async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<SettingsForm initialSettings={settings} onSave={onSave} />);

    const channelsInput = screen.getByLabelText(copy.settings.fields.channels);
    await user.clear(channelsInput);
    await user.type(channelsInput, "@alpha, @beta");

    await user.click(
      screen.getByRole("button", { name: copy.settings.save })
    );

    expect(onSave).toHaveBeenCalledTimes(1);
    const payload = onSave.mock.calls[0][0];
    expect(payload.channels).toEqual(["@alpha", "@beta"]);
  });
});
