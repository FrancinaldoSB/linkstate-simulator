#!/usr/bin/env python3
import subprocess
import time
import re
import sys
import json
import statistics
from typing import Dict, List, Tuple, Set
import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime

class Colors:
    GREEN = '\033[92m' 
    RED = '\033[91m' 
    YELLOW = '\033[93m'
    BLUE = '\033[94m'  
    ENDC = '\033[0m'   

def print_color(text, color):
    print(f"{color}{text}{Colors.ENDC}")

def format_table(rows, headers=None):
    if not rows:
        return ""

    num_cols = len(rows[0])
    col_widths = [0] * num_cols

    all_rows = []
    if headers:
        all_rows.append(headers)
    all_rows.extend(rows)

    for row in all_rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    result = []

    if headers:
        header_line = "| " + " | ".join(str(headers[i]).ljust(col_widths[i]) for i in range(num_cols)) + " |"
        result.append(header_line)
        separator = "+-" + "-+-".join("-" * col_widths[i] for i in range(num_cols)) + "-+"
        result.append(separator)

    for row in rows:
        data_line = "| " + " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(num_cols)) + " |"
        result.append(data_line)
    
    return "\n".join(result)

def run_command(command: List[str]) -> Tuple[int, str, str]:
    process = subprocess.run(command, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE, 
                            text=True)
    return process.returncode, process.stdout, process.stderr

def get_containers() -> Dict[str, Dict]:
    returncode, stdout, stderr = run_command(["docker", "ps", "--format", "{{.Names}},{{.ID}},{{.Image}}"])
    
    if returncode != 0:
        print_color(f"Erro ao obter contêineres: {stderr}", Colors.RED)
        return {}
    
    containers = {}
    for line in stdout.strip().split('\n'):
        if not line:
            continue
        name, container_id, image = line.split(',')
        if "linkstate-simulator" in name:
            match = re.match(r'linkstate-simulator_([a-z]+)([0-9]+[a-z]*)_1', name)
            if match:
                container_type, container_num = match.groups()
                containers[name] = {
                    "id": container_id,
                    "image": image,
                    "type": container_type,
                    "num": container_num,
                    "name": name
                }
    
    return containers

def get_container_info(container_id: str) -> Dict:
    returncode, stdout, stderr = run_command(["docker", "inspect", container_id])
    
    if returncode != 0:
        print_color(f"Erro ao inspecionar contêiner {container_id}: {stderr}", Colors.RED)
        return {}
    
    try:
        inspect_data = json.loads(stdout)[0]
        networks = inspect_data.get("NetworkSettings", {}).get("Networks", {})
        
        ips = {}
        for network_name, network_data in networks.items():
            if "linkstate-simulator" in network_name and "subnet" in network_name:
                ip = network_data.get("IPAddress", "")
                if ip:
                    subnet = re.search(r'subnet_([0-9]+)', network_name)
                    if subnet:
                        subnet_num = subnet.group(1)
                        ips[subnet_num] = ip
        
        return {
            "id": container_id,
            "name": inspect_data.get("Name", "").strip('/'),
            "ips": ips,
            "running": inspect_data.get("State", {}).get("Running", False)
        }
    except json.JSONDecodeError:
        print_color(f"Erro ao decodificar JSON para contêiner {container_id}", Colors.RED)
        return {}

def test_ping_latency(source_container: str, target_ip: str, count: int = 5) -> Tuple[bool, float]:
    command = ["docker", "exec", source_container, "ping", "-c", str(count), "-q", target_ip]
    returncode, stdout, stderr = run_command(command)
    
    if returncode != 0:
        return False, 0.0

    match = re.search(r'min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/[\d.]+', stdout)
    if match:
        avg_latency = float(match.group(1))
        return True, avg_latency
    
    return True, 0.0

