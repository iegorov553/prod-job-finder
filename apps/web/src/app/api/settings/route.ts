import { NextResponse } from "next/server";

import { copy } from "@/resources/en";
import { getSupabaseServer } from "@/lib/supabaseServer";
import { parseSettingsUpdate } from "@/lib/validators";

export const dynamic = "force-dynamic";

export async function GET() {
  const supabaseServer = getSupabaseServer();
  const { data, error } = await supabaseServer
    .from("settings")
    .select("*")
    .limit(1);

  if (error) {
    return NextResponse.json({ error: copy.errors.requestFailed }, { status: 500 });
  }

  return NextResponse.json(data?.[0] ?? null);
}

export async function PUT(request: Request) {
  const supabaseServer = getSupabaseServer();
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error: copy.errors.invalidPayload }, { status: 400 });
  }

  let update;
  try {
    update = parseSettingsUpdate(payload);
  } catch {
    return NextResponse.json({ error: copy.errors.invalidPayload }, { status: 400 });
  }

  const { data: existing, error: selectError } = await supabaseServer
    .from("settings")
    .select("id")
    .limit(1);

  if (selectError || !existing?.[0]) {
    return NextResponse.json({ error: copy.errors.requestFailed }, { status: 500 });
  }

  const { data, error } = await supabaseServer
    .from("settings")
    .update(update)
    .eq("id", existing[0].id)
    .select("*")
    .single();

  if (error) {
    return NextResponse.json({ error: copy.errors.requestFailed }, { status: 500 });
  }

  return NextResponse.json(data);
}
