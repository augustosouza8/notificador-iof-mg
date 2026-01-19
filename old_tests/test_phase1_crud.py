#!/usr/bin/env python3
"""Teste Fase 1.1: CRUD Completo da API."""
import sys
import requests
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
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ ERRO: Servidor Flask não está rodando!")
        print("   Execute: uv run python run.py")
        return False
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False


def test_list_configs():
    """Teste: Listar configurações."""
    print_test("GET /api/search/configs - Listar Configurações")
    try:
        response = requests.get(f"{BASE_URL}/search/configs", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Encontradas {len(data)} configurações")
            return True, data
        else:
            print_result(False, f"Status code: {response.status_code}")
            return False, None
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False, None


def test_create_config():
    """Teste: Criar configuração."""
    print_test("POST /api/search/configs - Criar Configuração")
    try:
        payload = {
            "label": "Teste CRUD Fase 1",
            "description": "Configuração criada para teste CRUD",
            "attach_csv": False,
            "mail_to": ["teste@example.com"],
            "mail_subject": "Teste CRUD",
            "terms": [
                {"term": "licitação", "exact": False},
                {"term": "pregão", "exact": True}
            ]
        }
        response = requests.post(
            f"{BASE_URL}/search/configs",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 201:
            data = response.json()
            config_id = data.get('id')
            print_result(True, f"Configuração criada com ID: {config_id}")
            # Verificar estrutura
            required_fields = ['id', 'label', 'description', 'terms', 'mail_to']
            missing = [f for f in required_fields if f not in data]
            if missing:
                print_result(False, f"Campos faltando: {missing}")
                return False, None
            # Verificar termos
            if len(data.get('terms', [])) != 2:
                print_result(False, f"Esperava 2 termos, encontrou {len(data.get('terms', []))}")
                return False, None
            print_result(True, "Estrutura da resposta válida")
            return True, config_id
        else:
            print_result(False, f"Status code: {response.status_code}, Response: {response.text}")
            return False, None
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False, None


def test_get_config(config_id: int):
    """Teste: Buscar configuração por ID."""
    print_test(f"GET /api/search/configs/{config_id} - Buscar por ID")
    try:
        response = requests.get(f"{BASE_URL}/search/configs/{config_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Configuração encontrada: {data.get('label')}")
            # Verificar que o ID corresponde
            if data.get('id') != config_id:
                print_result(False, f"ID esperado {config_id}, recebido {data.get('id')}")
                return False, None
            print_result(True, "ID corresponde corretamente")
            return True, data
        else:
            print_result(False, f"Status code: {response.status_code}")
            return False, None
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False, None


def test_update_config(config_id: int):
    """Teste: Atualizar configuração."""
    print_test(f"PUT /api/search/configs/{config_id} - Atualizar Configuração")
    try:
        payload = {
            "label": "Teste CRUD Atualizado",
            "description": "Descrição atualizada pelo teste CRUD",
            "attach_csv": True,
            "mail_to": ["novo@example.com", "outro@example.com"],
            "mail_subject": "Assunto Atualizado",
            "terms": [
                {"term": "licitação", "exact": False},
                {"term": "concorrência", "exact": True},
                {"term": "edital", "exact": False}
            ]
        }
        response = requests.put(
            f"{BASE_URL}/search/configs/{config_id}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Configuração atualizada: {data.get('label')}")
            # Verificar se foi realmente atualizada
            if data.get('label') != payload['label']:
                print_result(False, f"Label não atualizado. Esperado: {payload['label']}, Recebido: {data.get('label')}")
                return False, None
            if len(data.get('terms', [])) != 3:
                print_result(False, f"Termos não atualizados. Esperado: 3, Recebido: {len(data.get('terms', []))}")
                return False, None
            if len(data.get('mail_to', [])) != 2:
                print_result(False, f"Emails não atualizados. Esperado: 2, Recebido: {len(data.get('mail_to', []))}")
                return False, None
            print_result(True, "Todos os campos foram atualizados corretamente")
            return True, data
        else:
            print_result(False, f"Status code: {response.status_code}, Response: {response.text}")
            return False, None
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False, None


def test_delete_config(config_id: int):
    """Teste: Deletar configuração."""
    print_test(f"DELETE /api/search/configs/{config_id} - Deletar Configuração")
    try:
        response = requests.delete(f"{BASE_URL}/search/configs/{config_id}", timeout=5)
        if response.status_code == 204:
            print_result(True, "Configuração deletada com sucesso (204 No Content)")
            # Verificar se foi realmente deletada
            check_response = requests.get(f"{BASE_URL}/search/configs/{config_id}", timeout=5)
            if check_response.status_code == 404:
                print_result(True, "Verificação: Configuração não existe mais (404)")
            else:
                print_result(False, f"Verificação: Configuração ainda existe (status: {check_response.status_code})")
                return False
            return True
        else:
            print_result(False, f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def test_list_active_only():
    """Teste: Listar com filtro active_only."""
    print_test("GET /api/search/configs?active_only=... - Filtro active_only")
    try:
        # Listar apenas ativas
        response = requests.get(f"{BASE_URL}/search/configs?active_only=true", timeout=5)
        if response.status_code == 200:
            active_configs = response.json()
            print_result(True, f"Configurações ativas: {len(active_configs)}")
        else:
            print_result(False, f"Status code ao listar ativas: {response.status_code}")
            return False
        
        # Listar todas
        response = requests.get(f"{BASE_URL}/search/configs?active_only=false", timeout=5)
        if response.status_code == 200:
            all_configs = response.json()
            print_result(True, f"Total de configurações: {len(all_configs)}")
            # Verificar que total >= ativas
            if len(all_configs) < len(active_configs):
                print_result(False, f"Total ({len(all_configs)}) menor que ativas ({len(active_configs)})")
                return False
            print_result(True, "Filtro active_only funciona corretamente")
            return True
        else:
            print_result(False, f"Status code ao listar todas: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erro: {e}")
        return False


def main():
    """Executa todos os testes CRUD."""
    print("="*60)
    print("FASE 1.1: TESTE CRUD COMPLETO DA API")
    print("="*60)
    print("\n⚠️  Certifique-se de que o servidor Flask está rodando!")
    print("   Execute: uv run python run.py\n")
    
    # Verificar servidor
    if not check_server():
        sys.exit(1)
    
    results = []
    created_config_id: Optional[int] = None
    
    # Executar testes
    success, _ = test_list_configs()
    results.append(("Listar Configurações", success))
    
    success, config_id = test_create_config()
    results.append(("Criar Configuração", success))
    if config_id:
        created_config_id = config_id
    
    if created_config_id:
        success, _ = test_get_config(created_config_id)
        results.append(("Buscar por ID", success))
        
        success, _ = test_update_config(created_config_id)
        results.append(("Atualizar Configuração", success))
        
        success = test_delete_config(created_config_id)
        results.append(("Deletar Configuração", success))
    
    success = test_list_active_only()
    results.append(("Filtro active_only", success))
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES CRUD")
    print("="*60)
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n✅ Testes passaram: {passed}/{total}")
    print(f"❌ Testes falharam: {total - passed}/{total}")
    
    if all(success for _, success in results):
        print("\n🎉 TODOS OS TESTES CRUD PASSARAM!")
        sys.exit(0)
    else:
        print("\n⚠️  ALGUNS TESTES CRUD FALHARAM")
        sys.exit(1)


if __name__ == '__main__':
    main()
