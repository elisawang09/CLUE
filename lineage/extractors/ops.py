# lineage/extractors/ops.py
from typing import Dict, List, Tuple, Set, Optional
from sqlglot import exp

from models.nodes import Node
from models.relationships import Relationship


def _extract_column_inputs(expr: exp.Expression) -> List[str]:
    """
    Collect column names referenced in an expression.

    We return names in the form:
      - "table.col" if table is present
      - "col"       if unqualified

    Resolution to actual Column nodes is handled separately.
    """
    inputs: List[str] = []
    for col in expr.find_all(exp.Column):
        if col.table:
            inputs.append(f"{col.table}.{col.name}")
        else:
            inputs.append(col.name)
    # Deduplicate, preserve order
    seen = set()
    result = []
    for name in inputs:
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def _guess_op_kind(expr: exp.Expression) -> str:
    """
    Very rough heuristic to categorize an expression.
    You can refine this as needed.
    """
    if isinstance(expr, exp.AggFunc):
        return "aggregation"
    if isinstance(expr, exp.Case):
        return "conditional"
    if isinstance(expr, exp.Window):
        return "window"
    # fallback
    return "arithmetic"


def _find_source_model_for_column(
    column_name: str,
    current_model: str,
    upstream_map: Dict[str, Set[str]],
    base_schemas: Dict[str, Set[str]],
) -> Optional[str]:
    """
    Resolve the origin model for a bare column reference like 'order_total'
    in the context of 'orders', using:

      - upstream_map: model -> set(upstream_models)
      - base_schemas: model -> set(column_names)

    We return the FIRST upstream base model that has that column.
    """
    from collections import deque

    visited: Set[str] = set()
    queue = deque([current_model])

    while queue:
        model = queue.popleft()
        if model in visited:
            continue
        visited.add(model)

        # If this model has a base schema and contains the column, we’re done
        if model in base_schemas and column_name in base_schemas[model]:
            return model

        # Otherwise, walk upstream
        for up in upstream_map.get(model, set()):
            if up not in visited:
                queue.append(up)

    return None


def extract_ops(
    root: exp.Expression,
    model_node: Node,
    columns: Dict[str, Node],
    *,
    upstream_map: Dict[str, Set[str]],
    base_schemas: Dict[str, Set[str]],
) -> Tuple[Dict[str, Node], List[Relationship]]:
    """
    For each derived column in this model, create an Op node
    and wire FEEDS/OUTPUTS edges.

    Now with cross-model resolution:

      - If an input column is not found as a column in this model,
        we search upstream models using base_schemas + upstream_map
        and create/use Column nodes for those source models.
    """
    model_name = model_node.props["name"]
    ops: Dict[str, Node] = {}
    rels: List[Relationship] = {}

    # Track HAS_OP dedup (one per Op)
    has_op_linked: Set[str] = set()

    # Helper: ensure we have a Column node for (model, column_name)
    def ensure_column_node(
        col_model: str,
        col_name: str,
        kind: str = "base",
    ) -> Node:
        key = f"{col_model}.{col_name}"
        if key in columns:
            return columns[key]

        col = Node.column(
            dataset_name=col_model,  # we treat dataset_name as model name
            column_name=col_name,
            kind=kind,
        )
        col.props["model"] = col_model
        columns[key] = col
        return col

    # Helper: resolve "col" or "table.col" to Column nodes
    def resolve_input_columns(input_name: str) -> List[Node]:
        resolved: List[Node] = []

        # Case 1: fully qualified "table.col"
        if "." in input_name:
            table_name, col_name = input_name.split(".", 1)

            # If the table alias actually matches this model name, treat as local
            if table_name == model_name:
                key = f"{model_name}.{col_name}"
                col_node = columns.get(key)
                if col_node:
                    resolved.append(col_node)
                    return resolved

            # Otherwise, try to treat table_name as a model name in base_schemas
            if table_name in base_schemas and col_name in base_schemas[table_name]:
                col_node = ensure_column_node(
                    col_model=table_name,
                    col_name=col_name,
                    kind="base",
                )
                resolved.append(col_node)
                return resolved

            # Fallback: try upstream resolution starting from current model
            src_model = _find_source_model_for_column(
                column_name=col_name,
                current_model=model_name,
                upstream_map=upstream_map,
                base_schemas=base_schemas,
            )
            if src_model is not None:
                col_node = ensure_column_node(
                    col_model=src_model,
                    col_name=col_name,
                    kind="base",
                )
                resolved.append(col_node)
            return resolved

        # Case 2: bare "col" — first try local model
        key = f"{model_name}.{input_name}"
        local_col = columns.get(key)
        if local_col:
            resolved.append(local_col)
            return resolved

        # Not local; try upstream models via base_schemas
        src_model = _find_source_model_for_column(
            column_name=input_name,
            current_model=model_name,
            upstream_map=upstream_map,
            base_schemas=base_schemas,
        )
        if src_model is not None:
            col_node = ensure_column_node(
                col_model=src_model,
                col_name=input_name,
                kind="base",
            )
            resolved.append(col_node)

        return resolved

    def process_select(select: exp.Select, scope_cte: str | None):
        nonlocal ops, rels

        for proj in select.expressions:
            alias = proj.alias_or_name
            if not alias:
                continue

            output_key = f"{model_name}.{alias}"
            output_col = columns.get(output_key)
            if output_col is None:
                # Column wasn't registered (e.g. from SELECT *), skip
                continue

            expr = proj.this  # underlying expression

            # Skip pure passthroughs: SELECT col AS col
            if isinstance(expr, exp.Column) and expr.name == alias:
                # You’ll instead handle passthrough via DERIVES_FROM at column level.
                continue

            kind = _guess_op_kind(expr)
            op_name = f"{model_name}.{alias}"
            op_node = Node.op(
                name=op_name,
                kind=kind,
                expr=expr.sql(),
            )

            # Scope info
            if scope_cte is not None:
                op_node.props["scope_cte"] = scope_cte

            ops[op_node.id] = op_node

            # HAS_OP (dedup)
            if op_node.id not in has_op_linked:
                has_op_linked.add(op_node.id)
                rels.append(
                    Relationship(
                        start_id=model_node.id,
                        end_id=op_node.id,
                        rel_type="HAS_OP",
                    )
                )

            # FEEDS: resolve each input to local or upstream columns
            input_names = _extract_column_inputs(expr)
            for in_name in input_names:
                input_cols = resolve_input_columns(in_name)
                for in_col in input_cols:
                    rels.append(
                        Relationship(
                            start_id=in_col.id,
                            end_id=op_node.id,
                            rel_type="FEEDS",
                        )
                    )

            # OUTPUTS: op produces this column
            rels.append(
                Relationship(
                    start_id=op_node.id,
                    end_id=output_col.id,
                    rel_type="OUTPUTS",
                )
            )

    # 1) Ops in each CTE
    for cte in list(root.find_all(exp.CTE)):
        cte_name = cte.this.name if cte.this else None
        select = cte.find(exp.Select)
        if not select:
            continue
        process_select(select, scope_cte=cte_name)

    # 2) Ops in final SELECT
    final_select = root if isinstance(root, exp.Select) else root.find(exp.Select)
    if final_select is not None:
        process_select(final_select, scope_cte="__final__")

    return ops, rels
