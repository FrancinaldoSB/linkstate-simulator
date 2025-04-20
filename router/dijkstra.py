import heapq

def calculate_routes(start_router, lsdb):
    # Constrói o grafo com base na LSDB
    graph = {}
    for router_id, packet in lsdb.items():
        graph[router_id] = packet["neighbors"]

    # Inicializa distâncias
    distances = {router: float('inf') for router in graph}
    distances[start_router] = 0

    previous = {}
    queue = [(0, start_router)]

    while queue:
        current_distance, current_router = heapq.heappop(queue)

        if current_distance > distances[current_router]:
            continue

        for neighbor, cost in graph[current_router].items():
            distance = current_distance + cost
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous[neighbor] = current_router
                heapq.heappush(queue, (distance, neighbor))

    # Monta a tabela de roteamento: {destino: próximo salto}
    routing_table = {}
    for destination in graph:
        if destination == start_router:
            continue
        next_hop = destination
        while previous.get(next_hop) != start_router:
            next_hop = previous.get(next_hop)
            if next_hop is None:
                break
        if next_hop:
            routing_table[destination] = next_hop

    return routing_table
