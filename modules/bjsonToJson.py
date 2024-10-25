from typing import List
try:
    from .bjsonStructures import Tracking, StructEntry, BJSONRegions, StructureError, HeaderEntry
except:
    from bjsonStructures import Tracking, StructEntry, BJSONRegions, StructureError, HeaderEntry

def searchForHeader(headerIndexes: List[HeaderEntry], index: int) -> HeaderEntry | None:
    for i, element in enumerate(headerIndexes):
        if element.headerIndex == index:
            return headerIndexes.pop(i)
    return

def searchForIndexArray(arrayIndexes: List[int], index: int) -> bool:
    for i, element in enumerate(arrayIndexes):
        if element == index:
            arrayIndexes.pop(i)
            return True
    return False

def parseObject(root: dict, object: StructEntry, regions: BJSONRegions, tracking: Tracking):
    # Iterate over the lenght 
    for i in range(object.value1):
        tracking.item_idx += 1
        entry: StructEntry = regions.structre.pop(0)
        header = searchForHeader(regions.headerIndexes, tracking.item_idx)
        if not header:
            raise StructureError("Header not found for element with index " + tracking.item_idx)
        else:
            # This splits until first 0x00 starting from an index and then decodes it to utf-8
            headerString = regions.joinedHeaderStrings[header.stringPosition:].split(b'\0', 1)[0].decode("utf-8")
            tracking.db.addToDatabase(headerString, header.stringHash)

            match entry.data_type:
                case 0|1|2|3:
                    root[headerString] = entry.value1
                case 5:
                    # This splits until first 0x00 starting from an index and then decodes it to utf-8
                    root[headerString] = regions.joinedStrings[entry.value2:].split(b'\0', 1)[0].decode("utf-8")
                    tracking.db.addToDatabase(root[headerString], entry.value1)
                case 4:
                    root[headerString] = []
                    parseArray(root[headerString], entry, regions, tracking)
                case 6:
                    root[headerString] = {}
                    parseObject(root[headerString], entry, regions, tracking)
                case _:
                    raise StructureError("data_type unknown: " + entry.data_type)
            
def parseArray(root: list, object: StructEntry, regions: BJSONRegions, tracking: Tracking):
    # Iterate over array lenght
    for i in range(object.value1):
        tracking.item_idx += 1
        entry: StructEntry = regions.structre.pop(0)
        if not searchForIndexArray(regions.arrayIndexes, tracking.item_idx):
            raise StructureError("Index array not found for: " + tracking.item_idx)
        else:
            match entry.data_type:
                case 0|1|2|3:
                    root.append(entry.value1)
                case 5:
                    # This splits until first 0x00 starting from an index and then decodes it to utf-8
                    string = regions.joinedStrings[entry.value2:].split(b'\0', 1)[0].decode("utf-8")
                    root.append(string)
                    tracking.db.addToDatabase(string, entry.value1)
                case 4:
                    root_array = []
                    parseArray(root_array, entry, regions, tracking)
                    root.append(root_array)
                case 6:
                    parsedObject = {}
                    parseObject(parsedObject, entry, regions, tracking)
                    root.append(parsedObject)
                case _:
                    raise StructureError("data_type unknown: " + entry.data_type)