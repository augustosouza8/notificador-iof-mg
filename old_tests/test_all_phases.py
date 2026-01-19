#!/usr/bin/env python3
"""Script mestre que executa todos os testes das Fases 1, 2 e 3."""
import sys
import subprocess
import time
from datetime import datetime
from typing import List, Tuple


def print_header(text: str):
    """Imprime cabeçalho."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_result(test_name: str, success: bool, elapsed: float, output: str = ""):
    """Imprime resultado de um teste."""
    status = "✅ PASSOU" if success else "❌ FALHOU"
    print(f"\n{status} {test_name} ({elapsed:.2f}s)")
    if output and not success:
        # Mostrar apenas últimas linhas em caso de erro
        lines = output.split('\n')
        if len(lines) > 20:
            print("   ... (mostrando últimas 20 linhas) ...")
            for line in lines[-20:]:
                if line.strip():
                    print(f"   {line}")
        else:
            for line in lines:
                if line.strip():
                    print(f"   {line}")


def run_test(script_name: str) -> Tuple[bool, float, str]:
    """Executa um script de teste e retorna (sucesso, tempo, output)."""
    print(f"\n▶️  Executando: {script_name}")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos máximo por teste
        )
        elapsed = time.time() - start_time
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, elapsed, output
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        return False, elapsed, "Timeout após 5 minutos"
    except Exception as e:
        elapsed = time.time() - start_time
        return False, elapsed, f"Erro ao executar: {e}"


def main():
    """Executa todos os testes em ordem."""
    print_header("TESTE COMPLETO - FASES 1, 2 e 3")
    print(f"\nIniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n⚠️  Certifique-se de que o servidor Flask está rodando!")
    print("   Execute: uv run python run.py\n")
    
    # Lista de testes em ordem
    tests = [
        # Fase 1: API
        ("Fase 1.1: CRUD", "test_phase1_crud.py"),
        ("Fase 1.2: Validações", "test_phase1_validations.py"),
        ("Fase 1.3: Backtest", "test_phase1_backtest.py"),
        
        # Fase 2: Integração
        ("Fase 2.1: Integração", "test_phase2_integration.py"),
        ("Fase 2.2: Email", "test_phase2_email.py"),
        ("Fase 2.3: Notify", "test_phase2_notify.py"),
        
        # Fase 3: Performance e Robustez
        ("Fase 3.1: Múltiplas Configs", "test_phase3_multiple_configs.py"),
        ("Fase 3.2: Tratamento de Erros", "test_phase3_error_handling.py"),
        ("Fase 3.3: Busca FTS5", "test_phase3_fts5_search.py"),
    ]
    
    results = []
    total_start_time = time.time()
    
    # Executar cada teste
    for test_name, script_name in tests:
        success, elapsed, output = run_test(script_name)
        results.append((test_name, success, elapsed, output))
        print_result(test_name, success, elapsed, output)
        
        # Se teste crítico falhar, perguntar se continua
        if not success and test_name.startswith("Fase 1"):
            print("\n⚠️  Teste crítico da Fase 1 falhou.")
            print("   Deseja continuar com os testes seguintes? (s/n): ", end="")
            # Em modo automatizado, continuar sempre
            # response = input().strip().lower()
            # if response != 's':
            #     print("\n❌ Execução interrompida pelo usuário")
            #     break
    
    total_elapsed = time.time() - total_start_time
    
    # Resumo final
    print_header("RESUMO FINAL")
    
    print("\n📊 Resultados por Fase:")
    print("\nFASE 1: API")
    phase1_results = [r for r in results if r[0].startswith("Fase 1")]
    for test_name, success, elapsed, _ in phase1_results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name} ({elapsed:.2f}s)")
    
    print("\nFASE 2: Integração")
    phase2_results = [r for r in results if r[0].startswith("Fase 2")]
    for test_name, success, elapsed, _ in phase2_results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name} ({elapsed:.2f}s)")
    
    print("\nFASE 3: Performance e Robustez")
    phase3_results = [r for r in results if r[0].startswith("Fase 3")]
    for test_name, success, elapsed, _ in phase3_results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name} ({elapsed:.2f}s)")
    
    # Estatísticas
    passed = sum(1 for _, success, _, _ in results if success)
    total = len(results)
    total_time = sum(elapsed for _, _, elapsed, _ in results)
    
    print(f"\n📈 Estatísticas:")
    print(f"   Total de testes: {total}")
    print(f"   ✅ Passaram: {passed}")
    print(f"   ❌ Falharam: {total - passed}")
    print(f"   Taxa de sucesso: {(passed/total*100):.1f}%")
    print(f"   Tempo total: {total_elapsed:.2f}s")
    print(f"   Tempo de execução: {total_time:.2f}s")
    print(f"   Tempo médio por teste: {total_time/total:.2f}s")
    
    # Resultado final
    print_header("RESULTADO FINAL")
    
    if all(success for _, success, _, _ in results):
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print(f"   Executados {total} testes em {total_elapsed:.2f}s")
        sys.exit(0)
    else:
        failed_tests = [name for name, success, _, _ in results if not success]
        print(f"\n⚠️  {len(failed_tests)} TESTE(S) FALHARAM:")
        for test_name in failed_tests:
            print(f"   ❌ {test_name}")
        print(f"\n   Total: {passed}/{total} testes passaram")
        sys.exit(1)


if __name__ == '__main__':
    main()
