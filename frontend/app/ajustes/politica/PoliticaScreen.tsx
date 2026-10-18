"use client";

import { useCallback, useEffect, useState } from "react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import type { ApprovalRoute, RouteApprovalMode } from "@/lib/approval-policy-types";
import { catchAllRoute } from "@/lib/approval-policy-types";
import {
  addRoute,
  groupsToText,
  matchSummaryLabel,
  moveRouteDown,
  moveRouteUp,
  removeRoute,
  requireSummaryLabel,
  textToGroups,
  validateApprovalPolicyDraft,
} from "@/lib/approval-policy-form";

const FIXED_NOTE =
  "Estas rutas solo pueden pedir más aprobaciones; nunca autorizan un pago que las reglas frenen o escalen.";
const EMPTY_POLICY_NOTE = "Sin política propia: toda factura escalada necesita una aprobación.";

type RulesDocument = Record<string, unknown>;

function isApprovalRouteArray(value: unknown): value is ApprovalRoute[] {
  return Array.isArray(value);
}

/** Reads `document.approval_policy.routes`, or the fixed catch-all row when absent (T7.5 §2). */
function extractRoutes(document: RulesDocument): ApprovalRoute[] {
  const policy = document.approval_policy;
  if (policy && typeof policy === "object" && "routes" in policy) {
    const routes = (policy as { routes: unknown }).routes;
    if (isApprovalRouteArray(routes) && routes.length > 0) {
      return routes;
    }
  }
  return [catchAllRoute()];
}

async function fetchRulesDocument(): Promise<RulesDocument> {
  const res = await fetch("/api/rules", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`No se pudieron cargar las reglas (HTTP ${res.status}).`);
  }
  return (await res.json()) as RulesDocument;
}

function FieldLabel({ children, htmlFor }: { children: string; htmlFor: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block text-xs font-medium text-ink-muted">
      {children}
    </label>
  );
}

