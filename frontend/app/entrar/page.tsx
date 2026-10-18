"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { getSupabaseClient } from "@/lib/supabase-client";
import { setStoredUser } from "@/lib/session";

type Mode = "login" | "register";

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
    <div className="mx-auto max-w-md">
      <h1 className="text-2xl font-semibold text-ink">Entrar a Blinka</h1>
      <p className="mt-2 text-sm text-ink-muted">
        Demo hackathon: registro o inicio de sesión y entras al momento.
      </p>

      <div className="mt-6 flex gap-2">
        <button
          type="button"
          className={`rounded-lg px-3 py-2 text-sm font-medium focus-ring ${
            mode === "login" ? "bg-accent/10 text-ink" : "text-ink-muted"
          }`}
          onClick={() => setMode("login")}
        >
          Iniciar sesión
        </button>
        <button
          type="button"
          className={`rounded-lg px-3 py-2 text-sm font-medium focus-ring ${
            mode === "register" ? "bg-accent/10 text-ink" : "text-ink-muted"
          }`}
          onClick={() => setMode("register")}
        >
          Registrarse
        </button>
      </div>

      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <label className="block text-sm font-medium text-ink">
          Correo
          <input
            type="email"
            required
            autoComplete="email"
            className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink focus-ring"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="block text-sm font-medium text-ink">
          Contraseña
          <input
            type="password"
            required
            minLength={6}
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink focus-ring"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error ? (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white focus-ring disabled:opacity-60"
        >
          {busy ? "Un momento…" : mode === "register" ? "Crear cuenta y entrar" : "Entrar"}
        </button>
      </form>
    </div>
  );
}
