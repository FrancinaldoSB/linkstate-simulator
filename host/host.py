import os
import time
import socket
import subprocess
import ipaddress

def log(msg):
    print(msg, flush=True)

def get_ip_info():
    """Obtém informações de IP do host."""
    try:
        # Obter o endereço IP local e máscara
        ip_info = subprocess.run(["ip", "addr"], capture_output=True, text=True)
        log(f"Interfaces de rede: {ip_info.stdout}")
        
        # Executar o comando hostname -I para obter apenas o IP principal
        ip_cmd = subprocess.run(["hostname", "-I"], capture_output=True, text=True)
        if ip_cmd.stdout.strip():
            my_ip = ip_cmd.stdout.strip().split()[0]
            log(f"Meu IP: {my_ip}")
            return my_ip
        else:
            log("Não foi possível determinar o IP do host")
            return None
    except Exception as e:
        log(f"Erro ao obter informações de IP: {e}")
        return None

def find_gateway(my_ip):
    """Encontra o gateway (roteador) para este host com base no IP."""
    try:
        # Determinar a subrede com base no IP
        # Assumindo /24 como máscara
        ip_parts = my_ip.split('.')
        router_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.3"  # Assume que o roteador é .3
        
        log(f"Identificado gateway: {router_ip}")
        return router_ip
    except Exception as e:
        log(f"Erro ao identificar gateway: {e}")
        return None

def configure_routing(gateway_ip):
    """Configura a tabela de roteamento do host."""
    try:
        # Mostrar tabela de roteamento atual
        route_cmd = subprocess.run(["ip", "route"], capture_output=True, text=True)
        log(f"Tabela de roteamento atual: {route_cmd.stdout}")
        
        # Remover rota padrão existente se houver
        try:
            subprocess.run(["ip", "route", "del", "default"], check=False)
            log("Rota padrão existente removida")
        except:
            pass
        
        # Adicionar rota padrão via gateway
        result = subprocess.run(["ip", "route", "add", "default", "via", gateway_ip], 
                               capture_output=True, text=True, check=False)
        if result.returncode != 0:
            log(f"Erro ao adicionar rota padrão: {result.stderr}")
        else:
            log(f"Adicionada rota padrão via {gateway_ip}")
        
        # Para garantir, adicione rotas específicas para outras subredes
        for subnet in range(1, 6):  # Para as 5 possíveis subredes
            subnet_cidr = f"172.20.{subnet}.0/24"
            
            # Não adicionar rota para nossa própria subrede
            my_subnet = gateway_ip.split('.')[2]
            if str(subnet) == my_subnet:
                continue
                
            route_cmd = ["ip", "route", "replace", subnet_cidr, "via", gateway_ip]
            result = subprocess.run(route_cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                log(f"Adicionada rota para {subnet_cidr} via {gateway_ip}")
            else:
                log(f"Erro ao adicionar rota para {subnet_cidr}: {result.stderr}")
        
        # Verificar se as rotas foram adicionadas
        updated_route = subprocess.run(["ip", "route"], capture_output=True, text=True)
        log(f"Tabela de roteamento atualizada: {updated_route.stdout}")
        
        return True
    except Exception as e:
        log(f"Erro ao configurar roteamento: {e}")
        return False

def main():
    log("Iniciando configuração de host...")
    
    # Aguardar um pouco para que a rede esteja pronta
    time.sleep(5)
    
    # Obter informações de IP
    my_ip = get_ip_info()
    if not my_ip:
        log("Não foi possível continuar sem um IP válido")
        return
    
    # Encontrar o gateway
    gateway_ip = find_gateway(my_ip)
    if not gateway_ip:
        log("Não foi possível identificar o gateway")
        return
    
    # Configurar roteamento
    if configure_routing(gateway_ip):
        log("Configuração de roteamento concluída com sucesso")
    else:
        log("Falha na configuração de roteamento")
    
    # Loop principal - apenas mantém o host em execução sem testes periódicos
    log("Host configurado e em execução.")
    while True:
        # Apenas mantenha o processo vivo sem gerar logs excessivos
        time.sleep(300)  # Espera 5 minutos

if __name__ == "__main__":
    main()
