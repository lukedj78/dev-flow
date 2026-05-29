#!/usr/bin/env bash
# sync-supabase.sh — regenerate Supabase types into packages/shared/src/types/
#
# Reads the Supabase project ref from meta.json#stack_config.supabase_project_ref
# OR from the SUPABASE_PROJECT_REF env var. Runs supabase gen types and writes
# packages/shared/src/types/database.ts.
#
# Usage: sync-supabase.sh <project-root>

set -euo pipefail

PROJECT_ROOT="${1:?project root required}"
cd "$PROJECT_ROOT"

if [[ ! -f .workflow/meta.json ]]; then
  echo "[sync-supabase] no .workflow/meta.json found"
  exit 1
fi

# Try to read the project ref from meta.json, fall back to env var
REF=$(node -e "
  const fs = require('fs');
  try {
    const m = JSON.parse(fs.readFileSync('.workflow/meta.json', 'utf8'));
    console.log(m.stack_config?.supabase_project_ref || process.env.SUPABASE_PROJECT_REF || '');
  } catch(e) {
    console.log(process.env.SUPABASE_PROJECT_REF || '');
  }
")

if [[ -z "$REF" ]]; then
  echo "[sync-supabase] No Supabase project ref found."
  echo "  Set it in meta.json#stack_config.supabase_project_ref or via SUPABASE_PROJECT_REF env var."
  exit 1
fi

TARGET=packages/shared/src/types/database.ts

if [[ ! -d packages/shared/src/types ]]; then
  mkdir -p packages/shared/src/types
fi

echo "[sync-supabase] Generating types from Supabase project '$REF' → $TARGET …"
npx supabase gen types typescript --project-id "$REF" > "$TARGET"

# Verify file is non-empty
if [[ ! -s "$TARGET" ]]; then
  echo "[sync-supabase] ✗ Generated file is empty. Check supabase login + project access."
  exit 1
fi

# Ensure the barrel export includes the types
INDEX=packages/shared/src/index.ts
if [[ -f "$INDEX" ]]; then
  if ! grep -q "from './types/database'" "$INDEX"; then
    echo "" >> "$INDEX"
    echo "export type { Database } from './types/database';" >> "$INDEX"
    echo "[sync-supabase]   ✓ Added Database type export to $INDEX"
  fi
fi

LINES=$(wc -l < "$TARGET" | tr -d ' ')
echo "[sync-supabase] ✓ Generated $LINES lines into $TARGET"
echo "[sync-supabase] Run 'pnpm tsc --noEmit' to verify all consumers still type-check."
