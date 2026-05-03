export default function HomePage() {
  return (
    <main>
      {/* ── HERO ── */}
      <section className="min-h-[90vh] flex flex-col items-center justify-center px-6 text-center relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(124,58,237,0.15),_transparent_70%)]" />

        <div className="relative z-10 max-w-4xl">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#13131a] border border-[#1e1e2e] text-sm text-[#a78bfa] mb-8">
            <span className="w-2 h-2 rounded-full bg-[#34d399] animate-pulse" />
            Now in public beta
          </div>

          <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.05] mb-6">
            Build a business
            <br />
            <span className="text-[#a78bfa]">in 5 minutes.</span>
          </h1>

          <p className="text-xl sm:text-2xl text-[#71717a] max-w-2xl mx-auto mb-4">
            Not just an app. A complete business — storefront,
            payments, inventory, marketing. All built, deployed,
            monitored, and self-healing.
          </p>

          <p className="text-lg text-[#52525b] max-w-xl mx-auto mb-10">
            You describe the idea. AI builds everything. It fixes
            itself while you sleep. You wake up to a growing
            business.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="https://dashboard-chi-ivory-99.vercel.app/sign-up"
              className="px-8 py-4 bg-[#7c3aed] hover:bg-[#6d28d9] text-white rounded-xl font-semibold text-lg transition-all hover:shadow-[0_0_40px_rgba(124,58,237,0.3)]"
            >
              Start Building Free →
            </a>
            <a
              href="#demo"
              className="px-8 py-4 bg-[#13131a] border border-[#1e1e2e] hover:border-[#a78bfa] text-[#e4e4e7] rounded-xl font-semibold text-lg transition-all"
            >
              See How It Works ↓
            </a>
          </div>

          <p className="text-sm text-[#52525b] mt-6">
            No credit card. Build your first project in under 5
            minutes.
          </p>
        </div>
      </section>

      {/* ── DEMO: What you actually get ── */}
      <section id="demo" className="py-24 px-6 max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            One file.{" "}
            <span className="text-[#a78bfa]">Five minutes.</span>{" "}
            Live business.
          </h2>
          <p className="text-[#71717a] text-lg max-w-2xl mx-auto">
            This is the exact file that built Bez Spinki — a real
            plus-size fashion store for the Polish market. Products,
            payments, inventory sync, size guides. All from this.
          </p>
        </div>

        {/* Code block */}
        <div className="bg-[#13131a] border border-[#1e1e2e] rounded-2xl p-6 sm:p-8 font-mono text-sm sm:text-base overflow-x-auto mb-8">
          <div className="text-[#52525b] mb-3 select-none text-xs uppercase tracking-wider">
            .powerhouse.yml
          </div>
          <pre className="text-[#e4e4e7] leading-relaxed">
            <code>{`# Describe your business. That's it.
project: bez-spinki
description: "Polish plus-size fashion store"
stack: nextjs
market: PL

features:
  - shopify-checkout
  - blik-payments
  - size-guide-xl-6xl
  - inventory-sync
  - darmowa-dostawa

business_agents:
  merchandising: true   # Auto-monitors margins
  growth: true          # A/B tests, traffic alerts

monitoring:
  sentry: true
  phoenix: true
  autofix: true         # Sleep through bugs`}</code>
          </pre>
          <div className="mt-4 flex items-center gap-2 text-xs text-[#52525b]">
            <span className="w-2 h-2 rounded-full bg-[#34d399]" />
            That&apos;s the entire spec. Powerhouse builds the rest.
          </div>
        </div>

        {/* What you get grid */}
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
              className="bg-[#13131a] border border-[#1e1e2e] rounded-xl p-6 hover:border-[#a78bfa]/30 transition-colors"
            >
              <div className="text-2xl mb-3">{item.emoji}</div>
              <h3 className="font-semibold text-[#e4e4e7] mb-1">
                {item.title}
              </h3>
              <p className="text-sm text-[#71717a]">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="py-24 px-6 bg-[#13131a]/50">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-16">
            How it actually works
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                step: "1",
                title: "You describe the idea",
                body: "One YAML file. Or just type what you want in plain English. \"A plus-size fashion store for Poland with BLIK payments.\"",
              },
              {
                step: "2",
                title: "Agent swarm builds it",
                body: "Architect designs. Coder implements. Reviewer validates. DevOps deploys. They loop until it's perfect, then open a PR.",
              },
              {
                step: "3",
                title: "It runs itself",
                body: "Merchandising agent watches margins. Growth agent runs A/B tests. Autofix daemon patches bugs at 3am. You focus on vision.",
              },
            ].map((item) => (
              <div
                key={item.step}
                className="relative bg-[#0a0a0f] border border-[#1e1e2e] rounded-2xl p-8"
              >
                <div className="w-10 h-10 rounded-full bg-[#7c3aed]/10 border border-[#7c3aed]/30 flex items-center justify-center text-[#a78bfa] font-bold mb-6">
                  {item.step}
                </div>
                <h3 className="text-xl font-semibold mb-3">
                  {item.title}
                </h3>
                <p className="text-[#71717a] leading-relaxed">
                  {item.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── THE AUTONOMY DIFFERENCE ── */}
      <section className="py-24 px-6 max-w-6xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-bold text-center mb-6">
          Not just scaffolding.
          <br />
          <span className="text-[#a78bfa]">Autonomous operations.</span>
        </h2>
        <p className="text-[#71717a] text-lg text-center max-w-2xl mx-auto mb-16">
          Every other tool stops at "here's your code." Powerhouse
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
              desc: "Every decision remembered. Every error pattern learned. \"Have we seen this bug before?\" → Yes, here's what fixed it last time.",
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
              desc: "Error detected at 3am → autofix daemon diagnoses → patches → opens PR → CI passes → merged. You wake up to \"fixed while you slept.\"",
            },
          ].map((item) => (
            <div
              key={item.title}
              className="bg-[#13131a] border border-[#1e1e2e] rounded-xl p-6 hover:border-[#a78bfa]/20 transition-colors"
            >
              <h3 className="font-semibold text-[#a78bfa] mb-2">
                {item.title}
              </h3>
              <p className="text-sm text-[#71717a] leading-relaxed">
                {item.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── COMPARISON ── */}
      <section className="py-24 px-6 bg-[#13131a]/50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
            Why not just use Bolt or Lovable?
          </h2>
          <p className="text-[#71717a] text-center mb-12">
            They build an app. We build a business that runs itself.
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-[#1e1e2e]">
                  <th className="py-3 px-4 text-[#71717a] font-medium">Capability</th>
                  <th className="py-3 px-4 text-center text-[#71717a] font-medium">Bolt</th>
                  <th className="py-3 px-4 text-center text-[#71717a] font-medium">Lovable</th>
                  <th className="py-3 px-4 text-center text-[#71717a] font-medium">v0</th>
                  <th className="py-3 px-4 text-center text-[#a78bfa] font-medium bg-[#7c3aed]/5 rounded-t-lg">
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
                  <tr
                    key={i}
                    className="border-b border-[#1e1e2e]/50"
                  >
                    <td className="py-3 px-4 text-[#e4e4e7]">
                      {row[0]}
                    </td>
                    {row.slice(1).map((cell, j) => (
                      <td
                        key={j}
                        className={`py-3 px-4 text-center ${
                          j === 3
                            ? "text-[#a78bfa] font-semibold bg-[#7c3aed]/5"
                            : "text-[#71717a]"
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
            <span className="text-[#a78bfa]">built in minutes.</span>
          </h2>
          <p className="text-xl text-[#71717a] mb-10 max-w-xl mx-auto">
            No more spending weeks on boilerplate. Describe what you
            want. Our agent swarm builds, deploys, and runs it —
            while you focus on what matters.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="https://dashboard-chi-ivory-99.vercel.app/sign-up"
              className="px-8 py-4 bg-[#7c3aed] hover:bg-[#6d28d9] text-white rounded-xl font-semibold text-lg transition-all hover:shadow-[0_0_40px_rgba(124,58,237,0.3)]"
            >
              Start Free — No Credit Card →
            </a>
            <a
              href="https://github.com/zd87pl/powerhouse"
              className="px-8 py-4 bg-[#13131a] border border-[#1e1e2e] hover:border-[#a78bfa] text-[#e4e4e7] rounded-xl font-semibold text-lg transition-all"
            >
              ⭐ Star on GitHub
            </a>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="py-12 px-6 border-t border-[#1e1e2e] text-center">
        <div className="flex flex-wrap justify-center gap-6 text-sm text-[#52525b]">
          <a
            href="https://github.com/zd87pl/powerhouse"
            className="hover:text-[#a78bfa] transition-colors"
          >
            GitHub
          </a>
          <a
            href="https://dashboard-chi-ivory-99.vercel.app"
            className="hover:text-[#a78bfa] transition-colors"
          >
            Dashboard
          </a>
          <a
            href="https://instill-api.fly.dev/docs"
            className="hover:text-[#a78bfa] transition-colors"
          >
            API Docs
          </a>
        </div>
        <p className="text-xs text-[#3f3f46] mt-6">
          Built with ⚡ by Ziggy · MIT License
        </p>
      </footer>
    </main>
  );
}
