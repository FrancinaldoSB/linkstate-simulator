#!/usr/bin/env python3
import subprocess
import time
import re
import sys
import json
from typing import Dict, List, Tuple, Set

# Cores para saída no terminal
class Colors:
    GREEN = '\033[92m'  # Verde para sucesso
    RED = '\033[91m'    # Vermelho para falha
    YELLOW = '\033[93m' # Amarelo para aviso
    BLUE = '\033[94m'   # Azul para informação
    ENDC = '\033[0m'    # Resetar cor

def print_color(text, color):
    """Imprime texto colorido no terminal."""
    print(f"{color}{text}{Colors.ENDC}")

def format_table(rows, headers=None):
    """Formata uma tabela simples em texto sem dependências externas."""
    if not rows:
        return ""
    
    # Determinar larguras máximas para cada coluna
    num_cols = len(rows[0])
    col_widths = [0] * num_cols
    
    # Adicionar cabeçalhos se existirem
    all_rows = []
    if headers:
        all_rows.append(headers)
    all_rows.extend(rows)
    
    # Calcular largura máxima para cada coluna
    for row in all_rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Construir a tabela
    result = []
    
    # Adicionar linha de cabeçalho
    if headers:
        header_line = "| " + " | ".join(str(headers[i]).ljust(col_widths[i]) for i in range(num_cols)) + " |"
        result.append(header_line)
        separator = "+-" + "-+-".join("-" * col_widths[i] for i in range(num_cols)) + "-+"
        result.append(separator)
    
    # Adicionar linhas de dados
    for row in rows:
        data_line = "| " + " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(num_cols)) + " |"
        result.append(data_line)
    
    return "\n".join(result)

def run_command(command: List[str]) -> Tuple[int, str, str]:
    """Executa um comando e retorna o código de retorno, stdout e stderr."""
    process = subprocess.run(command, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE, 
                            text=True)
    return process.returncode, process.stdout, process.stderr

def get_containers() -> Dict[str, Dict]:
    """Obtém a lista de contêineres Docker em execução e suas informações."""
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
            # Extrai o tipo e número do contêiner (ex: router1, host2a)
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
    """Obtém informações detalhadas sobre um contêiner."""
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

def test_connectivity(source_container: str, target_ip: str) -> bool:
    """Testa a conectividade entre dois contêineres usando ping."""
    command = ["docker", "exec", source_container, "ping", "-c", "1", "-W", "1", target_ip]
    returncode, stdout, stderr = run_command(command)
    
    return returncode == 0

def get_routing_table(container: str) -> str:
    """Obtém a tabela de roteamento de um contêiner."""
    command = ["docker", "exec", container, "ip", "route"]
    returncode, stdout, stderr = run_command(command)
    
    if returncode != 0:
        return f"Erro ao obter tabela de roteamento: {stderr}"
    
    return stdout

def test_all_connectivity(containers: Dict[str, Dict]) -> Tuple[Dict, Dict, Dict]:
    """Testa a conectividade entre todos os contêineres."""
    router_to_router = {}
    router_to_host = {}
    host_to_host = {}
    
    # Mapeia nomes de contêineres para seus IDs para uso mais fácil
    container_map = {info["name"]: name for name, info in containers.items()}
    
    # Obtém informações detalhadas de cada contêiner
    container_details = {}
    for name, info in containers.items():
        container_details[name] = get_container_info(info["id"])
    
    # Testa conectividade entre roteadores
    routers = [name for name, info in containers.items() if info["type"] == "router"]
    hosts = [name for name, info in containers.items() if info["type"] == "host"]
    
    print_color("\n===== Testando conectividade entre roteadores =====", Colors.BLUE)
    for router1 in routers:
        router_to_router[router1] = {}
        for router2 in routers:
            if router1 != router2:
                # Obter todos os IPs do router2
                target_ips = container_details[router2]["ips"]
                # Testamos a conectividade com cada IP
                success = False
                for subnet, ip in target_ips.items():
                    if test_connectivity(router1, ip):
                        success = True
                        router_to_router[router1][router2] = True
                        print_color(f"✓ {router1} -> {router2} ({ip})", Colors.GREEN)
                        break
                
                if not success:
                    router_to_router[router1][router2] = False
                    print_color(f"✗ {router1} -> {router2} (todos IPs)", Colors.RED)
    
    print_color("\n===== Testando conectividade de roteadores para hosts =====", Colors.BLUE)
    for router in routers:
        router_to_host[router] = {}
        for host in hosts:
            # Determinar se o host está na mesma subrede que o roteador
            host_subnet = re.search(r'host([0-9]+)', container_details[host]["name"]).group(1)
            # Obter o IP do host
            host_ips = container_details[host]["ips"]
            target_ip = host_ips.get(host_subnet) if host_ips else None
            
            if target_ip:
                success = test_connectivity(router, target_ip)
                router_to_host[router][host] = success
                if success:
                    print_color(f"✓ {router} -> {host} ({target_ip})", Colors.GREEN)
                else:
                    print_color(f"✗ {router} -> {host} ({target_ip})", Colors.RED)
    
    print_color("\n===== Testando conectividade entre hosts =====", Colors.BLUE)
    for host1 in hosts:
        host_to_host[host1] = {}
        for host2 in hosts:
            if host1 != host2:
                # Obter o IP do host2
                host2_subnet = re.search(r'host([0-9]+)', container_details[host2]["name"]).group(1)
                host2_ips = container_details[host2]["ips"]
                target_ip = host2_ips.get(host2_subnet) if host2_ips else None
                
                if target_ip:
                    success = test_connectivity(host1, target_ip)
                    host_to_host[host1][host2] = success
                    if success:
                        print_color(f"✓ {host1} -> {host2} ({target_ip})", Colors.GREEN)
                    else:
                        print_color(f"✗ {host1} -> {host2} ({target_ip})", Colors.RED)
    
    return router_to_router, router_to_host, host_to_host

