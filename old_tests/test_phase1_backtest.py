#!/usr/bin/env python3
"""Teste Fase 1.3: Backtest End-to-End."""
import sys
import requests
from datetime import date, timedelta
from typing import Optional

BASE_URL = "http://localhost:5000/api"


def print_test(name: str):
    """Imprime cabeçalho de teste."""
    print(f"\n{'='*60}")
    print(f"TESTE: {name}")
    print('='*60)


def print_result(success: bool, message: str = ""):
    """Imprime resultado do teste."""
    status = "✅ PASSOU" if success else "❌ FALHOU"
    print(f"{status}: {message}")


def check_server():
    """Verifica se o servidor está rodando."""
    try:
        response = requests.get(f"{BASE_URL}/features", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get('backtest'):
                return True
            else:
                print("⚠️  Backtest não está habilitado (APP_ENV != development)")
                return False
        return False
    except requests.exceptions.ConnectionError:
        print("❌ ERRO: Servidor Flask não está rodando!")
        print("   Execute: uv run python run.py")
        return False
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False


def find_working_date():
    """Encontra uma data que funciona na API v1."""
    print_test("Encontrando data que funciona na API v1")
    today = date.today()
    for i in range(30):
        test_date = today - timedelta(days=i)
        try:
            url = (
                "https://www.jornalminasgerais.mg.gov.br/api/v1/"
                f"Jornal/ObterEdicaoPorDataPublicacao"
                f"?dataPublicacao={test_date.isoformat()}"
            )
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and 'dados' in data:
                    print_result(True, f"Data encontrada: {test_date.isoformat()}")
                    return test_date
        except Exception:
            continue
    print_result(False, "Nenhuma data funcionando nos últimos 30 dias")
    return None


def create_test_config():
    """Cria uma configuração de teste."""
    payload = {
        "label": "Teste Backtest",
        "description": "Configuração para teste de backtest",
        "attach_csv": False,
        "mail_to": ["teste@example.com"],
        "mail_subject": "Teste Backtest",
        "terms": [
            {"term": "licitação", "exact": False},
            {"term": "pregão", "exact": True}
        ]
    }
    try:
        response = requests.post(
            f"{BASE_URL}/search/configs",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 201:
            data = response.json()
            return data.get('id')
        return None
    except Exception:
        return None


def test_backtest_with_new_date(config_id: int, test_date: date):
    """Teste: Backtest com data que não está no banco."""
    print_test(f"Backtest com data nova ({test_date.isoformat()})")
    try:
        url = f"{BASE_URL}/search/configs/{config_id}/backtest?date={test_date.isoformat()}"
        response = requests.get(url, timeout=60)  # Timeout maior para download
        
        if response.status_code == 200:
            data = response.json()
            # Verificar estrutura
            required_fields = ['publish_date', 'highlights', 'search_terms', 'trigger', 'count']
            missing = [f for f in required_fields if f not in data]
            if missing:
                print_result(False, f"Campos faltando: {missing}")
                return False
            
            print_result(True, f"Backtest executado com sucesso")
            print(f"   Data: {data.get('publish_date')}")
            print(f"   Encontrados: {data.get('count')} resultados")
            print(f"   Termos: {len(data.get('search_terms', []))}")
            print(f"   Highlights: {len(data.get('highlights', []))}")
            
            # Verificar que a data corresponde
            if data.get('publish_date') != test_date.isoformat():
                print_result(False, f"Data não corresponde. Esperado: {test_date.isoformat()}, Recebido: {data.get('publish_date')}")
                return False
            
            return True
        elif response.status_code == 404:
            error_msg = response.text
            if 'não encontrado' in error_msg.lower() or 'not found' in error_msg.lower():
                print_result(True, f"Diário não encontrado para {test_date.isoformat()} (esperado)")
                return True
            else:
                print_result(False, f"404 inesperado: {error_msg}")
                return False
        else:
            print_result(False, f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except requests.exceptions.Timeout:
        print_result(False, "Timeout ao executar backtest")
        return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_backtest_multiple_terms(config_id: int, test_date: date):
    """Teste: Backtest com múltiplos termos."""
    print_test("Backtest com múltiplos termos")
    try:
        # Primeiro atualizar a config com mais termos
        payload = {
            "label": "Teste Backtest Múltiplos Termos",
            "description": "Configuração com múltiplos termos",
            "terms": [
                {"term": "licitação", "exact": False},
                {"term": "pregão", "exact": True},
                {"term": "edital", "exact": False},
                {"term": "concorrência", "exact": False}
            ]
        }
        update_response = requests.put(
            f"{BASE_URL}/search/configs/{config_id}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if update_response.status_code != 200:
            print_result(False, f"Erro ao atualizar config: {update_response.status_code}")
            return False
        
        # Executar backtest
        url = f"{BASE_URL}/search/configs/{config_id}/backtest?date={test_date.isoformat()}"
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            terms_count = len(data.get('search_terms', []))
            if terms_count == 4:
                print_result(True, f"Backtest com {terms_count} termos executado")
                return True
            else:
                print_result(False, f"Esperava 4 termos, encontrou {terms_count}")
                return False
        else:
            print_result(False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_backtest_exact_vs_inexact(config_id: int, test_date: date):
    """Teste: Backtest com termos exatos vs não exatos."""
    print_test("Backtest: Termos exatos vs não exatos")
    try:
        # Atualizar com mix de exatos e não exatos
        payload = {
            "label": "Teste Backtest Exato/Inexato",
            "terms": [
                {"term": "licitação", "exact": False},
                {"term": "pregão", "exact": True}
            ]
        }
        update_response = requests.put(
            f"{BASE_URL}/search/configs/{config_id}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if update_response.status_code != 200:
            print_result(False, f"Erro ao atualizar config: {update_response.status_code}")
            return False
        
        # Executar backtest
        url = f"{BASE_URL}/search/configs/{config_id}/backtest?date={test_date.isoformat()}"
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            terms = data.get('search_terms', [])
            exact_count = sum(1 for t in terms if t.get('exact', False))
            inexact_count = sum(1 for t in terms if not t.get('exact', False))
            
            print_result(True, f"Termos exatos: {exact_count}, não exatos: {inexact_count}")
            return True
        else:
            print_result(False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_backtest_invalid_date(config_id: int):
    """Teste: Backtest com data inválida."""
    print_test("Backtest: Data inválida")
    try:
        url = f"{BASE_URL}/search/configs/{config_id}/backtest?date=invalid-date"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 422:
            print_result(True, "Retorna 422 para data inválida")
            return True
        else:
            print_result(False, f"Esperava 422, recebeu {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_backtest_future_date(config_id: int):
    """Teste: Backtest com data futura."""
    print_test("Backtest: Data futura")
    try:
        future_date = date.today() + timedelta(days=1)
        url = f"{BASE_URL}/search/configs/{config_id}/backtest?date={future_date.isoformat()}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 422:
            print_result(True, "Retorna 422 para data futura")
            return True
        else:
            print_result(False, f"Esperava 422, recebeu {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_backtest_missing_date(config_id: int):
    """Teste: Backtest sem parâmetro date."""
    print_test("Backtest: Sem parâmetro date")
    try:
        url = f"{BASE_URL}/search/configs/{config_id}/backtest"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 422:
            print_result(True, "Retorna 422 quando date está ausente")
            return True
        else:
            print_result(False, f"Esperava 422, recebeu {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def cleanup_config(config_id: Optional[int]):
    """Remove configuração de teste."""
    if config_id:
        try:
            requests.delete(f"{BASE_URL}/search/configs/{config_id}", timeout=5)
        except Exception:
            pass


def main():
    """Executa todos os testes de backtest."""
    print("="*60)
    print("FASE 1.3: TESTE DE BACKTEST END-TO-END")
    print("="*60)
    print("\n⚠️  Certifique-se de que o servidor Flask está rodando!")
    print("   Execute: uv run python run.py\n")
    
    # Verificar servidor
    if not check_server():
        sys.exit(1)
    
    # Encontrar data que funciona
    test_date = find_working_date()
    if not test_date:
        print("⚠️  Não foi possível encontrar uma data que funciona. Pulando alguns testes.")
        test_date = date(2026, 1, 9)  # Data conhecida que funciona
    
    # Criar configuração de teste
    config_id = create_test_config()
    if not config_id:
        print("❌ ERRO: Não foi possível criar configuração de teste")
        sys.exit(1)
    
    results = []
    
    try:
        # Executar testes
        if test_date:
            results.append(("Backtest com data nova", test_backtest_with_new_date(config_id, test_date)))
            results.append(("Backtest múltiplos termos", test_backtest_multiple_terms(config_id, test_date)))
            results.append(("Backtest exato/inexato", test_backtest_exact_vs_inexact(config_id, test_date)))
        
        results.append(("Backtest data inválida", test_backtest_invalid_date(config_id)))
        results.append(("Backtest data futura", test_backtest_future_date(config_id)))
        results.append(("Backtest sem date", test_backtest_missing_date(config_id)))
        
    finally:
        # Limpar
        cleanup_config(config_id)
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES DE BACKTEST")
    print("="*60)
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n✅ Testes passaram: {passed}/{total}")
    print(f"❌ Testes falharam: {total - passed}/{total}")
    
    if all(success for _, success in results):
        print("\n🎉 TODOS OS TESTES DE BACKTEST PASSARAM!")
        sys.exit(0)
    else:
        print("\n⚠️  ALGUNS TESTES DE BACKTEST FALHARAM")
        sys.exit(1)


if __name__ == '__main__':
    main()
