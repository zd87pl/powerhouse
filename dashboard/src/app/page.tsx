"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Play,
  Zap,
  Github,
  Globe,
  CheckCircle2,
  KeyRound,
  Terminal,
  Sparkles,
} from "lucide-react";

const SETUP_STEPS = [
  { icon: KeyRound, label: "Connect GitHub", detail: "One-click OAuth" },
  { icon: Globe, label: "Connect Vercel", detail: "Paste your token" },
  { icon: Terminal, label: "Deploy API", detail: "Auto-provisioned on Fly.io" },
  { icon: CheckCircle2, label: "You're live", detail: "Start building" },
];

const DEMO_MESSAGES = [
  {
    role: "user",
    text: "Build me a plus-size fashion store for Poland with BLIK payments",
  },
  {
    role: "ai",
    text: "Analyzing intent...\n\nGot it. I'll set up `curvy-poland` — a Next.js storefront with Shopify backend, BLIK + Przelewy24 payments, size guide XL–6XL, and free shipping threshold at 200 zł.",
  },
  {
    role: "ai",
    text: "Generating project files, creating GitHub repo, configuring Vercel deploy...",
  },
  {
    role: "ai",
    text: "✅ Live at curvy-poland.vercel.app — 3m 47s total",
    isResult: true,
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 overflow-hidden">
      {/* Ambient orbs */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute w-[500px] h-[500px] rounded-full blur-[150px] bg-indigo-500/5 -top-40 -left-40" />
        <div className="absolute w-[400px] h-[400px] rounded-full blur-[120px] bg-violet-500/4 top-1/3 -right-20" />
        <div className="absolute w-[300px] h-[300px] rounded-full blur-[100px] bg-emerald-500/3 bottom-0 left-1/4" />
      </div>

      {/* Nav */}
      <nav className="relative z-10 border-b border-white/[0.04]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-400" />
            <span className="font-bold text-lg tracking-tight">Instill</span>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="https://github.com/zd87pl/powerhouse"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <Github className="h-4 w-4" />
              <span className="hidden sm:inline">GitHub</span>
            </a>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 pt-24 pb-16 sm:pt-32 sm:pb-20 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/20 bg-indigo-500/5 px-4 py-1.5 text-sm text-indigo-300 mb-8">
          <Zap className="h-3.5 w-3.5" />
          Open source • BYOK • Self-hosted
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-tight">
          Your own{" "}
          <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
            AI engineering
          </span>{" "}
          platform
        </h1>
        <p className="mt-6 text-lg sm:text-xl text-zinc-400 max-w-2xl mx-auto leading-relaxed">
          Describe what you want to build. Instill provisions repos, generates
          code, and deploys to production — all on your own infrastructure
          with your own keys.
        </p>

        {/* Dual CTAs */}
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/setup"
            className="group inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-8 py-4 text-base font-semibold text-white shadow-lg shadow-indigo-500/25 hover:bg-indigo-400 transition-all"
          >
            Get Started
            <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
          </Link>
          <Link
            href="/demo"
            className="group inline-flex items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.02] px-8 py-4 text-base font-medium text-zinc-300 hover:bg-white/[0.04] hover:border-white/[0.12] transition-all backdrop-blur-sm"
          >
            <Play className="h-4 w-4" />
            Try Demo
          </Link>
        </div>

        <p className="mt-3 text-xs text-zinc-600">
          No terminal required. Demo runs instantly — no keys needed.
        </p>
      </section>

      {/* How it works */}
      <section className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 pb-16">
        <h2 className="text-center text-2xl sm:text-3xl font-bold mb-12">
          Four steps to your own platform
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {SETUP_STEPS.map((step, i) => (
            <div
              key={step.label}
              className="group relative rounded-2xl border border-white/[0.04] bg-white/[0.015] p-6 backdrop-blur-sm hover:bg-white/[0.03] hover:border-white/[0.08] transition-all"
            >
              <div className="flex items-center gap-2 mb-3">
                <step.icon className="h-5 w-5 text-indigo-400" />
                <span className="text-xs font-mono text-zinc-600">
                  {i + 1}/4
                </span>
              </div>
              <h3 className="font-semibold text-zinc-200 mb-1">
                {step.label}
              </h3>
              <p className="text-sm text-zinc-500">{step.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Chat demo */}
      <section className="relative z-10 max-w-2xl mx-auto px-4 sm:px-6 pb-24">
        <h2 className="text-center text-2xl sm:text-3xl font-bold mb-8">
          Just describe it. We handle the rest.
        </h2>
        <p className="text-center text-zinc-500 mb-10 max-w-lg mx-auto">
          No YAML required. Just tell Instill what you want to build.
        </p>

        <div className="space-y-4">
          {DEMO_MESSAGES.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "gap-3"}`}
            >
              {msg.role === "ai" && (
                <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-xs shrink-0 mt-1">
                  ⚡
                </div>
              )}
              <div
                className={`rounded-2xl px-5 py-3 max-w-[85%] sm:max-w-[75%] whitespace-pre-line ${
                  msg.role === "user"
                    ? "bg-indigo-500 text-white rounded-br-md"
                    : msg.isResult
                      ? "bg-emerald-500/10 border border-emerald-500/20 rounded-bl-md"
                      : "bg-white/[0.03] border border-white/[0.04] rounded-bl-md"
                }`}
              >
                <p
                  className={`text-sm leading-relaxed ${
                    msg.role === "user" ? "text-white" : msg.isResult ? "text-emerald-300" : "text-zinc-300"
                  }`}
                >
                  {msg.text}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Collapsible config */}
        <details className="group mt-4 ml-11">
          <summary className="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer inline-flex items-center gap-1 mb-2">
            <svg
              className="w-3 h-3 transition-transform group-open:rotate-90"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
            See the generated config
          </summary>
          <div className="bg-zinc-900/50 border border-white/[0.04] rounded-xl p-4 font-mono text-xs text-zinc-500 leading-relaxed overflow-x-auto">
            <pre>{`project: curvy-poland
stack: nextjs
market: PL
features:
  - ecommerce-storefront
  - size-guide-xl-6xl
  - blik-payments
  - free-shipping-threshold
tools:
  - Shopify
  - Stripe`}</pre>
          </div>
        </details>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/[0.04] py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-zinc-600">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            <span>Instill — Autonomous AI Engineering</span>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com/zd87pl/powerhouse"
              target="_blank"
              rel="noreferrer"
              className="hover:text-zinc-400 transition-colors"
            >
              Open Source (MIT)
            </a>
            <span>Bring Your Own Keys</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
