#!/usr/bin/env bash
# Ambiente Frappe v15 para testes. Script único: roda como root, sem segredos, idempotente.
# Instala MariaDB, Redis, bench, frappe, payments, erpnext, hrms e os apps clonados na sessão. Base: ci.yml dos repos.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
REPOS="$(pwd)"   # pasta dos checkouts da sessão (o script roda aqui, depois do clone)
apt-get update -qq
apt-get install -y -qq --no-install-recommends build-essential git curl pkg-config xvfb libfontconfig1 \
  python3.12 python3.12-dev python3.12-venv python3-pip mariadb-server mariadb-client libmariadb-dev \
  redis-server wkhtmltopdf ghostscript libcairo2-dev libpango1.0-dev libffi-dev
id frappe >/dev/null 2>&1 || useradd -m -s /bin/bash frappe
chmod a+rx "$REPOS" 2>/dev/null || true   # o usuário frappe precisa ler os repos para `bench get-app <caminho>`

cat > /etc/mysql/mariadb.conf.d/99-frappe.cnf <<'CNF'
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
[mysql]
default-character-set = utf8mb4
CNF

# frappe-up: sobe MariaDB e Redis (13000 cache, 11000 fila). Rode a cada nova sessão.
cat > /usr/local/bin/frappe-up <<'UP'
#!/usr/bin/env bash
mkdir -p /run/mysqld && chown mysql:mysql /run/mysqld
pgrep -x mariadbd >/dev/null || { nohup mariadbd-safe --user=mysql >/var/log/mariadb-start.log 2>&1 & }
for _ in $(seq 40); do mariadb-admin ping --silent 2>/dev/null || mariadb-admin -uroot -proot ping --silent 2>/dev/null && break; sleep 1; done
for p in 13000 11000; do redis-cli -p "$p" ping >/dev/null 2>&1 || redis-server --port "$p" --daemonize yes --save "" >/dev/null; done
UP
chmod +x /usr/local/bin/frappe-up && frappe-up
# Senha local de teste, igual ao CI (root/root). Banco descartável, não é segredo.
mariadb -uroot -proot -e 'select 1' >/dev/null 2>&1 || mariadb -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'root'; FLUSH PRIVILEGES"

# frappe-env site <app> | test <app> [args]: um site por app, na ordem de install-app dos ci.yml
cat > /usr/local/bin/frappe-env <<'ENV'
#!/usr/bin/env bash
set -euo pipefail
if [ "$(id -u)" = 0 ]; then frappe-up; exec su - frappe -c "$0 $*"; fi
export PATH="$HOME/.local/bin:/opt/node22/bin:$PATH"; cd "$HOME/bench-dev"
cmd="$1"; app="$2"; shift 2
case "$app" in
  clm) deps="payments erpnext clm";;
  rh_brasil) deps="payments erpnext hrms clm assinatura_eletronica rh_brasil";;
  pulse_gestor) deps="erpnext clm pulse_gestor";;
  busca_cnpj) deps="erpnext busca_cnpj";;
  integracoes_customizadas) deps="erpnext hrms busca_cnpj clm rh_brasil integracoes_customizadas";;
  pulse_finance) deps="erpnext pulse_finance";;   # sem ci.yml: deduzido do required_apps
  bhcl_site) deps="erpnext hrms bhcl_site";;       # sem ci.yml: deduzido do required_apps
  assinatura_eletronica|pdf_ocr|pulse_process) deps="$app";;
  *) echo "app desconhecido: $app" >&2; exit 2;;
esac
if [ "$cmd" = site ]; then
  for d in $deps; do [ -d "apps/$d" ] || { echo "falta apps/$d (repo não clonado na sessão?)" >&2; exit 3; }; done
  if [ ! -d "sites/$app" ]; then
    bench new-site --db-root-password root --admin-password admin "$app"
    bench --site "$app" install-app $deps
    bench --site "$app" set-config allow_tests true
    case " $deps " in *" erpnext "*) printf '%s\n' 'frappe.flags.in_test = True' \
      'from erpnext.setup.utils import before_tests' 'before_tests()' 'frappe.db.commit()' | bench --site "$app" console;; esac
  fi
else exec bench --site "$app" run-tests --app "$app" "$@"; fi
ENV
chmod +x /usr/local/bin/frappe-env

# Parte do usuário não-root: bench, frappe, apps públicos e os apps clonados na sessão
cat > /tmp/frappe-user-setup.sh <<'USR'
set -euo pipefail
export PATH="$HOME/.local/bin:/opt/node22/bin:$PATH"
git config --global --add safe.directory '*'
python3.12 -m pip install --user --break-system-packages -q frappe-bench
B="$HOME/bench-dev"
[ -d "$B/apps/frappe" ] || bench init --skip-redis-config-generation --skip-assets --frappe-branch version-15 --python python3.12 "$B"
cd "$B"
for k in redis_cache:13000 redis_queue:11000 redis_socketio:11000; do bench set-config -g "${k%%:*}" "redis://127.0.0.1:${k##*:}"; done
for a in payments erpnext hrms; do [ -d "apps/$a" ] || bench get-app "$a" --branch version-15; done
for a in busca_cnpj clm assinatura_eletronica pdf_ocr rh_brasil integracoes_customizadas pulse_gestor pulse_finance pulse_process bhcl_site; do
  if [ -d "$REPOS/$a/.git" ] && [ ! -d "apps/$a" ]; then bench get-app "$a" "$REPOS/$a"; fi
done
bench setup requirements --dev
USR
su - frappe -c "REPOS='$REPOS' bash /tmp/frappe-user-setup.sh"
echo "Pronto. Bench: /home/frappe/bench-dev. Uso: frappe-env site <app> ; frappe-env test <app>"
