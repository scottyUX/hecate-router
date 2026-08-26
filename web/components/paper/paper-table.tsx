import { cn } from "@/lib/utils";

export function PaperTable({
  id,
  caption,
  headers,
  rows,
  highlight,
}: {
  id: string;
  caption: string;
  headers: string[];
  rows: string[][];
  highlight?: (row: string[]) => boolean;
}) {
  return (
    <figure id={id} className="my-8 scroll-mt-8">
      <figcaption className="mb-3 text-sm leading-[1.5] text-[#555]">
        {caption}
      </figcaption>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-lg">
          <thead>
            <tr className="border-b border-[var(--paper-ink)]">
              {headers.map((header) => (
                <th
                  key={header}
                  className="px-1.5 py-1.5 text-left align-bottom font-bold"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.join("|")}
                className={cn(
                  "border-b border-[var(--paper-line)]",
                  highlight?.(row) ? "bg-[var(--paper-card)]" : undefined
                )}
              >
                {row.map((cell, index) => (
                  <td
                    key={`${row[0]}-${index}`}
                    className={cn(
                      "px-1.5 py-1.5 align-top",
                      index > 0 ? "tabular-nums" : undefined
                    )}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}
