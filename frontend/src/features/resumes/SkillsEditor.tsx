import { useState, type FormEvent } from "react";

import { Button } from "../../components/ui/Button";
import { Alert, Card } from "../../components/ui/Feedback";
import { TextField } from "../../components/ui/Field";
import { toApiError } from "../../services/api";
import { addSkill, deleteSkill, updateSkill } from "../../services/resumes";
import type { ResumeSkill } from "../../types/api";
import { SourceBadge } from "./SourceBadge";

const SECTION_LABELS: Record<string, string> = {
  skills: "Skills section",
  experience: "Experience",
  projects: "Projects",
  certifications: "Certifications",
  summary: "Summary",
  education: "Education",
  header: "Resume header",
};

interface SkillsEditorProps {
  resumeId: string;
  skills: ResumeSkill[];
  onChange: (skills: ResumeSkill[]) => void;
}

export function SkillsEditor({ resumeId, skills, onChange }: SkillsEditorProps) {
  const [newSkill, setNewSkill] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | "new" | null>(null);

  const unconfirmed = skills.filter((s) => s.source === "parser" && !s.is_verified);

  async function run(id: number | "new", action: () => Promise<void>) {
    setError(null);
    setBusyId(id);
    try {
      await action();
    } catch (err) {
      const apiError = toApiError(err);
      setError(apiError.fieldMessage("name") ?? apiError.message);
    } finally {
      setBusyId(null);
    }
  }

  function handleAdd(event: FormEvent) {
    event.preventDefault();
    const name = newSkill.trim();
    if (!name) return;
    void run("new", async () => {
      const created = await addSkill(resumeId, name);
      onChange([...skills, created]);
      setNewSkill("");
    });
  }

  function confirmSkill(skill: ResumeSkill) {
    void run(skill.id, async () => {
      const updated = await updateSkill(resumeId, skill.id, { is_verified: true });
      onChange(skills.map((s) => (s.id === skill.id ? updated : s)));
    });
  }

  function confirmAll() {
    void run("new", async () => {
      const updated = await Promise.all(unconfirmed.map((s) => updateSkill(resumeId, s.id, { is_verified: true })));
      const byId = new Map(updated.map((s) => [s.id, s]));
      onChange(skills.map((s) => byId.get(s.id) ?? s));
    });
  }

  function removeSkill(skill: ResumeSkill) {
    if (!window.confirm(`Remove "${skill.name}" from this resume?`)) return;
    void run(skill.id, async () => {
      await deleteSkill(resumeId, skill.id);
      onChange(skills.filter((s) => s.id !== skill.id));
    });
  }

  return (
    <Card
      title={`Skills (${skills.length})`}
      actions={
        unconfirmed.length > 1 ? (
          <Button size="sm" variant="secondary" onClick={confirmAll} loading={busyId === "new"}>
            Confirm all {unconfirmed.length} detected
          </Button>
        ) : undefined
      }
    >
      {error && (
        <div className="mb-4">
          <Alert tone="error">{error}</Alert>
        </div>
      )}
      {skills.length === 0 ? (
        <p className="text-sm text-slate-600">No skills yet. Add the skills you've actually used below.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {skills.map((skill) => (
            <li key={skill.id} className="flex flex-wrap items-start justify-between gap-3 py-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-900">{skill.name}</span>
                  <SourceBadge source={skill.source} verified={skill.is_verified} />
                  {!skill.canonical && <span className="text-xs text-slate-500">(not in skills dictionary)</span>}
                </div>
                {skill.evidence && (
                  <p className="mt-1 text-xs text-slate-500">
                    Found in {SECTION_LABELS[skill.section] ?? skill.section}: <q className="text-slate-700">{skill.evidence}</q>
                  </p>
                )}
              </div>
              <div className="flex gap-2">
                {skill.source === "parser" && !skill.is_verified && (
                  <Button size="sm" variant="secondary" onClick={() => confirmSkill(skill)} loading={busyId === skill.id} aria-label={`Confirm ${skill.name}`}>
                    Confirm
                  </Button>
                )}
                <Button size="sm" variant="ghost" onClick={() => removeSkill(skill)} disabled={busyId === skill.id} aria-label={`Remove ${skill.name}`}>
                  Remove
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={handleAdd} className="mt-4 flex flex-wrap items-end gap-2 border-t border-slate-100 pt-4">
        <div className="min-w-[12rem] flex-1">
          <TextField
            label="Add a skill"
            hint="Aliases are normalised, e.g. 'JS' becomes JavaScript."
            value={newSkill}
            maxLength={100}
            onChange={(e) => setNewSkill(e.target.value)}
          />
        </div>
        <Button type="submit" disabled={!newSkill.trim()} loading={busyId === "new" && !!newSkill}>
          Add skill
        </Button>
      </form>
    </Card>
  );
}
