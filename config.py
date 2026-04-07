import json
import os

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".swpsfsb")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

_defaults = {
    "db_path": "",
    "base_output_dir": "",
}


def load() -> dict:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        return dict(_defaults)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**_defaults, **data}
    except (json.JSONDecodeError, OSError):
        return dict(_defaults)


def save(cfg: dict) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
