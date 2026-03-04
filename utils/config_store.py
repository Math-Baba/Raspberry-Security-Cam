import json
import os
import threading
from typing import Any, Dict

_LOCK = threading.Lock()

class ConfigStore:
    def __init__(self, path: str):
        self.path = path

    def read(self) -> Dict[str, Any]:
        with _LOCK:
            if not os.path.exists(self.path):
                raise FileNotFoundError(self.path)
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)

    def write(self, data: Dict[str, Any]) -> None:
        with _LOCK:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)