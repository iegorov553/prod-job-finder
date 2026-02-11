import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_COOKIE_NAME = "staging_auth";
const AUTH_SECRET = process.env.STAGING_PASSWORD || "default_staging_pass";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { password } = body;

    if (!password) {
      return NextResponse.json(
        { error: "Password is required" },
        { status: 400 }
      );
    }

    if (password !== AUTH_SECRET) {
      return NextResponse.json({ error: "Invalid password" }, { status: 401 });
    }

    // Create response with auth cookie
    const response = NextResponse.json({ success: true });

    // Set cookie with the password as value
    response.cookies.set({
      name: AUTH_COOKIE_NAME,
      value: AUTH_SECRET,
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 7 // 7 days
    });

    return response;
  } catch (error) {
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
