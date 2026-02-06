import { NextResponse } from "next/server";

import { copy } from "@/resources/en";
import { getSupabaseServer } from "@/lib/supabaseServer";
import { VacancyStatus } from "@/lib/types";

export const dynamic = "force-dynamic";

const validStatuses: VacancyStatus[] = [
  "new",
  "saved",
  "applied",
  "interview",
  "rejected",
  "offer"
];

export async function PATCH(
  request: Request,
  { params }: { params: { id: string } }
) {
  const supabaseServer = getSupabaseServer();
  const vacancyId = Number(params.id);
  if (!Number.isFinite(vacancyId)) {
    return NextResponse.json({ error: copy.errors.invalidPayload }, { status: 400 });
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error: copy.errors.invalidPayload }, { status: 400 });
  }

  if (!payload || typeof payload !== "object") {
    return NextResponse.json({ error: copy.errors.invalidPayload }, { status: 400 });
  }

  const data = payload as Record<string, unknown>;
  const status = typeof data.status === "string" ? data.status : null;
  const notes = typeof data.notes === "string" ? data.notes : null;

  if (status && !validStatuses.includes(status as VacancyStatus)) {
    return NextResponse.json({ error: copy.errors.invalidPayload }, { status: 400 });
  }

  const update: Record<string, unknown> = {};
  if (status) {
    update.status = status;
  }
  if (notes !== null) {
    update.notes = notes;
  }

  if (!Object.keys(update).length) {
    return NextResponse.json({ error: copy.errors.invalidPayload }, { status: 400 });
  }

  const { data: updated, error } = await supabaseServer
    .from("vacancies")
    .update(update)
    .eq("id", vacancyId)
    .select("*")
    .single();

  if (error) {
    return NextResponse.json({ error: copy.errors.requestFailed }, { status: 500 });
  }

  return NextResponse.json(updated);
}
