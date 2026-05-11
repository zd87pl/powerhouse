"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Loader2, Play, Sparkles, Tag, Wrench, Globe } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://instill-api.fly.dev/api";

interface ParseResult {
  project: string;
  stack: string;
  market: string;
  features: string[];
  tools: string[];
  explanation: string;
  required_keys: string[];
}

export default function DemoPage() {
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ParseResult | null>(null);
  const [error, setError] = useState("");

  const handleParse = async () => {
    if (!description.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: description.trim() }),
      });
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err || `API error: ${res.status}`);
      }
      const data: ParseResult = await res.json();
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
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
      </div>
    </div>
  );
}
