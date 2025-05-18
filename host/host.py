import os
import time
import socket
import subprocess
import ipaddress

def log(msg):
    print(msg, flush=True)

def get_ip_info():
    try:
        ip_info = subprocess.run(["ip", "addr"], capture_output=True, text=True)
        log(f"Interfaces de rede: {ip_info.stdout}")
        
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
    try:
        ip_parts = my_ip.split('.')
        router_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.3"
        
        log(f"Identificado gateway: {router_ip}")
        return router_ip
    except Exception as e:
        log(f"Erro ao identificar gateway: {e}")
        return None

def configure_routing(gateway_ip):
    try:
        route_cmd = subprocess.run(["ip", "route"], capture_output=True, text=True)
        log(f"Tabela de roteamento atual: {route_cmd.stdout}")
        
        try:
            subprocess.run(["ip", "route", "del", "default"], check=False)
            log("Rota padrão existente removida")
        except:
            pass
        
        result = subprocess.run(["ip", "route", "add", "default", "via", gateway_ip], 
                               capture_output=True, text=True, check=False)
        if result.returncode != 0:
            log(f"Erro ao adicionar rota padrão: {result.stderr}")
        else:
            log(f"Adicionada rota padrão via {gateway_ip}")
        
        for subnet in range(1, 6): 
            subnet_cidr = f"172.20.{subnet}.0/24"
            
            my_subnet = gateway_ip.split('.')[2]
            if str(subnet) == my_subnet:
                continue
                
            route_cmd = ["ip", "route", "replace", subnet_cidr, "via", gateway_ip]
            result = subprocess.run(route_cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                log(f"Adicionada rota para {subnet_cidr} via {gateway_ip}")
            else:
                log(f"Erro ao adicionar rota para {subnet_cidr}: {result.stderr}")
        
        updated_route = subprocess.run(["ip", "route"], capture_output=True, text=True)
        log(f"Tabela de roteamento atualizada: {updated_route.stdout}")
        
        return True
    except Exception as e:
        log(f"Erro ao configurar roteamento: {e}")
        return False

def main():
    log("Iniciando configuração de host...")
    
    time.sleep(5)
    
    my_ip = get_ip_info()
    if not my_ip:
        log("Não foi possível continuar sem um IP válido")
        return

    gateway_ip = find_gateway(my_ip)
    if not gateway_ip:
        log("Não foi possível identificar o gateway")
        return
    
    if configure_routing(gateway_ip):
        log("Configuração de roteamento concluída com sucesso")
    else:
        log("Falha na configuração de roteamento")

    log("Host configurado e em execução.")
    while True:

        time.sleep(300)

if __name__ == "__main__":
    main()
