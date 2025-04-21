import threading
import socket
import json
import time
import sys
import os
import argparse

# Adicionando o diretório raiz do projeto ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'utils')))

from dijkstra import calculate_routes
from link_state_packet import LinkStatePacket
from utils.logger import log

# ========================
# Argumentos de entrada
# ========================

parser = argparse.ArgumentParser(description="Roteador com algoritmo de estado de enlace")
parser.add_argument('--id', required=True, help='ID do roteador (ex: R1)')
parser.add_argument('--port', type=int, required=True, help='Porta local para escutar pacotes')
parser.add_argument('--neighbors', required=True, help='Lista de vizinhos no formato R2=1,R3=3')

args = parser.parse_args()

ROUTER_ID = args.id
PORT = args.port

# Ex: R2=1,R3=3 → {'R2': 1, 'R3': 3}
NEIGHBORS = dict((n.split('=')[0], int(n.split('=')[1])) for n in args.neighbors.split(','))

# ========================
# Configurações fixas
# ========================

ROUTER_IPS = {
    "R1": "router1",
    "R2": "router2",
    "R3": "router3"
}

PORTS = {
    "R1": 5001,
    "R2": 5002,
    "R3": 5003
}

LSDB = {
    ROUTER_ID: {
        "router_id": ROUTER_ID,
        "neighbors": NEIGHBORS
    }
}

ROUTING_TABLE = {}

# ========================
# Funções de rede
# ========================

def get_ip_for_router(router_id):
    return ROUTER_IPS.get(router_id, "127.0.0.1")

def receive_packets():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', PORT))
    log(f"{ROUTER_ID} aguardando pacotes na porta {PORT}...")
    while True:
        data, _ = sock.recvfrom(4096)
        packet = json.loads(data.decode())
        LSDB[packet["router_id"]] = packet
        update_routing_table()

def send_packets():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    intervalo_envio = 5
    proximo_envio = time.time()

    while True:
        agora = time.time()
        if agora >= proximo_envio:
            packet = LinkStatePacket(ROUTER_ID, NEIGHBORS).to_json()
            for neighbor in NEIGHBORS:
                try:
                    ip = get_ip_for_router(neighbor)
                    sock.sendto(packet.encode(), (ip, PORTS[neighbor]))
                except socket.gaierror as e:
                    log(f"{ROUTER_ID} falhou ao resolver {neighbor}: {e}")
                except Exception as e:
                    log(f"{ROUTER_ID} erro ao enviar para {neighbor}: {e}")
            log(f"{ROUTER_ID} enviou pacote para vizinhos: {list(NEIGHBORS.keys())}")
            proximo_envio = agora + intervalo_envio

def update_routing_table():
    global ROUTING_TABLE
    if not all(neighbor in LSDB for neighbor in NEIGHBORS):
        log(f"{ROUTER_ID} aguardando vizinhos na LSDB...")
        return
    ROUTING_TABLE = calculate_routes(ROUTER_ID, LSDB)
    log(f"{ROUTER_ID} atualizou tabela de rotas: {ROUTING_TABLE}")

# ========================
# Execução
# ========================
if __name__ == "__main__":
    threading.Thread(target=receive_packets).start()
    threading.Thread(target=send_packets).start()
