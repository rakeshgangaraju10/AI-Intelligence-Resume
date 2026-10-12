import { describe, expect, it } from "vitest";

import { parseWarningMessage } from "./messages";
import { splitSkillList } from "./skills";
import { validatePdfFile } from "./uploadValidation";

function file(name: string, size: number, type = "application/pdf"): File {
  return new File([new Uint8Array(size)], name, { type });
}

describe("validatePdfFile", () => {
  const max = 1024 * 1024;

  it("accepts a normal PDF", () => {
    expect(validatePdfFile(file("resume.PDF", 2048), max)).toBeNull();
  });

  it("accepts browsers that send a generic or empty type", () => {
    expect(validatePdfFile(file("resume.pdf", 10, "application/octet-stream"), max)).toBeNull();
    expect(validatePdfFile(file("resume.pdf", 10, ""), max)).toBeNull();
  });

  it("rejects other extensions, wrong types, empty and oversized files", () => {
    expect(validatePdfFile(file("resume.docx", 10), max)).toMatch(/only pdf/i);
    expect(validatePdfFile(file("resume.pdf", 10, "image/png"), max)).toMatch(/doesn't look like a pdf/i);
    expect(validatePdfFile(file("resume.pdf", 0), max)).toMatch(/empty/i);
    expect(validatePdfFile(file("resume.pdf", max + 1), max)).toMatch(/limit is 1\.0 MB/);
  });
});

describe("splitSkillList", () => {
  it("splits on commas and new lines, trims and de-duplicates case-insensitively", () => {
    expect(splitSkillList(" Python, Django\nSQL,python ,, \n  React  Native ")).toEqual(["Python", "Django", "SQL", "React Native"]);
  });

  it("returns an empty list for blank input", () => {
    expect(splitSkillList("  \n , ")).toEqual([]);
  });
});

describe("parseWarningMessage", () => {
  it("explains missing sections by name", () => {
    expect(parseWarningMessage("section_not_found:experience")).toMatch(/"Work experience"/);
  });

  it("falls back to the code for unknown warnings", () => {
    expect(parseWarningMessage("something_new")).toBe("something_new");
  });
});
