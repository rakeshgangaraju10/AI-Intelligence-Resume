import { useEffect } from "react";

/** Sets the browser tab title so screen-reader users hear the page change. */
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    document.title = title ? `${title} · CareerForge` : "CareerForge";
  }, [title]);
}
