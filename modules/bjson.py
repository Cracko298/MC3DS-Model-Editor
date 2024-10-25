import io
import json
from pathlib import Path

try:
    from .bjsonStructures import StructEntry, StructureError, HeaderEntry, Tracking, BJSONRegions
    from .bjsonToJson import parseObject, parseArray
    from .jsonTobjson import addObject, addList
    from .updateDatabase import MyDatabase
except:
    from bjsonStructures import StructEntry, StructureError, HeaderEntry, Tracking, BJSONRegions
    from bjsonToJson import parseObject, parseArray
    from jsonTobjson import addObject, addList
    from updateDatabase import MyDatabase

class BJSONFile:
    def open(self, path: str | Path):
        if isinstance(path, str):
            path = Path(path)
        elif not isinstance(path, Path):
            raise TypeError("path expected to be 'str' or 'Path'")
        
        if not path.exists():
            raise Exception("path doesn't exists")
        else:
            with open(path, "rb") as f:
                self.data = io.BytesIO(f.read())
        return self

    def load(self, data: bytes | bytearray):
        if isinstance(data, bytes) or isinstance(data, bytearray):
            self.data = io.BytesIO(data)
        else:
            raise TypeError("data expected to be 'bytes' or 'bytearray'")
        return self
    
    def getData(self):
        self.data.seek(0)
        data = self.data.read()
        self.data.seek(0)
        return data

    def toPython(self, showDebug: bool = False) -> dict | list:
        if showDebug:
            print("Getting structure")
        total_elements = int.from_bytes(self.data.read(4), "little")
        structEntries = []
        for i in range(total_elements):
            entry = StructEntry()
            entry.parseElement(self.data)
            structEntries.append(entry)

        if showDebug:
            print("Getting strings")
        lenght_strings = int.from_bytes(self.data.read(4), "little")
        joinedStrings = self.data.read(lenght_strings)
        
        if showDebug:
            print("Getting index for array items")
        total_array_items = int.from_bytes(self.data.read(4), "little")
        arrayIndexes = []
        for i in range(total_array_items):
            arrayIndexes.append(int.from_bytes(self.data.read(4), "little"))
            if arrayIndexes[-1] <= 0:
                raise StructureError(f"Unexpected array index found at: {self.data.tell()}")

        if showDebug:
            print("Getting index for headers")
        total_header_items = int.from_bytes(self.data.read(4), "little")
        headerIndexes = []
        for i in range(total_header_items):
            headerEntry = HeaderEntry()
            headerEntry.parseHeader(self.data)
            headerIndexes.append(headerEntry)

        if showDebug:
            print("Getting strings for headers")
        lenght_headers_strings = int.from_bytes(self.data.read(4), "little")
        joinedHeadersStrings = self.data.read(lenght_headers_strings)

        if showDebug:
            print("Assembling structure")
        track = Tracking(0, 0, 0, MyDatabase("./hash_database.json"))
        bjsonRegions = BJSONRegions(structEntries, joinedStrings, arrayIndexes, headerIndexes, joinedHeadersStrings)
        entry: StructEntry = bjsonRegions.structre.pop(0)
        if entry.data_type == 6:
            root = {}
            parseObject(root, entry, bjsonRegions, track)
        elif entry.data_type == 4:
            root = []
            parseArray(root, entry, bjsonRegions, track)
        else:
            raise StructureError(f"Data type {entry.data_type} is unknown or shouldn't go first in file. Expected 6 (object) or 4 (array)")

        track.db.save()
        self.data.seek(0)
        return root
    
    def toJson(self, showDebug: bool = False):
        return json.dumps(self.toPython(showDebug), ensure_ascii=False, indent=4)
    
    def fromPython(self, data: dict|list):
        tracking = Tracking(0, 0, 0, MyDatabase(".\\hash_database.json"))
        bjsonRegions = BJSONRegions([], b'', [], [], b'')

        if isinstance(data, dict):
            bjsonRegions.structre.append(StructEntry(6, len(data), 0))
            addObject(bjsonRegions, data, tracking)
        elif isinstance(data, list):
            bjsonRegions.structre.append(StructEntry(4, len(data), 0))
            addList(bjsonRegions, data, tracking)
        else:
            raise TypeError("data expected to be 'list' or 'dict'")
        
        self.data = io.BytesIO(bytearray())

        self.data.write(len(bjsonRegions.structre).to_bytes(4, "little"))
        for element in bjsonRegions.structre:
            element.writeToFile(self.data)

        self.data.write(len(bjsonRegions.joinedStrings).to_bytes(4, "little"))
        self.data.write(bjsonRegions.joinedStrings)

        self.data.write(len(bjsonRegions.arrayIndexes).to_bytes(4, "little"))
        for element in bjsonRegions.arrayIndexes:
            self.data.write(element.to_bytes(4, "little"))

        self.data.write(len(bjsonRegions.headerIndexes).to_bytes(4, "little"))
        for element in bjsonRegions.headerIndexes:
            element.writeToFile(self.data)

        self.data.write(len(bjsonRegions.joinedHeaderStrings).to_bytes(4, "little"))
        self.data.write(bjsonRegions.joinedHeaderStrings)

        self.data.seek(0)
        return
    
    def fromJson(self, json_str: str):
        self.fromPython(json.loads(json_str))
        return