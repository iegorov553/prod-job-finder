"use client";

import { useState } from "react";

import { copy } from "@/resources/en";
import { SettingsRecord, SettingsUpdatePayload } from "@/lib/types";
import { SettingsForm } from "@/components/SettingsForm";

export type SettingsPageProps = {
  initialSettings: SettingsRecord;
};

export const SettingsPage = ({ initialSettings }: SettingsPageProps) => {
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async (payload: SettingsUpdatePayload) => {
    setIsSaving(true);
    setError(null);
    try {
      const response = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        setError(copy.errors.requestFailed);
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="settings-page">
      {error ? <p className="error-text">{error}</p> : null}
      <SettingsForm
        initialSettings={initialSettings}
        onSave={handleSave}
        isSaving={isSaving}
      />
    </div>
  );
};
