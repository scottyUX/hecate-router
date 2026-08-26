export type JournalTextBlock = { type: "text"; text: string };
export type JournalTableBlock = {
  type: "table";
  headers: string[];
  rows: string[][];
};
export type JournalBlock = JournalTextBlock | JournalTableBlock;

function splitPipeRow(line: string): string[] {
  const trimmed = line.trim();
  const inner = trimmed.replace(/^\|/, "").replace(/\|$/, "");
  return inner.split("|").map((cell) => cell.trim());
}

function isPipeRow(line: string): boolean {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.includes("|", 1);
}

function isSeparatorRow(line: string): boolean {
  if (!isPipeRow(line)) return false;
  const cells = splitPipeRow(line);
  return cells.length > 0 && cells.every((cell) => /^:?-{1,}:?$/.test(cell));
}

function parseTableAt(
  lines: string[],
  start: number
): { block: JournalTableBlock; nextIndex: number } | null {
  if (start + 1 >= lines.length) return null;
  if (!isPipeRow(lines[start]) || !isSeparatorRow(lines[start + 1])) return null;

  const headers = splitPipeRow(lines[start]);
  if (headers.length < 2) return null;
  if (splitPipeRow(lines[start + 1]).length !== headers.length) return null;

  const rows: string[][] = [];
  let index = start + 2;
  while (index < lines.length && isPipeRow(lines[index]) && !isSeparatorRow(lines[index])) {
    const cells = splitPipeRow(lines[index]);
    if (cells.length !== headers.length) break;
    rows.push(cells);
    index += 1;
  }
  if (rows.length === 0) return null;
  return { block: { type: "table", headers, rows }, nextIndex: index };
}

export function splitJournalBlocks(body: string): JournalBlock[] {
  const lines = body.replace(/\r\n/g, "\n").split("\n");
  const blocks: JournalBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    const table = parseTableAt(lines, index);
    if (table) {
      blocks.push(table.block);
      index = table.nextIndex;
      continue;
    }

    const start = index;
    index += 1;
    while (index < lines.length && !parseTableAt(lines, index)) {
      index += 1;
    }
    blocks.push({ type: "text", text: lines.slice(start, index).join("\n") });
  }

  return blocks.filter((block) => block.type === "table" || block.text.length > 0);
}
