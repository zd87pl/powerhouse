"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  Globe,
  KeyRound,
  Loader2,
  Rocket,
  ShieldCheck,
  Sparkles,
  Terminal,
  XCircle,
} from "lucide-react";
import { api, type SetupProviderStatus, type SetupStatus } from "@/lib/api";

interface WizardStep {
  id: string;
  label: string;
  icon: typeof KeyRound;
  description: string;
}

const STEPS: WizardStep[] = [
  {
    id: "github",
    label: "Connect GitHub",
    icon: KeyRound,
    description: "Instill creates repos and manages code on your behalf",
  },
  {
    id: "vercel",
    label: "Connect Vercel",
    icon: Globe,
    description: "Instill deploys your generated projects to Vercel",
  },
  {
    id: "openrouter",
    label: "Connect OpenRouter",
    icon: Sparkles,
    description: "Powers the AI that understands your intent",
  },
  {
    id: "deploy",
    label: "Deploy Your API",
    icon: Rocket,
    description: "Spin up your personal Instill API instance",
  },
];

const PROVIDER_CONFIG: Record<string, { docsLabel: string; signupUrl: string; docsUrl: string }> = {
  github: {
    docsLabel: "Create a personal access token",
    signupUrl: "https://github.com/signup",
    docsUrl: "https://github.com/settings/tokens/new?scopes=repo,workflow&description=Instill",
  },
  vercel: {
    docsLabel: "Create a Vercel token",
    signupUrl: "https://vercel.com/signup",
    docsUrl: "https://vercel.com/account/settings/tokens",
  },
  openrouter: {
    docsLabel: "Create an OpenRouter API key",
    signupUrl: "https://openrouter.ai/sign-up",
    docsUrl: "https://openrouter.ai/settings/keys",
  },
};

