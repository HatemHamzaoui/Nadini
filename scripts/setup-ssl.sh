#!/usr/bin/env bash
# Nadini — SSL Certificate Setup (Let's Encrypt)
# Usage: DOMAIN=nadini.ai EMAIL=admin@nadini.ai bash scripts/setup-ssl.sh

set -euo pipefail

DOMAIN="${DOMAIN:?DOMAIN env var required (e.g. nadini.ai)}"
EMAIL="${EMAIL:?EMAIL env var required (e.g. admin@nadini.ai)}"
CERT_DIR="./certs"

mkdir -p "$CERT_DIR"

echo "[ssl] Requesting certificate for $DOMAIN"

# Use certbot with standalone mode (stop nginx first)
docker run --rm -it \
  -v "$PWD/$CERT_DIR:/etc/letsencrypt/live/$DOMAIN" \
  -p 80:80 \
  certbot/certbot certonly \
  --standalone \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN" \
  -d "www.$DOMAIN"

echo "[ssl] Certificates saved to $CERT_DIR/"
echo "[ssl] Files: fullchain.pem, privkey.pem"
echo ""
echo "Next steps:"
echo "  1. make prod-up"
echo "  2. Setup auto-renewal: add to crontab:"
echo "     0 3 * * 1 cd /opt/nadini && bash scripts/setup-ssl.sh && docker compose restart frontend"
