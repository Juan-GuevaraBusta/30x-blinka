export function AlertPanel({
  children,
  tone = "danger",
}: {
  children: React.ReactNode;
  tone?: "danger" | "neutral";
}) {
  const toneClass =
    tone === "danger"
      ? "border-danger/40 bg-danger/10 text-danger"
      : "border-line bg-paper text-ink";
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${toneClass}`} role="alert">
      {children}
    </div>
  );
}
