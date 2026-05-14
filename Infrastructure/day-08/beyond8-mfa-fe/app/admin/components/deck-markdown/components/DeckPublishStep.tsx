"use client";

import type { ComponentProps } from "react";
import { UploadMergeCard } from "./UploadMergeCard";
import { Textarea } from "@/components/ui/textarea";

type DeckPublishStepProps = {
  accumulatedMd: string;
  uploadMergeProps: ComponentProps<typeof UploadMergeCard>;
};

export function DeckPublishStep({ accumulatedMd, uploadMergeProps }: DeckPublishStepProps) {
  const lines = accumulatedMd ? accumulatedMd.split("\n").length : 0;
  const chars = accumulatedMd.length;

  return (
    <section
      className="flex h-full min-h-0 w-full flex-1 flex-col gap-2"
      aria-label="Xem trước markdown và upload"
    >
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <p className="shrink-0 text-right text-xs text-muted-foreground">
          {lines} dòng · {chars} ký tự
        </p>
        <Textarea
          readOnly
          value={accumulatedMd}
          aria-label="Nội dung markdown đầy đủ"
          className="mt-1 min-h-0 flex-1 resize-none rounded-lg border-2 bg-background font-mono text-sm leading-relaxed md:text-base"
        />
      </div>

      <UploadMergeCard {...uploadMergeProps} />
    </section>
  );
}
