import type { AdminSourceQuestionItem } from "@/lib/api/services/fetchQuestionSources";

import type { QuestionDraft } from "@/lib/types/source-questions-dialog";

export function emptyOption(): { label: string; text: string } {
  return { label: "", text: "" };
}

export function cloneDraft(q: AdminSourceQuestionItem): QuestionDraft {
  return {
    stem: q.stem,
    options:
      q.options.length > 0
        ? q.options.map((o) => ({ label: o.label, text: o.text }))
        : [emptyOption()],
    answer: q.answer,
  };
}

/** Form trống trước khi lưu (thêm câu mới). */
export function emptyComposeDraft(): QuestionDraft {
  return {
    stem: "",
    options: [
      { label: "A", text: "" },
      { label: "B", text: "" },
      { label: "C", text: "" },
      { label: "D", text: "" },
    ],
    answer: "A",
  };
}
