import { useId, useRef, useState, type DragEvent, type KeyboardEvent } from "react";

interface ResumeDropzoneProps {
  onFile: (file: File) => void;
  disabled?: boolean;
  maxLabel: string;
}

/** Drag-and-drop target that is also a keyboard-operable file picker. */
export function ResumeDropzone({ onFile, disabled = false, maxLabel }: ResumeDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const hintId = useId();

  function openPicker() {
    if (!disabled) inputRef.current?.click();
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (disabled) return;
    const file = event.dataTransfer.files?.[0];
    if (file) onFile(file);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openPicker();
    }
  }

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      aria-describedby={hintId}
      onClick={(e) => {
        // The hidden input's own click bubbles up here; don't re-open the picker for it.
        if (e.target !== inputRef.current) openPicker();
      }}
      onKeyDown={handleKeyDown}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-12 text-center transition-colors ${
        dragging ? "border-indigo-600 bg-indigo-50" : "border-slate-300 bg-white hover:border-indigo-400"
      } ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
    >
      <svg aria-hidden="true" className="h-10 w-10 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path d="M12 16V4m0 0l-4 4m4-4l4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
      </svg>
      <p className="mt-3 font-medium text-slate-900">Drag and drop your resume here, or click to choose a file</p>
      <p id={hintId} className="mt-1 text-sm text-slate-500">
        PDF only, up to {maxLabel}. Text-based PDFs work best (scanned images can't be read yet).
      </p>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="sr-only"
        tabIndex={-1}
        data-testid="resume-file-input"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.target.value = ""; // allow re-selecting the same file
        }}
      />
    </div>
  );
}
