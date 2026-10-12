import { LinkButton } from "../components/ui/Button";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export function NotFoundPage() {
  useDocumentTitle("Page not found");
  return (
    <div className="mx-auto max-w-md px-4 py-24 text-center">
      <p className="text-sm font-semibold text-indigo-700">404</p>
      <h1 className="mt-2 text-2xl font-bold text-slate-900">Page not found</h1>
      <p className="mt-2 text-slate-600">The page you're looking for doesn't exist or you don't have access to it.</p>
      <div className="mt-6">
        <LinkButton to="/">Back to home</LinkButton>
      </div>
    </div>
  );
}
