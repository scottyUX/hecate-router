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
    <figure id={id} className="my-6 scroll-mt-8">
      <figcaption className="mb-2 font-sans text-[13px] leading-[1.45] text-[#555]">
        {caption}
      </figcaption>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse font-sans text-[13px] leading-[1.4]">
          <thead>
            <tr className="border-b border-[var(--paper-ink)]/70">
              {headers.map((header) => (
                <th
                  key={header}
                  className="px-1 py-1 text-left align-bottom font-medium"
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
                      "px-1 py-1 align-top",
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
