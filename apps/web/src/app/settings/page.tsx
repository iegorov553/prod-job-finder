import { SettingsPage } from "@/components/SettingsPage";
import { copy } from "@/resources/en";
import { fetchSettings } from "@/lib/server/settings";

export const dynamic = "force-dynamic";

export default async function Settings() {
  const settings = await fetchSettings();

  if (!settings) {
    return <p className="error-text">{copy.settings.missing}</p>;
  }

  return <SettingsPage initialSettings={settings} />;
}