def test_convergence_time():
    print_color("\n===== Teste de Tempo de Convergência da Topologia =====", Colors.BLUE)

    containers = get_containers()
    if not containers:
        print_color("Nenhum contêiner encontrado. Certifique-se de que a rede está em execução.", Colors.RED)
        return False, 0
    
    routers = [name for name, info in containers.items() if info["type"] == "router"]
    hosts = [name for name, info in containers.items() if info["type"] == "host"]
    
    print_color(f"Testando convergência com {len(routers)} roteadores e {len(hosts)} hosts", Colors.BLUE)

    print_color("Reiniciando serviços de roteamento...", Colors.YELLOW)
    for router in routers:
        restart_cmd = ["docker", "exec", router, "pkill", "-f", "python.*router.py"]
        run_command(restart_cmd)

        start_cmd = ["docker", "exec", "-d", router, "python", "/app/router.py"]
        run_command(start_cmd)
    
    print_color("Serviços de roteamento reiniciados. Testando convergência...", Colors.YELLOW)

    start_time = time.time()

    max_attempts = 30 
    converged = False
    attempt = 0

    host_details = {}
    for host in hosts:
        host_details[host] = get_container_info(containers[host]["id"])
    
    while attempt < max_attempts and not converged:
        attempt += 1
        print_color(f"Tentativa {attempt}/{max_attempts}...", Colors.YELLOW)
 
        all_successful = True

        test_hosts = {}
        for host, details in host_details.items():
            for subnet_num, ip in details["ips"].items():
                if subnet_num not in test_hosts:
                    test_hosts[subnet_num] = (host, ip)

        if len(test_hosts) >= 2:
            subnets = list(test_hosts.keys())
            for i in range(len(subnets) - 1):
                source_host, _ = test_hosts[subnets[i]]
                _, target_ip = test_hosts[subnets[i+1]]
                
                print_color(f"Testando ping de {source_host} para {target_ip}...", Colors.YELLOW)
            
                command = ["docker", "exec", source_host, "ping", "-c", "1", "-W", "2", target_ip]
                returncode, _, _ = run_command(command)
                
                if returncode != 0:
                    print_color(f"Ping falhou de {source_host} para {target_ip}", Colors.RED)
                    all_successful = False
                    break
                else:
                    print_color(f"Ping bem-sucedido de {source_host} para {target_ip}", Colors.GREEN)
        else:
            print_color("Não há hosts suficientes em subredes diferentes para testar", Colors.RED)
            all_successful = False
        
        if all_successful:
            converged = True
            break

        time.sleep(2)

    elapsed_time = time.time() - start_time
    
    if converged:
        print_color(f"\nA rede convergiu em {elapsed_time:.2f} segundos ({attempt} tentativas)", Colors.GREEN)
    else:
        print_color(f"\nA rede não convergiu após {elapsed_time:.2f} segundos ({max_attempts} tentativas)", Colors.RED)
    
    return converged, elapsed_time

def generate_latency_heatmap(host_latencies: Dict[str, Dict[str, float]], output_file: str = "latency_heatmap.png"):
    hosts = sorted(list(host_latencies.keys()))
    num_hosts = len(hosts)

    latency_matrix = np.zeros((num_hosts, num_hosts))
    for i, source in enumerate(hosts):
        for j, target in enumerate(hosts):
            if source == target:
                latency_matrix[i][j] = 0  
            elif target in host_latencies[source]:
                latency_matrix[i][j] = host_latencies[source][target]
            else:
                latency_matrix[i][j] = np.nan  

    plt.figure(figsize=(10, 8))
    plt.imshow(latency_matrix, cmap='viridis', interpolation='nearest')

    plt.title('Latência entre Hosts (ms)', fontsize=16)
    plt.xticks(range(num_hosts), hosts, rotation=45, ha='right')
    plt.yticks(range(num_hosts), hosts)

    for i in range(num_hosts):
        for j in range(num_hosts):
            if not np.isnan(latency_matrix[i][j]):
                if latency_matrix[i][j] > 0: 
                    plt.text(j, i, f"{latency_matrix[i][j]:.2f}", ha='center', va='center', 
                             color='white' if latency_matrix[i][j] > np.nanmean(latency_matrix) else 'black')
    
    plt.colorbar(label='Latência (ms)')
    plt.tight_layout()
    
    plt.savefig(output_file)
    print_color(f"Gráfico de latência salvo como {output_file}", Colors.GREEN)
    