export default function SetupPage() {
  const [step, setStep] = useState(0);
  const [setup, setSetup] = useState<SetupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [error, setError] = useState("");

  // Key inputs
  const [githubToken, setGithubToken] = useState("");
  const [vercelToken, setVercelToken] = useState("");
  const [openrouterKey, setOpenrouterKey] = useState("");

  // Validation results
  const [githubValid, setGithubValid] = useState<boolean | null>(null);
  const [githubAccount, setGithubAccount] = useState("");
  const [vercelValid, setVercelValid] = useState<boolean | null>(null);
  const [vercelAccount, setVercelAccount] = useState("");

  // Referral
  const [referralUrl, setReferralUrl] = useState<string | null>(null);

  const fetchSetup = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.setup.status();
      setSetup(s);

      // Check for referral URL from OpenRouter provider
      const orProvider = s.providers.find((p) => p.provider === "openrouter");
      if (orProvider?.referral_url) {
        setReferralUrl(orProvider.referral_url);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not fetch setup status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchSetup();
  }, [fetchSetup]);

  const validateProvider = async (provider: string) => {
    setValidating(true);
    setError("");
    try {
      const result = await api.setup.validate(provider);
      const success = result.status === "connected" || result.status === "passed";
      if (provider === "github") {
        setGithubValid(success);
        setGithubAccount(result.account?.login || "");
      } else if (provider === "vercel") {
        setVercelValid(success);
        setVercelAccount(result.account?.email || result.account?.username || "");
      }
      await fetchSetup();
      return success;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Validation failed");
      return false;
    } finally {
      setValidating(false);
    }
  };

  const handleDeploy = async () => {
    setDeploying(true);
    setError("");
    try {
      // Poll setup status until ready
      for (let i = 0; i < 20; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        const s = await api.setup.status();
        setSetup(s);
        if (s.ready && s.connected >= 4) break;
      }
      await fetchSetup();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Deploy check failed");
    } finally {
      setDeploying(false);
    }
  };

  const canAdvance = () => {
    switch (step) {
      case 0: return githubValid === true;
      case 1: return vercelValid === true;
      case 2: return openrouterKey.length > 0;
      case 3: return setup?.ready === true;
      default: return false;
    }
  };

  const getProviderCards = (): SetupProviderStatus[] => {
    if (!setup) return [];
    return ["github", "vercel", "openrouter", "flyio"]
      .map((id) => setup.providers.find((p) => p.provider === id))
      .filter(Boolean) as SetupProviderStatus[];
  };

  if (loading && !setup) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100">
      {/* Ambient */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute w-[500px] h-[500px] rounded-full blur-[150px] bg-indigo-500/5 -top-40 left-1/4" />
      </div>

      <div className="relative z-10 max-w-2xl mx-auto px-4 sm:px-6 py-12 sm:py-20">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
            Set Up Your Platform
          </h1>
          <p className="mt-3 text-zinc-400">
            Bring your own keys. Everything runs on your infrastructure.
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-1 mb-12">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex items-center">
              <button
                onClick={() => i < step && setStep(i)}
                className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-all ${
                  i === step
                    ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                    : i < step
                      ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 cursor-pointer"
                      : "bg-white/[0.02] text-zinc-600 border border-white/[0.04]"
                }`}
              >
                {i < step ? (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                ) : (
                  <span className="text-xs font-mono">{i + 1}</span>
                )}
                <span className="hidden sm:inline">{s.label}</span>
              </button>
              {i < STEPS.length - 1 && (
                <div
                  className={`w-6 h-px mx-1 ${
                    i < step ? "bg-emerald-500/30" : "bg-white/[0.06]"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Error banner */}
        {error && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-400 mb-6 flex items-start gap-3">
            <XCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Step 0: GitHub */}
        {step === 0 && (
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.015] backdrop-blur-sm p-8">
            <div className="flex items-center gap-3 mb-6">
              <KeyRound className="h-6 w-6 text-indigo-400" />
              <div>
                <h2 className="text-xl font-bold">Connect GitHub</h2>
                <p className="text-sm text-zinc-500 mt-1">
                  Instill creates repos and manages code on your behalf
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-zinc-500">Don&apos;t have an account?</span>
                <a
                  href="https://github.com/signup"
                  target="_blank"
                  rel="noreferrer"
                  className="text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1"
                >
                  Sign up on GitHub
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  GitHub Personal Access Token
                </label>
                <div className="flex gap-2">
                  <input
                    type="password"
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                    placeholder="ghp_..."
                    className="flex-1 rounded-xl border border-white/[0.08] bg-zinc-900/50 px-4 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                  <button
                    onClick={() => validateProvider("github")}
                    disabled={validating || !githubToken}
                    className="inline-flex items-center gap-2 rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-4 py-2.5 text-sm font-medium text-indigo-300 hover:bg-indigo-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all shrink-0"
                  >
                    {validating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ShieldCheck className="h-4 w-4" />
                    )}
                    Validate
                  </button>
                </div>
                <a
                  href="https://github.com/settings/tokens/new?scopes=repo,workflow&description=Instill"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 mt-2 text-xs text-zinc-500 hover:text-zinc-300"
                >
                  How to create a token
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              {githubValid === true && (
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-center gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-emerald-300">
                      Connected as {githubAccount || "your GitHub account"}
                    </p>
                    <p className="text-xs text-emerald-500/70 mt-0.5">
                      Token has the required permissions
                    </p>
                  </div>
                </div>
              )}

              {githubValid === false && (
                <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 flex items-center gap-3">
                  <XCircle className="h-5 w-5 text-red-400 shrink-0" />
                  <p className="text-sm text-red-300">
                    Token validation failed. Make sure it has the &apos;repo&apos; scope.
                  </p>
                </div>
              )}
            </div>

            <button
              onClick={() => setStep(1)}
              disabled={!canAdvance()}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-6 py-3 text-sm font-semibold text-white hover:bg-indigo-400 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              Next: Connect Vercel
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Step 1: Vercel */}
        {step === 1 && (
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.015] backdrop-blur-sm p-8">
            <div className="flex items-center gap-3 mb-6">
              <Globe className="h-6 w-6 text-indigo-400" />
              <div>
                <h2 className="text-xl font-bold">Connect Vercel</h2>
                <p className="text-sm text-zinc-500 mt-1">
                  Instill deploys your generated projects to Vercel
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-zinc-500">Don&apos;t have an account?</span>
                <a
                  href="https://vercel.com/signup"
                  target="_blank"
                  rel="noreferrer"
                  className="text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1"
                >
                  Sign up on Vercel
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Vercel Token
                </label>
                <div className="flex gap-2">
                  <input
                    type="password"
                    value={vercelToken}
                    onChange={(e) => setVercelToken(e.target.value)}
                    placeholder="vcp_..."
                    className="flex-1 rounded-xl border border-white/[0.08] bg-zinc-900/50 px-4 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                  <button
                    onClick={() => validateProvider("vercel")}
                    disabled={validating || !vercelToken}
                    className="inline-flex items-center gap-2 rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-4 py-2.5 text-sm font-medium text-indigo-300 hover:bg-indigo-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all shrink-0"
                  >
                    {validating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ShieldCheck className="h-4 w-4" />
                    )}
                    Validate
                  </button>
                </div>
                <a
                  href="https://vercel.com/account/settings/tokens"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 mt-2 text-xs text-zinc-500 hover:text-zinc-300"
                >
                  How to create a token
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              {vercelValid === true && (
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-center gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-emerald-300">
                      Connected{vercelAccount ? ` as ${vercelAccount}` : ""}
                    </p>
                    <p className="text-xs text-emerald-500/70 mt-0.5">
                      Token is valid and active
                    </p>
                  </div>
                </div>
              )}

              {vercelValid === false && (
                <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 flex items-center gap-3">
                  <XCircle className="h-5 w-5 text-red-400 shrink-0" />
                  <p className="text-sm text-red-300">
                    Token validation failed. Check your token and try again.
                  </p>
                </div>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setStep(0)}
                className="rounded-xl border border-white/[0.08] px-5 py-3 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03] transition-all"
              >
                Back
              </button>
              <button
                onClick={() => setStep(2)}
                disabled={!canAdvance()}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-6 py-3 text-sm font-semibold text-white hover:bg-indigo-400 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                Next: Connect OpenRouter
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: OpenRouter */}
        {step === 2 && (
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.015] backdrop-blur-sm p-8">
            <div className="flex items-center gap-3 mb-6">
              <Sparkles className="h-6 w-6 text-indigo-400" />
              <div>
                <h2 className="text-xl font-bold">Connect OpenRouter</h2>
                <p className="text-sm text-zinc-500 mt-1">
                  Powers the AI that understands your intent and generates code
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-zinc-500">Don&apos;t have an account?</span>
                <a
                  href="https://openrouter.ai/sign-up"
                  target="_blank"
                  rel="noreferrer"
                  className="text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1"
                >
                  Sign up on OpenRouter
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              {referralUrl && (
                <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                  <p className="text-sm text-amber-300">
                    💡 New to OpenRouter? Use this referral link for bonus credits:
                  </p>
                  <a
                    href={referralUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-flex items-center gap-1 text-sm text-amber-400 hover:text-amber-300 font-mono"
                  >
                    {referralUrl}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  OpenRouter API Key
                </label>
                <input
                  type="password"
                  value={openrouterKey}
                  onChange={(e) => setOpenrouterKey(e.target.value)}
                  placeholder="sk-or-v1-..."
                  className="w-full rounded-xl border border-white/[0.08] bg-zinc-900/50 px-4 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
                <a
                  href="https://openrouter.ai/settings/keys"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 mt-2 text-xs text-zinc-500 hover:text-zinc-300"
                >
                  How to create a key
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              {openrouterKey.length > 0 && (
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-center gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
                  <p className="text-sm text-emerald-300">
                    API key saved. You can validate it after deployment.
                  </p>
                </div>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setStep(1)}
                className="rounded-xl border border-white/[0.08] px-5 py-3 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03] transition-all"
              >
                Back
              </button>
              <button
                onClick={() => setStep(3)}
                disabled={!canAdvance()}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-6 py-3 text-sm font-semibold text-white hover:bg-indigo-400 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                Next: Deploy
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Deploy */}
        {step === 3 && (
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.015] backdrop-blur-sm p-8">
            <div className="flex items-center gap-3 mb-6">
              <Rocket className="h-6 w-6 text-indigo-400" />
              <div>
                <h2 className="text-xl font-bold">Ready to Deploy</h2>
                <p className="text-sm text-zinc-500 mt-1">
                  All providers configured. Deploy your personal Instill API.
                </p>
              </div>
            </div>

            {/* Provider summary */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
              {getProviderCards().map((provider) => (
                <div
                  key={provider.provider}
                  className="rounded-xl border border-white/[0.04] bg-white/[0.01] p-4"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-zinc-300">
                      {provider.label}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        provider.status === "connected"
                          ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                          : provider.status === "configured"
                            ? "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                            : "bg-red-500/10 text-red-300 border border-red-500/20"
                      }`}
                    >
                      {provider.status}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-600 mt-1">
                    {provider.status === "connected"
                      ? "Ready"
                      : provider.status === "configured"
                        ? "Needs validation"
                        : "Not configured"}
                  </p>
                </div>
              ))}
            </div>

            {/* Deploy button */}
            <button
              onClick={handleDeploy}
              disabled={deploying}
              className="w-full inline-flex items-center justify-center gap-3 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 px-6 py-4 text-base font-semibold text-white hover:from-indigo-400 hover:to-violet-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-indigo-500/25"
            >
              {deploying ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Deploying your API...
                </>
              ) : (
                <>
                  <Rocket className="h-5 w-5" />
                  Deploy to Fly.io
                </>
              )}
            </button>

            {deploying && (
              <div className="mt-4 rounded-xl border border-indigo-500/10 bg-indigo-500/[0.02] p-4">
                <div className="flex items-center gap-2 text-sm text-indigo-300">
                  <Terminal className="h-4 w-4" />
                  <span>Provisioning infrastructure, setting secrets, deploying...</span>
                </div>
                <div className="mt-3 flex gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse [animation-delay:0.2s]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse [animation-delay:0.4s]" />
                </div>
              </div>
            )}

            {setup?.ready && (
              <div className="mt-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6 text-center">
                <CheckCircle2 className="h-10 w-10 text-emerald-400 mx-auto mb-3" />
                <h3 className="text-lg font-bold text-emerald-300 mb-2">
                  Your platform is live!
                </h3>
                <p className="text-sm text-emerald-400/70 mb-4">
                  All providers connected. Instill API is running on Fly.io.
                </p>
                <Link
                  href="/dashboard"
                  className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-6 py-3 text-sm font-semibold text-white hover:bg-emerald-400 transition-all"
                >
                  Go to Dashboard
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            )}

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setStep(2)}
                disabled={deploying}
                className="rounded-xl border border-white/[0.08] px-5 py-3 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03] transition-all disabled:opacity-50"
              >
                Back
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
