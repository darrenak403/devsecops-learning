"use client";

import { DeckMarkdownPageClient } from "./components/DeckMarkdownPageClient";

/** View soạn deck markdown trong shell `/admin` (sidebar + header). */
export function DeckMarkdownView() {
  return (
    <div className="flex h-full min-h-0 flex-1 flex-col">
      <DeckMarkdownPageClient embedded />
    </div>
  );
}

export default DeckMarkdownView;
