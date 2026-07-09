"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Loader2,
  Play,
  Rocket,
  Sparkles,
  Tag,
  Wrench,
  Globe,
  Bug,
  AlertTriangle,
  FileCode,
} from "lucide-react";
import { api, type DiagnoseResult, type ParseResult, type Project } from "@/lib/api";
import { errorMessage } from "@/lib/utils";

const SEVERITY_STYLES: Record<string, string> = {
  high: "border-red-500/20 bg-red-500/5 text-red-300",
  medium: "border-amber-500/20 bg-amber-500/5 text-amber-300",
  low: "border-zinc-500/20 bg-zinc-500/5 text-zinc-300",
};

export default function DemoPage() {
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ParseResult | null>(null);
  const [error, setError] = useState("");

  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<Project | null>(null);
  const [createError, setCreateError] = useState("");

  const [errorText, setErrorText] = useState("");
  const [diagLoading, setDiagLoading] = useState(false);
  const [diagResult, setDiagResult] = useState<DiagnoseResult | null>(null);
  const [diagError, setDiagError] = useState("");

  const handleParse = async () => {
    if (!description.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    setCreated(null);
    setCreateError("");
    try {
      const data = await api.demo.parse(description.trim());
      setResult(data);
    } catch (e: unknown) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async () => {
    if (!result) return;
    setCreating(true);
    setCreateError("");
    try {
      const project = await api.projects.create({
        name: result.project,
        description: description.trim(),
        stack: result.stack,
        intent_yaml: result.intent_yaml,
      });
      setCreated(project);
    } catch (e: unknown) {
      const msg = errorMessage(e);
      setCreateError(
        msg.includes("401") || msg.toLowerCase().includes("authentication")
          ? "Creating projects needs your own Instill instance — run the API locally or finish Setup first."
          : msg,
      );
    } finally {
      setCreating(false);
    }
  };

  const handleDiagnose = async () => {
    if (!errorText.trim()) return;
    setDiagLoading(true);
    setDiagError("");
    setDiagResult(null);
    try {
      const data = await api.demo.diagnose(errorText.trim());
      setDiagResult(data);
    } catch (e: unknown) {
      setDiagError(errorMessage(e));
    } finally {
      setDiagLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100">
      {/* Ambient */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute w-[400px] h-[400px] rounded-full blur-[120px] bg-indigo-500/5 -top-20 -left-20" />
        <div className="absolute w-[300px] h-[300px] rounded-full blur-[100px] bg-emerald-500/3 bottom-10 right-0" />
      </div>

      <div className="relative z-10 max-w-2xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-4 py-1.5 text-sm text-emerald-300 mb-6">
            <Play className="h-3.5 w-3.5" />
            Interactive Demo
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
            Try Instill
          </h1>
          <p className="mt-3 text-zinc-400 max-w-md mx-auto">
            Describe what you want to build. Instill will analyze your intent
            and show you the plan — no keys required.
          </p>
        </div>

        {/* Input */}
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.015] backdrop-blur-sm p-6 mb-6">
          <label className="block text-sm font-medium text-zinc-300 mb-3">
            What do you want to build?
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleParse();
              }
            }}
            placeholder="e.g. Build me a plus-size fashion store for Poland with BLIK payments, Shopify backend, and free shipping over 200 zł"
            rows={4}
            className="w-full rounded-xl border border-white/[0.08] bg-zinc-900/50 px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 resize-none"
          />
          <button
            onClick={handleParse}
            disabled={loading || !description.trim()}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-6 py-2.5 text-sm font-medium text-white hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Parse Intent
              </>
            )}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-400 mb-6">
            {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.015] p-6 animate-pulse">
            <div className="h-4 w-32 bg-white/[0.04] rounded mb-4" />
            <div className="h-3 w-48 bg-white/[0.03] rounded mb-3" />
            <div className="flex gap-2 mb-4">
              <div className="h-6 w-16 bg-white/[0.04] rounded-full" />
              <div className="h-6 w-20 bg-white/[0.04] rounded-full" />
            </div>
            <div className="h-3 w-full bg-white/[0.03] rounded" />
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-emerald-500/10 bg-emerald-500/[0.02] p-6">
              <h2 className="text-xl font-bold text-white mb-3">
                {result.project}
              </h2>

              <div className="flex flex-wrap gap-2 mb-4">
                <span className="inline-flex items-center gap-1 rounded-full border border-indigo-500/20 bg-indigo-500/5 px-3 py-1 text-xs text-indigo-300">
                  <Globe className="h-3 w-3" />
                  {result.stack}
                </span>
                <span className="inline-flex items-center gap-1 rounded-full border border-violet-500/20 bg-violet-500/5 px-3 py-1 text-xs text-violet-300">
                  Market: {result.market}
                </span>
              </div>

              {result.features.length > 0 && (
                <div className="mb-3">
                  <div className="flex items-center gap-1.5 text-xs text-zinc-500 mb-2">
                    <Tag className="h-3 w-3" />
                    Features
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {result.features.map((f) => (
                      <span
                        key={f}
                        className="rounded-full border border-white/[0.06] bg-white/[0.02] px-2.5 py-0.5 text-xs text-zinc-400 font-mono"
                      >
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {result.tools.length > 0 && (
                <div className="mb-3">
                  <div className="flex items-center gap-1.5 text-xs text-zinc-500 mb-2">
                    <Wrench className="h-3 w-3" />
                    Tools Required
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {result.tools.map((t) => (
                      <span
                        key={t}
                        className="rounded-full border border-amber-500/20 bg-amber-500/5 px-2.5 py-0.5 text-xs text-amber-300"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <p className="text-sm text-zinc-400 leading-relaxed mt-4 p-4 rounded-xl bg-white/[0.02] border border-white/[0.03]">
                {result.explanation}
              </p>

              {result.intent_yaml && (
                <details className="mt-4">
                  <summary className="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer">
                    View generated .powerhouse.yml
                  </summary>
                  <pre className="mt-2 p-4 rounded-xl bg-zinc-900/60 border border-white/[0.04] font-mono text-xs text-zinc-400 overflow-x-auto whitespace-pre">
                    {result.intent_yaml}
                  </pre>
                </details>
              )}

              {/* Create the project from this spec */}
              <div className="mt-5 pt-5 border-t border-white/[0.04]">
                {created ? (
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                    <p className="text-sm font-medium text-emerald-300">
                      Project “{created.name}” created.
                    </p>
                    <Link
                      href={`/dashboard/projects/${created.id}`}
                      className="mt-2 inline-flex items-center gap-2 text-sm text-emerald-400 hover:text-emerald-300"
                    >
                      Open it in the dashboard and run the first reconcile
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </div>
                ) : (
                  <>
                    <button
                      onClick={handleCreateProject}
                      disabled={creating}
                      className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-6 py-3 text-sm font-semibold text-white hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                      {creating ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Rocket className="h-4 w-4" />
                      )}
                      Create this project
                    </button>
                    <p className="mt-2 text-xs text-zinc-600">
                      Registers the project with this intent so you can reconcile
                      infrastructure from the dashboard.
                    </p>
                    {createError && (
                      <p className="mt-2 text-sm text-amber-400">{createError}</p>
                    )}
                  </>
                )}
              </div>
            </div>

            {/* CTA */}
            <div className="rounded-2xl border border-indigo-500/10 bg-indigo-500/[0.02] p-6 text-center">
              <p className="text-zinc-300 text-sm mb-4">
                Want this built for real on your own infrastructure?
              </p>
              <Link
                href="/setup"
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-6 py-3 text-sm font-semibold text-white hover:bg-indigo-400 transition-all shadow-lg shadow-indigo-500/20"
              >
                Get Started — It&apos;s free
                <ArrowRight className="h-4 w-4" />
              </Link>
              <p className="mt-2 text-xs text-zinc-600">
                Open source. Bring your own keys. Your infrastructure.
              </p>
            </div>
          </div>
        )}

        {/* ── Autofix diagnosis ── */}
        <div className="mt-16 pt-10 border-t border-white/[0.06]">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-rose-500/20 bg-rose-500/5 px-4 py-1.5 text-sm text-rose-300 mb-5">
              <Bug className="h-3.5 w-3.5" />
              Autofix · Self-healing
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Paste an error, get a fix plan
            </h2>
            <p className="mt-3 text-zinc-400 max-w-md mx-auto">
              The first stage of the autofix loop: drop in a stack trace and
              Instill diagnoses the root cause — no keys required.
            </p>
          </div>

          {/* Input */}
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.015] backdrop-blur-sm p-6 mb-6">
            <label className="block text-sm font-medium text-zinc-300 mb-3">
              Paste an error message or stack trace
            </label>
            <textarea
              value={errorText}
              onChange={(e) => setErrorText(e.target.value)}
              placeholder={
                "e.g. TypeError: Cannot read properties of undefined (reading 'map')\n  at ProductList (src/app/products/page.tsx:42:18)"
              }
              rows={4}
              className="w-full rounded-xl border border-white/[0.08] bg-zinc-900/50 px-4 py-3 text-sm text-zinc-200 font-mono placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-rose-500/50 focus:border-rose-500/50 resize-none"
            />
            <button
              onClick={handleDiagnose}
              disabled={diagLoading || !errorText.trim()}
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-rose-500 px-6 py-2.5 text-sm font-medium text-white hover:bg-rose-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {diagLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Diagnosing...
                </>
              ) : (
                <>
                  <Bug className="h-4 w-4" />
                  Diagnose
                </>
              )}
            </button>
          </div>

          {/* Error */}
          {diagError && (
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-400 mb-6">
              {diagError}
            </div>
          )}

          {/* Loading skeleton */}
          {diagLoading && (
            <div className="rounded-2xl border border-white/[0.06] bg-white/[0.015] p-6 animate-pulse">
              <div className="h-4 w-40 bg-white/[0.04] rounded mb-4" />
              <div className="h-3 w-56 bg-white/[0.03] rounded mb-3" />
              <div className="h-3 w-full bg-white/[0.03] rounded mb-2" />
              <div className="h-3 w-2/3 bg-white/[0.03] rounded" />
            </div>
          )}

          {/* Result */}
          {diagResult && (
            <div className="rounded-2xl border border-white/[0.06] bg-white/[0.015] p-6">
              <div className="flex items-center gap-2 flex-wrap mb-4">
                <span
                  className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium ${
                    SEVERITY_STYLES[diagResult.severity] || SEVERITY_STYLES.medium
                  }`}
                >
                  <AlertTriangle className="h-3 w-3" />
                  {diagResult.severity} severity
                </span>
                <span className="rounded-full border border-white/[0.06] bg-white/[0.02] px-2.5 py-1 text-xs text-zinc-400 font-mono">
                  {diagResult.category}
                </span>
                <span className="ml-auto text-xs text-zinc-600">
                  {diagResult.source === "llm" ? "LLM-assisted" : "heuristic"} ·{" "}
                  {diagResult.confidence} confidence
                </span>
              </div>

              <h3 className="text-lg font-semibold text-white mb-2">
                {diagResult.summary}
              </h3>
              <p className="text-sm text-zinc-400 leading-relaxed mb-5">
                {diagResult.root_cause}
              </p>

              {diagResult.suggested_fix.length > 0 && (
                <div className="mb-5">
                  <div className="flex items-center gap-1.5 text-xs text-zinc-500 mb-2">
                    <Wrench className="h-3 w-3" />
                    Suggested fix
                  </div>
                  <ol className="space-y-2">
                    {diagResult.suggested_fix.map((step, i) => (
                      <li
                        key={i}
                        className="flex gap-2.5 text-sm text-zinc-300 rounded-xl bg-white/[0.02] border border-white/[0.03] px-3 py-2"
                      >
                        <span className="text-rose-400 font-mono text-xs mt-0.5">
                          {i + 1}
                        </span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {diagResult.likely_files.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 text-xs text-zinc-500 mb-2">
                    <FileCode className="h-3 w-3" />
                    Likely files
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {diagResult.likely_files.map((f) => (
                      <span
                        key={f}
                        className="rounded-full border border-white/[0.06] bg-white/[0.02] px-2.5 py-0.5 text-xs text-zinc-400 font-mono"
                      >
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
