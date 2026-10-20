import type { NextRequest } from "next/server";

import { fetchFeedPage } from "@/lib/bluesky/service";

import { errorResponse } from "../../respond";

export async function GET(request: NextRequest) {
  try {
    return Response.json(await fetchFeedPage(request.nextUrl.searchParams.get("cursor")));
  } catch (error) {
    return errorResponse(error);
  }
}
