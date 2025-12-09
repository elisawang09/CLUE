from typing import Tuple, Dict, List, Set
from sqlglot import exp
from models.graph import LineageGraph
from models.nodes import Node
from models.relationships import Relationship


def _create_datamodel_node(model_info:dict) -> Node:
    return Node.datamodel(name=model_info["alias"], type=model_info["type"], description=model_info["description"])

def extract_datamodel_and_dependencies(model_info: dict, current_graph: LineageGraph ) -> Tuple[Node, Dict[str, Node], List[Relationship]]:
    """
    Create a DataModel node for each SQL model and discover other models/tables
    it depends on.

    Returns:
        model_node: DataModel for this SQL file
        external_models: name -> DataModel (stubs for dependencies)
        rels: DEPENDS_ON relationships
    """
    model_nodes: Dict[str, Node] = {}
    rels: List[Relationship] = []

    # Create node for current model
    node_id = model_info["alias"]
    if node_id not in current_graph.nodes:
        current_model_node = _create_datamodel_node(model_info)
        model_nodes[node_id] = current_model_node
    else:
        current_model_node = current_graph.nodes[node_id]

    # Create nodes & relationships for dependencies
    for dep_name in model_info["depends_on"]:
        parent_node = None

        # The name in depends_on is like "source(model).dbt_project_name.model_name", which is different from the node_id we use.
        # Get the node_id from the raw (parsed) manifest info.
        dep_info = current_graph.raw_sources_info[dep_name] if "source" in dep_name else current_graph.raw_models_info[dep_name]
        dep_node_id = dep_info["alias"] # the node_id used in our graph

        if dep_node_id not in current_graph.nodes:
            parent_node = _create_datamodel_node(dep_info)
            model_nodes[dep_node_id] = parent_node
        else:
            parent_node = current_graph.nodes[dep_node_id]

        # Create DEPENDS_ON edge from current model → parent model
        rels.append(
            Relationship(
                start_id=current_model_node.id,
                end_id=parent_node.id,
                rel_type="DEPENDS_ON",
            )
        )
    # Save to current graph here for testing purpose
    current_graph.save_nodes(model_nodes)
    current_graph.save_rels(rels)

    return current_model_node, model_nodes, rels



