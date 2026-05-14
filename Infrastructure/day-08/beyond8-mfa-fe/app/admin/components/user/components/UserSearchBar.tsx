import { memo, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface UserSearchBarProps {
  search: string;
  onSearchChange: (val: string) => void;
  onSearchSubmit: (e: FormEvent) => void;
  filter: "all" | "active" | "blocked";
  onFilterChange: (filter: "all" | "active" | "blocked") => void;
}

export const UserSearchBar = memo(({ 
  search, 
  onSearchChange, 
  onSearchSubmit, 
  filter, 
  onFilterChange 
}: UserSearchBarProps) => (
  <div className="flex w-full flex-col gap-3">
    <form className="flex w-full flex-col gap-2 md:flex-row" onSubmit={onSearchSubmit}>
      <Input
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Tìm theo email người dùng"
        className="w-full"
      />
      <Button type="submit" variant="outline" className="md:min-w-28">
        Tìm
      </Button>
    </form>
    <div className="flex flex-wrap items-center gap-2">
      <p className="text-xs text-muted-foreground">Bộ lọc trạng thái:</p>
      {(["all", "active", "blocked"] as const).map((item) => (
        <Button
          key={item}
          type="button"
          variant={filter === item ? "default" : "outline"}
          size="sm"
          aria-pressed={filter === item}
          onClick={() => onFilterChange(item)}
        >
          {item === "all" ? "Tất cả" : item === "active" ? "Đang hoạt động" : "Đã khóa"}
        </Button>
      ))}
    </div>
  </div>
));

UserSearchBar.displayName = "UserSearchBar";
