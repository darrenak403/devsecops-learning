import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface UserTableSkeletonProps {
  /** Số dòng placeholder khi đang tải dữ liệu user */
  rowCount?: number;
}

export function UserTableSkeleton({ rowCount = 6 }: UserTableSkeletonProps) {
  return (
    <div className="w-full overflow-x-auto rounded-xl border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Email</TableHead>
            <TableHead>Role</TableHead>
            <TableHead>Trạng thái</TableHead>
            <TableHead>Key OTP</TableHead>
            <TableHead>OTP vừa tạo</TableHead>
            <TableHead>Lý do khóa</TableHead>
            <TableHead className="text-right">Thao tác</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: rowCount }).map((_, idx) => (
            <TableRow key={idx} aria-hidden>
              <TableCell>
                <Skeleton className="h-5 w-full max-w-[min(100%,14rem)]" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-6 w-16 rounded-full" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-5 w-28" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-6 w-24 rounded-full" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-5 w-32" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-5 w-full max-w-[min(100%,10rem)]" />
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-2">
                  <Skeleton className="h-9 w-[4.5rem]" />
                  <Skeleton className="h-9 w-[5.25rem]" />
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
