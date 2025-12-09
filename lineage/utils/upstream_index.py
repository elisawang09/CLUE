# lineage/utils/upstream_index.py
from collections import defaultdict
from typing import Dict, Set, List

from models.nodes import Node
from models.relationships import Relationship


def _dataset_name_from_id(node_id: str) -> str:
    # assuming ids look like "dataset:<name>"
    kind, name = node_id.split(":", 1)
    assert kind == "dataset"
    return name


def _transformation_name_from_id(node_id: str) -> str:
    # "transformation:<name>"
    kind, name = node_id.split(":", 1)
    assert kind == "transformation"
    return name


def build_upstream_dataset_map(
    datasets: Dict[str, Node],
    relationships: List[Relationship],
) -> Dict[str, Set[str]]:
    """
    Build a mapping:
        upstream_map[dataset_name] -> set of upstream CTEs

        For example,

        upstream_map["orders"]                 == {"stg_orders"}
        upstream_map["compute_booleans"]       == {"orders", "order_items_summary"}
        upstream_map["customer_order_count"]   == {"compute_booleans"}
        upstream_map["final_output"]           == {"customer_order_count"}


    where upstreams come from:
      - ALIAS_OF:    cte_ds -> base_ds
      - READS_FROM + WRITES_TO:
          for each Transformation, all datasets written-to have as upstream
          all datasets read-from.
    """
    # For each transformation, record its input & output datasets
    tr_inputs: Dict[str, Set[str]] = defaultdict(set)
    tr_outputs: Dict[str, Set[str]] = defaultdict(set)

    alias_edges: List[tuple[str, str]] = []

    for rel in relationships:
        if rel.rel_type == "ALIAS_OF":
            # start_id: cte dataset, end_id: base dataset
            src = _dataset_name_from_id(rel.start_id)
            dst = _dataset_name_from_id(rel.end_id)
            alias_edges.append((src, dst))

        elif rel.rel_type == "READS_FROM":
            # start: dataset, end: transformation
            ds_name = _dataset_name_from_id(rel.start_id)
            tr_name = _transformation_name_from_id(rel.end_id)
            tr_inputs[tr_name].add(ds_name)

        elif rel.rel_type == "WRITES_TO":
            # start: transformation, end: dataset
            tr_name = _transformation_name_from_id(rel.start_id)
            ds_name = _dataset_name_from_id(rel.end_id)
            tr_outputs[tr_name].add(ds_name)

    upstream_map: Dict[str, Set[str]] = defaultdict(set)

    # Alias edges
    for src, dst in alias_edges:
        upstream_map[src].add(dst)

    # For each transformation, connect outputs to inputs
    for tr_name, input_datasets in tr_inputs.items():
        for out_ds in tr_outputs.get(tr_name, []):
            upstream_map[out_ds].update(input_datasets)

    return upstream_map
