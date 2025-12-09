from typing import List, Dict, Tuple
from sqlglot import exp, parse_one

from models.nodes import Node
from models.relationships import Relationship
from models.graph import LineageGraph
from extractors.datamodels import extract_datamodel_and_dependencies
from extractors.columns import extract_columns
from extractors.ops import extract_ops



def build_graph(model_info: Dict, current_graph: LineageGraph) -> Tuple[Dict[str, Node], List[Relationship]]:
    ast = parse_one(model_info["sql"], dialect="postgres")

    # Extract DataModel and dependencies
    current_model_node, all_related_models, model_rels = extract_datamodel_and_dependencies(model_info, current_graph)

    # Extract Columns for this model
    columns, col_rels = extract_columns(ast, current_model_node)

    # Extract Ops + FEEDS/OUTPUTS
    ops, op_rels = extract_ops(ast, current_model_node, columns)

    all_nodes = all_related_models | columns | ops
    rels = model_rels + col_rels + op_rels
    return all_nodes, rels

