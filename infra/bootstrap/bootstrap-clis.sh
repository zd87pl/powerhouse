#!/bin/bash
# =============================================================================
# Bootstrap script — Install all missing CLIs on a persistent path
# =============================================================================
set -euo pipefail

HERMES_DIR="/data/powerhouse/hermes"
BIN_DIR="$HERMES_DIR/bin"
FLY_DIR="$HERMES_DIR/flyctl"
mkdir -p "$BIN_DIR" "$FLY_DIR"

echo "🔧 Powerhouse CLI Bootstrap"
echo "   Persistent path: $HERMES_DIR"
echo ""

# ─── Fly.io ─────────────────────────────────────────────────────────────────
if [ ! -f "$FLY_DIR/bin/flyctl" ]; then
    echo "Installing Fly.io CLI..."
    curl -L https://fly.io/install.sh | FLYCTL_INSTALL="$FLY_DIR" sh
fi
ln -sf "$FLY_DIR/bin/flyctl" "$BIN_DIR/fly"
ln -sf "$FLY_DIR/bin/flyctl" "$BIN_DIR/flyctl"
echo "✅ Fly.io: $BIN_DIR/flyctl"

# ─── Vercel ─────────────────────────────────────────────────────────────────
if ! command -v vercel &> /dev/null; then
    echo "Installing Vercel CLI..."
    npm install -g vercel@latest
fi
echo "✅ Vercel: $(which vercel)"

# ─── Supabase ───────────────────────────────────────────────────────────────
if ! command -v supabase &> /dev/null; then
    echo "Installing Supabase CLI..."
    npm install -g supabase@latest
fi
echo "✅ Supabase: $(which supabase)"

# ─── Sentry ─────────────────────────────────────────────────────────────────
if ! command -v sentry-cli &> /dev/null; then
    echo "Installing Sentry CLI..."
    curl -sL https://sentry.io/get-cli/ | bash
    # Move to persistent bin if installed to tmp
    if [ -f /usr/local/bin/sentry-cli ]; then
        mv /usr/local/bin/sentry-cli "$BIN_DIR/"
    fi
fi
echo "✅ Sentry: $(which sentry-cli 2>/dev/null || echo in PATH)"

# ─── Wrangler (Cloudflare) ──────────────────────────────────────────────────
if ! command -v wrangler &> /dev/null; then
    echo "Installing Wrangler..."
    npm install -g wrangler@latest
fi
echo "✅ Wrangler: $(which wrangler)"

# ─── GitHub CLI ─────────────────────────────────────────────────────────────
if ! command -v gh &> /dev/null; then
    echo "Installing GitHub CLI..."
    curl -sL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \
        dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \
        tee /etc/apt/sources.list.d/github-cli-stable.list > /dev/null
    apt-get update -qq && apt-get install -y -qq gh
fi
echo "✅ GitHub CLI: $(which gh)"

# ─── Railway ────────────────────────────────────────────────────────────────
if ! command -v railway &> /dev/null; then
    echo "Installing Railway CLI..."
    curl -fsSL https://railway.app/install.sh | sh
    # Binary installs to ~/.railway/bin/railway — symlink to persistent bin
    if [ -f "$HOME/.railway/bin/railway" ]; then
        ln -sf "$HOME/.railway/bin/railway" "$BIN_DIR/railway"
    fi
fi
echo "✅ Railway: $(which railway 2>/dev/null || echo "$BIN_DIR/railway")"

# ─── Git Identity ───────────────────────────────────────────────────────────
if [ -z "$(git config --global user.email 2>/dev/null || true)" ]; then
    echo "⚠️  Git identity not set. Run:"
    echo "   git config --global user.email 'you@example.com'"
    echo "   git config --global user.name 'Your Name'"
fi

# ─── Verify ─────────────────────────────────────────────────────────────────
echo ""
echo "🎉 Bootstrap complete!"
echo ""
echo "Available tools:"
for cmd in fly vercel supabase wrangler gh railway; do
    if command -v "$cmd" &> /dev/null; then
        echo "  ✅ $cmd"
    else
        echo "  ❌ $cmd (not in PATH)"
    fi
done
echo ""
echo "Next steps:"
echo "  1. Source your env: source /data/powerhouse/hermes/.envrc"
echo "  2. Authenticate: fly auth token, vercel login, supabase login, gh auth login, railway login"
echo "  3. Start services: ./infra/scripts/start-services.sh"
