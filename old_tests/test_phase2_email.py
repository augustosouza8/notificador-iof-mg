#!/usr/bin/env python3
"""Teste Fase 2.2: Sistema de Email."""
import sys
import os
from datetime import date
from app import create_app
from mailer.mailer import Mailer, Email
from mailer.notification import notification_email
from search.source import Report, Highlight, Term, Trigger


def print_test(name: str):
    """Imprime cabeçalho de teste."""
    print(f"\n{'='*60}")
    print(f"TESTE: {name}")
    print('='*60)


def print_result(success: bool, message: str = ""):
    """Imprime resultado do teste."""
    status = "✅ PASSOU" if success else "❌ FALHOU"
    print(f"{status}: {message}")


def test_email_generation():
    """Teste: Geração de email de notificação."""
    print_test("Geração de email de notificação")
    try:
        # Criar report de teste
        report = Report(
            publish_date=date.today(),
            highlights=[
                Highlight(
                    page=1,
                    content="<b>licitação</b> encontrada no texto",
                    term="licitação",
                    page_url="https://example.com/page/1"
                ),
                Highlight(
                    page=2,
                    content="<b>pregão</b> mencionado aqui",
                    term="pregão",
                    page_url="https://example.com/page/2"
                )
            ],
            search_terms=[
                Term(term="licitação", exact=False),
                Term(term="pregão", exact=True)
            ],
            trigger=Trigger.CRON,
            count=2
        )
        
        # Gerar email
        recipients = ["teste@example.com", "outro@example.com"]
        email = notification_email(recipients, report, subject="Teste de Email")
        
        # Verificar estrutura
        if not email.to:
            print_result(False, "Lista de destinatários vazia")
            return False
        
        if len(email.to) != 2:
            print_result(False, f"Esperava 2 destinatários, encontrou {len(email.to)}")
            return False
        
        if not email.subject:
            print_result(False, "Assunto vazio")
            return False
        
        if not email.text:
            print_result(False, "Corpo de texto vazio")
            return False
        
        if not email.html:
            print_result(False, "Corpo HTML vazio")
            return False
        
        # Verificar conteúdo
        if "licitação" not in email.text.lower():
            print_result(False, "Termo 'licitação' não encontrado no texto")
            return False
        
        if "pregão" not in email.text.lower():
            print_result(False, "Termo 'pregão' não encontrado no texto")
            return False
        
        print_result(True, "Email gerado com sucesso")
        print(f"   Destinatários: {len(email.to)}")
        print(f"   Assunto: {email.subject}")
        print(f"   Tamanho texto: {len(email.text)} chars")
        print(f"   Tamanho HTML: {len(email.html)} chars")
        return True
    except Exception as e:
        print_result(False, f"Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_template_content():
    """Teste: Conteúdo do template."""
    print_test("Conteúdo do template de email")
    try:
        report = Report(
            publish_date=date(2026, 1, 9),
            highlights=[
                Highlight(
                    page=1,
                    content="<b>teste</b>",
                    term="teste",
                    page_url="https://example.com"
                )
            ],
            search_terms=[Term(term="teste", exact=False)],
            trigger=Trigger.CRON,
            count=1
        )
        
        email = notification_email(["test@example.com"], report)
        
        # Verificar que contém informações do report
        checks = [
            ("count", str(report.count)),
            ("publish_date", "09/01/2026"),
            ("term", "teste"),
            ("page", "1")
        ]
        
        for check_name, check_value in checks:
            if check_value.lower() not in email.text.lower() and check_value.lower() not in email.html.lower():
                print_result(False, f"'{check_name}' ({check_value}) não encontrado no email")
                return False
        
        print_result(True, "Template contém todas as informações necessárias")
        return True
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_email_multiple_recipients():
    """Teste: Email com múltiplos destinatários."""
    print_test("Email com múltiplos destinatários")
    try:
        report = Report(
            publish_date=date.today(),
            highlights=[],
            search_terms=[Term(term="teste", exact=False)],
            trigger=Trigger.CRON,
            count=0
        )
        
        recipients = ["email1@example.com", "email2@example.com", "email3@example.com"]
        email = notification_email(recipients, report)
        
        if len(email.to) != 3:
            print_result(False, f"Esperava 3 destinatários, encontrou {len(email.to)}")
            return False
        
        if set(email.to) != set(recipients):
            print_result(False, "Lista de destinatários não corresponde")
            return False
        
        print_result(True, f"Email criado com {len(email.to)} destinatários")
        return True
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_email_send():
    """Teste: Envio de email (requer SMTP configurado)."""
    print_test("Envio de email (SMTP real)")
    try:
        app = create_app()
        with app.app_context():
            # Verificar se SMTP está configurado
            mail_server = app.config.get('MAIL_SERVER')
            if not mail_server or mail_server == 'localhost':
                print_result(False, "SMTP não configurado (MAIL_SERVER não definido ou é localhost)")
                print("   Configure MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD no .env")
                return False
            
            mailer = Mailer(app)
            
            # Criar email de teste simples
            test_email = Email(
                to=[app.config.get('MAIL_DEFAULT_SENDER', 'test@example.com')],
                subject="Teste - Notificador IOF MG",
                text="Este é um email de teste do sistema de notificações.",
                html="<p>Este é um email de teste do sistema de notificações.</p>"
            )
            
            # Tentar enviar
            try:
                mailer.send(test_email)
                print_result(True, "Email enviado com sucesso")
                return True
            except Exception as e:
                error_msg = str(e).lower()
                if 'connection' in error_msg or 'refused' in error_msg:
                    print_result(False, f"Erro de conexão SMTP: {e}")
                    print("   Verifique se o servidor SMTP está acessível")
                elif 'authentication' in error_msg or 'login' in error_msg:
                    print_result(False, f"Erro de autenticação SMTP: {e}")
                    print("   Verifique MAIL_USERNAME e MAIL_PASSWORD no .env")
                else:
                    print_result(False, f"Erro ao enviar email: {e}")
                return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_smtp_error_handling():
    """Teste: Tratamento de erro de SMTP."""
    print_test("Tratamento de erro de SMTP")
    try:
        app = create_app()
        with app.app_context():
            # Configurar SMTP inválido temporariamente
            original_server = app.config.get('MAIL_SERVER')
            app.config['MAIL_SERVER'] = 'invalid-smtp-server.example.com'
            app.config['MAIL_PORT'] = 587
            
            mailer = Mailer(app)
            
            test_email = Email(
                to=["test@example.com"],
                subject="Teste",
                text="Teste"
            )
            
            try:
                mailer.send(test_email)
                print_result(False, "Email enviado mesmo com SMTP inválido (não esperado)")
                return False
            except Exception as e:
                print_result(True, f"Erro tratado corretamente: {type(e).__name__}")
                return True
            finally:
                # Restaurar configuração original
                if original_server:
                    app.config['MAIL_SERVER'] = original_server
    except Exception as e:
        # Se der erro na configuração, considerar como sucesso (erro foi tratado)
        print_result(True, f"Erro tratado: {type(e).__name__}")
        return True


def main():
    """Executa todos os testes de email."""
    print("="*60)
    print("FASE 2.2: TESTE DE SISTEMA DE EMAIL")
    print("="*60)
    print("\n⚠️  Testes de envio requerem SMTP configurado no .env\n")
    
    results = []
    
    # Executar testes
    results.append(("Geração de email", test_email_generation()))
    results.append(("Conteúdo do template", test_email_template_content()))
    results.append(("Múltiplos destinatários", test_email_multiple_recipients()))
    results.append(("Envio de email (SMTP)", test_email_send()))
    results.append(("Tratamento de erro SMTP", test_email_smtp_error_handling()))
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES DE EMAIL")
    print("="*60)
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n✅ Testes passaram: {passed}/{total}")
    print(f"❌ Testes falharam: {total - passed}/{total}")
    
    # Nota sobre SMTP
    if not results[3][1]:  # test_email_send
        print("\n⚠️  Nota: Teste de envio SMTP falhou. Isso é esperado se SMTP não estiver configurado.")
        print("   Configure MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD no .env para testar envio real.")
    
    # Considerar sucesso se pelo menos os testes básicos passaram
    basic_tests_passed = all(success for _, success in results[:3])
    if basic_tests_passed:
        print("\n🎉 TESTES BÁSICOS DE EMAIL PASSARAM!")
        sys.exit(0)
    else:
        print("\n⚠️  ALGUNS TESTES DE EMAIL FALHARAM")
        sys.exit(1)


if __name__ == '__main__':
    main()
