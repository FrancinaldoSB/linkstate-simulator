import threading
import socket
import json
import time  # Faltava importar
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dijkstra import calculate_routes
from link_state_packet import LinkStatePacket
from utils.logger import log

# ========================
# Configurações Fixas (por enquanto)
# ========================
ROUTER_ID = "R1"
NEIGHBORS = {"R2": 1, "R3": 3} # Nome do roteador vizinho e custo do enlace

ROUTER_IPS = {
    "R1": "127.0.0.1",
    "R2": "127.0.0.1",
    "R3": "127.0.0.1"
}

# ========================
# Tabelas do roteador
# ========================
LSDB = {}            # Link State Database
ROUTING_TABLE = {}   # Tabela de roteamento

# ========================
# Funções de rede
# ========================

def get_ip_for_router(router_id):
    return ROUTER_IPS.get(router_id, "127.0.0.1")

def receive_packets():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 5002))
    log(f"{ROUTER_ID} aguardando pacotes...")
    while True:
        data, _ = sock.recvfrom(4096)
        packet = json.loads(data.decode())
        LSDB[packet["router_id"]] = packet
        update_routing_table()

def send_packets():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        packet = LinkStatePacket(ROUTER_ID, NEIGHBORS).to_json()
        for neighbor in NEIGHBORS:
            ip = get_ip_for_router(neighbor)
            sock.sendto(packet.encode(), (ip, 5000))
        log(f"{ROUTER_ID} enviou pacote para vizinhos: {list(NEIGHBORS.keys())}")
        time.sleep(5)

def update_routing_table():
    global ROUTING_TABLE
    ROUTING_TABLE = calculate_routes(ROUTER_ID, LSDB)
    log(f"{ROUTER_ID} atualizou tabela de rotas: {ROUTING_TABLE}")

# ========================
# Execução principal
# ========================
if __name__ == "__main__":
    threading.Thread(target=receive_packets).start()
    threading.Thread(target=send_packets).start()
