import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export function MetricTable({
  caption,
  headers,
  rows,
  highlight,
}: {
  caption?: string;
  headers: string[];
  rows: string[][];
  highlight?: (row: string[]) => boolean;
}) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-border bg-card">
      <Table>
        {caption ? (
          <TableCaption className="mt-0 caption-top border-b px-4 py-3 text-left text-sm text-muted-foreground">
            {caption}
          </TableCaption>
        ) : null}
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {headers.map((header) => (
              <TableHead
                key={header}
                className="h-11 bg-muted/40 px-4 text-xs font-medium tracking-wide whitespace-normal text-muted-foreground uppercase"
              >
                {header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow
              key={row.join("|")}
              className={highlight?.(row) ? "bg-accent/70 hover:bg-accent/70" : undefined}
            >
              {row.map((cell, index) => (
                <TableCell
                  key={`${row[0]}-${index}`}
                  className={cn(
                    "px-4 py-3 whitespace-normal",
                    index === 0
                      ? "font-medium text-foreground"
                      : "font-mono text-xs tabular-nums text-foreground md:text-sm"
                  )}
                >
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
