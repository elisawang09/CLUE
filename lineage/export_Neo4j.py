import csv
from pathlib import Path
from typing import List

from models.nodes import Node
from models.relationships import Relationship


def export_to_neo4j_csv(nodes: List[Node], rels: List[Relationship], output_dir: str) -> None:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    nodes_file = out_path / "nodes.csv"
    rels_file = out_path / "relationships.csv"

    # Nodes CSV: :ID,:LABEL,name,kind,data_type,expr,…
    with nodes_file.open("w", newline="") as f:
        writer = csv.writer(f)
        header = [":ID", ":LABEL", "name", "kind", "dataset", "data_type", "type", "expr", "sql_snippet"]
        writer.writerow(header)
        for n in nodes:
            p = n.props
            writer.writerow([
                n.id,
                n.label,
                p.get("name", ""),
                p.get("kind", ""),
                p.get("dataset", ""),
                p.get("data_type", ""),
                p.get("type", ""),
                p.get("expr", ""),
                p.get("sql_snippet", ""),
            ])

    # Relationships CSV: :START_ID,:END_ID,:TYPE
    with rels_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([":START_ID", ":END_ID", ":TYPE"])
        for r in rels:
            writer.writerow([r.start_id, r.end_id, r.rel_type])
