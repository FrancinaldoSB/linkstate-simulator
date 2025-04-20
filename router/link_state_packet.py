import json

class LinkStatePacket:
    def __init__(self, router_id, neighbors):
        self.router_id = router_id
        self.neighbors = neighbors  # {"R2": 1, "R3": 2}

    def to_json(self):
        return json.dumps({
            "router_id": self.router_id,
            "neighbors": self.neighbors
        })
