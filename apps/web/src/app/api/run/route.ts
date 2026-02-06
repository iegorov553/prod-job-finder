import { NextResponse } from "next/server";

import { copy } from "@/resources/en";
import { getRunApiEnv } from "@/lib/env";

export const dynamic = "force-dynamic";

export async function POST() {
  const runEnv = getRunApiEnv();
  const response = await fetch(`${runEnv.runApiBaseUrl}/api/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${runEnv.runApiToken}`
    }
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    return NextResponse.json(
      data ?? { error: copy.errors.requestFailed },
      { status: response.status }
    );
  }

  return NextResponse.json(data);
}
