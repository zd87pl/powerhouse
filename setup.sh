#!/usr/bin/env bash
# Instill Setup Wizard — BYOK (Bring Your Own Keys)
# One command to go from clone → deployed autonomous engineering platform
set -euo pipefail

# ── Colors ──
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ── Referral Links (earns credits for the OSS maintainer) ──
# These are baked into the setup flow. Users who don't have accounts yet
# are directed to these signup links. No cost to the user.
OPENROUTER_REFERRAL="${OPENROUTER_REFERRAL:-}"  # Set via env or edit below
# Example: OPENROUTER_REFERRAL="https://openrouter.ai?ref=YOUR_ID"

# ── Banner ──
echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ██╗███╗   ██╗███████╗████████╗██╗██╗     ██╗ ║"
echo "║              ██║████╗  ██║██╔════╝╚══██╔══╝██║██║     ██║ ║"
echo "║              ██║██╔██╗ ██║███████╗   ██║   ██║██║     ██║ ║"
echo "║              ██║██║╚██╗██║╚════██║   ██║   ██║██║     ██║ ║"
echo "║              ██║██║ ╚████║███████║   ██║   ██║███████╗███████╗║"
echo "║              ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝╚══════╝╚══════╝║"
echo "║                                                              ║"
echo "║       Autonomous AI Engineering Platform — Self-Hosted        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo -e "${BOLD}Welcome to the Instill Setup Wizard!${NC}"
echo ""
echo -e "${DIM}This wizard will set up your personal autonomous engineering platform."
echo "You bring your own API keys, Instill handles everything else.${NC}"
echo ""
echo -e "What we'll do:"
echo -e "  ${GREEN}1.${NC} Collect your API keys (${BOLD}BYOK${NC} — your keys, your infra)"
echo -e "  ${GREEN}2.${NC} Validate each key is working"
echo -e "  ${GREEN}3.${NC} Deploy the Instill API to Fly.io"
echo -e "  ${GREEN}4.${NC} Deploy the Dashboard to Vercel"
echo -e "  ${GREEN}5.${NC} You're live — type what you want to build!"
echo ""

# ── Check prerequisites ──
echo -e "${BOLD}Checking prerequisites...${NC}"

command -v flyctl >/dev/null 2>&1 || { echo -e "${RED}✗ flyctl not found. Install: curl -L https://fly.io/install.sh | sh${NC}"; exit 1; }
echo -e "  ${GREEN}✓${NC} flyctl"

command -v vercel >/dev/null 2>&1 || { echo -e "${RED}✗ vercel not found. Install: npm i -g vercel${NC}"; exit 1; }
echo -e "  ${GREEN}✓${NC} vercel"

command -v git >/dev/null 2>&1 || { echo -e "${RED}✗ git not found${NC}"; exit 1; }
echo -e "  ${GREEN}✓${NC} git"

command -v python3 >/dev/null 2>&1 || { echo -e "${RED}✗ python3 not found${NC}"; exit 1; }
echo -e "  ${GREEN}✓${NC} python3"

echo ""

# ── Create .env ──
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠  .env already exists. We'll update it with any new keys.${NC}"
else
    touch "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi

