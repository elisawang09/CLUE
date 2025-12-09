from dataclasses import dataclass
from typing import Dict

"""
    Represents a relationship between two nodes in the lineage graph.
    Relationships:
        (:DataModel)-[:HAS_COLUMN]->(:Column)
        (:DataModel)-[:HAS_OP]->(:Op)
        (:DataModel)-[:DEPENDS_ON_MODEL]->(:DataModel)

        (:Column)-[:DERIVES_FROM ({mode: "passthrough"})]->(:Column)    # Add mode: "passthrough" to mark a simple passthrough / alias / SELECT * chain
        (:Column)-[:FEEDS]->(:Op)
        (:Op)-[:OUTPUTS]->(:Column)
"""
@dataclass
class Relationship:
    start_id: str
    end_id: str
    rel_type: str
    props: Dict[str, str] | None = None
