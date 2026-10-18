import VendorDetailScreen from "./VendorDetailScreen";

export default async function VendorDetailPage({
  params,
}: {
  params: Promise<{ nombre: string }>;
}) {
  const { nombre } = await params;
  return <VendorDetailScreen vendorNameParam={nombre} />;
}
