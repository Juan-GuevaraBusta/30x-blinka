"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ArrowRight, Loader2, Lock, Mail, ShieldCheck } from "lucide-react";

import { BrandMark } from "@/components/ui/BrandMark";
import { AlertPanel } from "@/components/ui/AlertPanel";
import { DecisionBadge, PulseDot } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { Decision } from "@/lib/decision-types";
import { getSupabaseClient } from "@/lib/supabase-client";
import { setStoredUser } from "@/lib/session";

type Mode = "login" | "register";

const PITCH: Array<{ decision: Decision; text: string }> = [
  { decision: "PAGAR", text: "Cumple las reglas: lista para pagar." },
  { decision: "ESCALAR", text: "Hay dudas: la revisa una persona." },
  { decision: "FRENAR", text: "Rompe una regla: no se paga." },
];

export default function EntrarPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const supabase = getSupabaseClient();
      if (mode === "register") {
        const { data, error: signUpError } = await supabase.auth.signUp({ email, password });
        if (signUpError) {
          setError(signUpError.message);
          return;
        }
        if (!data.session?.user?.id) {
          setError(
            "Revisa el correo o desactiva la confirmación de email en Supabase (Auth → Providers).",
          );
          return;
        }
        setStoredUser(data.session.user.id, data.session.user.email ?? email);
      } else {
        const { data, error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (signInError) {
          setError(signInError.message);
          return;
        }
        if (!data.session?.user?.id) {
          setError("No se pudo obtener la sesión.");
          return;
        }
        setStoredUser(data.session.user.id, data.session.user.email ?? email);
      }
      router.replace("/");
    } catch {
      setError("Configura NEXT_PUBLIC_SUPABASE_URL y NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="-mx-4 -my-8 grid min-h-screen sm:-mx-8 sm:-my-10 lg:-mx-10 lg:grid-cols-2">
      <section className="relative hidden overflow-hidden bg-night px-10 py-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute inset-0 bg-grid-night opacity-40" aria-hidden="true" />
        <div className="pointer-events-none absolute -left-20 top-1/3 h-80 w-80 rounded-full bg-brand-500/40 blur-3xl" aria-hidden="true" />
        <div className="pointer-events-none absolute -bottom-16 right-0 h-64 w-64 rounded-full bg-signal/20 blur-3xl" aria-hidden="true" />

        <div className="relative flex items-center gap-3">
          <BrandMark />
          <span className="font-display text-lg font-bold tracking-tight">Tachyon</span>
        </div>

        <div className="relative max-w-md animate-fade-up">
          <p className="inline-flex items-center gap-2 rounded-full border border-night-line bg-night-soft px-3 py-1 text-xs font-semibold text-brand-100">
            <PulseDot tone="signal" />
            Tachyon · pagos a proveedores para equipos de finanzas
          </p>
          <h2 className="mt-5 text-display text-white">
            Cada factura, con una decisión <span className="text-signal">explicable</span>.
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-brand-100">
            El agente lee la factura, la contrasta con las reglas de tu empresa y decide si se paga, se frena o
            escala a una persona. Todo queda registrado y auditable.
          </p>
          <ul className="mt-8 space-y-3">
            {PITCH.map((item) => (
              <li key={item.decision} className="flex items-center gap-3 rounded-xl border border-night-line bg-night-soft/80 px-4 py-3">
                <DecisionBadge decision={item.decision} size="sm" />
                <span className="text-sm text-brand-100">{item.text}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative flex items-center gap-2 text-xs text-brand-200">
          <ShieldCheck className="h-4 w-4 text-signal" aria-hidden="true" />
          Registro encadenado por hash · datos sintéticos de demo
        </p>
      </section>

      <section className="flex items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-md animate-fade-up">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <BrandMark />
            <span className="font-display text-lg font-bold tracking-tight text-ink">Tachyon</span>
          </div>
          <h1 className="text-h1 text-ink">Entrar a Tachyon</h1>
          <p className="mt-2 text-sm text-ink-muted">
            Demo hackathon: registro o inicio de sesión y entras al momento.
          </p>

          <div className="mt-6 grid grid-cols-2 gap-1 rounded-xl border border-line bg-surface-sunken p-1">
            <button
              type="button"
              aria-pressed={mode === "login"}
              className={`rounded-lg px-3 py-2 text-sm font-semibold transition-all focus-ring ${
                mode === "login" ? "bg-surface text-brand-700 shadow-sm" : "text-ink-muted hover:text-ink"
              }`}
              onClick={() => setMode("login")}
            >
              Iniciar sesión
            </button>
            <button
              type="button"
              aria-pressed={mode === "register"}
              className={`rounded-lg px-3 py-2 text-sm font-semibold transition-all focus-ring ${
                mode === "register" ? "bg-surface text-brand-700 shadow-sm" : "text-ink-muted hover:text-ink"
              }`}
              onClick={() => setMode("register")}
            >
              Registrarse
            </button>
          </div>

          <form className="mt-6 space-y-4 rounded-2xl border border-line bg-surface p-6 shadow-md" onSubmit={onSubmit}>
            <label className="block text-sm font-semibold text-ink">
              Correo
              <span className="relative mt-1.5 block">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle" aria-hidden="true" />
                <input
                  type="email"
                  required
                  autoComplete="email"
                  className="input-field pl-9"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </span>
            </label>
            <label className="block text-sm font-semibold text-ink">
              Contraseña
              <span className="relative mt-1.5 block">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle" aria-hidden="true" />
                <input
                  type="password"
                  required
                  minLength={6}
                  autoComplete={mode === "register" ? "new-password" : "current-password"}
                  className="input-field pl-9"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </span>
            </label>
            {error ? <AlertPanel tone="danger">{error}</AlertPanel> : null}
            <Button
              type="submit"
              disabled={busy}
              size="lg"
              className="w-full"
              icon={busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : undefined}
            >
              {busy ? "Un momento…" : mode === "register" ? "Crear cuenta y entrar" : "Entrar"}
              {busy ? null : <ArrowRight className="h-4 w-4" aria-hidden="true" />}
            </Button>
          </form>
        </div>
      </section>
    </div>
  );
}
