import { CheckError, genericCheckError, type CheckErrorCode } from "@/lib/models/errors";

const statusFor: Record<CheckErrorCode, number> = {
  invalidLink: 400,
  postNotFound: 404,
  noImage: 422,
  network: 502,
  unreadablePhoto: 422,
  unsupported: 400,
  tooLarge: 413,
};

/** JSON error body shared by every route: `{ code, error }`, where `error` is user-facing copy. */
export function errorResponse(error: unknown) {
  if (error instanceof CheckError) {
    return Response.json({ code: error.code, error: error.message }, { status: statusFor[error.code] });
  }
  console.error(error);
  return Response.json({ code: "unknown", error: genericCheckError }, { status: 500 });
}
