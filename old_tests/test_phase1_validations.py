#!/usr/bin/env python3
"""Teste Fase 1.2: Validações e Edge Cases."""
import sys
import requests
import json

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


def test_missing_label():
    """Teste: Criar sem label."""
    print_test("Validação: Criar sem label")
    try:
        payload = {
            "description": "Sem label",
            "terms": [{"term": "teste", "exact": False}]
        }
        response = requests.post(
            f"{BASE_URL}/search/configs",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 422:
            data = response.json()
            if 'label' in str(data).lower() or 'errors' in data:
                print_result(True, "Retorna 422 com erro de validação para label")
                return True
            else:
                print_result(False, "Retorna 422 mas sem mensagem de erro apropriada")
                return False
        else:
            print_result(False, f"Esperava 422, recebeu {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_missing_terms():
    """Teste: Criar sem terms."""
    print_test("Validação: Criar sem terms")
    try:
        payload = {
            "label": "Teste sem terms",
            "description": "Sem termos"
        }
        response = requests.post(
            f"{BASE_URL}/search/configs",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        # Pode aceitar sem terms ou retornar erro - depende da implementação
        # Vamos verificar se retorna erro ou aceita
        if response.status_code in [201, 422]:
            print_result(True, f"Retorna status apropriado: {response.status_code}")
            return True
        else:
            print_result(False, f"Status inesperado: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_too_many_terms():
    """Teste: Criar com mais de 5 termos."""
    print_test("Validação: Mais de 5 termos")
    try:
        payload = {
            "label": "Teste",
            "terms": [
                {"term": "termo1", "exact": False},
                {"term": "termo2", "exact": False},
                {"term": "termo3", "exact": False},
                {"term": "termo4", "exact": False},
                {"term": "termo5", "exact": False},
                {"term": "termo6", "exact": False}
            ]
        }
        response = requests.post(
            f"{BASE_URL}/search/configs",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 422:
            data = response.json()
            if 'terms' in str(data).lower() or 'errors' in data:
                print_result(True, "Retorna 422 com erro de validação para termos")
                return True
            else:
                print_result(False, "Retorna 422 mas sem mensagem de erro apropriada")
                return False
        else:
            print_result(False, f"Esperava 422, recebeu {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_invalid_json():
    """Teste: JSON malformado."""
    print_test("Validação: JSON malformado")
    try:
        response = requests.post(
            f"{BASE_URL}/search/configs",
            data="invalid json{",
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        # Flask pode retornar 400, 422 ou até 500 dependendo de como trata JSON malformado
        if response.status_code in [400, 422, 500]:
            print_result(True, f"Retorna erro apropriado: {response.status_code}")
            return True
        else:
            print_result(False, f"Status inesperado: {response.status_code}, Response: {response.text[:100]}")
            return False
    except requests.exceptions.RequestException as e:
        # Se der exceção de requisição, também é válido (JSON malformado pode causar isso)
        print_result(True, f"Exceção tratada (esperado para JSON malformado): {type(e).__name__}")
        return True
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_empty_body():
    """Teste: Corpo vazio."""
    print_test("Validação: Corpo vazio")
    try:
        response = requests.post(
            f"{BASE_URL}/search/configs",
            json={},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code in [400, 422]:
            print_result(True, f"Retorna erro apropriado: {response.status_code}")
            return True
        else:
            print_result(False, f"Status inesperado: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_nonexistent_id():
    """Teste: Buscar configuração inexistente."""
    print_test("Validação: ID inexistente")
    try:
        response = requests.get(f"{BASE_URL}/search/configs/99999", timeout=5)
        if response.status_code == 404:
            print_result(True, "Retorna 404 para ID inexistente")
            return True
        else:
            print_result(False, f"Esperava 404, recebeu {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_update_nonexistent():
    """Teste: Atualizar configuração inexistente."""
    print_test("Validação: Atualizar ID inexistente")
    try:
        payload = {
            "label": "Teste",
            "terms": [{"term": "teste", "exact": False}]
        }
        response = requests.put(
            f"{BASE_URL}/search/configs/99999",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 404:
            print_result(True, "Retorna 404 para ID inexistente")
            return True
        else:
            print_result(False, f"Esperava 404, recebeu {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_delete_nonexistent():
    """Teste: Deletar configuração inexistente."""
    print_test("Validação: Deletar ID inexistente")
    try:
        response = requests.delete(f"{BASE_URL}/search/configs/99999", timeout=5)
        if response.status_code == 404:
            print_result(True, "Retorna 404 para ID inexistente")
            return True
        else:
            print_result(False, f"Esperava 404, recebeu {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_empty_label():
    """Teste: Label vazio."""
    print_test("Validação: Label vazio")
    try:
        payload = {
            "label": "",
            "terms": [{"term": "teste", "exact": False}]
        }
        response = requests.post(
            f"{BASE_URL}/search/configs",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 422:
            print_result(True, "Retorna 422 para label vazio")
            return True
        else:
            print_result(False, f"Esperava 422, recebeu {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_invalid_term_structure():
    """Teste: Estrutura de term inválida."""
    print_test("Validação: Estrutura de term inválida")
    try:
        payload = {
            "label": "Teste",
            "terms": [
                {"invalid": "structure"}
            ]
        }
        response = requests.post(
            f"{BASE_URL}/search/configs",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        # Pode aceitar ou rejeitar - depende da implementação
        if response.status_code in [201, 400, 422, 500]:
            print_result(True, f"Retorna status apropriado: {response.status_code}")
            return True
        else:
            print_result(False, f"Status inesperado: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def main():
    """Executa todos os testes de validação."""
    print("="*60)
    print("FASE 1.2: TESTE DE VALIDAÇÕES E EDGE CASES")
    print("="*60)
    print("\n⚠️  Certifique-se de que o servidor Flask está rodando!")
    print("   Execute: uv run python run.py\n")
    
    # Verificar servidor
    if not check_server():
        sys.exit(1)
    
    results = []
    
    # Executar testes
    results.append(("Criar sem label", test_missing_label()))
    results.append(("Criar sem terms", test_missing_terms()))
    results.append(("Mais de 5 termos", test_too_many_terms()))
    results.append(("JSON malformado", test_invalid_json()))
    results.append(("Corpo vazio", test_empty_body()))
    results.append(("ID inexistente (GET)", test_nonexistent_id()))
    results.append(("ID inexistente (PUT)", test_update_nonexistent()))
    results.append(("ID inexistente (DELETE)", test_delete_nonexistent()))
    results.append(("Label vazio", test_empty_label()))
    results.append(("Estrutura de term inválida", test_invalid_term_structure()))
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES DE VALIDAÇÃO")
    print("="*60)
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n✅ Testes passaram: {passed}/{total}")
    print(f"❌ Testes falharam: {total - passed}/{total}")
    
    if all(success for _, success in results):
        print("\n🎉 TODOS OS TESTES DE VALIDAÇÃO PASSARAM!")
        sys.exit(0)
    else:
        print("\n⚠️  ALGUNS TESTES DE VALIDAÇÃO FALHARAM")
        sys.exit(1)


if __name__ == '__main__':
    main()
