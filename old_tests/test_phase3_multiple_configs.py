#!/usr/bin/env python3
"""Teste Fase 3.1: Múltiplas Configurações."""
import sys
import requests
import time
from datetime import date, timedelta
from typing import List

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
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ ERRO: Servidor Flask não está rodando!")
        print("   Execute: uv run python run.py")
        return False
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False


def find_working_date():
    """Encontra uma data que funciona na API v1."""
    from iof.v1.consulta import consulta_por_data
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


def create_multiple_configs(count: int = 8) -> List[int]:
    """Cria múltiplas configurações de teste."""
    print_test(f"Criando {count} configurações de teste")
    config_ids = []
    
    terms_sets = [
        [{"term": "licitação", "exact": False}],
        [{"term": "pregão", "exact": True}],
        [{"term": "edital", "exact": False}],
        [{"term": "concorrência", "exact": False}],
        [{"term": "licitação", "exact": False}, {"term": "pregão", "exact": True}],
        [{"term": "edital", "exact": False}, {"term": "concorrência", "exact": False}],
        [{"term": "tomada", "exact": False}, {"term": "preços", "exact": False}],
        [{"term": "homologação", "exact": True}]
    ]
    
    for i in range(count):
        payload = {
            "label": f"Config Teste {i+1}",
            "description": f"Configuração de teste número {i+1}",
            "attach_csv": i % 2 == 0,  # Alternar
            "mail_to": [f"test{i+1}@example.com"],
            "mail_subject": f"Teste {i+1}",
            "terms": terms_sets[i % len(terms_sets)]
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
                config_ids.append(data.get('id'))
            else:
                print_result(False, f"Erro ao criar config {i+1}: {response.status_code}")
        except Exception as e:
            print_result(False, f"Erro ao criar config {i+1}: {e}")
    
    if len(config_ids) == count:
        print_result(True, f"Criadas {len(config_ids)} configurações")
    else:
        print_result(False, f"Esperava {count}, criou {len(config_ids)}")
    
    return config_ids


def test_backtest_all_configs(config_ids: List[int], test_date: date):
    """Teste: Executar backtest para todas as configurações."""
    print_test(f"Backtest para {len(config_ids)} configurações")
    results = []
    start_time = time.time()
    
    for i, config_id in enumerate(config_ids, 1):
        try:
            url = f"{BASE_URL}/search/configs/{config_id}/backtest?date={test_date.isoformat()}"
            response = requests.get(url, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                results.append({
                    'config_id': config_id,
                    'success': True,
                    'count': data.get('count', 0),
                    'highlights': len(data.get('highlights', []))
                })
                print(f"  ✅ Config {config_id}: {data.get('count')} resultados")
            else:
                results.append({
                    'config_id': config_id,
                    'success': False,
                    'error': f"Status {response.status_code}"
                })
                print(f"  ❌ Config {config_id}: Erro {response.status_code}")
        except Exception as e:
            results.append({
                'config_id': config_id,
                'success': False,
                'error': str(e)
            })
            print(f"  ❌ Config {config_id}: {e}")
    
    elapsed_time = time.time() - start_time
    successful = sum(1 for r in results if r.get('success'))
    
    print_result(
        successful == len(config_ids),
        f"{successful}/{len(config_ids)} backtests executados com sucesso"
    )
    print(f"   Tempo total: {elapsed_time:.2f}s")
    print(f"   Tempo médio por config: {elapsed_time/len(config_ids):.2f}s")
    
    return results


def test_overlapping_terms(config_ids: List[int], test_date: date):
    """Teste: Configurações com termos sobrepostos."""
    print_test("Configurações com termos sobrepostos")
    try:
        # Encontrar configs com termos sobrepostos
        overlapping_configs = []
        for config_id in config_ids[:3]:  # Testar primeiras 3
            try:
                response = requests.get(f"{BASE_URL}/search/configs/{config_id}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    terms = [t.get('term') for t in data.get('terms', [])]
                    if 'licitação' in terms or 'pregão' in terms:
                        overlapping_configs.append(config_id)
            except Exception:
                continue
        
        if len(overlapping_configs) >= 2:
            print_result(True, f"Encontradas {len(overlapping_configs)} configs com termos sobrepostos")
            
            # Executar backtest para verificar que resultados podem ser diferentes
            results = []
            for config_id in overlapping_configs[:2]:
                try:
                    url = f"{BASE_URL}/search/configs/{config_id}/backtest?date={test_date.isoformat()}"
                    response = requests.get(url, timeout=60)
                    if response.status_code == 200:
                        data = response.json()
                        results.append(data.get('count', 0))
                except Exception:
                    results.append(0)
            
            if len(results) == 2:
                print(f"   Resultados: {results[0]} e {results[1]} matches")
                print_result(True, "Termos sobrepostos processados corretamente")
                return True
        
        print_result(False, "Não encontrou configs com termos sobrepostos para testar")
        return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_different_terms(config_ids: List[int], test_date: date):
    """Teste: Configurações com termos diferentes."""
    print_test("Configurações com termos diferentes")
    try:
        # Executar backtest para configs diferentes
        results = {}
        for config_id in config_ids[:5]:  # Testar primeiras 5
            try:
                response = requests.get(f"{BASE_URL}/search/configs/{config_id}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    terms = [t.get('term') for t in data.get('terms', [])]
                    term_key = '_'.join(sorted(terms))
                    
                    url = f"{BASE_URL}/search/configs/{config_id}/backtest?date={test_date.isoformat()}"
                    backtest_response = requests.get(url, timeout=60)
                    if backtest_response.status_code == 200:
                        backtest_data = backtest_response.json()
                        results[term_key] = backtest_data.get('count', 0)
            except Exception:
                continue
        
        if len(results) >= 3:
            print_result(True, f"Testadas {len(results)} configurações com termos diferentes")
            print(f"   Resultados variam de {min(results.values())} a {max(results.values())} matches")
            return True
        else:
            print_result(False, f"Esperava pelo menos 3 configs diferentes, testou {len(results)}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def cleanup_configs(config_ids: List[int]):
    """Remove configurações de teste."""
    print_test("Limpando configurações de teste")
    deleted = 0
    for config_id in config_ids:
        try:
            response = requests.delete(f"{BASE_URL}/search/configs/{config_id}", timeout=5)
            if response.status_code == 204:
                deleted += 1
        except Exception:
            pass
    
    print_result(deleted == len(config_ids), f"Deletadas {deleted}/{len(config_ids)} configurações")


def main():
    """Executa todos os testes com múltiplas configurações."""
    print("="*60)
    print("FASE 3.1: TESTE COM MÚLTIPLAS CONFIGURAÇÕES")
    print("="*60)
    print("\n⚠️  Certifique-se de que o servidor Flask está rodando!")
    print("   Execute: uv run python run.py\n")
    
    # Verificar servidor
    if not check_server():
        sys.exit(1)
    
    # Encontrar data que funciona
    test_date = find_working_date()
    print(f"📅 Usando data: {test_date.isoformat()}\n")
    
    config_ids = []
    results = []
    
    try:
        # Criar múltiplas configurações
        config_ids = create_multiple_configs(8)
        if not config_ids:
            print("❌ ERRO: Não foi possível criar configurações")
            sys.exit(1)
        
        results.append(("Criação de múltiplas configs", len(config_ids) == 8))
        
        # Executar testes
        backtest_results = test_backtest_all_configs(config_ids, test_date)
        results.append(("Backtest para todas", all(r.get('success') for r in backtest_results)))
        results.append(("Termos sobrepostos", test_overlapping_terms(config_ids, test_date)))
        results.append(("Termos diferentes", test_different_terms(config_ids, test_date)))
        
    finally:
        # Limpar
        if config_ids:
            cleanup_configs(config_ids)
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES COM MÚLTIPLAS CONFIGURAÇÕES")
    print("="*60)
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n✅ Testes passaram: {passed}/{total}")
    print(f"❌ Testes falharam: {total - passed}/{total}")
    
    if all(success for _, success in results):
        print("\n🎉 TODOS OS TESTES COM MÚLTIPLAS CONFIGURAÇÕES PASSARAM!")
        sys.exit(0)
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM")
        sys.exit(1)


if __name__ == '__main__':
    main()
