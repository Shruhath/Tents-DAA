"""
game_grapher.py - State-Space Search Tree Visualizer

Renders the BackBot's backtracking search tree as a hierarchical
graph image using networkx and matplotlib. The solution path is
highlighted in green; pruned/backtracked branches are shown in red.
"""

import os
from datetime import datetime
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class StateGrapher:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_counter = 0
        self.labels = {}
        self.parents = {}      # child_id -> parent_id
        self.pruned = set()
        self.victory = set()

    def add_node(self, label):
        """Add a node with a descriptive label. Returns the node ID."""
        node_id = self.node_counter
        self.node_counter += 1
        self.graph.add_node(node_id)
        self.labels[node_id] = label
        return node_id

    def add_edge(self, parent_id, child_id):
        """Connect parent to child and record parentage."""
        self.graph.add_edge(parent_id, child_id)
        self.parents[child_id] = parent_id

    def set_pruned(self, node_id):
        """Mark a node (and its entire subtree) as pruned/backtracked."""
        self.pruned.add(node_id)
        for child in nx.descendants(self.graph, node_id):
            self.pruned.add(child)

    def set_victory_route(self, leaf_id):
        """Trace from leaf back to root, marking the solution path green."""
        node = leaf_id
        while node is not None:
            self.victory.add(node)
            node = self.parents.get(node)

    def _hierarchy_layout(self, root=0):
        """Compute a top-down hierarchical position layout via BFS."""
        if not self.graph.nodes:
            return {}

        levels = {}
        queue = [root]
        levels[root] = 0
        while queue:
            node = queue.pop(0)
            for child in self.graph.successors(node):
                if child not in levels:
                    levels[child] = levels[node] + 1
                    queue.append(child)

        by_level = {}
        for node, level in levels.items():
            by_level.setdefault(level, []).append(node)

        pos = {}
        for level, nodes in by_level.items():
            n = len(nodes)
            for i, node in enumerate(nodes):
                x = (i - (n - 1) / 2) * 2.0
                y = -level * 2.0
                pos[node] = (x, y)

        return pos

    def render_graph(self, board_size):
        """Render the search tree to a PNG file in the graphs/ directory."""
        if not self.graph.nodes:
            return

        os.makedirs("graphs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"graphs/search_tree_{timestamp}.png"

        # Try pydot hierarchical layout, fall back to BFS layout
        try:
            from networkx.drawing.nx_pydot import graphviz_layout
            pos = graphviz_layout(self.graph, prog="dot")
        except Exception:
            pos = self._hierarchy_layout()

        # Classify node colors
        node_colors = []
        for node in self.graph.nodes:
            if node in self.victory:
                node_colors.append("#2ecc71")   # green
            elif node in self.pruned:
                node_colors.append("#e74c3c")   # red
            else:
                node_colors.append("#95a5a6")   # gray

        # Classify edge colors and widths
        edge_colors = []
        edge_widths = []
        for u, v in self.graph.edges:
            if u in self.victory and v in self.victory:
                edge_colors.append("#27ae60")
                edge_widths.append(3.0)
            elif v in self.pruned:
                edge_colors.append("#c0392b")
                edge_widths.append(1.0)
            else:
                edge_colors.append("#bdc3c7")
                edge_widths.append(1.0)

        # Scale figure to graph complexity
        num_nodes = len(self.graph.nodes)
        fig_w = max(12, num_nodes * 0.6)
        fig_h = max(8, num_nodes * 0.4)
        fig, ax = plt.subplots(figsize=(fig_w, fig_h))

        nx.draw(
            self.graph, pos, ax=ax,
            labels=self.labels,
            node_color=node_colors,
            edge_color=edge_colors,
            width=edge_widths,
            node_size=800,
            font_size=6,
            font_weight="bold",
            arrows=True,
            arrowsize=15,
        )

        ax.set_title(
            f"BackBot Search Tree  |  {board_size}x{board_size}  |  "
            f"{num_nodes} nodes explored",
            fontsize=14, fontweight="bold",
        )

        # Empirical complexity metrics
        time_complexity = len(self.graph.nodes)
        space_complexity = nx.dag_longest_path_length(self.graph)
        metrics_text = (
            f"EMPIRICAL ANALYSIS\n"
            f"----------------------\n"
            f"Time Complexity: O({time_complexity}) operations\n"
            f"Space Complexity: O({space_complexity}) max depth"
        )
        props = dict(boxstyle='round', facecolor='#2c3e50',
                     alpha=0.9, edgecolor='#34495e')
        ax.text(0.98, 0.02, metrics_text, transform=ax.transAxes,
                fontsize=12, verticalalignment='bottom',
                horizontalalignment='right', bbox=props,
                color='white', fontweight='bold',
                fontfamily='monospace', zorder=5)

        plt.tight_layout()
        plt.savefig(filepath, dpi=150)
        plt.close(fig)
