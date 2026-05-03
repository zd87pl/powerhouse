export default function HomePage() {
  return (
    <main>
      {/* ── HERO ── */}
      <section className="min-h-[90vh] flex flex-col items-center justify-center px-6 text-center relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(124,58,237,0.15),transparent_70%)]" />
        <div className="relative z-10 max-w-4xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface border border-border text-sm text-accent mb-8">
            <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
            Now in public beta
          </div>
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.05] mb-6">
            Build a business<br />
            <span className="text-accent">in 5 minutes.</span>
          </h1>
          <p className="text-xl sm:text-2xl text-muted max-w-2xl mx-auto mb-4">
            Not just an app. A complete business — storefront, payments,
            inventory, marketing. All built, deployed, monitored, and
            self-healing.
          </p>
          <p className="text-lg text-zinc-600 max-w-xl mx-auto mb-10">
            You describe the idea. AI builds everything. It fixes itself
            while you sleep. You wake up to a growing business.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="https://dashboard-chi-ivory-99.vercel.app/sign-up"
              className="px-8 py-4 bg-accent-glow hover:bg-violet-700 text-white rounded-xl font-semibold text-lg transition-all hover:shadow-[0_0_40px_rgba(124,58,237,0.3)]"
            >
              Start Building Free →
            </a>
            <a
              href="#demo"
              className="px-8 py-4 bg-surface border border-border hover:border-accent text-text rounded-xl font-semibold text-lg transition-all"
            >
              See How It Works ↓
            </a>
          </div>
          <p className="text-sm text-zinc-600 mt-6">
            No credit card. Build your first project in under 5 minutes.
          </p>
        </div>
      </section>

      {/* ── DEMO ── */}
      <section id="demo" className="py-24 px-6 max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            Just describe it.{" "}
            <span className="text-accent">We handle the rest.</span>
          </h2>
          <p className="text-muted text-lg max-w-2xl mx-auto">
            No YAML required. Just tell Powerhouse what you want to
            build — it extracts the intent, generates the config,
            and builds everything while you watch.
          </p>
        </div>

        {/* Chat Demo — knowledge compression in action */}
        <div className="max-w-2xl mx-auto mb-8">
          {/* User message */}
          <div className="flex justify-end mb-4">
            <div className="bg-accent-glow text-white rounded-2xl rounded-br-md px-5 py-3 max-w-[85%] sm:max-w-[75%]">
              <p className="text-sm sm:text-base">
                Build me a plus-size fashion store for Poland. I need BLIK
                payments, sizes XL to 6XL, free shipping over 200 zł, and
                Shopify backend.
              </p>
            </div>
          </div>

          {/* Powerhouse thinking */}
          <div className="flex gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-accent-glow/20 border border-accent-glow/30 flex items-center justify-center text-xs shrink-0 mt-1">
              ⚡
            </div>
            <div className="bg-surface border border-border rounded-2xl rounded-bl-md px-5 py-3 max-w-[85%] sm:max-w-[75%]">
              <p className="text-xs text-muted mb-2 font-mono">
                Analyzing intent...
              </p>
              <p className="text-sm text-text leading-relaxed">
                Got it. I&apos;ll set up{" "}
                <span className="text-accent">bez-spinki</span> — a
                Next.js storefront with Shopify checkout, BLIK
                integration, size guide (XL–6XL), and free shipping
                threshold at 200 zł. Inventory sync from your suppliers.
                Margin monitoring and A/B testing agents included.
              </p>
            </div>
          </div>

          {/* Generated YAML — expandable */}
          <details className="group mb-3 ml-11">
            <summary className="text-xs text-muted hover:text-accent cursor-pointer transition-colors inline-flex items-center gap-1 mb-2">
              <svg className="w-3 h-3 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              See the generated config
            </summary>
            <div className="bg-bg border border-border/50 rounded-xl p-4 font-mono text-xs text-muted leading-relaxed overflow-x-auto">
              <pre>{`project: bez-spinki
stack: nextjs
market: PL

features:
  - shopify-checkout
  - blik-payments
  - size-guide-xl-6xl
  - free-shipping-200pln

business_agents:
  merchandising: true
  growth: true

monitoring:
  sentry: true
  autofix: true`}</pre>
            </div>
          </details>

          {/* Build started */}
          <div className="flex gap-3 ml-11">
            <div className="bg-surface border border-border rounded-2xl rounded-bl-md px-5 py-3 max-w-[85%] sm:max-w-[75%]">
              <div className="flex items-center gap-3 mb-2">
                <span className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                  <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse [animation-delay:0.2s]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse [animation-delay:0.4s]" />
                </span>
                <span className="text-xs text-muted font-mono">
                  Building...
                </span>
              </div>
              <div className="space-y-1">
                {[
                  { label: "GitHub repo", done: true },
                  { label: "Next.js scaffold", done: true },
                  { label: "Shopify integration", done: true },
                  { label: "Vercel deploy", done: false },
                ].map((step) => (
                  <div
                    key={step.label}
                    className="flex items-center gap-2 text-xs"
                  >
                    <span
                      className={
                        step.done
                          ? "text-success"
                          : "text-muted animate-pulse"
                      }
                    >
                      {step.done ? "✓" : "○"}
                    </span>
                    <span
                      className={
                        step.done ? "text-muted" : "text-text"
                      }
                    >
                      {step.label}
                    </span>
                    {step.done && (
                      <span className="text-zinc-700 font-mono">
                        1.2s
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Live URL */}
          <div className="flex gap-3 mt-4 ml-11">
            <div className="bg-surface border border-success/30 rounded-2xl rounded-bl-md px-5 py-3">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-success" />
                <span className="text-xs text-muted">Live at</span>
                <span className="text-sm text-accent font-mono">
                  bez-spinki.vercel.app
                </span>
                <span className="text-xs text-zinc-700">4m 32s</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              emoji: "🛍️",
              title: "Live Store",
              desc: "Next.js storefront, Polish UX, BLIK payments. Your domain.",
            },
            {
              emoji: "📦",
              title: "Inventory",
              desc: "Products synced from suppliers. Real stock. Real prices.",
            },
            {
              emoji: "📊",
              title: "Growth Engine",
              desc: "Margin monitoring, A/B testing, traffic anomaly detection.",
            },
            {
              emoji: "🔧",
              title: "Self-Healing",
              desc: "Bug at 3am? Fixed before you wake up. PR waiting for you.",
            },
          ].map((item) => (
            <div
              key={item.title}
              className="bg-surface border border-border rounded-xl p-6 hover:border-accent/30 transition-colors"
            >
              <div className="text-2xl mb-3">{item.emoji}</div>
              <h3 className="font-semibold text-text mb-1">{item.title}</h3>
              <p className="text-sm text-muted">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── OPENJARVIS HYBRID ── */}
      <section className="py-24 px-6 max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            Runs on your machine.
            <br />
            <span className="text-accent">Escalates to the cloud</span>{" "}
            when it matters.
          </h2>
          <p className="text-muted text-lg max-w-2xl mx-auto">
            Powered by{" "}
            <span className="text-text font-semibold">OpenJarvis</span>{" "}
            — Stanford&apos;s local-first AI framework. Simple tasks run
            instantly on your device. Complex builds scale to our agent
            swarm. You never choose — the system routes intelligently.
          </p>
        </div>

        {/* Split panel */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-12">
          {/* Local side */}
          <div className="bg-surface border border-border rounded-2xl p-6 sm:p-8 relative overflow-hidden">
            <div className="absolute top-0 right-0 px-3 py-1 bg-accent-glow/10 border-b border-l border-accent-glow/20 rounded-bl-lg text-xs text-accent font-mono">
              YOUR MACHINE
            </div>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-success/10 border border-success/20 flex items-center justify-center text-lg">
                🖥️
              </div>
              <div>
                <h3 className="font-semibold text-text">
                  Local Agent
                </h3>
                <p className="text-xs text-muted">
                  OpenJarvis · Qwen 4B · Instant
                </p>
              </div>
            </div>

            <div className="space-y-3">
              {[
                {
                  q: "What's my margin on Sukienki XL?",
                  t: "0.3s",
                  label: "Margin check",
                },
                {
                  q: "Summarize today's orders",
                  t: "0.8s",
                  label: "Order summary",
                },
                {
                  q: "Is the BLIK payment gateway up?",
                  t: "0.2s",
                  label: "Health check",
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="bg-bg rounded-xl p-3 border border-border/50"
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="text-xs text-muted font-mono">
                      {item.label}
                    </span>
                    <span className="text-xs text-success font-mono shrink-0">
                      {item.t}
                    </span>
                  </div>
                  <p className="text-sm text-text">{item.q}</p>
                </div>
              ))}
            </div>

            <div className="mt-4 flex items-center gap-2 text-xs text-muted">
              <span className="w-1.5 h-1.5 rounded-full bg-success" />
              Private · Offline capable · $0 per query
            </div>
          </div>

          {/* Cloud side */}
          <div className="bg-surface border border-border rounded-2xl p-6 sm:p-8 relative overflow-hidden">
            <div className="absolute top-0 right-0 px-3 py-1 bg-accent-glow/10 border-b border-l border-accent-glow/20 rounded-bl-lg text-xs text-accent font-mono">
              POWERHOUSE CLOUD
            </div>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-accent-glow/10 border border-accent-glow/20 flex items-center justify-center text-lg">
                ☁️
              </div>
              <div>
                <h3 className="font-semibold text-text">
                  Agent Swarm
                </h3>
                <p className="text-xs text-muted">
                  Claude Opus · 5 agents · Full power
                </p>
              </div>
            </div>

            <div className="space-y-3">
              {[
                {
                  q: "Build me a complete store with Shopify + BLIK",
                  t: "4m 32s",
                  label: "Full build",
                },
                {
                  q: "Analyze traffic anomaly on /sukienki",
                  t: "12s",
                  label: "Growth analysis",
                },
                {
                  q: "Deploy hotfix for checkout crash",
                  t: "45s",
                  label: "Emergency fix",
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="bg-bg rounded-xl p-3 border border-border/50"
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="text-xs text-muted font-mono">
                      {item.label}
                    </span>
                    <span className="text-xs text-accent font-mono shrink-0">
                      {item.t}
                    </span>
                  </div>
                  <p className="text-sm text-text">{item.q}</p>
                </div>
              ))}
            </div>

            <div className="mt-4 flex items-center gap-2 text-xs text-muted">
              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
              Full agent swarm · Deliberation council · Persistent memory
            </div>
          </div>
        </div>

        {/* Flow indicator */}
        <div className="flex items-center justify-center gap-4 text-sm text-muted">
          <span>Simple queries</span>
          <span className="flex items-center gap-1">
            <span className="w-16 h-0.5 bg-success/30 rounded-full" />
            <span className="text-success text-xs">local</span>
          </span>
          <span className="text-zinc-600">·</span>
          <span className="flex items-center gap-1">
            <span className="text-accent text-xs">cloud</span>
            <span className="w-16 h-0.5 bg-accent/30 rounded-full" />
          </span>
          <span>Complex builds</span>
        </div>

        <div className="text-center mt-8">
          <p className="text-xs text-zinc-600 max-w-lg mx-auto">
            Built on{" "}
            <a
              href="https://github.com/open-jarvis/OpenJarvis"
              className="text-accent hover:underline"
            >
              OpenJarvis
            </a>
            {" "}— Stanford Hazy Research. Local-first, cloud when needed.
            Same skills catalog. Same agent standard.
          </p>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="py-24 px-6 bg-surface/30">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-16">
            How it actually works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                step: "1",
                title: "You describe the idea",
                body: 'One YAML file. Or just type what you want. "A plus-size fashion store for Poland with BLIK payments."',
              },
              {
                step: "2",
                title: "Agent swarm builds it",
                body: "Architect designs. Coder implements. Reviewer validates. DevOps deploys. They loop until it's perfect.",
              },
              {
                step: "3",
                title: "It runs itself",
                body: "Merchandising agent watches margins. Growth agent runs A/B tests. Autofix daemon patches bugs at 3am.",
              },
            ].map((item) => (
              <div
                key={item.step}
                className="relative bg-bg border border-border rounded-2xl p-8"
              >
                <div className="w-10 h-10 rounded-full bg-accent-glow/10 border border-accent-glow/30 flex items-center justify-center text-accent font-bold mb-6">
                  {item.step}
                </div>
                <h3 className="text-xl font-semibold mb-3">{item.title}</h3>
                <p className="text-muted leading-relaxed">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── AUTONOMY DIFFERENCE ── */}
      <section className="py-24 px-6 max-w-6xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-bold text-center mb-6">
          Not just scaffolding.<br />
          <span className="text-accent">Autonomous operations.</span>
        </h2>
        <p className="text-muted text-lg text-center max-w-2xl mx-auto mb-16">
          Every other tool stops at &quot;here&apos;s your code.&quot; Powerhouse
          keeps working long after you close your laptop.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {[
            {
              title: "Agent Swarm",
              desc: "5 specialized agents work together. Architect → Coder → Reviewer → DevOps → Tester. They iterate until the Reviewer says PASS.",
            },
            {
              title: "Deliberation Council",
              desc: "High-stakes actions require 5-agent approval. Hotfix deploy? Council votes. Rollback? Council rejects. No rogue automation.",
            },
            {
              title: "Episodic Memory",
              desc: 'Every decision remembered. Every error pattern learned. "Have we seen this bug before?" → Yes, here\'s what fixed it last time.',
            },
            {
              title: "Business Agents",
              desc: "Merchandising agent watches your margins. Growth agent optimizes your conversion. Like having a team that never sleeps.",
            },
            {
              title: "Model Router",
              desc: "Complex architecture → Claude Opus. Quick fixes → Llama (free). Saves 70% on API costs without sacrificing quality.",
            },
            {
              title: "Self-Healing",
              desc: 'Error detected at 3am → autofix daemon diagnoses → patches → opens PR → CI passes → merged. You wake up to "fixed while you slept."',
            },
          ].map((item) => (
            <div
              key={item.title}
              className="bg-surface border border-border rounded-xl p-6 hover:border-accent/20 transition-colors"
            >
              <h3 className="font-semibold text-accent mb-2">{item.title}</h3>
              <p className="text-sm text-muted leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── COMPARISON ── */}
      <section className="py-24 px-6 bg-surface/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
            Why not just use Bolt or Lovable?
          </h2>
          <p className="text-muted text-center mb-12">
            They build an app. We build a business that runs itself.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-3 px-4 text-muted font-medium">
                    Capability
                  </th>
                  <th className="py-3 px-4 text-center text-muted font-medium">
                    Bolt
                  </th>
                  <th className="py-3 px-4 text-center text-muted font-medium">
                    Lovable
                  </th>
                  <th className="py-3 px-4 text-center text-muted font-medium">
                    v0
                  </th>
                  <th className="py-3 px-4 text-center text-accent font-medium bg-accent-glow/5 rounded-t-lg">
                    Powerhouse
                  </th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {[
                  ["Builds an app", "✅", "✅", "✅", "✅"],
                  ["Deploys it", "✅", "✅", "✅", "✅"],
                  ["CI/CD + monitoring", "❌", "❌", "❌", "✅"],
                  ["Self-healing", "❌", "❌", "❌", "✅"],
                  ["Agent swarms", "❌", "❌", "⚠️", "✅"],
                  ["Business agents", "❌", "❌", "❌", "✅"],
                  ["Open source", "❌", "❌", "❌", "✅ MIT"],
                ].map((row, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="py-3 px-4 text-text">{row[0]}</td>
                    {row.slice(1).map((cell, j) => (
                      <td
                        key={j}
                        className={`py-3 px-4 text-center ${
                          j === 3
                            ? "text-accent font-semibold bg-accent-glow/5"
                            : "text-muted"
                        }`}
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="py-24 px-6 text-center">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl sm:text-5xl font-bold mb-6">
            Your business,{" "}
            <span className="text-accent">built in minutes.</span>
          </h2>
          <p className="text-xl text-muted mb-10 max-w-xl mx-auto">
            No more spending weeks on boilerplate. Describe what you want.
            Our agent swarm builds, deploys, and runs it — while you focus
            on what matters.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="https://dashboard-chi-ivory-99.vercel.app/sign-up"
              className="px-8 py-4 bg-accent-glow hover:bg-violet-700 text-white rounded-xl font-semibold text-lg transition-all hover:shadow-[0_0_40px_rgba(124,58,237,0.3)]"
            >
              Start Free — No Credit Card →
            </a>
            <a
              href="https://github.com/zd87pl/powerhouse"
              className="px-8 py-4 bg-surface border border-border hover:border-accent text-text rounded-xl font-semibold text-lg transition-all"
            >
              ⭐ Star on GitHub
            </a>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="py-12 px-6 border-t border-border text-center">
        <div className="flex flex-wrap justify-center gap-6 text-sm text-zinc-600">
          <a
            href="https://github.com/zd87pl/powerhouse"
            className="hover:text-accent transition-colors"
          >
            GitHub
          </a>
          <a
            href="https://dashboard-chi-ivory-99.vercel.app"
            className="hover:text-accent transition-colors"
          >
            Dashboard
          </a>
          <a
            href="https://instill-api.fly.dev/docs"
            className="hover:text-accent transition-colors"
          >
            API Docs
          </a>
        </div>
        <p className="text-xs text-zinc-800 mt-6">
          Built with ⚡ by Ziggy · MIT License
        </p>
      </footer>
    </main>
  );
}
