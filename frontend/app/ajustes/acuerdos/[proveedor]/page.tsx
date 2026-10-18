import AcuerdoDetailScreen from "./AcuerdoDetailScreen";

export default async function AcuerdoDetailPage({
  params,
}: {
  params: Promise<{ proveedor: string }>;
}) {
  const { proveedor } = await params;
  return <AcuerdoDetailScreen vendorKeyParam={proveedor} />;
}
