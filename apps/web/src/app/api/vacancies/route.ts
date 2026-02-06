import { NextResponse } from "next/server";

import { copy } from "@/resources/en";
import { supabaseServer } from "@/lib/supabaseServer";

const parseBoolean = (value: string | null): boolean | null => {
  if (value === null) {
    return null;
  }
  if (value === "true") {
    return true;
  }
  if (value === "false") {
    return false;
  }
  return null;
};

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const status = searchParams.get("status");
  const relevant = parseBoolean(searchParams.get("is_relevant"));
  const query = searchParams.get("q");
  const limitRaw = Number(searchParams.get("limit") ?? 50);
  const offsetRaw = Number(searchParams.get("offset") ?? 0);
  const limit = Number.isFinite(limitRaw) ? limitRaw : 50;
  const offset = Number.isFinite(offsetRaw) ? offsetRaw : 0;

  let requestBuilder = supabaseServer.from("vacancies").select("*");

  if (status) {
    requestBuilder = requestBuilder.eq("status", status);
  }
  if (relevant !== null) {
    requestBuilder = requestBuilder.eq("is_relevant", relevant);
  }
  if (query) {
    requestBuilder = requestBuilder.or(
      `title.ilike.%${query}%,company.ilike.%${query}%,location.ilike.%${query}%`
    );
  }

  const { data, error } = await requestBuilder
    .order("created_at", { ascending: false })
    .range(offset, offset + Math.max(limit, 1) - 1);

  if (error) {
    return NextResponse.json({ error: copy.errors.requestFailed }, { status: 500 });
  }

  return NextResponse.json(data ?? []);
}
