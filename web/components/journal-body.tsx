import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { splitJournalBlocks } from "@/lib/journal-blocks";

export function JournalBody({ text }: { text: string }) {
  const body = text.trim();
  if (!body) return <div className="text-muted-foreground">—</div>;

  return (
    <div className="space-y-4 text-muted-foreground">
      {splitJournalBlocks(body).map((block, index) =>
        block.type === "table" ? (
          <div
            key={index}
            className="overflow-hidden rounded-lg border bg-card text-card-foreground"
          >
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  {block.headers.map((header, headerIndex) => (
                    <TableHead
                      key={headerIndex}
                      className="whitespace-normal bg-muted/40"
                    >
                      {header || null}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {block.rows.map((row, rowIndex) => (
                  <TableRow key={rowIndex}>
                    {row.map((cell, cellIndex) => (
                      <TableCell
                        key={cellIndex}
                        className={
                          cellIndex === 0
                            ? "whitespace-normal font-medium text-foreground"
                            : "whitespace-normal"
                        }
                      >
                        {cell}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <div key={index} className="whitespace-pre-wrap">
            {block.text}
          </div>
        )
      )}
    </div>
  );
}
