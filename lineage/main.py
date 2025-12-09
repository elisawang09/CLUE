from sqlglot import parse_one, exp
from pathlib import Path
from models.graph import LineageGraph
from manifest_loader import load_dbt_manifest
from graph_builder import *

DBT_MANIFEST_PATH = Path("../dbt/target/manifest.json")
OUTPUT_DIR = Path("neo4j_export")



def main():
    current_graph = LineageGraph()

    all_models, sources = load_dbt_manifest(DBT_MANIFEST_PATH)
    current_graph.save_parsed_manifest_info(sources, all_models)

    # Build graph for each model
    for model_name, model_info in all_models.items():
        print(model_name)
        nodes, rels = build_graph(model_info, current_graph)

        # Update global nodes and relationships
        current_graph.save_nodes(nodes)
        current_graph.save_rels(rels)


    current_graph.export_to_csv(output_dir=str(OUTPUT_DIR))


if __name__ == "__main__":
    main()
