import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { toApiError } from "../services/api";

/**
 * Map an API validation error onto react-hook-form fields. Returns a message
 * for errors that don't belong to a visible field (non_field_errors, network…).
 */
export function applyServerErrors<T extends FieldValues>(
  err: unknown,
  setError: UseFormSetError<T>,
  fields: readonly Path<T>[],
): string | null {
  const apiError = toApiError(err);
  let unplaced: string | null = null;
  const known = new Set<string>(fields);
  for (const [field, errors] of Object.entries(apiError.fields)) {
    const message = errors.map((e) => e.message).join(" ");
    if (known.has(field)) {
      setError(field as Path<T>, { type: "server", message });
    } else if (!unplaced) {
      unplaced = message;
    }
  }
  if (Object.keys(apiError.fields).length === 0) return apiError.message;
  return unplaced;
}
