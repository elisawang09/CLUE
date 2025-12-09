from dataclasses import dataclass, field
from typing import Dict, List, Literal
import uuid

NodeKind = Literal["DataModel", "Column", "Op"]


@dataclass
class Node:
    id: str
    label: NodeKind
    props: Dict[str, str] = field(default_factory=dict)

    @staticmethod
    def datamodel(name: str, type: str, description: str) -> "Node":
        return Node(
            id=name,
            label="Model",
            props={"name": name,
                   "type": type,    # "staging" | "mart" | "prod_table"
                   "description": description},
        )

    @staticmethod
    def column(model_name: str, column_name: str, type: str = "base") -> "Node":
        return Node(
            id=f"column:{model_name}.{column_name}",
            label="Column",
            props={
                "name": column_name,
                "datamodel": model_name,
                "type": type,  # "base" | "derived"
            },
        )

    # @staticmethod
    # def transformation(name: str, ttype: str, sql_snippet: str = "") -> "Node":
    #     """
    #         Create a Transformation node to represent a *dataset-level* operation
    #     """
    #     return Node(
    #         id=f"transformation:{name}",
    #         label="Transformation",
    #         props={"name": name, "type": ttype, "sql_snippet": sql_snippet},
    #     )

    @staticmethod
    def op(name: str, type: str, expr: str, has_filter: None, filter_exprs: None, group_by_keys: None) -> "Node":
        """
            Create an Op (Operation) node to represent the logic that produces *one derived column*"""
        return Node(
            id=f"op:{name}_expr",
            label="Op",
            props={"name": name,
                    "type": type,   # category of operation,  e.g. "arithmetic", "aggregation", "conditional_flag"
                    "expr": expr,
                    "has_filter": has_filter,   # boolean, wherher the op has filter conditions (where / having)
                    "filter_exprs":  filter_exprs,  # list of filter expressions
                    "group_by_keys": group_by_keys,}    # list of group by keys

        )
