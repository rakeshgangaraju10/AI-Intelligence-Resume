interface SpinnerProps {
  size?: "sm" | "md";
  /** Screen-reader text; pass "" when a visible label already exists. */
  label?: string;
}

export function Spinner({ size = "md", label = "Loading" }: SpinnerProps) {
  const dimension = size === "sm" ? "h-4 w-4" : "h-6 w-6";
  return (
    <span role={label ? "status" : undefined} className="inline-flex items-center">
      <span className={`${dimension} animate-spin rounded-full border-2 border-current border-t-transparent`} aria-hidden="true" />
      {label && <span className="sr-only">{label}</span>}
    </span>
  );
}

export function PageSpinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex justify-center py-16 text-indigo-700">
      <Spinner label={label} />
    </div>
  );
}
