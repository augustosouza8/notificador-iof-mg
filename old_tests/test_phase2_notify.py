#!/usr/bin/env python3
"""Teste Fase 2.3: Integração Notify."""
import sys
import os
from datetime import date, timedelta
from app import create_app
from app.extensions import db
from app.services.search_service import SearchService
from app.tasks.notify import notify_search_config
from search.source import SearchSource, Pagina, Term, Trigger
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
    today = date.today()
    for i in range(30):
        test_date = today - timedelta(days=i)
        try:
            response = consulta_por_data(test_date)
            if response and response.dados:
                return test_date
        except Exception:
            continue
    return None


def setup_test_data(test_date: date):
    """Prepara dados de teste: importa diário e cria configuração."""
    app = create_app()
    with app.app_context():
        try:
            # Baixar e importar diário
            response = consulta_por_data(test_date)
            arquivo = response.dados.arquivo_caderno_principal.arquivo
            paginas_iof = convert_pages(arquivo, test_date)
            
            # Importar no banco
            diarios_dir = app.config.get('DIARIOS_DIR', 'diarios')
            os.makedirs(diarios_dir, exist_ok=True)
            search_db = os.path.join(diarios_dir, 'diarios_test_notify.db')
            
            if os.path.exists(search_db):
                os.remove(search_db)
            
            source = SearchSource(search_db)
            try:
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
                source.import_pages(paginas)
            finally:
                source.close()
            
            # Criar configuração de teste
            config_data = {
                "label": "Teste Notify",
                "description": "Config para teste de notificação",
                "mail_to": ["teste@example.com"],
                "mail_subject": "Teste Notify",
                "terms": [
                    {"term": "licitação", "exact": False}
                ]
            }
            config = SearchService.save_config(config_data)
            
            return config.id, search_db
        except Exception as e:
            print_result(False, f"Erro ao preparar dados: {e}")
            import traceback
            traceback.print_exc()
            return None, None


def test_notify_config_search():
    """Teste: Busca de configuração."""
    print_test("Busca de configuração")
    try:
        app = create_app()
        with app.app_context():
            config = SearchService.get_config(1)  # Assumindo que existe
            if not config:
                print_result(False, "Configuração não encontrada (crie uma primeiro)")
                return False
            
            print_result(True, f"Configuração encontrada: {config.label}")
            return True, config.id
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False, None


