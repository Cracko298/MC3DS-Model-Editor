from pathlib import Path
import json, os

class MyDatabase():
    def __init__(self, fp):
        self.filepath = Path(fp)
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.json_data = json.loads(f.read())
        else:
            self.json_data = {}

    def save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.json_data, indent=4))

    def addToDatabase(self, text: str, hashlist: list) -> None:
        self.json_data[text] = hashlist

    def getValue(self, key: str) -> list:
        with open(self.filepath, "r", encoding="utf-8") as f:
            json_data = json.loads(f.read())
        if key in json_data:
            return json_data[key]
        else:
            return False