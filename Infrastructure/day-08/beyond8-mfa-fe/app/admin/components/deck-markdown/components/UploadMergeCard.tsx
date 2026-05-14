"use client";

import { useState } from "react";
import type { MergeBankPreviewResponse } from "@/lib/api/services/fetchQuestionSources";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

type UploadMergeProps = {
  selectedSlug: string;
  accumulatedMd: string;
  filenameDuplicate: boolean;
  uploadFileName: string;
  isUploading: boolean;
  isPreviewing: boolean;
  isMerging: boolean;
  lastUploadSourceId: string | null;
  previewMerge: MergeBankPreviewResponse | null;
  onUpload: () => void;
  onDownload: () => void;
  onPreviewMerge: () => void;
  onMergeCommit: () => void;
};

function PreviewMergeSummary({ previewMerge }: { previewMerge: MergeBankPreviewResponse }) {
  return (
    <div
      className="inline-block max-w-full rounded-lg border-2 border-primary/40 bg-primary/12 px-3 py-2 text-sm font-semibold leading-snug text-foreground shadow-sm"
      role="status"
      aria-live="polite"
    >
      <span className="text-primary">Preview:</span> thêm {previewMerge.added}, bỏ trùng {previewMerge.skippedDuplicate},
      tổng sau merge {previewMerge.bankQuestionCountAfter}
      {previewMerge.wouldCreateBank ? (
        <span className="mt-0.5 block text-xs font-medium text-primary">(sẽ tạo source ngân hàng mới)</span>
      ) : null}
    </div>
  );
}

export function UploadMergeCard(props: UploadMergeProps) {
  const {
    selectedSlug,
    accumulatedMd,
    filenameDuplicate,
    uploadFileName,
    isUploading,
    isPreviewing,
    isMerging,
    lastUploadSourceId,
    previewMerge,
    onUpload,
    onDownload,
    onPreviewMerge,
    onMergeCommit,
  } = props;

  const [mergeDialogOpen, setMergeDialogOpen] = useState(false);

  return (
    <>
      <footer className="shrink-0 border-t border-border pt-2" aria-label="Upload và hợp nhất ngân hàng">
        {!lastUploadSourceId ? (
          <div className="flex w-full min-w-0 flex-wrap items-center gap-2 sm:gap-3">
            <Button
              type="button"
              size="lg"
              className="h-12 shrink-0 cursor-pointer gap-2 rounded-lg px-3 transition-colors duration-200 sm:px-4"
              onClick={onUpload}
              disabled={
                isUploading ||
                !selectedSlug ||
                !accumulatedMd.trim() ||
                filenameDuplicate ||
                !uploadFileName
              }
            >
              {isUploading ? "Đang upload…" : "Upload đề lên server"}
            </Button>
            <Button
              type="button"
              size="lg"
              variant="secondary"
              className="h-12 shrink-0 cursor-pointer gap-2 rounded-lg px-3 transition-colors duration-200 sm:px-4"
              onClick={onDownload}
              disabled={!accumulatedMd.trim()}
            >
              Tải xuống .md
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Source vừa upload: <span className="font-mono text-foreground">{lastUploadSourceId}</span>
            </p>

            <div className="flex w-full min-w-0 flex-col gap-3 md:flex-row md:items-center md:gap-3">
              <div className="flex min-w-0 flex-shrink-0 flex-wrap items-center gap-2 sm:gap-3">
                {selectedSlug ? (
                  <>
                    <Button
                      type="button"
                      size="lg"
                      variant="secondary"
                      className="h-12 shrink-0 cursor-pointer gap-2 rounded-lg px-3 transition-colors duration-200 sm:px-4"
                      onClick={onPreviewMerge}
                      disabled={isPreviewing}
                    >
                      {isPreviewing ? "Đang xem trước…" : "Xem trước merge ngân hàng"}
                    </Button>
                    <Button
                      type="button"
                      size="lg"
                      className="h-12 shrink-0 cursor-pointer gap-2 rounded-lg px-3 transition-colors duration-200 sm:px-4"
                      onClick={() => setMergeDialogOpen(true)}
                      disabled={isMerging}
                    >
                      {isMerging ? "Đang hợp nhất…" : "Hợp nhất vào câu-hỏi-tổng-hợp (DB)"}
                    </Button>
                  </>
                ) : null}
                <Button
                  type="button"
                  size="lg"
                  variant="secondary"
                  className="h-12 shrink-0 cursor-pointer gap-2 rounded-lg px-3 transition-colors duration-200 sm:px-4"
                  onClick={onDownload}
                  disabled={!accumulatedMd.trim()}
                >
                  Tải xuống .md
                </Button>
              </div>

              {previewMerge && selectedSlug ? (
                <div className="flex min-w-0 flex-1 justify-start md:justify-end">
                  <PreviewMergeSummary previewMerge={previewMerge} />
                </div>
              ) : null}
            </div>
          </div>
        )}
      </footer>

      <AlertDialog open={mergeDialogOpen} onOpenChange={setMergeDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xác nhận hợp nhất</AlertDialogTitle>
            <AlertDialogDescription>
              Bạn có chắc chắn muốn hợp nhất deck này vào ngân hàng câu hỏi tổng hợp không?
              {previewMerge ? (
                <>
                  <br />
                  <br />
                  <strong>Preview:</strong> thêm {previewMerge.added}, bỏ trùng {previewMerge.skippedDuplicate},
                  tổng sau merge {previewMerge.bankQuestionCountAfter}
                  {previewMerge.wouldCreateBank ? " (sẽ tạo source ngân hàng mới)" : ""}
                </>
              ) : null}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Hủy</AlertDialogCancel>
            <AlertDialogAction onClick={onMergeCommit} disabled={isMerging}>
              {isMerging ? "Đang hợp nhất…" : "Hợp nhất"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
