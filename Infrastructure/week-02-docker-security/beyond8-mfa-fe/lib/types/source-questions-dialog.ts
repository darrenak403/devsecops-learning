import type { SourceItem } from "@/lib/api/services/fetchQuestionSources";

export interface SourceQuestionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subjectSlug: string | null;
  source: SourceItem | null;
}

export type QuestionDraft = {
  stem: string;
  options: { label: string; text: string }[];
  answer: string;
};
