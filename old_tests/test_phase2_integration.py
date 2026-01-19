#!/usr/bin/env python3
"""Teste Fase 2.1: Fluxo Completo de Processamento."""
import sys
import os
from datetime import date, timedelta
from app import create_app
from app.extensions import db
from app.services.search_service import SearchService
from search.source import SearchSource, Pagina
from iof.v1.consulta import consulta_por_data, convert_pages


def print_test(name: str):
    """Imprime cabeçalho de teste."""
    print(f"\n{'='*60}")
    print(f"TESTE: {name}")
    print('='*60)


def print_result(success: bool, message: str = ""):
    """Imprime resultado do teste."""
    status = "✅ PASSOU" if success else "❌ FALHOU"
    print(f"{status}: {message}")


def find_working_date():
    """Encontra uma data que funciona na API v1."""
    print_test("Encontrando data que funciona na API v1")
    today = date.today()
    for i in range(30):
        test_date = today - timedelta(days=i)
        try:
            response = consulta_por_data(test_date)
            if response and response.dados:
                print_result(True, f"Data encontrada: {test_date.isoformat()}")
                return test_date
        except Exception:
            continue
    print_result(False, "Nenhuma data funcionando nos últimos 30 dias")
    return None


def test_download_from_api(test_date: date):
    """Teste: Download do diário via API v1."""
    print_test(f"Download do diário via API v1 ({test_date.isoformat()})")
    try:
        response = consulta_por_data(test_date)
        
        if not response or not response.dados:
            print_result(False, "Resposta vazia da API")
            return False
        
        arquivo = response.dados.arquivo_caderno_principal.arquivo
        if not arquivo:
            print_result(False, "Arquivo Base64 vazio")
            return False
        
        total_pages = response.dados.arquivo_caderno_principal.total_paginas
        print_result(True, f"Download bem-sucedido: {len(arquivo):,} chars, {total_pages} páginas")
        return True, response
    except Exception as e:
        print_result(False, f"Erro ao baixar: {e}")
        return False, None


