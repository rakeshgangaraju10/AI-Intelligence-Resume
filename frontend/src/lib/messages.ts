// User-facing copy for machine-readable codes returned by the API.

export const UPLOAD_ERROR_MESSAGES: Record<string, string> = {
  invalid_extension: "Only PDF files (.pdf) can be uploaded.",
  invalid_content_type: "This file doesn't look like a PDF.",
  empty_file: "The file is empty.",
  file_too_large: "The file is too large.",
  invalid_signature: "The file content is not a PDF, even though its name ends in .pdf.",
  pdf_corrupt: "The PDF couldn't be read. It may be damaged. Try exporting it again.",
  pdf_encrypted: "The PDF is password-protected. Remove the password and upload it again.",
  pdf_too_many_pages: "The PDF has too many pages for a resume.",
  pdf_no_text:
    "No selectable text was found. This usually means the PDF is a scanned image. OCR isn't supported yet, so please upload a text-based PDF (for example, exported from Word or Google Docs).",
  pdf_text_too_long: "The PDF contains far more text than a resume.",
  throttled: "You've uploaded several files in a short time. Please wait a little and try again.",
};

const SECTION_NAMES: Record<string, string> = {
  skills: "Skills",
  education: "Education",
  experience: "Work experience",
  projects: "Projects",
};

/** Explain a parser warning code in plain language. */
export function parseWarningMessage(code: string): string {
  if (code.startsWith("section_not_found:")) {
    const section = SECTION_NAMES[code.split(":")[1]] ?? code.split(":")[1];
    return `No "${section}" heading was found. If your resume has this section under a different name, add the entries below.`;
  }
  switch (code) {
    case "no_skills_detected":
      return "No skills from our dictionary were detected. Add your skills manually.";
    case "experience_unstructured":
      return "Experience text was found but couldn't be split into entries (no date ranges). Add entries manually.";
    case "education_unstructured":
      return "Education text was found but no degree or institution was recognised. Add entries manually.";
    case "projects_unstructured":
      return "Projects text was found but couldn't be split into entries. Add entries manually.";
    case "email_not_found":
      return "No email address was found in your resume.";
    case "name_not_found":
      return "Your name wasn't recognised. You can enter it in the profile section.";
    default:
      return code;
  }
}
