import Explorer from "@/components/alpha/explorer";
import { requireJournalPage } from "@/lib/auth";

export const metadata = { title: "Hecate Alpha · Training", robots: { index: false, follow: false } };

export default async function Page() {
  await requireJournalPage("/alpha");
  return <Explorer page="training" />;
}
