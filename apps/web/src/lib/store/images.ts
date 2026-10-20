import { inMemoryImageUrl, isInMemoryImage } from "../models/verification-case";

/** Uploaded photos, held as blobs in this tab only; cases refer to them as `memory://upload/{id}`. */
const uploads = new Map<string, { blob: Blob; objectUrl: string }>();

const idOf = (url: string) => url.slice(url.lastIndexOf("/") + 1);

export function keepUpload(id: string, blob: Blob) {
  uploads.set(id, { blob, objectUrl: URL.createObjectURL(blob) });
  return inMemoryImageUrl(id);
}

export const uploadBlob = (url: string) => uploads.get(idOf(url))?.blob ?? null;

/** What an `<img>` can load for a case's image URL, or null when the upload is gone. */
export function imageSrc(url: string | null) {
  if (!url) return null;
  if (!isInMemoryImage(url)) return url;
  return uploads.get(idOf(url))?.objectUrl ?? null;
}

export function dropUpload(url: string | null) {
  if (!url || !isInMemoryImage(url)) return;
  const entry = uploads.get(idOf(url));
  if (entry) URL.revokeObjectURL(entry.objectUrl);
  uploads.delete(idOf(url));
}

export function dropAllUploads() {
  uploads.forEach((entry) => URL.revokeObjectURL(entry.objectUrl));
  uploads.clear();
}

/** Longest edge of photos saved by Keep My Checks, in pixels. */
const SAVED_PHOTO_SIZE = 1024;

/** A small JPEG copy for saving, like the mobile apps keep. */
export async function smallCopy(blob: Blob): Promise<Blob> {
  const bitmap = await createImageBitmap(blob);
  const scale = Math.min(1, SAVED_PHOTO_SIZE / Math.max(bitmap.width, bitmap.height));
  const canvas = new OffscreenCanvas(Math.round(bitmap.width * scale), Math.round(bitmap.height * scale));
  canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return canvas.convertToBlob({ type: "image/jpeg", quality: 0.8 });
}