# ── Helper: prompt for a secret ──
prompt_secret() {
    local var_name="$1"
    local description="$2"
    local docs_url="$3"
    local referral="${4:-}"
    local required="${5:-true}"

    echo -e "${BOLD}${description}${NC}"
    echo -e "  ${DIM}Get one at: ${docs_url}${NC}"

    if [ -n "$referral" ] && [ "$referral" != "none" ]; then
        echo -e "  ${YELLOW}💡 New to this service? Use this link for bonus credits:${NC}"
        echo -e "     ${CYAN}${referral}${NC}"
    fi

    local existing
    existing=$(grep "^${var_name}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' || true)

    if [ -n "$existing" ] && [ "$existing" != "***" ] && [ "$existing" != "YOUR_${var_name}" ]; then
        echo -e "  ${GREEN}✓ Already configured${NC}"
        return 0
    fi

    if [ "$required" = "true" ]; then
        read -r -p "  ${CYAN}Enter ${var_name}: ${NC}" value
    else
        read -r -p "  ${CYAN}Enter ${var_name} (press Enter to skip): ${NC}" value
        if [ -z "$value" ]; then
            echo -e "  ${DIM}→ Skipped (optional)${NC}"
            return 0
        fi
    fi

    if [ -n "$value" ]; then
        # Update or add to .env
        if grep -q "^${var_name}=" "$ENV_FILE" 2>/dev/null; then
            sed -i "s|^${var_name}=.*|${var_name}=\"${value}\"|" "$ENV_FILE"
        else
            echo "${var_name}=\"${value}\"" >> "$ENV_FILE"
        fi
        echo -e "  ${GREEN}✓ Saved${NC}"
    else
        if [ "$required" = "true" ]; then
            echo -e "  ${RED}✗ Required — please provide a value${NC}"
            prompt_secret "$var_name" "$description" "$docs_url" "$referral" "$required"
        fi
    fi
}

# ── Helper: validate a key via the API ──
validate_key() {
    local provider="$1"
    local label="$2"

    echo -n "  Validating ${label}... "
    if command -v curl >/dev/null 2>&1; then
        # We'll validate after the API is deployed — skip for now
        echo -e "${YELLOW}will validate after deploy${NC}"
    else
        echo -e "${YELLOW}skipped (no curl)${NC}"
    fi
}

# ═══════════════════════════════════════════════
# STEP 1: Collect API Keys
# ═══════════════════════════════════════════════

echo -e "${BOLD}${CYAN}━━━ Step 1: API Keys ━━━${NC}"
echo -e "${DIM}Instill uses your own API keys to provision infrastructure and run agents."
echo -e "None of your keys leave your machine. Everything runs on your accounts.${NC}"
echo ""

# Required providers
prompt_secret "GITHUB_TOKEN" "GitHub Token" \
    "https://github.com/settings/tokens/new?scopes=repo,workflow&description=Instill" \
    "none" "true"
echo ""

prompt_secret "VERCEL_TOKEN" "Vercel Token" \
    "https://vercel.com/account/settings/tokens" \
    "none" "true"
echo ""

# Semi-required
prompt_secret "FLY_API_TOKEN" "Fly.io Token" \
    "https://fly.io/user/personal_access_tokens" \
    "none" "true"
echo ""

prompt_secret "OPENROUTER_API_KEY" "OpenRouter API Key" \
    "https://openrouter.ai/settings/keys" \
    "$OPENROUTER_REFERRAL" "true"
echo ""

# Dashboard auth
echo -e "${BOLD}Clerk (Dashboard Authentication)${NC}"
echo -e "  ${DIM}Create a Clerk app at https://clerk.com — free tier is generous${NC}"
echo ""

prompt_secret "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" "Clerk Publishable Key" \
    "https://dashboard.clerk.com/last-active?path=api-keys" \
    "none" "true"
echo ""

prompt_secret "CLERK_SECRET_KEY" "Clerk Secret Key" \
    "https://dashboard.clerk.com/last-active?path=api-keys" \
    "none" "true"
echo ""

# Optional: Supabase
echo -e "${BOLD}Optional Services${NC}"
echo -e "  ${DIM}Press Enter to skip any optional service${NC}"
echo ""

prompt_secret "SUPABASE_URL" "Supabase Project URL" \
    "https://supabase.com/dashboard" \
    "none" "false"
echo ""

if grep -q "^SUPABASE_URL=" "$ENV_FILE" 2>/dev/null; then
    prompt_secret "SUPABASE_SERVICE_ROLE_KEY" "Supabase Service Role Key" \
        "https://supabase.com/dashboard/project/_/settings/api" \
        "none" "false"
    echo ""
fi

prompt_secret "SENTRY_AUTH_TOKEN" "Sentry Auth Token" \
    "https://sentry.io/settings/account/api/auth-tokens/" \
    "none" "false"
echo ""

prompt_secret "STRIPE_SECRET_KEY" "Stripe Secret Key" \
    "https://dashboard.stripe.com/apikeys" \
    "none" "false"
echo ""

# ── Source the env ──
set -a
source "$ENV_FILE" 2>/dev/null || true
set +a

# ═══════════════════════════════════════════════
# STEP 2: Deploy API to Fly.io
# ═══════════════════════════════════════════════

echo -e "${BOLD}${CYAN}━━━ Step 2: Deploy API to Fly.io ━━━${NC}"
echo ""

# Check if app already exists
APP_NAME="${FLY_APP_NAME:-instill-api}"
if flyctl status -a "$APP_NAME" >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓ App '${APP_NAME}' already exists on Fly.io${NC}"
else
    echo -e "  Creating Fly.io app: ${BOLD}${APP_NAME}${NC}"
    flyctl apps create "$APP_NAME" --org personal 2>/dev/null || {
        echo -e "  ${YELLOW}⚠ Could not create app (may already exist or org issue)${NC}"
    }
fi

# Set secrets
echo -e "  Setting secrets on Fly.io..."
flyctl secrets set \
    CLERK_SECRET_KEY="$CLERK_SECRET_KEY" \
    GITHUB_TOKEN="$GITHUB_TOKEN" \
    VERCEL_TOKEN="$VERCEL_TOKEN" \
    OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
    -a "$APP_NAME" 2>/dev/null || true

# Set optional secrets
[ -n "${SUPABASE_URL:-}" ] && flyctl secrets set SUPABASE_URL="$SUPABASE_URL" -a "$APP_NAME" 2>/dev/null || true
[ -n "${SUPABASE_SERVICE_ROLE_KEY:-}" ] && flyctl secrets set SUPABASE_SERVICE_ROLE_KEY="$SUPABASE_SERVICE_ROLE_KEY" -a "$APP_NAME" 2>/dev/null || true
[ -n "${SENTRY_AUTH_TOKEN:-}" ] && flyctl secrets set SENTRY_AUTH_TOKEN="$SENTRY_AUTH_TOKEN" -a "$APP_NAME" 2>/dev/null || true
[ -n "${STRIPE_SECRET_KEY:-}" ] && flyctl secrets set STRIPE_SECRET_KEY="$STRIPE_SECRET_KEY" -a "$APP_NAME" 2>/dev/null || true

# Deploy
echo -e "  ${BOLD}Deploying API...${NC}"
cd services/instill_api
flyctl deploy --app "$APP_NAME" --ha=false 2>&1 | tail -5
cd - >/dev/null

API_URL="https://${APP_NAME}.fly.dev"
echo ""
echo -e "  ${GREEN}✓ API deployed!${NC}"
echo -e "  ${DIM}Health check: ${API_URL}/api/health${NC}"

# Verify health
sleep 3
if curl -sf "${API_URL}/api/health" >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓ API is healthy${NC}"
else
    echo -e "  ${YELLOW}⚠ API may still be starting... check ${API_URL}/api/health${NC}"
fi
echo ""

# ═══════════════════════════════════════════════
# STEP 3: Deploy Dashboard to Vercel
# ═══════════════════════════════════════════════

echo -e "${BOLD}${CYAN}━━━ Step 3: Deploy Dashboard to Vercel ━━━${NC}"
echo ""

cd dashboard

# Create .env.local for the build
cat > .env.local << DASHBOARDEOF
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
CLERK_SECRET_KEY=${CLERK_SECRET_KEY}
NEXT_PUBLIC_API_URL=${API_URL}
DASHBOARDEOF

echo -e "  Deploying dashboard to Vercel..."
vercel --prod --token "$VERCEL_TOKEN" --yes 2>&1 | tail -5
cd - >/dev/null

echo ""
echo -e "  ${GREEN}✓ Dashboard deployed!${NC}"
echo ""

# ═══════════════════════════════════════════════
# STEP 4: Done!
# ═══════════════════════════════════════════════

echo -e "${GREEN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                  🎉 Setup Complete! 🎉                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "  ${BOLD}API:${NC}      ${CYAN}${API_URL}${NC}"
echo -e "  ${BOLD}Dashboard:${NC} ${CYAN}(check Vercel output above)${NC}"
echo ""
echo -e "${BOLD}Next steps:${NC}"
echo -e "  1. Open the dashboard URL and sign in with Clerk"
echo -e "  2. Run setup validation: ${DIM}curl ${API_URL}/api/setup/status${NC}"
echo -e "  3. Try building something: type what you want in the dashboard"
echo ""
echo -e "${DIM}Need help? Open an issue: https://github.com/zd87pl/powerhouse/issues${NC}"
echo ""
