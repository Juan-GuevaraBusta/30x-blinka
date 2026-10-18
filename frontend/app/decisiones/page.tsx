import { parseInitialFilter } from "@/lib/decisions-list";

import DecisionsScreen from "./DecisionsScreen";

export default async function DecisionesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const initialFilter = parseInitialFilter(params.estado);
  return (
    <main className="mx-auto min-h-screen max-w-4xl px-4 py-10 sm:px-6">
      <DecisionsScreen initialFilter={initialFilter} />
    </main>
  );
}
