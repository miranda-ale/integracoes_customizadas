#!/usr/bin/env bash
# Instala os pacotes de sistema (apt) declarados pelos apps do bench em [deploy.dependencies.apt] do pyproject.toml.
# O bench instala dependências pip/yarn sozinho, mas não pacotes de sistema; rode isto ANTES do `bench install-app`.
#
# Uso: bash apps/integracoes_customizadas/scripts/install_system_deps.sh [--dry-run] [--bench-path /caminho/do/bench]
set -euo pipefail

dry_run=0
bench_path="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
while [ $# -gt 0 ]; do
	case "$1" in
	--dry-run) dry_run=1 ;;
	--bench-path)
		shift
		bench_path="$(cd "${1:?--bench-path exige um caminho}" && pwd)"
		;;
	*)
		echo "Argumento desconhecido: $1" >&2
		exit 2
		;;
	esac
	shift
done

[ -d "$bench_path/apps" ] || { echo "Não achei $bench_path/apps (use --bench-path)." >&2; exit 1; }

# uma linha por app: "<app>: pacote pacote ..."
declarados="$(python3 - "$bench_path/apps" <<'PY'
import sys, tomllib
from pathlib import Path

for pyproject in sorted(Path(sys.argv[1]).glob("*/pyproject.toml")):
    data = tomllib.loads(pyproject.read_text())
    pacotes = data.get("deploy", {}).get("dependencies", {}).get("apt", {}).get("packages", [])
    if pacotes:
        print(f"{pyproject.parent.name}: {' '.join(pacotes)}")
PY
)"

if [ -z "$declarados" ]; then
	echo "Nenhum app declara pacotes de sistema."
	exit 0
fi

echo "Pacotes de sistema declarados pelos apps:"
echo "$declarados" | sed 's/^/  /'
pacotes="$(echo "$declarados" | cut -d: -f2- | tr ' ' '\n' | sort -u | grep -v '^$' | tr '\n' ' ')"

if [ "$dry_run" -eq 1 ]; then
	echo "[dry-run] sudo apt install -y $pacotes"
	exit 0
fi

# shellcheck disable=SC2086
sudo apt-get install -y $pacotes
