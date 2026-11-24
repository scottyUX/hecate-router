import Explorer from "@/components/alpha/explorer";
import { requireJournalPage } from "@/lib/auth";

export const metadata = { title: "Hecate Alpha · Runtime", robots: { index: false, follow: false } };

export default async function Page() {
  await requireJournalPage("/alpha/runtime");
  return <Explorer page="runtime" />;
}
