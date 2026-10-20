import type { NextRequest } from "next/server";

import { fetchPost } from "@/lib/bluesky/service";

import { errorResponse } from "../../respond";

export async function GET(request: NextRequest) {
  try {
    return Response.json(await fetchPost(request.nextUrl.searchParams.get("link") ?? ""));
  } catch (error) {
    return errorResponse(error);
  }
}
