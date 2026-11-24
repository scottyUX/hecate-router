import Explorer from "@/components/alpha/explorer";
import { requireJournalPage } from "@/lib/auth";

export const metadata = { title: "Hecate Alpha · Ppo", robots: { index: false, follow: false } };

export default async function Page() {
  await requireJournalPage("/alpha/ppo");
  return <Explorer page="ppo" />;
}
