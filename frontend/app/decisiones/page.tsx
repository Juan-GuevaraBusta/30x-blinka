import { parseInitialFilter } from "@/lib/decisions-list";

import DecisionsScreen from "./DecisionsScreen";

export default async function DecisionesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const initialFilter = parseInitialFilter(params.estado);
  return <DecisionsScreen initialFilter={initialFilter} />;
}