def save_statistics_to_file(stats: Dict, filename: str = "latency_stats.txt"):
    with open(filename, 'w') as f:
        f.write(f"Estatísticas de Latência - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*50 + "\n\n")
        
        for key, value in stats.items():
            f.write(f"{key}: {value:.3f} ms\n")
    
    print_color(f"Estatísticas salvas no arquivo {filename}", Colors.GREEN)

def test_ping_latency_all_hosts():
    print_color("\n===== Teste de Latência de Ping entre Hosts =====", Colors.BLUE)
    
    containers = get_containers()
    if not containers:
        print_color("Nenhum contêiner encontrado. Certifique-se de que a rede está em execução.", Colors.RED)
        return []
    
    hosts = {name: info for name, info in containers.items() if info["type"] == "host"}
    
    print_color(f"Testando latência entre {len(hosts)} hosts", Colors.BLUE)
    
    host_details = {}
    for name, info in hosts.items():
        host_details[name] = get_container_info(info["id"])
    
    results = []
    
    host_latencies = {host: {} for host in host_details.keys()}
    
    ping_count = 1

    for source_name, source_info in host_details.items():
        for target_name, target_info in host_details.items():
            if source_name == target_name:
                continue
            
            target_ip = None
            for subnet, ip in target_info["ips"].items():
                target_ip = ip
                break
            
            if not target_ip:
                print_color(f"Não foi possível obter IP para {target_name}", Colors.RED)
                continue
            
            print_color(f"Testando latência de {source_name} para {target_name} ({target_ip})...", Colors.YELLOW)
            
            success, latency = test_ping_latency(source_name, target_ip, ping_count)
            
            if success:
                print_color(f"Latência média: {latency:.3f} ms", Colors.GREEN)
                results.append([source_name, target_name, f"{latency:.3f} ms", "✓"])
                host_latencies[source_name][target_name] = latency
            else:
                print_color(f"Falha no teste de ping", Colors.RED)
                results.append([source_name, target_name, "N/A", "✗"])
    
    if results:
        headers = ["Origem", "Destino", "Latência Média", "Status"]
        print("\n" + format_table(results, headers))
        
        latencies = [float(r[2].replace(" ms", "")) for r in results if r[3] == "✓"]
        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            median_latency = statistics.median(latencies)
            
            print_color("\nEstatísticas de Latência:", Colors.BLUE)
            print(f"Média: {avg_latency:.3f} ms")
            print(f"Mínima: {min_latency:.3f} ms")
            print(f"Máxima: {max_latency:.3f} ms")
            print(f"Mediana: {median_latency:.3f} ms")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            heatmap_file = f"latency_heatmap_{timestamp}.png"
            stats_file = f"latency_stats_{timestamp}.txt"
            
            generate_latency_heatmap(host_latencies, heatmap_file)
            
            stats = {
                "Média": avg_latency,
                "Mínima": min_latency,
                "Máxima": max_latency,
                "Mediana": median_latency
            }
            save_statistics_to_file(stats, stats_file)
    
    return results

def main():
    print_color("=== Teste de Limiar de Estresse da Rede ===", Colors.BLUE)
    print_color("IMPORTANTE: Este script deve ser executado com a topologia já em execução!", Colors.YELLOW)
    print_color("Certifique-se de que todos os contêineres do simulador estejam rodando antes de prosseguir.", Colors.YELLOW)
    print()
    print("Selecione uma opção de teste:")
    print("1. Teste de tempo de convergência da topologia")
    print("2. Teste de latência de ping entre hosts")
    print("3. Executar ambos os testes")
    
    option = input("Opção (1/2/3): ").strip()
    
    if option == "1" or option == "3":
        converged, time_elapsed = test_convergence_time()
    
    if option == "2" or option == "3":
        results = test_ping_latency_all_hosts()

if __name__ == "__main__":
    main()
