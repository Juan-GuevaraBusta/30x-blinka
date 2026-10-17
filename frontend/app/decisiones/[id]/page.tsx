import DecisionDetailScreen from "./DecisionDetailScreen";

export default async function DecisionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <main className="mx-auto min-h-screen max-w-4xl px-4 py-10 sm:px-6">
      <DecisionDetailScreen decisionId={id} />
    </main>
  );
}