export default function PoliticaScreen() {
  const [fullDocument, setFullDocument] = useState<RulesDocument | null>(null);
  const [routes, setRoutes] = useState<ApprovalRoute[]>([catchAllRoute()]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveErrorDetail, setSaveErrorDetail] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const applyDocument = useCallback((document: RulesDocument) => {
    setFullDocument(document);
    setRoutes(extractRoutes(document));
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const document = await fetchRulesDocument();
        if (!cancelled) {
          applyDocument(document);
          setLoadError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : "Error al cargar la política.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applyDocument]);

  const resetMessages = () => {
    setValidationErrors([]);
    setSaveMessage(null);
    setSaveErrorDetail(null);
  };

  const updateRoute = (index: number, updater: (route: ApprovalRoute) => ApprovalRoute) => {
    setRoutes((prev) => prev.map((route, i) => (i === index ? updater(route) : route)));
    resetMessages();
  };

  const updateMatchNumber = (
    index: number,
    field: "amount_base_gte" | "amount_base_lt",
    raw: string,
  ) => {
    const trimmed = raw.trim();
    if (trimmed === "") {
      updateRoute(index, (route) => ({ ...route, match: { ...route.match, [field]: null } }));
      return;
    }
    const value = Number(trimmed);
    if (Number.isNaN(value)) return;
    updateRoute(index, (route) => ({ ...route, match: { ...route.match, [field]: value } }));
  };

  const updateMatchText = (
    index: number,
    field: "beneficiary" | "department" | "invoice_type",
    raw: string,
  ) => {
    const trimmed = raw.trim();
    updateRoute(index, (route) => ({
      ...route,
      match: { ...route.match, [field]: trimmed === "" ? null : raw },
    }));
  };

  const updateRequireMode = (index: number, mode: RouteApprovalMode) => {
    updateRoute(index, (route) => {
      if (mode === "auto") {
        return { ...route, require: { mode: "auto", min_approvals: null, from_groups: [] } };
      }
      return {
        ...route,
        require: {
          mode: "approvals",
          min_approvals: route.require.min_approvals ?? 1,
          from_groups: route.require.from_groups,
        },
      };
    });
  };

  const updateMinApprovals = (index: number, raw: string) => {
    const trimmed = raw.trim();
    updateRoute(index, (route) => ({
      ...route,
      require: { ...route.require, min_approvals: trimmed === "" ? null : Number(trimmed) },
    }));
  };

  const updateGroupsText = (index: number, text: string) => {
    updateRoute(index, (route) => ({
      ...route,
      require: { ...route.require, from_groups: textToGroups(text) },
    }));
  };

  const handleAdd = () => {
    setRoutes((prev) => addRoute(prev));
    resetMessages();
  };

  const handleRemove = (index: number) => {
    setRoutes((prev) => {
      const result = removeRoute(prev, index);
      if (!result.ok) {
        setValidationErrors([result.error]);
        return prev;
      }
      return result.routes;
    });
    setSaveMessage(null);
    setSaveErrorDetail(null);
  };

  const handleMoveUp = (index: number) => {
    setRoutes((prev) => moveRouteUp(prev, index));
    resetMessages();
  };

  const handleMoveDown = (index: number) => {
    setRoutes((prev) => moveRouteDown(prev, index));
    resetMessages();
  };

  const handleSave = async () => {
    setSaveMessage(null);
    setSaveErrorDetail(null);
    const result = validateApprovalPolicyDraft(routes);
    if (!result.ok) {
      setValidationErrors(result.errors);
      return;
    }
    setValidationErrors([]);
    if (!fullDocument) return;

    setSaving(true);
    try {
      const merged = { ...fullDocument, approval_policy: result.policy };
      const res = await fetch("/api/rules", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(merged),
      });
      if (res.status === 502) {
        setSaveErrorDetail("No se pudo conectar con el servidor.");
        return;
      }
      if (res.status === 422) {
        const body = await res.json().catch(() => null);
        const detail = body && typeof body === "object" && "detail" in body ? body.detail : body;
        setSaveErrorDetail(`El servidor rechazó la política: ${JSON.stringify(detail)}`);
        return;
      }
      if (!res.ok) {
        setSaveErrorDetail(`No se pudo guardar la política (HTTP ${res.status}).`);
        return;
      }
      const saved = (await res.json()) as RulesDocument;
      applyDocument(saved);
      setSaveMessage("Política de aprobación guardada.");
    } catch {
      setSaveErrorDetail("No se pudo conectar con el servidor.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <p className="text-sm text-ink-muted" role="status">
        Cargando política de aprobación…
      </p>
    );
  }

  if (loadError) {
    return <AlertPanel>{loadError}</AlertPanel>;
  }

  const hasCustomRoutes = routes.length > 1;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Política de aprobación"
        description={<p>Defina qué rutas exigen más firmas antes de pagar una factura escalada.</p>}
      />

      <p className="text-sm text-ink-muted">{FIXED_NOTE}</p>
      {!hasCustomRoutes ? <p className="text-sm text-ink-muted">{EMPTY_POLICY_NOTE}</p> : null}

      {validationErrors.length > 0 || saveMessage || saveErrorDetail ? (
        <div
          className={`rounded-md px-4 py-3 text-sm ${
            validationErrors.length > 0 || saveErrorDetail
              ? "border border-danger/40 bg-danger/10 text-danger"
              : "border border-success/40 bg-success/10 text-success"
          }`}
          role="alert"
        >
          {validationErrors.length > 0 ? (
            <ul className="list-disc space-y-1 pl-5">
              {validationErrors.map((msg) => (
                <li key={msg}>{msg}</li>
              ))}
            </ul>
          ) : (
            saveErrorDetail ?? saveMessage
          )}
        </div>
      ) : null}

      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line text-left text-ink-muted">
              <th className="px-2 py-2 font-medium">Nombre</th>
              <th className="px-2 py-2 font-medium">Cuándo aplica</th>
              <th className="px-2 py-2 font-medium">Quién aprueba</th>
              <th className="px-2 py-2 font-medium">Aprobaciones</th>
              <th className="px-2 py-2 font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {routes.map((route, index) => {
              const isCatchAll = index === routes.length - 1;

              if (isCatchAll) {
                return (
                  <tr key={route.id} className="border-b border-line/60 align-top">
                    <td className="px-2 py-3 font-medium text-ink">Todo lo demás</td>
                    <td className="px-2 py-3 text-ink-muted">{matchSummaryLabel(route)}</td>
                    <td className="px-2 py-3 text-ink-muted">No aplica</td>
                    <td className="px-2 py-3 text-ink-muted">{requireSummaryLabel(route.require)}</td>
                    <td className="px-2 py-3 text-ink-muted">Fija al final</td>
                  </tr>
                );
              }

              return (
                <tr key={`${route.id}-${index}`} className="border-b border-line/60 align-top">
                  <td className="px-2 py-3">
                    <FieldLabel htmlFor={`route-name-${index}`}>Nombre</FieldLabel>
                    <input
                      id={`route-name-${index}`}
                      type="text"
                      value={route.id}
                      onChange={(e) =>
                        updateRoute(index, (r) => ({ ...r, id: e.target.value }))
                      }
                      className="input-field"
                    />
                  </td>
                  <td className="min-w-[220px] px-2 py-3">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <FieldLabel htmlFor={`route-amt-gte-${index}`}>Monto ≥</FieldLabel>
                        <input
                          id={`route-amt-gte-${index}`}
                          type="number"
                          inputMode="decimal"
                          value={route.match.amount_base_gte ?? ""}
                          onChange={(e) => updateMatchNumber(index, "amount_base_gte", e.target.value)}
                          className="input-field"
                        />
                      </div>
                      <div>
                        <FieldLabel htmlFor={`route-amt-lt-${index}`}>Monto &lt;</FieldLabel>
                        <input
                          id={`route-amt-lt-${index}`}
                          type="number"
                          inputMode="decimal"
                          value={route.match.amount_base_lt ?? ""}
                          onChange={(e) => updateMatchNumber(index, "amount_base_lt", e.target.value)}
                          className="input-field"
                        />
                      </div>
                      <div>
                        <FieldLabel htmlFor={`route-dept-${index}`}>Departamento</FieldLabel>
                        <input
                          id={`route-dept-${index}`}
                          type="text"
                          value={route.match.department ?? ""}
                          onChange={(e) => updateMatchText(index, "department", e.target.value)}
                          className="input-field"
                        />
                      </div>
                      <div>
                        <FieldLabel htmlFor={`route-ben-${index}`}>Proveedor</FieldLabel>
                        <input
                          id={`route-ben-${index}`}
                          type="text"
                          value={route.match.beneficiary ?? ""}
                          onChange={(e) => updateMatchText(index, "beneficiary", e.target.value)}
                          className="input-field"
                        />
                      </div>
                      <div className="col-span-2">
                        <FieldLabel htmlFor={`route-invtype-${index}`}>Tipo de factura</FieldLabel>
                        <input
                          id={`route-invtype-${index}`}
                          type="text"
                          value={route.match.invoice_type ?? ""}
                          onChange={(e) => updateMatchText(index, "invoice_type", e.target.value)}
                          className="input-field"
                        />
                      </div>
                    </div>
                    <p className="mt-2 text-xs text-ink-muted">{matchSummaryLabel(route)}</p>
                  </td>
                  <td className="min-w-[180px] px-2 py-3">
                    {route.require.mode === "auto" ? (
                      <p className="text-xs text-ink-muted">No aplica (modo automático)</p>
                    ) : (
                      <>
                        <FieldLabel htmlFor={`route-groups-${index}`}>Grupos (separados por coma)</FieldLabel>
                        <input
                          id={`route-groups-${index}`}
                          type="text"
                          value={groupsToText(route.require.from_groups)}
                          onChange={(e) => updateGroupsText(index, e.target.value)}
                          className="input-field"
                        />
                      </>
                    )}
                  </td>
                  <td className="min-w-[200px] px-2 py-3">
                    <FieldLabel htmlFor={`route-mode-${index}`}>Modo</FieldLabel>
                    <select
                      id={`route-mode-${index}`}
                      value={route.require.mode}
                      onChange={(e) => updateRequireMode(index, e.target.value as RouteApprovalMode)}
                      className="input-field"
                    >
                      <option value="auto">Automático</option>
                      <option value="approvals">N aprobaciones de grupo</option>
                    </select>
                    {route.require.mode === "approvals" ? (
                      <div className="mt-2">
                        <FieldLabel htmlFor={`route-minapprovals-${index}`}>Número de aprobaciones</FieldLabel>
                        <input
                          id={`route-minapprovals-${index}`}
                          type="number"
                          inputMode="numeric"
                          min={1}
                          value={route.require.min_approvals ?? ""}
                          onChange={(e) => updateMinApprovals(index, e.target.value)}
                          className="input-field"
                        />
                      </div>
                    ) : null}
                    <p className="mt-2 text-xs text-ink-muted">{requireSummaryLabel(route.require)}</p>
                  </td>
                  <td className="px-2 py-3">
                    <div className="flex flex-col gap-2">
                      <button
                        type="button"
                        disabled={index === 0}
                        onClick={() => handleMoveUp(index)}
                        className="btn-secondary px-2 py-1 text-xs"
                      >
                        Subir
                      </button>
                      <button
                        type="button"
                        disabled={index === routes.length - 2}
                        onClick={() => handleMoveDown(index)}
                        className="btn-secondary px-2 py-1 text-xs"
                      >
                        Bajar
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRemove(index)}
                        className="btn-secondary px-2 py-1 text-xs"
                      >
                        Borrar
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={handleAdd} className="btn-secondary">
          Agregar ruta
        </button>
        <button type="button" disabled={saving} onClick={() => void handleSave()} className="btn-primary">
          {saving ? "Guardando…" : "Guardar política"}
        </button>
      </div>
    </div>
  );
}
