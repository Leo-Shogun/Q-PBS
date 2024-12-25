# requests.py
import random
from typing import Dict, List, Tuple
from basicsystem import GridTopology
import networkx as nx
import heapq

class Requests:
    def __init__(self, topology: GridTopology):
        self.topology = topology
        self.topology.build()
        self.size = topology.size

    def generate_random_requests(self, num_requests: int) -> List[Tuple[str, str]]:
        nodes = self.topology.nl
        requests = []
        for _ in range(num_requests):
            node1, node2 = random.sample(nodes, 2)
            requests.append((node1.name, node2.name))
        return requests

    def yen_k_shortest_paths(self, graph: nx.Graph, source: str, target: str, K: int) -> List[List[str]]:
        def dijkstra(graph: nx.Graph, source: str) -> Dict[str, Tuple[float, List[str]]]:
            dist = {node: (float('inf'), []) for node in graph.nodes()}
            dist[source] = (0, [source])
            pq = [(0, source)]
            while pq:
                (d, u) = heapq.heappop(pq)
                if d > dist[u][0]:
                    continue
                for v in graph.neighbors(u):
                    weight = graph[u][v].get('weight', 1)
                    if dist[u][0] + weight < dist[v][0]:
                        dist[v] = (dist[u][0] + weight, dist[u][1] + [v])
                        heapq.heappush(pq, (dist[v][0], v))
            return dist

        def remove_edge(graph: nx.Graph, u: str, v: str):
            if graph.has_edge(u, v):
                graph.remove_edge(u, v)

        def restore_edge(graph: nx.Graph, u: str, v: str, weight: float):
            graph.add_edge(u, v, weight=weight)

        def path_weight(graph: nx.Graph, path: List[str]) -> float:
            return sum(graph[u][v].get('weight', 1) for u, v in zip(path[:-1], path[1:]))

        dist = dijkstra(graph, source)
        if target not in dist or dist[target][0] == float('inf'):
            return []

        A = [dist[target][1]]
        B = []

        for k in range(1, K):
            for i in range(len(A[-1]) - 1):
                spur_node = A[-1][i]
                root_path = A[-1][:i + 1]

                removed_edges = []
                for path in A:
                    if len(path) > i + 1 and path[:i + 1] == root_path:
                        u = path[i]
                        v = path[i + 1]
                        remove_edge(graph, u, v)
                        removed_edges.append((u, v, 1))

                spur_path_dist = dijkstra(graph, spur_node)
                if target in spur_path_dist and spur_path_dist[target][0] < float('inf'):
                    total_path = root_path[:-1] + spur_path_dist[target][1]
                    if total_path not in B:
                        B.append(total_path)

                for u, v, weight in removed_edges:
                    restore_edge(graph, u, v, weight)

            if not B:
                break

            B.sort(key=lambda x: path_weight(graph, x))
            A.append(B.pop(0))

        return A

    def find_all_shortest_paths(self, requests: List[Tuple[str, str]]) -> Dict[Tuple[str, str], List[List[str]]]:
        nodes = self.topology.nl
        links = self.topology.ll
        G = nx.Graph()

        for node in nodes:
            G.add_node(node.name)

        for link in links:
            for node in nodes:
                if link in node.qchannels:
                    for other_node in nodes:
                        if other_node != node and link in other_node.qchannels:
                            G.add_edge(node.name, other_node.name, weight=1)
                            break

        all_shortest_paths = {}
        K = 10  # Increase K to find more paths
        for (src, dst) in requests:
            k_shortest_paths = self.yen_k_shortest_paths(G, src, dst, K)
            all_shortest_paths[(src, dst)] = k_shortest_paths
        return all_shortest_paths

    def identify_high_weight_paths(self, requests: List[Tuple[str, str, str]], paths: Dict[Tuple[str, str], List[List[str]]]) -> Dict[str, Tuple[List[str], List[str]]]:
        high_weight_paths = {}
        for request_id, src, dst in requests:
            if (src, dst) in paths and paths[(src, dst)]:
                path_list = paths[(src, dst)]
                if len(path_list) == 1:
                    high_weight_paths[request_id] = (path_list[0], [])
                else:
                    high_weight_paths[request_id] = (path_list[0], path_list[-1])
            else:
                high_weight_paths[request_id] = ([], [])
        return high_weight_paths

    def display_high_weight_paths(self, high_weight_paths: Dict[str, Tuple[List[str], List[str]]]):
        print("High weight paths for each request:")
        for request_id, (first_path, last_path) in high_weight_paths.items():
            print(f"{request_id}:")
            if last_path:
                print(f"  First Path: {' -> '.join(first_path) if first_path else 'No path found'}")
                print(f"  Redundant Path: {' -> '.join(last_path) if last_path else 'No path found'}")
            else:
                print(f"  Path: {' -> '.join(first_path) if first_path else 'No path found'}")
            print()

    def generate_requests_by_rounds(self, num_requests: int, num_rounds: int) -> List[Dict[str, List[Tuple[str, str, str]]]]:
        all_requests = []
        for round_number in range(1, num_rounds + 1):
            requests = self.generate_random_requests(num_requests)
            requests_with_ids = [(f"Round {round_number} Request {i+1}", src, dst) for i, (src, dst) in enumerate(requests)]
            all_requests.append({
                "round_number": round_number,
                "requests": requests_with_ids
            })
        return all_requests

    def calculate_manhattan_distance(self, node1, node2):
        index1 = int(node1.name[1:]) - 1
        index2 = int(node2.name[1:]) - 1
        row1, col1 = divmod(index1, self.size)
        row2, col2 = divmod(index2, self.size)
        return abs(row1 - row2) + abs(col1 - col2)
