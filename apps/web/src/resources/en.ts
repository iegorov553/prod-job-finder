export const copy = {
  common: {
    empty: "-",
    yes: "Yes",
    no: "No",
    all: "All",
    untitled: "vacancy",
    timePlaceholder: "HH:MM"
  },
  appName: "Job Finder Control",
  nav: {
    dashboard: "Run & Vacancies",
    settings: "Settings"
  },
  run: {
    title: "Run Pipeline",
    start: "Start run",
    running: "Running",
    success: "Success",
    failed: "Failed",
    idle: "Idle",
    lastRun: "Last run",
    noRuns: "No runs yet",
    errorLabel: "Error",
    digestLabel: "Digest preview",
    runInProgress: "A run is already in progress."
  },
  runs: {
    title: "Run History",
    empty: "No runs yet",
    columns: {
      status: "Status",
      started: "Started",
      finished: "Finished"
    }
  },
  vacancies: {
    title: "Vacancies",
    empty: "No vacancies found.",
    filters: {
      status: "Status",
      relevant: "Relevant only",
      query: "Search"
    },
    columns: {
      title: "Title",
      company: "Company",
      status: "Status",
      relevant: "Relevant",
      source: "Source"
    },
    aria: {
      statusFor: "Status for {title}"
    },
    statusOptions: {
      new: "New",
      saved: "Saved",
      applied: "Applied",
      interview: "Interview",
      rejected: "Rejected",
      offer: "Offer"
    }
  },
  settings: {
    title: "Settings",
    description: "Manage channels, scheduler, and LLM configuration.",
    missing: "Settings not found.",
    save: "Save settings",
    sections: {
      channels: "Channels",
      scheduler: "Scheduler",
      llm: "LLM",
      limits: "Limits",
      prompt: "Custom prompt",
      jobspy: "JobSpy (Job Boards)"
    },
    fields: {
      channels: "Channels (comma-separated)",
      schedulerEnabled: "Scheduler enabled",
      schedulerTimeUtc: "Scheduler time (UTC, HH:MM)",
      llmModel: "Model name",
      llmTemperature: "Temperature",
      llmTimeout: "Timeout (seconds)",
      llmRetryMax: "Retry max",
      llmRetryBackoff: "Retry backoff",
      maxPostsPerBatch: "Max posts per batch",
      maxPostsPerRun: "Max posts per run",
      hoursLookback: "Hours lookback",
      customPrompt: "Custom prompt",
      jobspyEnabled: "JobSpy enabled",
      jobspySites: "Sites (comma-separated: linkedin, indeed, glassdoor, google)",
      jobspySearchTerms: "Search terms (comma-separated)",
      jobspyLocation: "Location",
      jobspyCountry: "Country code",
      jobspyResultsWanted: "Results per search",
      jobspyHoursOld: "Max age (hours)",
      jobspyJobType: "Job type (fulltime, parttime, contract, internship)",
      jobspyIsRemote: "Remote only"
    }
  },
  actions: {
    refresh: "Refresh",
    saving: "Saving..."
  },
  errors: {
    invalidPayload: "Invalid payload",
    requestFailed: "Request failed"
  }
};
