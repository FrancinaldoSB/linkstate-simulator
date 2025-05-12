#!/usr/bin/env python3
import sys
import argparse
from typing import Dict, List, Set, Tuple

def gerar_docker_compose(num_roteadores: int, links_roteadores: Dict[str, List[str]]):
    """
    Gera um arquivo docker-compose.yml para uma topologia de rede.
    
    Args:
        num_roteadores: Número de roteadores (e consequentemente subredes) a serem criados
        links_roteadores: Dicionário que mapeia cada roteador aos roteadores com os quais se conecta
    """
    # Para controlar as conexões dos roteadores e as redes
    router_networks = {}  # router_name -> {network_name -> ip}
    router_ips = {}  # router_name -> primary_ip
    router_env_vars = {}  # router_name -> list of env vars
    
    # Primeira passagem: determinar IP principal de cada roteador
    for i, router_name in enumerate(links_roteadores.keys(), 1):
        primary_network = f"subnet_{i}"
        primary_ip = f"172.20.{i}.3"
        router_ips[router_name] = primary_ip
        
        # Inicializa as redes e variáveis de ambiente para este roteador
        router_networks[router_name] = {primary_network: primary_ip}
        connections = links_roteadores[router_name]
        router_env_vars[router_name] = [
            f"router_links={','.join(connections)}",
            f"my_ip={primary_ip}",
            f"my_name={router_name}"
        ]
    
    # Segunda passagem: adicionar IPs dos vizinhos às variáveis de ambiente
    for router_name, connections in links_roteadores.items():
        for conn in connections:
            if conn in router_ips:
                router_env_vars[router_name].append(f"{conn}_ip={router_ips[conn]}")
    
    # Terceira passagem: configurar conexões de rede entre roteadores
    for i, (router_name, connections) in enumerate(links_roteadores.items(), 1):
        for conn_router in connections:
            if conn_router in links_roteadores:
                conn_idx = list(links_roteadores.keys()).index(conn_router) + 1
                conn_network = f"subnet_{conn_idx}"
                
                # Se ainda não tem conexão com esta rede
                if conn_network not in router_networks[router_name]:
                    # Atribui um IP nesta rede
                    conn_ip = f"172.20.{conn_idx}.{i+3}"  # +3 para evitar conflito com IP principal
                    router_networks[router_name][conn_network] = conn_ip
    
    # Agora, geramos o conteúdo do docker-compose com todas as informações coletadas
    content = "services:\n"
    
    # Adiciona os serviços de roteadores
    for router_name in links_roteadores.keys():
        content += f"  {router_name}:\n"
        content += "    build:\n"
        content += "      context: ./router\n"
        content += "      dockerfile: Dockerfile\n"
        
        # Adiciona variáveis de ambiente
        content += "    environment:\n"
        for env_var in router_env_vars[router_name]:
            content += f"    - {env_var}\n"
        
        # Adiciona redes
        content += "    networks:\n"
        for network, ip in router_networks[router_name].items():
            content += f"      {network}:\n"
            content += f"        ipv4_address: {ip}\n"
        
        # Adiciona capacidades
        content += "    cap_add:\n"
        content += "    - NET_ADMIN\n"
    
    # Gera hosts para cada rede
    for i in range(1, num_roteadores + 1):
        router_name = f"router{i}"
        if router_name not in links_roteadores:
            continue
            
        # Adiciona dois hosts por rede
        for h in ['a', 'b']:
            host_name = f"host{i}{h}"
            content += f"  {host_name}:\n"
            content += "    build:\n"
            content += "      context: ./host\n"
            content += "      dockerfile: Dockerfile\n"
            content += "    networks:\n"
            content += f"      subnet_{i}:\n"
            content += f"        ipv4_address: 172.20.{i}.1{ord(h) - ord('a')}0\n"
            content += "    depends_on:\n"
            content += f"    - {router_name}\n"
            # Adicionar capacidade NET_ADMIN para os hosts
            content += "    cap_add:\n"
            content += "    - NET_ADMIN\n"
    
    # Gera seção de redes
    content += "networks:\n"
    for i in range(1, num_roteadores + 1):
        content += f"  subnet_{i}:\n"
        content += "    driver: bridge\n"
        content += "    ipam:\n"
        content += "      config:\n"
        content += f"      - subnet: 172.20.{i}.0/24\n"
    
    return content