def analyze_results(router_to_router, router_to_host, host_to_host):
    """Analisa os resultados dos testes de conectividade."""
    print_color("\n===== Análise dos Testes de Conectividade =====", Colors.BLUE)
    
    # Contadores para estatísticas
    r2r_success = sum(1 for r1 in router_to_router for r2 in router_to_router[r1] if router_to_router[r1][r2])
    r2r_total = sum(1 for r1 in router_to_router for r2 in router_to_router[r1])
    
    r2h_success = sum(1 for r in router_to_host for h in router_to_host[r] if router_to_host[r][h])
    r2h_total = sum(1 for r in router_to_host for h in router_to_host[r])
    
    h2h_success = sum(1 for h1 in host_to_host for h2 in host_to_host[h1] if host_to_host[h1][h2])
    h2h_total = sum(1 for h1 in host_to_host for h2 in host_to_host[h1])
    
    # Cria tabela de resultados
    results = [
        ["Roteador → Roteador", f"{r2r_success}/{r2r_total}", f"{(r2r_success/r2r_total*100) if r2r_total > 0 else 0:.1f}%"],
        ["Roteador → Host", f"{r2h_success}/{r2h_total}", f"{(r2h_success/r2h_total*100) if r2h_total > 0 else 0:.1f}%"],
        ["Host → Host", f"{h2h_success}/{h2h_total}", f"{(h2h_success/h2h_total*100) if h2h_total > 0 else 0:.1f}%"],
        ["Total", f"{r2r_success+r2h_success+h2h_success}/{r2r_total+r2h_total+h2h_total}", 
         f"{((r2r_success+r2h_success+h2h_success)/(r2r_total+r2h_total+h2h_total)*100) if (r2r_total+r2h_total+h2h_total) > 0 else 0:.1f}%"]
    ]
    
    # Mostrar tabela formatada
    headers = ["Tipo de Conexão", "Sucesso/Total", "Taxa de Sucesso"]
    print(format_table(results, headers))
    
    # Verifica problemas específicos
    if r2r_success < r2r_total:
        print_color("\nProblemas de conectividade entre roteadores:", Colors.YELLOW)
        for r1 in router_to_router:
            for r2 in router_to_router[r1]:
                if not router_to_router[r1][r2]:
                    print_color(f"  - {r1} não consegue alcançar {r2}", Colors.RED)
                    # Verifica se o IP forwarding está ativado
                    returncode, stdout, stderr = run_command(["docker", "exec", r1, "cat", "/proc/sys/net/ipv4/ip_forward"])
                    if returncode == 0 and stdout.strip() == "0":
                        print_color(f"    IP Forwarding não está ativado em {r1}", Colors.RED)
    
    if h2h_success < h2h_total:
        print_color("\nProblemas de conectividade entre hosts:", Colors.YELLOW)
        for h1 in host_to_host:
            failed_connections = [h2 for h2 in host_to_host[h1] if not host_to_host[h1][h2]]
            if failed_connections:
                print_color(f"  - {h1} não consegue alcançar: {', '.join(failed_connections)}", Colors.RED)
                # Verifica se há uma rota padrão
                routes = get_routing_table(h1)
                if "default" not in routes:
                    print_color(f"    {h1} não tem rota padrão configurada", Colors.RED)

def main():
    print_color("=== Teste de Conectividade da Rede ===", Colors.BLUE)
    print("Buscando contêineres em execução...")
    
    containers = get_containers()
    if not containers:
        print_color("Nenhum contêiner encontrado. Certifique-se de que a rede está em execução.", Colors.RED)
        sys.exit(1)
    
    print_color(f"Encontrados {len(containers)} contêineres", Colors.GREEN)
    
    # Classifica contêineres por tipo
    routers = [name for name, info in containers.items() if info["type"] == "router"]
    hosts = [name for name, info in containers.items() if info["type"] == "host"]
    
    print_color(f"Roteadores: {len(routers)}", Colors.BLUE)
    print_color(f"Hosts: {len(hosts)}", Colors.BLUE)
    
    # Testa conectividade
    r2r, r2h, h2h = test_all_connectivity(containers)
    
    # Analisa resultados
    analyze_results(r2r, r2h, h2h)

if __name__ == "__main__":
    main()
