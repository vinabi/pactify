import json, re
from typing import Any, Dict

class JsonRepair:
    @staticmethod
    def extract_json(s: str) -> Dict[str, Any]:
        """Attempt to find and parse a JSON object in a string; very defensive."""
        # First try direct parse
        try:
            return json.loads(s)
        except Exception:
            pass
        # Find first {...} block
        match = re.search(r"\{[\s\S]*\}", s)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        # Basic fixes
        s = s.replace("\n", " ")
        s = re.sub(r"(\w+):", r'"\1":', s)  # keys without quotes
        s = s.replace("'", '"')
        try:
            return json.loads(s)
        except Exception:
            return {}
