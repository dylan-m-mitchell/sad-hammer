#!/usr/bin/env bash
set -euo pipefail

# Start Vite dev server for the new React frontend. Backend assumed at http://127.0.0.1:5000
# Vite proxy (vite.config.js) forwards /api to backend.

cd "$(dirname "$0")/../frontend"

if command -v npm >/dev/null 2>&1; then
	if [ -f package-lock.json ]; then
		npm ci || npm install
	else
		npm install
	fi
	npm run dev
else
	echo "npm is required to run the frontend dev server." >&2
	exit 1
fi
