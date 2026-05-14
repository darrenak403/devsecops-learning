"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils/cn";

export type DeckWizardStep = 1 | 2 | 3;

const LABELS: Record<DeckWizardStep, string> = {
  1: "Môn & file",
  2: "Soạn câu",
  3: "Xem trước & đẩy lên",
};

type DeckStepIndicatorProps = {
  current: DeckWizardStep;
  className?: string;
};

export function DeckStepIndicator({ current, className }: DeckStepIndicatorProps) {
  const steps: DeckWizardStep[] = [1, 2, 3];

  return (
    <nav aria-label="Tiến trình deck" className={cn("w-full", className)}>
      <ol className="m-0 flex w-full list-none flex-col gap-4 p-0 sm:flex-row sm:items-center sm:gap-0">
        {steps.map((n, i) => {
          const done = current > n;
          const active = current === n;
          const segmentAfterDone = current > n;
          const segmentBeforeDone = i > 0 && current > steps[i - 1]!;

          return (
            <li
              key={n}
              className="flex min-w-0 flex-1 basis-0 flex-row items-center sm:min-h-[2.75rem]"
            >
              {i > 0 ? (
                <div
                  className={cn(
                    "mr-2 hidden h-px min-w-[0.5rem] flex-1 self-center sm:block",
                    segmentBeforeDone ? "bg-primary" : "bg-border"
                  )}
                  aria-hidden
                />
              ) : null}

              <div className="flex shrink-0 flex-col items-center gap-1.5 text-center sm:max-w-[11rem]">
                <span
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold transition-colors duration-200",
                    done && "border-primary bg-primary text-primary-foreground",
                    active && !done && "border-primary text-primary",
                    !active && !done && "border-muted-foreground/30 text-muted-foreground"
                  )}
                  aria-current={active ? "step" : undefined}
                >
                  {done ? <Check className="h-4 w-4" aria-hidden /> : n}
                </span>
                <span
                  className={cn(
                    "max-w-[10rem] text-xs font-semibold leading-snug sm:text-sm",
                    active ? "text-foreground" : "text-muted-foreground"
                  )}
                >
                  {LABELS[n]}
                </span>
              </div>

              {i < steps.length - 1 ? (
                <div
                  className={cn(
                    "ml-2 hidden h-px min-w-[0.5rem] flex-1 self-center sm:block",
                    segmentAfterDone ? "bg-primary" : "bg-border"
                  )}
                  aria-hidden
                />
              ) : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