def test_extract_pages(response_data):
    """Teste: Extração de páginas do PDF."""
    print_test("Extração de páginas do PDF")
    try:
        arquivo_base64 = response_data.dados.arquivo_caderno_principal.arquivo
        test_date = date.fromisoformat(response_data.dados.data_publicacao.split('T')[0])
        
        paginas_iof = convert_pages(arquivo_base64, test_date)
        
        if not paginas_iof:
            print_result(False, "Nenhuma página extraída")
            return False, None
        
        print_result(True, f"Extraídas {len(paginas_iof)} páginas")
        
        # Verificar estrutura das páginas
        for i, pagina in enumerate(paginas_iof[:3]):  # Verificar primeiras 3
            if not pagina.conteudo:
                print_result(False, f"Página {i+1} sem conteúdo")
                return False, None
        
        print_result(True, "Estrutura das páginas válida")
        return True, paginas_iof
    except Exception as e:
        print_result(False, f"Erro ao extrair: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_import_to_database(paginas_iof, test_date: date):
    """Teste: Importação no banco SQLite."""
    print_test("Importação no banco SQLite")
    try:
        app = create_app()
        with app.app_context():
            diarios_dir = app.config.get('DIARIOS_DIR', 'diarios')
            os.makedirs(diarios_dir, exist_ok=True)
            search_db = os.path.join(diarios_dir, 'diarios_test.db')
            
            # Remover banco de teste se existir
            if os.path.exists(search_db):
                os.remove(search_db)
            
            source = SearchSource(search_db)
            
            try:
                # Converter para Pagina do search
                paginas = [
                    Pagina(
                        titulo="",
                        num_pagina=p.num_pagina,
                        descricao="",
                        conteudo=p.conteudo,
                        data_publicacao=p.data_publicacao
                    )
                    for p in paginas_iof
                ]
                
                # Importar
                source.import_pages(paginas)
                
                # Verificar se foi importado
                has_pages = source.has_pages(test_date)
                if not has_pages:
                    print_result(False, "Páginas não foram importadas")
                    return False
                
                print_result(True, f"Páginas importadas com sucesso")
                
                # Verificar contagem
                import sqlite3
                conn = sqlite3.connect(search_db)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM documentos WHERE data_publicacao = ?",
                    (test_date.isoformat(),)
                )
                count = cursor.fetchone()[0]
                conn.close()
                
                if count != len(paginas):
                    print_result(False, f"Contagem incorreta. Esperado: {len(paginas)}, Encontrado: {count}")
                    return False
                
                print_result(True, f"Contagem correta: {count} páginas")
                # NÃO fechar source aqui - será fechado após o uso em test_search_after_import
                return True, source, search_db
                
            except Exception as e:
                source.close()  # Fechar apenas em caso de erro
                raise
    except Exception as e:
        print_result(False, f"Erro ao importar: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


def test_search_after_import(source, test_date: date):
    """Teste: Busca após importação."""
    print_test("Busca após importação")
    try:
        from search.source import Term, Trigger
        
        # Testar busca simples
        search_terms = [
            Term(term="licitação", exact=False),
            Term(term="pregão", exact=True)
        ]
        
        report = source.lookup(Trigger.BACKTEST, test_date, search_terms)
        
        print_result(True, f"Busca executada: {report.count} resultados encontrados")
        print(f"   Termos: {len(report.search_terms)}")
        print(f"   Highlights: {len(report.highlights)}")
        
        # Verificar estrutura do report
        if report.publish_date != test_date:
            print_result(False, f"Data do report incorreta: {report.publish_date} != {test_date}")
            return False
        
        return True
    except Exception as e:
        print_result(False, f"Erro na busca: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Fechar source após o uso
        if source:
            source.close()


def test_multiple_configs_processing(test_date: date):
    """Teste: Processamento com múltiplas configurações."""
    print_test("Processamento com múltiplas configurações")
    try:
        app = create_app()
        with app.app_context():
            # Criar múltiplas configurações
            configs_data = [
                {
                    "label": "Config Teste 1",
                    "description": "Primeira config",
                    "terms": [{"term": "licitação", "exact": False}]
                },
                {
                    "label": "Config Teste 2",
                    "description": "Segunda config",
                    "terms": [{"term": "pregão", "exact": True}]
                },
                {
                    "label": "Config Teste 3",
                    "description": "Terceira config",
                    "terms": [{"term": "edital", "exact": False}]
                }
            ]
            
            config_ids = []
            for config_data in configs_data:
                config = SearchService.save_config(config_data)
                config_ids.append(config.id)
            
            print_result(True, f"Criadas {len(config_ids)} configurações")
            
            # Listar configurações ativas
            active_configs = SearchService.list_configs(active_only=True)
            if len(active_configs) < len(config_ids):
                print_result(False, f"Esperava pelo menos {len(config_ids)} configs ativas, encontrou {len(active_configs)}")
                return False
            
            print_result(True, f"Encontradas {len(active_configs)} configurações ativas")
            
            # Limpar
            for config_id in config_ids:
                SearchService.delete_config(config_id)
            
            return True
    except Exception as e:
        print_result(False, f"Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_test_db(db_path):
    """Remove banco de teste."""
    if db_path and os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass


def main():
    """Executa todos os testes de integração."""
    print("="*60)
    print("FASE 2.1: TESTE DE INTEGRAÇÃO COMPLETA")
    print("="*60)
    print("\n⚠️  Este teste requer acesso à API IOF v1\n")
    
    # Encontrar data que funciona
    test_date = find_working_date()
    if not test_date:
        print("❌ ERRO: Não foi possível encontrar uma data que funciona")
        sys.exit(1)
    
    results = []
    test_db_path = None
    source = None
    
    try:
        # Teste 1: Download
        success, response_data = test_download_from_api(test_date)
        results.append(("Download via API v1", success))
        if not success or not response_data:
            print("❌ Falha no download. Pulando testes subsequentes.")
            sys.exit(1)
        
        # Teste 2: Extração
        success, paginas_iof = test_extract_pages(response_data)
        results.append(("Extração de páginas", success))
        if not success or not paginas_iof:
            print("❌ Falha na extração. Pulando testes subsequentes.")
            sys.exit(1)
        
        # Teste 3: Importação
        success, source, test_db_path = test_import_to_database(paginas_iof, test_date)
        results.append(("Importação no banco", success))
        if not success:
            print("❌ Falha na importação. Pulando testes subsequentes.")
            sys.exit(1)
        
        # Teste 4: Busca
        if source:
            success = test_search_after_import(source, test_date)
            results.append(("Busca após importação", success))
            # source será fechado dentro de test_search_after_import
            source = None
        
        # Teste 5: Múltiplas configurações
        success = test_multiple_configs_processing(test_date)
        results.append(("Múltiplas configurações", success))
        
    finally:
        # Limpar
        if source:
            source.close()
        cleanup_test_db(test_db_path)
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES DE INTEGRAÇÃO")
    print("="*60)
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n✅ Testes passaram: {passed}/{total}")
    print(f"❌ Testes falharam: {total - passed}/{total}")
    
    if all(success for _, success in results):
        print("\n🎉 TODOS OS TESTES DE INTEGRAÇÃO PASSARAM!")
        sys.exit(0)
    else:
        print("\n⚠️  ALGUNS TESTES DE INTEGRAÇÃO FALHARAM")
        sys.exit(1)


if __name__ == '__main__':
    main()
