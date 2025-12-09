from typing import Dict, List, Tuple
from sqlglot import exp

from models.nodes import Node
from models.relationships import Relationship


def extract_columns(
    root: exp.Expression,
    model_node: Node,
) -> Tuple[Dict[str, Node], List[Relationship]]:
    """
    Extract Column nodes for this model based on:
      - each CTE's SELECT list
      - the final SELECT list

    Also extracts DERIVES_FROM relationships for pure column renames.

    We do NOT create columns for external models here.
    """
    columns: Dict[str, Node] = {}
    rels: List[Relationship] = []

    # Track which columns we've already linked via HAS_COLUMN
    has_column_linked: set[str] = set()

    def get_column_type(proj: exp.Expression) -> str:
        type_expr = proj.args.get("expression")

        return "derived" if type_expr else "base"

    def add_column(model_name:str, col_name: str, type: str) -> None:

        key = f"{model_name}.{col_name}"

        if key not in has_column_linked:
            col_node = Node.column(
                model_name=model_name,
                column_name=col_name,
                type=type,
            )

            rels.append(
                Relationship(
                    start_id=model_node.id,
                    end_id=col_node.id,
                    rel_type="HAS_COLUMN",
                )
            )

            has_column_linked.add(key)


    # 1) CTE columns and pure renames
    for cte in list(root.find_all(exp.CTE)):
        select = cte.this
        if not isinstance(select, exp.Select):
            continue

        # Get CTE name
        cte_name = cte.alias.this.this if cte.alias and cte.alias.this else None

        for proj in select.expressions:
            alias = proj.alias_or_name
            if not alias or alias == "*":
                continue
            col_type = get_column_type(proj)
            add_column(model_node.id, alias, col_type)

    # 2) Final SELECT columns
    final_select = root if isinstance(root, exp.Select) else root.find(exp.Select)
    if final_select is not None:
        for proj in final_select.expressions:
            alias = proj.alias_or_name
            if not alias or alias == "*":
                continue
            col_type = get_column_type(proj)
            add_column(model_node.id, alias, col_type)

    return columns, rels
