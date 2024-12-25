# basicsystem.py
from qns.entity.node.app import Application
from qns.entity.qchannel.qchannel import QuantumChannel
from qns.entity.node.node import QNode
from typing import Dict, List, Optional, Tuple
from qns.network.topology import Topology
from qns.entity.memory.memory import QuantumMemory
import math
import networkx as nx
import matplotlib.pyplot as plt


class GridTopology(Topology):

    def __init__(self, nodes_number, nodes_apps: List[Application] = [],
                 qchannel_args: Dict = {}, cchannel_args: Dict = {},
                 memory_args: Optional[List[Dict]] = {}):
        super().__init__(nodes_number, nodes_apps, qchannel_args, cchannel_args, memory_args)
        size = int(math.sqrt(self.nodes_number))
        self.size = size
        assert (size ** 2 == self.nodes_number)
        self.nl = []
        self.ll = []

    def build(self) -> Tuple[List[QNode], List[QuantumChannel]]:
        # Create the lists of QNodes and QuantumChannels
        self.nl: List[QNode] = []
        self.ll = []

        for i in range(self.nodes_number):
            n = QNode(f"V{i+1}")
            self.nl.append(n)

        if self.nodes_number > 1:
            for i in range(self.nodes_number):
                if (i + 1) % self.size != 0:
                    link = QuantumChannel(name=f"E{i+1},{i+2}", **self.qchannel_args)
                    self.ll.append(link)
                    self.nl[i].add_qchannel(link)
                    self.nl[i + 1].add_qchannel(link)
                if i + self.size < self.nodes_number:
                    link = QuantumChannel(name=f"E{i+1},{i+1+self.size}", **self.qchannel_args)
                    self.ll.append(link)
                    self.nl[i].add_qchannel(link)
                    self.nl[i + self.size].add_qchannel(link)

        self._add_apps(self.nl)
        self._add_memories(self.nl)
        return self.nl, self.ll

    def _add_memories(self, nl: List[QNode]):
        # Add memories to the nodes based on their position (corner, edge, or center)
        size = self.size
        for node in nl:
            index = int(node.name[1:]) - 1
            row, col = divmod(index, size)
            # Check if the node is in the corner
            if (row == 0 or row == size - 1) and (col == 0 or col == size - 1):
                memory_count = 4
            # Check if the node is on the edge (but not in the corner)
            elif row == 0 or row == size - 1 or col == 0 or col == size - 1:
                memory_count = 6
            # The node is in the center
            else:
                memory_count = 8  # Assuming center nodes get more memories

            for i in range(memory_count):
                memory = QuantumMemory(name=f"Q{i + 1}-{node.name}", **self.memory_args)
                node.add_memory(memory)

    def draw_graph(self):
        # Draw the graph of the topology
        # Call the build method and store its return value
        nl, ll = self.build()

        # Create a new networkx graph
        G = nx.Graph()

        # Add nodes to the graph
        for node in nl:
            G.add_node(node.name)

        # Add edges to the graph and store the edge names
        edge_labels = {}
        for link in ll:
            # Find the nodes connected by the link
            for node in nl:
                if link in node.qchannels:
                    for other_node in nl:
                        if other_node != node and link in other_node.qchannels:
                            G.add_edge(node.name, other_node.name)
                            edge_labels[(node.name, other_node.name)] = link.name
                            break
                    break

        # Draw the graph
        pos = nx.spring_layout(G, seed=28)
        nx.draw(G, pos, with_labels=True, node_size=600, node_color="Aqua", font_size=10, font_weight="bold",
                font_color="Gray", edge_color="RoyalBlue", width=2)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
        plt.show()
        plt.close()

    def print_memory_counts(self):
        # Print the memory counts of each node and the total number of memories
        nodes, _ = self.build()
        total_memories = 0
        for node in nodes:
            print(f"Node {node.name} has {len(node.memories)} qubits.")
            total_memories += len(node.memories)
            for memory in node.memories:
                print(f"- {memory.name}")
            print()
        print(f"Total number of memories in the system: {total_memories}")
        print('\n')

    def draw_memory_histogram(self):
        # Draw a histogram of the number of memories per node
        # Build the topology
        if self.nodes_number <= 16:
            nodes, _ = self.build()

            # Prepare data for the histogram
            node_names = [node.name for node in nodes]
            memory_counts = [len(node.memories) for node in nodes]

            # Create the histogram
            plt.bar(node_names, memory_counts)
            plt.xlabel('Nodes')
            plt.ylabel('Number of Qubits')
            plt.title('Number of Qubits for Each Node')
            plt.show()
