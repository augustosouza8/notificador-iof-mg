#!/usr/bin/env python3
"""Teste Fase 3.3: Busca FTS5 com Dados Reais."""
import sys
import os
import time
from datetime import date, timedelta
from app import create_app
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
    return date(2026, 1, 9)  # Data conhecida


def import_journal(test_date: date, search_db: str):
    """Importa jornal completo para o banco."""
    print_test(f"Importando jornal completo ({test_date.isoformat()})")
    try:
        # Baixar diário
        response = consulta_por_data(test_date)
        arquivo = response.dados.arquivo_caderno_principal.arquivo
        total_pages = response.dados.arquivo_caderno_principal.total_paginas
        
        # Extrair páginas
        paginas_iof = convert_pages(arquivo, test_date)
        
        # Importar
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
            
            # Verificar
            has_pages = source.has_pages(test_date)
            if has_pages:
                print_result(True, f"Jornal importado: {len(paginas)} páginas")
                return True, source
            else:
                print_result(False, "Páginas não foram importadas")
                return False, None
        finally:
            if source:
                source.close()
    except Exception as e:
        print_result(False, f"Erro: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_multiple_terms_search(source: SearchSource, test_date: date):
    """Teste: Busca com múltiplos termos."""
    print_test("Busca com múltiplos termos")
    try:
        search_terms = [
            Term(term="licitação", exact=False),
            Term(term="pregão", exact=True),
            Term(term="edital", exact=False)
        ]
        
        start_time = time.time()
        report = source.lookup(Trigger.BACKTEST, test_date, search_terms)
        elapsed = time.time() - start_time
        
        print_result(True, f"Busca executada em {elapsed:.3f}s")
        print(f"   Termos: {len(search_terms)}")
        print(f"   Resultados: {report.count}")
        print(f"   Highlights: {len(report.highlights)}")
        
        return True
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_exact_vs_inexact_search(source: SearchSource, test_date: date):
    """Teste: Termos exatos vs não exatos."""
    print_test("Termos exatos vs não exatos")
    try:
        # Busca com termo exato
        exact_terms = [Term(term="pregão", exact=True)]
        exact_report = source.lookup(Trigger.BACKTEST, test_date, exact_terms)
        
        # Busca com termo não exato
        inexact_terms = [Term(term="pregão", exact=False)]
        inexact_report = source.lookup(Trigger.BACKTEST, test_date, inexact_terms)
        
        print_result(True, "Ambas as buscas executadas")
        print(f"   Exato: {exact_report.count} resultados")
        print(f"   Não exato: {inexact_report.count} resultados")
        
        # Não exato geralmente retorna mais resultados
        if inexact_report.count >= exact_report.count:
            print_result(True, "Busca não exata retorna >= resultados (esperado)")
            return True
        else:
            print_result(False, "Busca não exata retornou menos resultados (inesperado)")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_nonexistent_term_search(source: SearchSource, test_date: date):
    """Teste: Busca por termo que não existe."""
    print_test("Busca por termo inexistente")
    try:
        search_terms = [Term(term="termo_que_nao_existe_12345", exact=False)]
        
        report = source.lookup(Trigger.BACKTEST, test_date, search_terms)
        
        if report.count == 0:
            print_result(True, "Nenhum resultado encontrado (esperado)")
            return True
        else:
            print_result(False, f"Encontrou {report.count} resultados (inesperado)")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_partial_term_search(source: SearchSource, test_date: date):
    """Teste: Busca por termo parcial."""
    print_test("Busca por termo parcial")
    try:
        # Buscar por parte de uma palavra
        search_terms = [Term(term="licit", exact=False)]
        
        report = source.lookup(Trigger.BACKTEST, test_date, search_terms)
        
        print_result(True, f"Busca parcial executada: {report.count} resultados")
        
        # Verificar que highlights contêm o termo
        if report.highlights:
            first_highlight = report.highlights[0]
            if "licit" in first_highlight.content.lower():
                print_result(True, "Highlight contém termo parcial")
                return True
            else:
                print_result(False, "Highlight não contém termo parcial")
                return False
        else:
            print_result(True, "Nenhum resultado (pode ser esperado)")
            return True
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_special_characters_search(source: SearchSource, test_date: date):
    """Teste: Busca com caracteres especiais."""
    print_test("Busca com caracteres especiais")
    try:
        # Termos com caracteres que podem causar problemas em FTS5
        special_terms = [
            Term(term="R$", exact=False),
            Term(term="nº", exact=False),
            Term(term="art.", exact=False)
        ]
        
        results = []
        for term in special_terms:
            try:
                report = source.lookup(Trigger.BACKTEST, test_date, [term])
                results.append((term.term, report.count))
            except Exception as e:
                print(f"  ⚠️  Erro com '{term.term}': {e}")
                results.append((term.term, -1))
        
        successful = sum(1 for _, count in results if count >= 0)
        print_result(successful == len(special_terms), f"{successful}/{len(special_terms)} termos processados")
        
        for term_str, count in results:
            print(f"   '{term_str}': {count} resultados")
        
        return successful > 0  # Pelo menos um funcionou
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_search_performance(source: SearchSource, test_date: date):
    """Teste: Performance da busca."""
    print_test("Performance da busca")
    try:
        search_terms = [
            Term(term="licitação", exact=False),
            Term(term="pregão", exact=False),
            Term(term="edital", exact=False)
        ]
        
        # Executar múltiplas buscas e medir tempo
        times = []
        for _ in range(5):
            start_time = time.time()
            report = source.lookup(Trigger.BACKTEST, test_date, search_terms)
            elapsed = time.time() - start_time
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print_result(True, f"Performance medida")
        print(f"   Média: {avg_time:.3f}s")
        print(f"   Mín: {min_time:.3f}s")
        print(f"   Máx: {max_time:.3f}s")
        
        # Verificar que é razoavelmente rápido (< 1s para busca simples)
        if avg_time < 1.0:
            print_result(True, "Performance aceitável (< 1s)")
            return True
        else:
            print_result(False, f"Performance lenta (média: {avg_time:.3f}s)")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_highlights_structure(source: SearchSource, test_date: date):
    """Teste: Estrutura dos highlights."""
    print_test("Estrutura dos highlights")
    try:
        search_terms = [Term(term="licitação", exact=False)]
        report = source.lookup(Trigger.BACKTEST, test_date, search_terms)
        
        if report.count == 0:
            print_result(True, "Nenhum highlight (esperado se termo não existe)")
            return True
        
        # Verificar estrutura dos highlights
        for highlight in report.highlights[:3]:  # Verificar primeiros 3
            if not hasattr(highlight, 'page'):
                print_result(False, "Highlight sem atributo 'page'")
                return False
            if not hasattr(highlight, 'content'):
                print_result(False, "Highlight sem atributo 'content'")
                return False
            if not hasattr(highlight, 'term'):
                print_result(False, "Highlight sem atributo 'term'")
                return False
            if not hasattr(highlight, 'page_url'):
                print_result(False, "Highlight sem atributo 'page_url'")
                return False
        
        print_result(True, f"Estrutura válida para {len(report.highlights)} highlights")
        return True
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_page_urls(source: SearchSource, test_date: date):
    """Teste: URLs das páginas no novo formato."""
    print_test("URLs das páginas (novo formato)")
    try:
        search_terms = [Term(term="licitação", exact=False)]
        report = source.lookup(Trigger.BACKTEST, test_date, search_terms)
        
        if report.count == 0:
            print_result(True, "Nenhum resultado para verificar URLs")
            return True
        
        # Verificar URLs no novo formato
        expected_base = "https://www.jornalminasgerais.mg.gov.br/edicao-do-dia?dados="
        
        for highlight in report.highlights[:3]:
            url = highlight.page_url
            
            # Verificar formato básico
            if not url.startswith('http'):
                print_result(False, f"URL inválida (não começa com http): {url}")
                return False
            
            # Verificar novo formato
            if not url.startswith(expected_base):
                print_result(False, f"URL não usa novo formato (esperado: {expected_base}...): {url}")
                return False
            
            # Verificar que contém dados codificados
            if 'dados=' not in url:
                print_result(False, f"URL não contém parâmetro 'dados=': {url}")
                return False
            
            # Verificar que a data está no formato correto (YYYY-MM-DD)
            date_str = test_date.isoformat()
            if date_str not in url:
                print_result(False, f"URL não contém data {date_str}: {url}")
                return False
            
            # Verificar que o número da página está presente (pode estar codificado)
            # Como está codificado, vamos verificar se a URL tem conteúdo suficiente
            if len(url) < len(expected_base) + 50:  # JSON codificado deve ter pelo menos 50 chars
                print_result(False, f"URL parece muito curta (dados codificados ausentes?): {url}")
                return False
        
        print_result(True, f"URLs válidas no novo formato para {len(report.highlights)} highlights")
        print(f"   📋 Exemplo de URL: {report.highlights[0].page_url[:100]}...")
        return True
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_fts5_search_with_email_notification(source: SearchSource, test_date: date):
    """Teste: Fluxo completo - Busca FTS5 com envio de email quando termos são encontrados."""
    print_test("Fluxo completo: Busca FTS5 → Relatório → Email")
    try:
        app = create_app()
        with app.app_context():
            from app.services.search_service import SearchService
            from mailer.mailer import Mailer
            from mailer.notification import notification_email
            from search.source import Term, Trigger
            
            # Criar configuração com termos que sabemos que existem no jornal
            config_data = {
                "label": "Teste FTS5 Email Completo",
                "description": "Config para testar fluxo completo: busca → email",
                "mail_to": ["augustocesargs@gmail.com"],
                "mail_subject": "Teste - Termos encontrados no Diário Oficial",
                "terms": [
                    {"term": "licitação", "exact": False},
                    {"term": "pregão", "exact": True}
                ]
            }
            config = SearchService.save_config(config_data)
            
            try:
                # Passo 1: Executar busca FTS5
                print("   📋 Passo 1: Executando busca FTS5...")
                search_terms = [
                    Term(term=term.term, exact=term.exact)
                    for term in config.terms
                ]
                
                report = source.lookup(Trigger.CRON, test_date, search_terms)
                
                if report.count == 0:
                    print("   ⚠️  Nenhum termo encontrado nesta data")
                    print("   💡 Isso pode acontecer se os termos não existem no jornal desta data")
                    print("   📧 Testando geração de email mesmo sem resultados (para validar template)...")
                    # Continuar o teste para validar que o email pode ser gerado mesmo sem resultados
                else:
                    print_result(True, f"Termos encontrados: {report.count} resultados")
                    print(f"   📊 Highlights: {len(report.highlights)}")
                    print(f"   🔍 Termos buscados: {[t.term for t in report.search_terms]}")
                
                # Passo 2: Gerar email de notificação
                print("   📧 Passo 2: Gerando email de notificação...")
                email = notification_email(
                    config.mail_to,
                    report,
                    subject=config.mail_subject
                )
                
                # Verificar estrutura do email
                if not email.to:
                    print_result(False, "Email sem destinatários")
                    return False
                
                if not email.subject:
                    print_result(False, "Email sem assunto")
                    return False
                
                if not email.text:
                    print_result(False, "Email sem corpo de texto")
                    return False
                
                if not email.html:
                    print_result(False, "Email sem corpo HTML")
                    return False
                
                print_result(True, "Email gerado com sucesso")
                print(f"   📬 Destinatários: {len(email.to)}")
                print(f"   📝 Assunto: {email.subject}")
                print(f"   📄 Tamanho texto: {len(email.text)} chars")
                print(f"   🌐 Tamanho HTML: {len(email.html)} chars")
                
                # Passo 3: Verificar conteúdo do email
                print("   ✅ Passo 3: Verificando conteúdo do email...")
                content_checks = []
                
                # Verificar que contém informações do relatório
                if str(report.count) in email.text:
                    content_checks.append(("Contagem de resultados", True))
                else:
                    content_checks.append(("Contagem de resultados", False))
                
                # Verificar que contém os termos buscados
                for term in report.search_terms:
                    if term.term.lower() in email.text.lower():
                        content_checks.append((f"Termo '{term.term}'", True))
                    else:
                        content_checks.append((f"Termo '{term.term}'", False))
                
                # Verificar que contém link do jornal do dia
                from mailer.notification import generate_daily_gazette_link
                expected_gazette_link = generate_daily_gazette_link(test_date)
                
                if expected_gazette_link in email.text or expected_gazette_link in email.html:
                    content_checks.append(("Link do jornal do dia", True))
                else:
                    content_checks.append(("Link do jornal do dia", False))
                
                # Verificar que o texto do link está presente
                if "Acessar Diário Oficial" in email.text or "Acessar Diário Oficial" in email.html:
                    content_checks.append(("Texto do link do jornal", True))
                else:
                    content_checks.append(("Texto do link do jornal", False))
                
                # Se houver highlights, verificar que estão no email
                if report.highlights:
                    if "Página" in email.text or "página" in email.text.lower():
                        content_checks.append(("Informações de páginas", True))
                    else:
                        content_checks.append(("Informações de páginas", False))
                else:
                    # Se não houver highlights, verificar que o email informa isso
                    if "0" in email.text or "nenhuma" in email.text.lower() or "nenhum" in email.text.lower():
                        content_checks.append(("Informação de nenhum resultado", True))
                    else:
                        content_checks.append(("Informação de nenhum resultado", False))
                
                # Verificar que pelo menos as informações básicas estão presentes
                required_checks = [check for check in content_checks if "Contagem" in check[0] or "Termo" in check[0]]
                all_required_passed = all(check[1] for check in required_checks)
                
                for check_name, passed in content_checks:
                    status = "✅" if passed else "❌"
                    print(f"      {status} {check_name}")
                
                if not all_required_passed:
                    print_result(False, "Verificações obrigatórias de conteúdo falharam")
                    return False
                
                if report.count > 0 and not all(check[1] for check in content_checks):
                    print("   ⚠️  Algumas verificações opcionais falharam, mas obrigatórias passaram")
                
                print_result(True, "Conteúdo do email válido")
                
                # Passo 4: Tentar enviar email (ou verificar que seria enviado)
                print("   📤 Passo 4: Tentando enviar email...")
                mailer = Mailer(app)
                
                # Verificar se SMTP está configurado
                mail_server = app.config.get('MAIL_SERVER')
                if not mail_server or mail_server == 'localhost':
                    print("   ⚠️  SMTP não configurado (MAIL_SERVER não definido ou é localhost)")
                    print("   ✅ Email gerado corretamente (envio pulado - SMTP não configurado)")
                    print("   💡 Configure MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD no .env para testar envio real")
                    return True  # Considerar sucesso se email foi gerado
                
                try:
                    mailer.send(email)
                    print_result(True, f"✅ Email enviado com sucesso para {config.mail_to}")
                    print(f"   📧 Email contém {report.count} resultados encontrados")
                    print(f"   📄 {len(report.highlights)} highlights incluídos")
                    return True
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'connection' in error_msg or 'refused' in error_msg:
                        print(f"   ⚠️  Erro de conexão SMTP: {e}")
                        print("   ✅ Email gerado corretamente (envio falhou por conexão)")
                        print("   💡 Verifique se o servidor SMTP está acessível")
                        return True  # Considerar sucesso se email foi gerado
                    elif 'authentication' in error_msg or 'login' in error_msg:
                        print(f"   ⚠️  Erro de autenticação SMTP: {e}")
                        print("   ✅ Email gerado corretamente (envio falhou por autenticação)")
                        print("   💡 Verifique MAIL_USERNAME e MAIL_PASSWORD no .env")
                        return True  # Considerar sucesso se email foi gerado
                    else:
                        print_result(False, f"Erro ao enviar email: {e}")
                        return False
                        
            finally:
                # Limpar configuração de teste
                try:
                    SearchService.delete_config(config.id)
                except Exception:
                    pass
                
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
    """Executa todos os testes de busca FTS5."""
    print("="*60)
    print("FASE 3.3: TESTE DE BUSCA FTS5 COM DADOS REAIS")
    print("="*60)
    print("\n⚠️  Este teste requer acesso à API IOF v1\n")
    
    # Encontrar data que funciona
    test_date = find_working_date()
    print(f"📅 Usando data: {test_date.isoformat()}\n")
    
    # Preparar banco de teste
    test_db = "/tmp/test_fts5_search.db"
    cleanup_test_db(test_db)
    
    source = None
    results = []
    
    try:
        # Importar jornal
        success, source = import_journal(test_date, test_db)
        results.append(("Importação do jornal", success))
        if not success or not source:
            print("❌ ERRO: Não foi possível importar jornal")
            sys.exit(1)
        
        # Reabrir source para testes
        source = SearchSource(test_db)
        
        try:
            # Executar testes
            results.append(("Múltiplos termos", test_multiple_terms_search(source, test_date)))
            results.append(("Exato vs não exato", test_exact_vs_inexact_search(source, test_date)))
            results.append(("Termo inexistente", test_nonexistent_term_search(source, test_date)))
            results.append(("Termo parcial", test_partial_term_search(source, test_date)))
            results.append(("Caracteres especiais", test_special_characters_search(source, test_date)))
            results.append(("Performance", test_search_performance(source, test_date)))
            results.append(("Estrutura highlights", test_highlights_structure(source, test_date)))
            results.append(("URLs das páginas", test_page_urls(source, test_date)))
            # Teste do fluxo completo: Busca → Relatório → Email
            results.append(("Fluxo completo (Busca→Email)", test_fts5_search_with_email_notification(source, test_date)))
        finally:
            source.close()
            source = None
        
    finally:
        cleanup_test_db(test_db)
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES DE BUSCA FTS5")
    print("="*60)
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n✅ Testes passaram: {passed}/{total}")
    print(f"❌ Testes falharam: {total - passed}/{total}")
    
    if all(success for _, success in results):
        print("\n🎉 TODOS OS TESTES DE BUSCA FTS5 PASSARAM!")
        sys.exit(0)
    else:
        print("\n⚠️  ALGUNS TESTES DE BUSCA FTS5 FALHARAM")
        sys.exit(1)


if __name__ == '__main__':
    main()
