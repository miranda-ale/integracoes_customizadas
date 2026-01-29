"""
Script para validar fixtures antes da importação
Execute com: bench --site [site] console
Depois: exec(open(frappe.get_app_path("integracoes_customizadas", "contencioso", "validate_fixtures.py")).read())
OU simplesmente execute: from integracoes_customizadas.contencioso.validate_fixtures import validate_all_fixtures; validate_all_fixtures()
"""
import json
import os
import frappe

# Importar a função corretamente
try:
    from frappe.modules.import_file import import_file_by_path
except ImportError:
    # Fallback caso o import falhe
    import_file_by_path = None

def validate_all_fixtures():
    """Função principal para validar todas as fixtures"""
    fixtures_path = frappe.get_app_path("integracoes_customizadas", "fixtures")
    fixture_files = sorted([f for f in os.listdir(fixtures_path) if f.endswith(".json")])

    print(f"\n=== Validando {len(fixture_files)} arquivos de fixtures ===\n")

    errors = []
    warnings = []

    for fname in fixture_files:
        file_path = os.path.join(fixtures_path, fname)
        print(f"Processando: {fname}...")
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                data = [data]
            
            for idx, doc_dict in enumerate(data):
                doctype = doc_dict.get("doctype")
                name = doc_dict.get("name") or doc_dict.get("chart_name") or doc_dict.get("dashboard_name") or f"item_{idx}"
                
                # Validações específicas por doctype
                if doctype == "Dashboard Chart":
                    report_name = doc_dict.get("report_name")
                    if report_name:
                        if not frappe.db.exists("Report", report_name):
                            error_msg = f"Dashboard Chart '{name}' referencia Report '{report_name}' que não existe"
                            errors.append(error_msg)
                            print(f"  ❌ ERRO: {error_msg}")
                        else:
                            print(f"  ✓ Report '{report_name}' existe")
                
                elif doctype == "Dashboard":
                # Verificar se charts e cards referenciados existem
                charts = doc_dict.get("charts", [])
                cards = doc_dict.get("cards", [])
                
                for chart_link in charts:
                    chart_name = chart_link.get("chart")
                    if chart_name and not frappe.db.exists("Dashboard Chart", chart_name):
                        # Aviso apenas, não erro - será criado durante a importação
                        warning_msg = f"Dashboard '{name}' referencia Chart '{chart_name}' que ainda não existe (será criado durante importação)"
                        warnings.append(warning_msg)
                        print(f"  ⚠ AVISO: {warning_msg}")
                
                for card_link in cards:
                    card_name = card_link.get("card")
                    if card_name and not frappe.db.exists("Number Card", card_name):
                        # Aviso apenas, não erro - será criado durante a importação se number_card.json vier antes
                        warning_msg = f"Dashboard '{name}' referencia Number Card '{card_name}' que ainda não existe (será criado durante importação se number_card.json vier antes)"
                        warnings.append(warning_msg)
                        print(f"  ⚠ AVISO: {warning_msg}")
                
                elif doctype == "Number Card":
                    method = doc_dict.get("method")
                    if method:
                        # Verificar se o método existe
                        try:
                            frappe.get_attr(method)
                            print(f"  ✓ Método '{method}' existe")
                        except AttributeError:
                            error_msg = f"Number Card '{name}' referencia método '{method}' que não existe"
                            errors.append(error_msg)
                            print(f"  ❌ ERRO: {error_msg}")
            
            print(f"  ✓ {fname} validado\n")
            
        except Exception as e:
            error_msg = f"Erro ao processar {fname}: {str(e)}"
            errors.append(error_msg)
            print(f"  ❌ ERRO: {error_msg}\n")

    print("\n=== Resumo da Validação ===\n")
    if errors:
        print(f"❌ {len(errors)} ERROS encontrados:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✓ Nenhum erro encontrado!")

    if warnings:
        print(f"\n⚠ {len(warnings)} AVISOS:")
        for warning in warnings:
            print(f"  - {warning}")

    print("\n=== Tentando importar fixtures ===\n")
    
    if not import_file_by_path:
        print("⚠ import_file_by_path não disponível. Pulando importação de teste.\n")
        print("   Execute 'bench migrate' para importar as fixtures normalmente.\n")
    else:
        # Tentar importar cada fixture
        for fname in fixture_files:
            file_path = os.path.join(fixtures_path, fname)
            print(f"Importando: {fname}...")
            
            try:
                import_file_by_path(file_path, force=True, ignore_version=True)
                print(f"  ✓ {fname} importado com sucesso\n")
                
            except Exception as e:
                error_msg = f"Erro ao importar {fname}: {str(e)}"
                print(f"  ❌ ERRO: {error_msg}\n")
                print(f"  Traceback completo:")
                import traceback
                traceback.print_exc()

    print("\n=== Validação concluída ===\n")
    return errors, warnings

# Executar automaticamente se chamado diretamente
if __name__ == "__main__":
    validate_all_fixtures()
else:
    # Se executado via exec(), também executa
    try:
        validate_all_fixtures()
    except:
        pass