def main():
    parser = argparse.ArgumentParser(description='Gerar arquivo docker-compose.yml para simulador Link State')
    parser.add_argument('-n', '--num-roteadores', type=int, default=3,
                        help='Número de roteadores/subredes a serem criados (padrão: 3). '
                             'Cada roteador gerencia uma subrede com 2 hosts.')
    parser.add_argument('-o', '--output', type=str, default='docker-compose.yml',
                        help='Nome do arquivo de saída (padrão: docker-compose.yml)')
    parser.add_argument('-t', '--tipo', type=str, choices=['linha', 'anel', 'estrela', 'custom'], default='linha',
                        help='Tipo de topologia: linha, anel, estrela ou custom (padrão: linha)')
    parser.add_argument('-c', '--conexoes', type=str, default='',
                        help='Formato para conexões personalizadas: "router1:router2,router3;router2:router1,router3"')
    
    args = parser.parse_args()
    
    # Determina as conexões entre roteadores
    links = {}
    
    if args.tipo == 'linha':
        # Topologia em linha: r1 -- r2 -- r3 -- ...
        for i in range(1, args.num_roteadores + 1):
            router = f"router{i}"
            links[router] = []
            if i > 1:
                links[router].append(f"router{i-1}")
            if i < args.num_roteadores:
                links[router].append(f"router{i+1}")
        print("\nTopologia em Linha criada:")
        print("  " + " -- ".join([f"router{i}" for i in range(1, args.num_roteadores + 1)]))
    
    elif args.tipo == 'anel':
        # Topologia em anel: r1 -- r2 -- r3 -- ... -- r1
        for i in range(1, args.num_roteadores + 1):
            router = f"router{i}"
            links[router] = []
            # Conecta com o anterior (ou o último se for o primeiro)
            prev = f"router{args.num_roteadores if i == 1 else i-1}"
            links[router].append(prev)
            # Conecta com o próximo (ou o primeiro se for o último)
            next_r = f"router{1 if i == args.num_roteadores else i+1}"
            links[router].append(next_r)
        print("\nTopologia em Anel criada:")
        print("  " + " -- ".join([f"router{i}" for i in range(1, args.num_roteadores + 1)]) + f" -- router1")
    
    elif args.tipo == 'estrela':
        # Topologia em estrela: r1 é o centro, conectado a todos os outros
        central = "router1"
        links[central] = [f"router{i}" for i in range(2, args.num_roteadores + 1)]
        for i in range(2, args.num_roteadores + 1):
            router = f"router{i}"
            links[router] = [central]
        
        # Representação visual da topologia estrela
        print("\nTopologia em Estrela criada:")
        print("  router1 (central)")
        for i in range(2, args.num_roteadores + 1):
            print(f"  |-- router{i}")
    
    elif args.tipo == 'custom' and args.conexoes:
        # Topologia personalizada a partir de string
        for conn_str in args.conexoes.split(';'):
            if ':' in conn_str:
                router, connections = conn_str.split(':')
                if not router.strip():
                    continue
                connections_list = [c.strip() for c in connections.split(',') if c.strip()]
                links[router.strip()] = connections_list
        
        # Visualização da topologia personalizada
        print("\nTopologia Personalizada criada:")
        for router, connections in links.items():
            print(f"  {router} conectado a: {', '.join(connections)}")
    else:
        if args.tipo == 'custom':
            print("Erro: Conexões personalizadas não fornecidas. Usando topologia em linha como padrão.")
            # Criar topologia em linha como fallback
            for i in range(1, args.num_roteadores + 1):
                router = f"router{i}"
                links[router] = []
                if i > 1:
                    links[router].append(f"router{i-1}")
                if i < args.num_roteadores:
                    links[router].append(f"router{i+1}")
    
    # Gera o conteúdo do docker-compose
    compose_content = gerar_docker_compose(args.num_roteadores, links)
    
    # Escreve no arquivo
    with open(args.output, 'w') as f:
        f.write(compose_content)
    
    print(f"\nArquivo {args.output} gerado com sucesso!")
    print(f"Topologia: {args.tipo} com {args.num_roteadores} roteadores/subredes")
    print("\nConexões entre roteadores:")
    for router, connections in links.items():
        print(f"  {router} → {', '.join(connections)}")
    
    print("\nCada subrede possui um roteador principal e 2 hosts.")
    print("Configuração de subredes:")
    for i in range(1, args.num_roteadores + 1):
        if f"router{i}" in links:
            print(f"  subnet_{i}: 172.20.{i}.0/24 (router{i}, host{i}a, host{i}b)")
    
    print("\nPara executar a simulação:")
    print("  docker-compose -f ./docker-compose.yml up -d")
    print("\nPara verificar os logs:")
    print("  docker-compose logs -f")

if __name__ == "__main__":
    main()
