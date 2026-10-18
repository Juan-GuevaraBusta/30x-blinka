import NuevoAcuerdoScreen from "./NuevoAcuerdoScreen";

export default async function NuevoAcuerdoPage({
  searchParams,
}: {
  searchParams: Promise<{ proveedor?: string }>;
}) {
  const { proveedor } = await searchParams;
  return <NuevoAcuerdoScreen initialVendorName={proveedor} />;
}
