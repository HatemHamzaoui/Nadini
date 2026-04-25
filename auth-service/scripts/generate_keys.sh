#!/usr/bin/env bash
# Erzeugt RS256-Schlüsselpaar für JWT-Signierung.
# Ausgabe: ./secrets/jwt-private.pem, ./secrets/jwt-public.pem
set -euo pipefail

OUT_DIR="${OUT_DIR:-./secrets}"
mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/jwt-private.pem" ]]; then
    echo "Schlüssel existieren bereits unter $OUT_DIR. Abbruch."
    exit 0
fi

openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
    -out "$OUT_DIR/jwt-private.pem"
openssl rsa -pubout -in "$OUT_DIR/jwt-private.pem" \
    -out "$OUT_DIR/jwt-public.pem"

chmod 600 "$OUT_DIR/jwt-private.pem"
chmod 644 "$OUT_DIR/jwt-public.pem"

echo "JWT-Schlüssel erstellt unter $OUT_DIR/"
