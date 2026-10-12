const DEFAULT_MAX_MB = 5;
const ALLOWED_TYPES = new Set(["application/pdf", "application/x-pdf", "application/octet-stream", ""]);

export function maxUploadBytes(): number {
  const configured = Number(import.meta.env.VITE_MAX_UPLOAD_MB);
  const mb = Number.isFinite(configured) && configured > 0 ? configured : DEFAULT_MAX_MB;
  return Math.round(mb * 1024 * 1024);
}

/**
 * Quick client-side checks for a better experience. The server repeats every
 * check (and inspects the file content), so this is never the security boundary.
 */
export function validatePdfFile(file: File, maxBytes: number = maxUploadBytes()): string | null {
  if (!file.name.toLowerCase().endsWith(".pdf")) return "Only PDF files (.pdf) can be uploaded.";
  if (!ALLOWED_TYPES.has(file.type)) return "This file doesn't look like a PDF.";
  if (file.size === 0) return "The file is empty.";
  if (file.size > maxBytes) {
    return `The file is ${(file.size / (1024 * 1024)).toFixed(1)} MB; the limit is ${(maxBytes / (1024 * 1024)).toFixed(1)} MB.`;
  }
  return null;
}
