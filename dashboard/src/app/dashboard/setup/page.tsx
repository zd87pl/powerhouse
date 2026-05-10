"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  KeyRound,
  Loader2,
  Plug,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import {
  api,
  type SetupProviderStatus,
  type SetupStatus,
  type SetupValidationResult,
} from "@/lib/api";
import { errorMessage, formatDate, statusColor } from "@/lib/utils";

const VALIDATABLE_PROVIDERS = new Set(["github", "vercel"]);

function statusLabel(status: string) {
  return status.replace(/_/g, " ");
}

function providerIcon(provider: SetupProviderStatus) {
  if (provider.status === "connected") {
    return <CheckCircle2 className="h-5 w-5 text-green-400" />;
  }
  if (provider.status === "configured") {
    return <ShieldCheck className="h-5 w-5 text-amber-400" />;
  }
  if (provider.required) {
    return <AlertTriangle className="h-5 w-5 text-red-400" />;
  }
  return <Plug className="h-5 w-5 text-slate-500" />;
}

export default function SetupPage() {
  const [setup, setSetup] = useState<SetupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState<string | null>(null);
  const [validationResults, setValidationResults] = useState<Record<string, SetupValidationResult>>({});
  const [error, setError] = useState("");

  const fetchSetup = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setSetup(await api.setup.status());
    } catch (e: unknown) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(fetchSetup);
  }, [fetchSetup]);

  const validateProvider = async (provider: string) => {
    setValidating(provider);
    setError("");
    try {
      const result = await api.setup.validate(provider);
      setValidationResults((current) => ({ ...current, [provider]: result }));
      await fetchSetup();
    } catch (e: unknown) {
      setError(errorMessage(e));
    } finally {
      setValidating(null);
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Setup</h1>
          <p className="mt-1 text-slate-400">
            Connect the services Powerhouse needs to build, deploy, and track OSS projects.
          </p>
        </div>
        <button
          onClick={fetchSetup}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
        </div>
      )}

      {!loading && setup && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <p className="text-sm text-slate-500">Required Ready</p>
              <p className="mt-1 text-2xl font-bold text-white">
                {setup.ready ? "Yes" : "No"}
              </p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <p className="text-sm text-slate-500">Connected</p>
              <p className="mt-1 text-2xl font-bold text-white">{setup.connected}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <p className="text-sm text-slate-500">Stored Keys</p>
              <p className="mt-1 text-2xl font-bold text-white">{setup.configured}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <p className="text-sm text-slate-500">Missing Required</p>
              <p className="mt-1 text-2xl font-bold text-white">
                {setup.missing_required}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-center gap-3">
              <KeyRound className="h-5 w-5 text-indigo-400" />
              <div>
                <p className="font-medium text-white">Bring your own keys</p>
                <p className="text-sm text-slate-500">
                  Environment variables are active immediately. Stored keys are encrypted and ready for provider validation.
                </p>
              </div>
            </div>
            <Link
              href="/dashboard/keys"
              className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-600"
            >
              Manage Keys
            </Link>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {setup.providers.map((provider) => (
              <div key={provider.provider} className="rounded-lg border border-slate-800 bg-slate-900 p-5">
                <div className="mb-4 flex items-start justify-between gap-4">
                  <div className="flex min-w-0 items-center gap-3">
                    {providerIcon(provider)}
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="font-semibold text-white">{provider.label}</h2>
                        {provider.required && (
                          <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-xs text-indigo-300">
                            required
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-slate-500">{provider.source}</p>
                    </div>
                  </div>
                  <span
                    className={`shrink-0 rounded-full border px-2 py-1 text-xs capitalize ${statusColor(provider.status)}`}
                  >
                    {statusLabel(provider.status)}
                  </span>
                </div>

                <p className="mb-4 text-sm leading-6 text-slate-400">
                  {provider.next_action}
                </p>

                <div className="mb-4 flex flex-wrap gap-2">
                  {provider.required_env.map((envName) => {
                    const missing = provider.missing_env.includes(envName);
                    return (
                      <span
                        key={envName}
                        className={`rounded border px-2 py-1 font-mono text-xs ${
                          missing
                            ? "border-red-500/20 bg-red-500/10 text-red-300"
                            : "border-green-500/20 bg-green-500/10 text-green-300"
                        }`}
                      >
                        {envName}
                      </span>
                    );
                  })}
                </div>

                <div className="flex items-center justify-between gap-3 border-t border-slate-800 pt-4">
                  <span className="text-xs text-slate-500">
                    {provider.has_key ? "Encrypted key saved" : "No stored key"}
                  </span>
                  <div className="flex items-center gap-3">
                    {VALIDATABLE_PROVIDERS.has(provider.provider) && (
                      <button
                        onClick={() => validateProvider(provider.provider)}
                        disabled={validating === provider.provider}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-200 transition-colors hover:bg-slate-800 disabled:opacity-50"
                      >
                        {validating === provider.provider ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <ShieldCheck className="h-3.5 w-3.5" />
                        )}
                        Validate
                      </button>
                    )}
                    <a
                      href={provider.docs_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-indigo-400 hover:text-indigo-300"
                    >
                      Docs
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>
                </div>

                {validationResults[provider.provider] && (
                  <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950/60 p-4">
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-medium text-white">
                          {validationResults[provider.provider].summary}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          Validated {formatDate(validationResults[provider.provider].validated_at)} via {validationResults[provider.provider].source}
                        </p>
                      </div>
                      <span
                        className={`rounded-full border px-2 py-1 text-xs capitalize ${statusColor(validationResults[provider.provider].status)}`}
                      >
                        {statusLabel(validationResults[provider.provider].status)}
                      </span>
                    </div>

                    <div className="space-y-2">
                      {validationResults[provider.provider].checks.map((check) => (
                        <div key={`${check.label}-${check.status}`} className="flex items-start justify-between gap-3 text-sm">
                          <div>
                            <p className="font-medium text-slate-300">{check.label}</p>
                            <p className="mt-0.5 text-xs leading-5 text-slate-500">{check.detail}</p>
                          </div>
                          <span className={`shrink-0 rounded-full border px-2 py-0.5 text-xs ${statusColor(check.status)}`}>
                            {check.status}
                          </span>
                        </div>
                      ))}
                    </div>

                    {validationResults[provider.provider].next_action && (
                      <p className="mt-3 border-t border-slate-800 pt-3 text-xs text-slate-500">
                        {validationResults[provider.provider].next_action}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
