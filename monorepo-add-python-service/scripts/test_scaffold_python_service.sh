#!/usr/bin/env bash
# test_scaffold_python_service.sh — exercises scaffold_python_service.sh against a throwaway
# monorepo root. No network, no uv sync, no pnpm install: this tests the SCAFFOLD, and a test
# that needs the internet is a test that fails for reasons unrelated to the thing it covers.
#
# Usage: test_scaffold_python_service.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCAFFOLD="$HERE/scaffold_python_service.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ok()   { echo "  ok   $1"; pass=$((pass+1)); }
bad()  { echo "  FAIL $1"; fail=$((fail+1)); }
check(){ if eval "$2"; then ok "$1"; else bad "$1"; fi; }

make_root() {
  local root="$1"
  mkdir -p "$root/apps" "$root/packages"
  printf "packages:\n  - 'apps/*'\n  - 'packages/*'\n" > "$root/pnpm-workspace.yaml"
  printf '{"$schema":"https://turborepo.dev/schema.json","tasks":{"dev":{"cache":false,"persistent":true}}}\n' > "$root/turbo.json"
  mkdir -p "$root/.workflow"
  printf '{"project_slug":"acme","phase":"scaffolded","stack":{"framework":"monorepo"}}\n' > "$root/.workflow/meta.json"
}

echo "== refuses what it cannot scaffold into =="
EMPTY="$TMP/empty"; mkdir -p "$EMPTY"
check "no pnpm-workspace.yaml → exit != 0" '! bash "$SCAFFOLD" "$EMPTY" >/dev/null 2>&1'

NOGLOB="$TMP/noglob"; mkdir -p "$NOGLOB"
printf "packages:\n  - 'packages/*'\n" > "$NOGLOB/pnpm-workspace.yaml"
printf '{"tasks":{}}\n' > "$NOGLOB/turbo.json"
check "apps/* not globbed → exit != 0" '! bash "$SCAFFOLD" "$NOGLOB" >/dev/null 2>&1'

R="$TMP/repo"; make_root "$R"
check "reserved name web → exit != 0"    '! bash "$SCAFFOLD" "$R" --name web >/dev/null 2>&1'
check "non-kebab name → exit != 0"       '! bash "$SCAFFOLD" "$R" --name My_Svc >/dev/null 2>&1'
check "unknown variant → exit != 0"      '! bash "$SCAFFOLD" "$R" --variant rust >/dev/null 2>&1'
check "non-numeric port → exit != 0"     '! bash "$SCAFFOLD" "$R" --port http >/dev/null 2>&1'

echo "== generic variant =="
OUT="$(bash "$SCAFFOLD" "$R" --name ml --port 8000 --variant generic)"
A="$R/apps/ml"
for f in package.json pyproject.toml .python-version .env.example .gitignore Dockerfile README.md \
         src/ml/main.py src/ml/schemas.py src/ml/__init__.py tests/test_api.py scripts/export_openapi.py; do
  check "created $f" '[ -f "$A/$f" ]'
done
check "package name is @acme/ml"            'grep -q "\"@acme/ml\"" "$A/package.json"'
check "dev script pins the port"            'grep -q "port 8000" "$A/package.json"'
check "openapi script is wired"             'grep -q "export_openapi.py" "$A/package.json"'
check "no npm dependencies key"             '! grep -q "\"dependencies\"" "$A/package.json"'
check "module placeholder substituted"      '! grep -q "__MOD__" "$A/scripts/export_openapi.py"'
check "export script imports the module"    'grep -q "from ml.main import app" "$A/scripts/export_openapi.py"'
check "generic has NO ml extra"             '! grep -q "optional-dependencies" "$A/pyproject.toml"'
check "generic has no models.py"            '[ ! -f "$A/src/ml/models.py" ]'
check "dev group holds pytest + ruff"       'grep -q "pytest" "$A/pyproject.toml" && grep -q "ruff" "$A/pyproject.toml"'
check "Dockerfile binds 0.0.0.0"            'grep -q "0.0.0.0" "$A/Dockerfile"'
check "Dockerfile syncs --no-dev"           'grep -q "no-dev" "$A/Dockerfile"'
check ".gitignore covers __pycache__"       'grep -q "__pycache__" "$A/.gitignore"'

echo "== idempotence =="
SECOND="$(bash "$SCAFFOLD" "$R" --name ml --port 8000 --variant generic)"
check "second run creates nothing"          'echo "$SECOND" | grep -q "0 created"'
check "second run says already scaffolded"  'echo "$SECOND" | grep -q "already scaffolded"'
check "second run reports exists lines"     'echo "$SECOND" | grep -q "exists   apps/ml/package.json"'
# and it must not have rewritten a file the user edited
printf '# EDITED BY HAND\n' >> "$A/README.md"
bash "$SCAFFOLD" "$R" --name ml >/dev/null
check "does not overwrite an edited file"   'grep -q "EDITED BY HAND" "$A/README.md"'

echo "== ml variant =="
R2="$TMP/repo2"; make_root "$R2"
bash "$SCAFFOLD" "$R2" --name vision --port 8100 --variant ml >/dev/null
B="$R2/apps/vision"
check "ml: models.py scaffolded"            '[ -f "$B/src/vision/models.py" ]'
check "ml: device.py scaffolded"            '[ -f "$B/src/vision/device.py" ]'
check "ml: extra exists"                    'grep -q "optional-dependencies" "$B/pyproject.toml"'
check "ml: torch is NOT a base dependency"  '! sed -n "/^dependencies/,/^]/p" "$B/pyproject.toml" | grep -q torch'
check "ml: torch IS in the extra"           'sed -n "/optional-dependencies/,/^]/p" "$B/pyproject.toml" | grep -q torch'
check "ml: weights are gitignored"          'grep -q "safetensors" "$B/.gitignore"'
check "ml: HF_HOME in .env.example"         'grep -q "HF_HOME" "$B/.env.example"'
check "ml: loader is an extension point"    'grep -q "NotImplementedError" "$B/src/vision/models.py"'
check "ml: version helper exists"           'grep -q "def current_version" "$B/src/vision/models.py"'
check "ml: port 8100 honoured"              'grep -q "port 8100" "$B/package.json"'
check "ml: module name from app name"       'grep -q "vision.main:app" "$B/package.json"'

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
