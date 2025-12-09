from pathlib import Path


def load_dbt_manifest(path: Path) -> dict:
    sources, models = {}, {}

    import json

    with path.open("r") as f:
        manifest = json.load(f)
    manifest_nodes = manifest["nodes"]
    manifest_sources = manifest["sources"]

    for model_name, node in manifest_nodes.items():
        if node["resource_type"] == "model":
            model_type = "stg" if "stg" in model_name else "mart"
            name_alias = node["name"] if "stg" in model_name else f'mart_{node["name"]}'
            model_name_key = f"model.{name_alias}"
            models[model_name] = {
                "alias": model_name_key,
                "type": model_type,
                "sql": node["compiled_code"],
                "depends_on": node["depends_on"]["nodes"],
                "description":""
            }

    for source_name, source in manifest_sources.items():
        name_alias = f"source.{source['name']}"
        sources[source_name] = {
            "alias": name_alias,
            "type": "prod_table",
            "description": source.get("description", ""),
            "sql": "",
        }

    return models, sources