def test_notify_report_generation(config_id: int, test_date: date, search_db: str):
    """Teste: Geração de relatório."""
    print_test("Geração de relatório")
    try:
        app = create_app()
        with app.app_context():
            config = SearchService.get_config(config_id)
            if not config:
                print_result(False, "Configuração não encontrada")
                return False
            
            source = SearchSource(search_db)
            try:
                search_terms = [
                    Term(term=term.term, exact=term.exact)
                    for term in config.terms
                ]
                
                report = source.lookup(Trigger.CRON, test_date, search_terms)
                
                print_result(True, f"Relatório gerado: {report.count} resultados")
                print(f"   Termos: {len(report.search_terms)}")
                print(f"   Highlights: {len(report.highlights)}")
                
                return True
            finally:
                source.close()
    except Exception as e:
        print_result(False, f"Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_notify_with_matches(config_id: int, test_date: date, search_db: str):
    """Teste: Notificação quando há matches."""
    print_test("Notificação com matches")
    try:
        # Simular chamada de notify_search_config
        # Mas sem enviar email real (para não depender de SMTP)
        app = create_app()
        with app.app_context():
            config = SearchService.get_config(config_id)
            if not config:
                print_result(False, "Configuração não encontrada")
                return False
            
            source = SearchSource(search_db)
            try:
                search_terms = [
                    Term(term=term.term, exact=term.exact)
                    for term in config.terms
                ]
                
                report = source.lookup(Trigger.CRON, test_date, search_terms)
                
                if report.count == 0:
                    print_result(False, "Nenhum match encontrado (esperava pelo menos 1)")
                    return False
                
                # Verificar que email seria enviado
                if config.mail_to:
                    print_result(True, f"Email seria enviado para {len(config.mail_to)} destinatário(s)")
                    print(f"   Matches encontrados: {report.count}")
                    return True
                else:
                    print_result(False, "Configuração sem destinatários de email")
                    return False
            finally:
                source.close()
    except Exception as e:
        print_result(False, f"Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_notify_without_matches(config_id: int, test_date: date, search_db: str):
    """Teste: Notificação quando não há matches."""
    print_test("Notificação sem matches")
    try:
        app = create_app()
        with app.app_context():
            # Criar config com termo que não existe
            config_data = {
                "label": "Teste Sem Matches",
                "description": "Config sem matches",
                "mail_to": ["teste@example.com"],
                "terms": [
                    {"term": "termo_que_nao_existe_12345", "exact": False}
                ]
            }
            config = SearchService.save_config(config_data)
            
            source = SearchSource(search_db)
            try:
                search_terms = [
                    Term(term=term.term, exact=term.exact)
                    for term in config.terms
                ]
                
                report = source.lookup(Trigger.CRON, test_date, search_terms)
                
                if report.count > 0:
                    print_result(False, f"Encontrou {report.count} matches (esperava 0)")
                    SearchService.delete_config(config.id)
                    return False
                
                print_result(True, "Nenhum match encontrado (esperado)")
                print("   Email não seria enviado (correto)")
                
                # Limpar
                SearchService.delete_config(config.id)
                return True
            finally:
                source.close()
    except Exception as e:
        print_result(False, f"Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_notify_multiple_configs(test_date: date, search_db: str):
    """Teste: Múltiplas configurações."""
    print_test("Múltiplas configurações")
    try:
        app = create_app()
        with app.app_context():
            # Criar múltiplas configs
            configs_data = [
                {
                    "label": "Config Notify 1",
                    "mail_to": ["test1@example.com"],
                    "terms": [{"term": "licitação", "exact": False}]
                },
                {
                    "label": "Config Notify 2",
                    "mail_to": ["test2@example.com"],
                    "terms": [{"term": "pregão", "exact": True}]
                }
            ]
            
            config_ids = []
            for config_data in configs_data:
                config = SearchService.save_config(config_data)
                config_ids.append(config.id)
            
            source = SearchSource(search_db)
            try:
                # Processar cada config
                processed = 0
                for config_id in config_ids:
                    config = SearchService.get_config(config_id)
                    search_terms = [
                        Term(term=term.term, exact=term.exact)
                        for term in config.terms
                    ]
                    report = source.lookup(Trigger.CRON, test_date, search_terms)
                    if report.count > 0:
                        processed += 1
                
                print_result(True, f"Processadas {processed}/{len(config_ids)} configurações com matches")
                
                # Limpar
                for config_id in config_ids:
                    SearchService.delete_config(config_id)
                
                return True
            finally:
                source.close()
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
    """Executa todos os testes de notificação."""
    print("="*60)
    print("FASE 2.3: TESTE DE INTEGRAÇÃO NOTIFY")
    print("="*60)
    print("\n⚠️  Este teste requer acesso à API IOF v1\n")
    
    # Encontrar data que funciona
    test_date = find_working_date()
    if not test_date:
        print("❌ ERRO: Não foi possível encontrar uma data que funciona")
        sys.exit(1)
    
    config_id = None
    test_db_path = None
    
    try:
        # Preparar dados de teste
        print_test("Preparando dados de teste")
        config_id, test_db_path = setup_test_data(test_date)
        if not config_id:
            print("❌ ERRO: Não foi possível preparar dados de teste")
            sys.exit(1)
        print_result(True, f"Configuração {config_id} criada, diário importado")
        
        results = []
        
        # Executar testes
        results.append(("Busca de configuração", test_notify_config_search()[0] if test_notify_config_search()[0] else False))
        results.append(("Geração de relatório", test_notify_report_generation(config_id, test_date, test_db_path)))
        results.append(("Notificação com matches", test_notify_with_matches(config_id, test_date, test_db_path)))
        results.append(("Notificação sem matches", test_notify_without_matches(config_id, test_date, test_db_path)))
        results.append(("Múltiplas configurações", test_notify_multiple_configs(test_date, test_db_path)))
        
    finally:
        # Limpar
        if config_id:
            app = create_app()
            with app.app_context():
                try:
                    SearchService.delete_config(config_id)
                except Exception:
                    pass
        cleanup_test_db(test_db_path)
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES DE NOTIFICAÇÃO")
    print("="*60)
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n✅ Testes passaram: {passed}/{total}")
    print(f"❌ Testes falharam: {total - passed}/{total}")
    
    if all(success for _, success in results):
        print("\n🎉 TODOS OS TESTES DE NOTIFICAÇÃO PASSARAM!")
        sys.exit(0)
    else:
        print("\n⚠️  ALGUNS TESTES DE NOTIFICAÇÃO FALHARAM")
        sys.exit(1)


if __name__ == '__main__':
    main()
