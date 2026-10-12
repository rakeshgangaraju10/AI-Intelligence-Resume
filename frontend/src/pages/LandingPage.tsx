import { LinkButton } from "../components/ui/Button";
import { useAuth } from "../features/auth/AuthContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

const FEATURES = [
  {
    title: "Structured resume parsing",
    text: "Upload a text-based PDF and get skills, education, experience, projects and certifications as editable sections. Anything detected automatically is marked so you can confirm or correct it.",
  },
  {
    title: "Explainable match score",
    text: "Compare your resume with a job description. The 0–100 score is the weighted share of the job's skills found in your resume, with the formula shown.",
  },
  {
    title: "Evidence for every result",
    text: "Each matched skill links to the line in your resume that supports it. Missing and related skills come with plain-language explanations.",
  },
  {
    title: "Honest suggestions",
    text: "Feedback points at real gaps and at skills you list but never show in use. It never suggests claiming experience you don't have.",
  },
];

const STEPS = [
  "Upload your resume as a PDF.",
  "Review and correct what was extracted.",
  "Paste a job description and check its required and preferred skills.",
  "Run an analysis to see matched, missing and related skills with evidence.",
];

export function LandingPage() {
  useDocumentTitle("");
  const { user } = useAuth();

  return (
    <div>
      <section className="bg-white">
        <div className="mx-auto max-w-4xl px-4 py-16 text-center sm:py-24">
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
            See how your resume matches a job, <span className="text-indigo-700">and why</span>
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-600">
            CareerForge extracts the skills and experience in your resume, compares them with a job description, and explains
            every result with evidence from your own resume.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {user ? (
              <LinkButton to="/dashboard">Go to your dashboard</LinkButton>
            ) : (
              <>
                <LinkButton to="/register">Create a free account</LinkButton>
                <LinkButton to="/login" variant="secondary">
                  Log in
                </LinkButton>
              </>
            )}
          </div>
        </div>
      </section>

      <section aria-labelledby="features" className="mx-auto max-w-6xl px-4 py-16">
        <h2 id="features" className="text-center text-2xl font-bold text-slate-900">
          What it does
        </h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="font-semibold text-slate-900">{f.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{f.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="how" className="bg-white">
        <div className="mx-auto max-w-3xl px-4 py-16">
          <h2 id="how" className="text-center text-2xl font-bold text-slate-900">
            How it works
          </h2>
          <ol className="mt-8 space-y-4">
            {STEPS.map((step, i) => (
              <li key={step} className="flex items-start gap-4">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-700 text-sm font-semibold text-white">
                  {i + 1}
                </span>
                <span className="pt-1 text-slate-700">{step}</span>
              </li>
            ))}
          </ol>
          <p className="mt-8 text-center text-sm text-slate-500">
            The score measures skill overlap between your resume and a job description. It is not a prediction of whether
            you'll be hired.
          </p>
        </div>
      </section>
    </div>
  );
}
