import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "../../components/ui/Button";
import { Alert, Card } from "../../components/ui/Feedback";
import { TextArea, TextField } from "../../components/ui/Field";
import { applyServerErrors } from "../../lib/forms";
import { addEntry, deleteEntry, updateEntry, type EntryPayload, type SectionEntry } from "../../services/resumes";
import { toApiError } from "../../services/api";
import type { ResumeSection } from "../../types/api";
import { SourceBadge } from "./SourceBadge";

export interface FieldConfig {
  name: string;
  label: string;
  type?: "text" | "textarea" | "checkbox" | "list";
  maxLength?: number;
  hint?: string;
  /** Spans both columns in the form grid. */
  wide?: boolean;
}

export interface SectionConfig {
  section: ResumeSection;
  title: string;
  addLabel: string;
  emptyText: string;
  fields: FieldConfig[];
  heading: (entry: SectionEntry) => string;
  subheading: (entry: SectionEntry) => string;
  /** Client-side check mirroring the backend rule; returns an error or null. */
  validate?: (values: EntryPayload) => string | null;
}

type FormValues = Record<string, string | boolean>;

function readField(entry: SectionEntry, name: string): unknown {
  return (entry as unknown as Record<string, unknown>)[name];
}

function descriptionOf(entry: SectionEntry): string {
  const value = readField(entry, "description");
  return typeof value === "string" ? value : "";
}

function toFormValues(config: SectionConfig, entry: SectionEntry | null): FormValues {
  const values: FormValues = {};
  for (const field of config.fields) {
    const raw = entry ? readField(entry, field.name) : undefined;
    if (field.type === "checkbox") values[field.name] = Boolean(raw);
    else if (field.type === "list") values[field.name] = Array.isArray(raw) ? raw.join(", ") : "";
    else values[field.name] = typeof raw === "string" ? raw : "";
  }
  return values;
}

function toPayload(config: SectionConfig, values: FormValues): EntryPayload {
  const payload: EntryPayload = {};
  for (const field of config.fields) {
    const value = values[field.name];
    if (field.type === "checkbox") payload[field.name] = Boolean(value);
    else if (field.type === "list")
      payload[field.name] = String(value ?? "")
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean);
    else payload[field.name] = String(value ?? "").trim();
  }
  return payload;
}

interface EntryFormProps {
  config: SectionConfig;
  entry: SectionEntry | null;
  onSubmit: (payload: EntryPayload) => Promise<void>;
  onCancel: () => void;
}

function EntryForm({ config, entry, onSubmit, onCancel }: EntryFormProps) {
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ defaultValues: toFormValues(config, entry) });

  async function submit(values: FormValues) {
    setFormError(null);
    const payload = toPayload(config, values);
    const clientError = config.validate?.(payload);
    if (clientError) {
      setFormError(clientError);
      return;
    }
    try {
      await onSubmit(payload);
    } catch (err) {
      setFormError(applyServerErrors(err, setError, config.fields.map((f) => f.name)));
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} noValidate className="space-y-4 rounded-md border border-indigo-200 bg-indigo-50/40 p-4">
      {formError && <Alert tone="error">{formError}</Alert>}
      <div className="grid gap-4 sm:grid-cols-2">
        {config.fields.map((field) => {
          const error = errors[field.name]?.message;
          const rules = field.maxLength
            ? { maxLength: { value: field.maxLength, message: `Use ${field.maxLength} characters or fewer.` } }
            : {};
          const span = field.wide || field.type === "textarea" ? "sm:col-span-2" : "";
          if (field.type === "checkbox") {
            return (
              <label key={field.name} className={`flex items-center gap-2 text-sm text-slate-800 ${span}`}>
                <input type="checkbox" className="h-4 w-4 rounded border-slate-300" {...register(field.name)} />
                {field.label}
              </label>
            );
          }
          if (field.type === "textarea") {
            return (
              <div key={field.name} className={span}>
                <TextArea label={field.label} hint={field.hint} rows={4} error={typeof error === "string" ? error : undefined} {...register(field.name, rules)} />
              </div>
            );
          }
          return (
            <div key={field.name} className={span}>
              <TextField label={field.label} hint={field.hint} error={typeof error === "string" ? error : undefined} {...register(field.name, rules)} />
            </div>
          );
        })}
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={isSubmitting}>
          Save
        </Button>
      </div>
    </form>
  );
}

