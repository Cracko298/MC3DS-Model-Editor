import struct
from typing import BinaryIO, List
from dataclasses import dataclass
try:
    from .updateDatabase import MyDatabase
except:
    from updateDatabase import MyDatabase

class StructureError(Exception):
    def __init__(self, *args):
        super().__init__(*args)

class StructEntry:
    def __init__(self, data_type = 0, value1 = 0, value2 = 0):
        self.data_type = data_type
        self.value1 = value1
        self.value2 = value2

    def parseElement(self, file: BinaryIO):
        self.data_type = int.from_bytes(file.read(4), "little")
        raw_data1 = file.read(4)
        raw_data2 = file.read(4)
        if len(raw_data1) == 0 or len(raw_data2) == 0:
            raise ValueError("Unexpected empty value while reading structure")
        match self.data_type:
            case 0:
                # null value
                self.value1 = None
                self.value2 = 0
            case 1:
                # boolean value
                raw_data1 = int.from_bytes(raw_data1, "little")
                if raw_data1 == 1:
                    self.value1 = True
                else:
                    self.value1 = False
                self.value2 = 0
            case 2:
                # integer value
                self.value1 = int.from_bytes(raw_data1, "little", signed=True)
                self.value2 = 0
            case 3:
                # float value
                self.value1 = float("{:.5f}".format(struct.unpack('<f', raw_data1)[0]))
                self.value2 = 0
            case 4|5|6:
                # array type | string type | object type
                self.value1 = int.from_bytes(raw_data1, "little")
                self.value2 = int.from_bytes(raw_data2, "little")

    def writeToFile(self, file: BinaryIO):
        file.write(self.data_type.to_bytes(4, "little"))
        match self.data_type:
            case 0:
                # null value
                file.write(int(0).to_bytes(4, "little"))
                file.write(int(0).to_bytes(4, "little"))
            case 1:
                # boolean value
                if self.value1 == True:
                    file.write(int(1).to_bytes(4, "little"))
                else:
                    file.write(int(0).to_bytes(4, "little"))
                file.write(int(0).to_bytes(4, "little"))
            case 2:
                # integer value
                file.write(self.value1.to_bytes(4, "little", signed=True))
                file.write(int(0).to_bytes(4, "little"))
            case 3:
                # float value
                file.write(struct.pack('<f', self.value1))
                file.write(int(0).to_bytes(4, "little"))
            case 4|5|6:
                # array type | string type | object type
                file.write(self.value1.to_bytes(4, "little"))
                file.write(self.value2.to_bytes(4, "little"))

@dataclass
class Tracking:
    item_idx: int
    objects_lenght: int
    arrays_lenght: int
    db: MyDatabase

class HeaderEntry:
    def __init__(self, stringHash = 0, stringPosition = 0, headerIndex = 0):
        self.stringHash = stringHash
        self.stringPosition = stringPosition
        self.headerIndex = headerIndex

    def parseHeader(self, file: BinaryIO):
        self.stringHash = int.from_bytes(file.read(4), "little")
        self.stringPosition = int.from_bytes(file.read(4), "little")
        self.headerIndex = int.from_bytes(file.read(4), "little")

        if self.headerIndex <= 0:
            raise StructureError(f"Unexpected header index found at: {file.tell()}")
        
    def writeToFile(self, file: BinaryIO):
        file.write(self.stringHash.to_bytes(4, "little"))
        file.write(self.stringPosition.to_bytes(4, "little"))
        file.write(self.headerIndex.to_bytes(4, "little"))
        
@dataclass
class BJSONRegions:
    structre: List[StructEntry]
    joinedStrings: bytes
    arrayIndexes: List[int]
    headerIndexes: List[HeaderEntry]
    joinedHeaderStrings: bytes