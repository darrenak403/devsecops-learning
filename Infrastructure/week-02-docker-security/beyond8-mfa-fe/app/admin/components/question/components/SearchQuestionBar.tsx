"use client";

import { Input } from "@/components/ui/input";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className="shrink-0 border-b px-3 pb-2 pt-2">
      <Input
        type="search"
        placeholder="Tìm trong câu hỏi, đáp án…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 text-sm"
        aria-label="Tìm câu hỏi"
      />
    </div>
  );
}
