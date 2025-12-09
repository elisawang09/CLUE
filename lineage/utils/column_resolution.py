# lineage/base_models/schema_loader.py
import json
from pathlib import Path
from typing import Dict, Set


def load_base_schemas(schema_dir: str) -> Dict[str, Set[str]]:
    """
    Returns:
        base_schemas[dataset_name] = set of column names
        base_schemas = {
        "stg_orders": {"order_total", "customer_id", "ordered_at", ...},
        "stg_payments": {...},
        ...
        }
    """
    base_schemas: Dict[str, Set[str]] = {}
    for path in Path(schema_dir).glob("*.json"):
        with path.open() as f:
            data = json.load(f)
        ds_name = data["dataset"]
        cols = set(data["columns"])
        base_schemas[ds_name] = cols
    return base_schemas



# lineage/utils/column_resolution.py (new version)
from collections import deque
from typing import Dict, Set, Optional

from lineage.models.nodes import Node


def find_source_dataset_for_column(
    column_name: str,
    current_dataset: str,
    datasets: Dict[str, Node],
    upstream_map: Dict[str, Set[str]],
    base_schemas: Dict[str, Set[str]],
) -> Optional[str]:
    """
    Resolve the origin dataset for a column reference like 'order_total'
    in the context of 'final_output', using:

      - dataset graph (upstream_map)
      - preloaded base_schemas: dataset -> set(column_name)

    We return the FIRST upstream base dataset that has that column,
    preferring tables / models over intermediate CTEs.
    """
    visited: Set[str] = set()
    queue = deque([current_dataset])

    while queue:
        ds_name = queue.popleft()
        if ds_name in visited:
            continue
        visited.add(ds_name)

        # If ds_name is in base_schemas and has this column, we’re done
        if ds_name in base_schemas and column_name in base_schemas[ds_name]:
            return ds_name

        # Otherwise, keep walking upstream
        for up_ds in upstream_map.get(ds_name, []):
            if up_ds not in visited:
                queue.append(up_ds)

    return None