interface EntrySectionEditorProps<T extends SectionEntry> {
  resumeId: string;
  config: SectionConfig;
  entries: T[];
  onChange: (entries: T[]) => void;
}

export function EntrySectionEditor<T extends SectionEntry>({ resumeId, config, entries, onChange }: EntrySectionEditorProps<T>) {
  const [editingId, setEditingId] = useState<number | "new" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function create(payload: EntryPayload) {
    const created = await addEntry<T>(resumeId, config.section, payload);
    onChange([...entries, created]);
    setEditingId(null);
  }

  async function save(entry: T, payload: EntryPayload) {
    const updated = await updateEntry<T>(resumeId, config.section, entry.id, payload);
    onChange(entries.map((e) => (e.id === entry.id ? updated : e)));
    setEditingId(null);
  }

  async function act(entry: T, action: () => Promise<void>) {
    setError(null);
    setBusyId(entry.id);
    try {
      await action();
    } catch (err) {
      setError(toApiError(err).message);
    } finally {
      setBusyId(null);
    }
  }

  function confirm(entry: T) {
    void act(entry, async () => {
      const updated = await updateEntry<T>(resumeId, config.section, entry.id, { is_verified: true });
      onChange(entries.map((e) => (e.id === entry.id ? updated : e)));
    });
  }

  function remove(entry: T) {
    if (!window.confirm(`Delete "${config.heading(entry) || "this entry"}"?`)) return;
    void act(entry, async () => {
      await deleteEntry(resumeId, config.section, entry.id);
      onChange(entries.filter((e) => e.id !== entry.id));
    });
  }

  return (
    <Card
      title={`${config.title} (${entries.length})`}
      actions={
        editingId !== "new" ? (
          <Button size="sm" variant="secondary" onClick={() => setEditingId("new")}>
            {config.addLabel}
          </Button>
        ) : undefined
      }
    >
      {error && (
        <div className="mb-4">
          <Alert tone="error">{error}</Alert>
        </div>
      )}
      {editingId === "new" && (
        <div className="mb-4">
          <EntryForm config={config} entry={null} onSubmit={create} onCancel={() => setEditingId(null)} />
        </div>
      )}
      {entries.length === 0 && editingId !== "new" ? (
        <p className="text-sm text-slate-600">{config.emptyText}</p>
      ) : (
        <ul className="space-y-3">
          {entries.map((entry) => (
            <li key={entry.id}>
              {editingId === entry.id ? (
                <EntryForm config={config} entry={entry} onSubmit={(payload) => save(entry, payload)} onCancel={() => setEditingId(null)} />
              ) : (
                <div className="flex flex-wrap items-start justify-between gap-3 rounded-md border border-slate-200 p-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-medium text-slate-900">{config.heading(entry) || <span className="italic text-slate-400">Untitled</span>}</h3>
                      <SourceBadge source={entry.source} verified={entry.is_verified} />
                    </div>
                    {config.subheading(entry) && <p className="mt-1 text-sm text-slate-600">{config.subheading(entry)}</p>}
                    {descriptionOf(entry) && (
                      <p className="mt-2 whitespace-pre-line text-sm text-slate-700">{descriptionOf(entry)}</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {entry.source === "parser" && !entry.is_verified && (
                      <Button size="sm" variant="secondary" onClick={() => confirm(entry)} loading={busyId === entry.id}>
                        Confirm
                      </Button>
                    )}
                    <Button size="sm" variant="secondary" onClick={() => setEditingId(entry.id)}>
                      Edit
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => remove(entry)} disabled={busyId === entry.id}>
                      Delete
                    </Button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
