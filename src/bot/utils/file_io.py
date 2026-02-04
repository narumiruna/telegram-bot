import json
from pathlib import Path
from typing import Any


def save_text(text: str, f: str | Path) -> None:
    path = Path(f)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w") as fp:
        fp.write(text)


def load_json(f: str | Path) -> Any:
    path = Path(f)
    if path.suffix != ".json":
        raise ValueError(f"File {f} is not a json file")

    with path.open(encoding="utf-8") as fp:
        return json.load(fp)


def save_json(data: Any, f: str | Path) -> None:
    path = Path(f)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=4)
