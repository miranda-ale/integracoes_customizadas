"""
Prepara e valida o teste de User Permission por Item Group na List View.

Uso (no container):
  ./env/bin/python /tmp/setup_item_group_test.py

Passos:
  1) Escolhe um usuario Purchase User (ou o informado em TEST_USER)
  2) Aplica User Permission em Item Group = grupo mais comum nas MRs
  3) Compara contagem total (Admin) vs filtrada (usuario)
  4) Valida que a lista filtrada nao vaza itens de outros grupos
  5) Imprime instrucoes de teste manual no browser
  6) Por padrao NAO remove a UP (para voce testar no browser).
     Passe RESTORE=1 para reverter ao final.
"""
from __future__ import annotations

import os
import sys

import frappe

SITE = "osscesariolange.erpnext.com"
# opcional: force um usuario, ex: export via env no comando
TEST_USER = os.environ.get("TEST_USER")  # None = auto
RESTORE = os.environ.get("RESTORE", "0") == "1"


def main():
	os.chdir("/home/frappe/frappe-bench/sites")
	frappe.init(site=SITE)
	frappe.connect()
	frappe.set_user("Administrator")

	from integracoes_customizadas.permissions import item_group_access as iga
	from frappe.model.db_query import DatabaseQuery

	hooks = frappe.get_hooks("permission_query_conditions")
	print("OK hook MR:", hooks.get("Material Request"))
	print("OK hook PO:", hooks.get("Purchase Order"))

	# Top grupos em Solicitacao de Compras
	rows = frappe.db.sql(
		"""
		SELECT COALESCE(NULLIF(mri.item_group,''), i.item_group) AS ig,
		       COUNT(DISTINCT mri.parent) AS docs,
		       COUNT(*) AS nlines
		FROM `tabMaterial Request Item` mri
		LEFT JOIN `tabItem` i ON i.name = mri.item_code
		WHERE COALESCE(NULLIF(mri.item_group,''), i.item_group) IS NOT NULL
		GROUP BY 1
		ORDER BY docs DESC
		LIMIT 8
		""",
		as_dict=True,
	)
	print("\n=== Grupos mais usados em Solicitacao de Compras ===")
	for r in rows:
		print(f"  {r.ig}: {r.docs} documentos, {r.nlines} linhas")

	if not rows:
		print("ERRO: nao ha itens em Material Request para testar.")
		frappe.destroy()
		sys.exit(1)

	target_group = rows[0].ig
	other_group = rows[1].ig if len(rows) > 1 else None
	print(f"\nGrupo do teste (permitido): {target_group}")
	if other_group:
		print(f"Grupo de contraste (bloqueado): {other_group}")

	# Escolher usuario
	user = TEST_USER
	if not user:
		candidates = frappe.db.sql(
			"""
			SELECT u.name, u.full_name
			FROM tabUser u
			INNER JOIN `tabHas Role` r ON r.parent = u.name AND r.role = 'Purchase User'
			WHERE u.enabled = 1 AND u.name NOT IN ('Administrator', 'Guest')
			ORDER BY u.name
			LIMIT 20
			""",
			as_dict=True,
		)
		print("\n=== Candidatos (Purchase User) ===")
		for c in candidates:
			print(f"  {c.name}  ({c.full_name or ''})")
		if not candidates:
			print("ERRO: nenhum Purchase User habilitado.")
			frappe.destroy()
			sys.exit(1)
		user = candidates[0].name

	print(f"\n>>> Usuario de teste: {user}")

	# Snapshot UPs existentes de Item Group
	existing = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Item Group"},
		fields=["name", "for_value", "apply_to_all_doctypes", "applicable_for", "hide_descendants", "is_default"],
	)
	print(f"User Permissions Item Group ja existentes: {len(existing)}")
	for e in existing:
		print(" ", e)

	# Remove UPs Item Group atuais e cria uma limpa so no target_group
	for e in existing:
		frappe.delete_doc("User Permission", e.name, ignore_permissions=True, force=True)

	up = frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": user,
			"allow": "Item Group",
			"for_value": target_group,
			"apply_to_all_doctypes": 1,
			"hide_descendants": 0,
			"is_default": 0,
		}
	)
	up.insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.cache.hdel("user_permissions", user)
	frappe.clear_cache(user=user)
	print(f"\nCriada User Permission: {user} → Item Group = {target_group}")
	print(f"  name do doc: {up.name}")

	# Contagens
	admin_total = frappe.db.count("Material Request")
	print(f"\nTotal Solicitacoes (Admin): {admin_total}")

	frappe.set_user(user)
	allowed = iga.get_allowed_item_groups(user, "Material Request")
	print(f"Grupos permitidos para o usuario (com descendentes): {len(allowed or [])}")
	if allowed:
		print("  amostra:", allowed[:8])

	cond = iga.permission_query_conditions(user=user, doctype="Material Request")
	print(f"SQL condition gerada: {bool(cond)} ({len(cond or '')} chars)")

	q = DatabaseQuery("Material Request")
	q.user = user
	result = q.execute(fields=["name", "title", "status"], limit_page_length=500, as_list=False) or []
	print(f"List View filtrada (ate 500): {len(result)} documentos")

	# Validar vazamento
	leaks = []
	for d in result[:200]:
		items = frappe.get_all(
			"Material Request Item",
			filters={"parent": d.name},
			fields=["item_code", "item_group"],
		)
		for it in items:
			ig = it.item_group or frappe.db.get_value("Item", it.item_code, "item_group")
			if ig and allowed and ig not in allowed:
				leaks.append((d.name, it.item_code, ig))
				break
	print(f"Vazamentos na lista filtrada: {len(leaks)}")
	for L in leaks[:5]:
		print("  LEAK", L)

	# Amostra de docs VISIVEIS
	print("\n=== Amostra VISIVEL para o usuario (deve ser so do grupo permitido) ===")
	for d in result[:8]:
		print(f"  {d.name} | {d.get('status')} | {d.get('title') or ''}")

	# Amostra de docs que NAO devem aparecer
	frappe.set_user("Administrator")
	if other_group and allowed:
		hidden = frappe.db.sql(
			"""
			SELECT DISTINCT mri.parent AS name
			FROM `tabMaterial Request Item` mri
			LEFT JOIN `tabItem` i ON i.name = mri.item_code
			WHERE COALESCE(NULLIF(mri.item_group,''), i.item_group) = %s
			LIMIT 5
			""",
			(other_group,),
			as_dict=True,
		)
		print(f"\n=== Docs do grupo bloqueado '{other_group}' (NAO devem aparecer na lista) ===")
		for h in hidden:
			visible = any(r.name == h.name for r in result)
			print(f"  {h.name} | visivel_pro_usuario={visible}")

	# Restore?
	if RESTORE:
		frappe.delete_doc("User Permission", up.name, ignore_permissions=True, force=True)
		for e in existing:
			doc = frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": user,
					"allow": "Item Group",
					"for_value": e.for_value,
					"apply_to_all_doctypes": e.apply_to_all_doctypes,
					"applicable_for": e.applicable_for,
					"hide_descendants": e.hide_descendants,
					"is_default": e.is_default,
				}
			)
			doc.insert(ignore_permissions=True)
		frappe.db.commit()
		frappe.cache.hdel("user_permissions", user)
		print("\nRESTORE=1 → permissoes anteriores restauradas.")
	else:
		print("\n" + "=" * 60)
		print("TESTE MANUAL NO BROWSER (permissao DEIXADA ATIVA)")
		print("=" * 60)
		print(f"1. Abra o ERP em aba anonima / outro browser")
		print(f"2. Login: {user}")
		print(f"   (use a senha desse usuario; se nao souber, redefina em Usuario)")
		print(f"3. Va em: Compra → Solicitacao de Material / Material Request")
		print(f"   URL tipica: /app/material-request")
		print(f"4. A lista deve mostrar ~{len(result)} docs (nao {admin_total})")
		print(f"5. Todos os itens devem ser do grupo: {target_group}")
		if other_group:
			print(f"6. Nao deve aparecer solicitacao so de: {other_group}")
		print(f"7. Em Item (lista/link), so itens do grupo permitido")
		print()
		print("Para DESFAZER a User Permission de teste depois:")
		print(f"  - Apagar User Permission do usuario {user} (Item Group = {target_group})")
		print(f"  - Ou rodar: RESTORE=1 ./env/bin/python /tmp/setup_item_group_test.py")
		print(f"  - Doc da UP de teste: {up.name}")
		print("=" * 60)

	frappe.destroy()


if __name__ == "__main__":
	main()
