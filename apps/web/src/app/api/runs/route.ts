import { NextResponse } from "next/server";

import { copy } from "@/resources/en";
import { supabaseServer } from "@/lib/supabaseServer";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limitRaw = Number(searchParams.get("limit") ?? 10);
  const limit = Number.isFinite(limitRaw) ? limitRaw : 10;

  const { data, error } = await supabaseServer
    .from("runs")
    .select("*")
    .order("started_at", { ascending: false })
    .limit(Math.max(limit, 1));

  if (error) {
    return NextResponse.json({ error: copy.errors.requestFailed }, { status: 500 });
  }

  return NextResponse.json(data ?? []);
}
