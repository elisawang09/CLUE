from typing import Dict, List, Tuple
from models.nodes import Node
from models.relationships import Relationship
from export_Neo4j import export_to_neo4j_csv


# We need a Class for storing all nodes and relationships for accessing across model files.
# This class can be passed into build_graph function to update the nodes and relationships.

class LineageGraph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}    # node_id -> Node, use dict for easy lookup
        self.rels: List[Relationship] = []

    def save_parsed_manifest_info(self, source_tables: Dict[str, dict], models: Dict[str, dict]):
        self.raw_sources_info = source_tables
        self.raw_models_info = models

    def save_nodes(self, nodes: Dict[str, Node]):
        self.nodes.update(nodes)

    def save_rels(self, rels: List[Relationship]):
        self.rels.extend(rels)

    def export_to_csv(self, output_dir: str):
        export_to_neo4j_csv(list(self.nodes.values()), self.rels, output_dir)
