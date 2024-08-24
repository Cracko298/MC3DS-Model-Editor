import json, math, sys, os
from .conversions import *
from pathlib import Path
from .JOAAThash import getLittleJOAAThash
from .updateDatabase import MyDatabase

def extract_chunk(data: bytes, idx: int, size: int = 4, start_from: int = 0):
    start = idx * size + start_from
    return data[start:start + size]

def getHeaders(data: bytes, hash_database: MyDatabase):
    text_region_start = (int.from_bytes(extract_chunk(data, 0), "little", signed=False) * 3 * 4) + 4
    lenght_text_r = int.from_bytes(extract_chunk(data, 0, 4, text_region_start), "little", signed=False)
    region_start = text_region_start + lenght_text_r + 4
    pre_region_len = int.from_bytes(extract_chunk(data, 0, 4, region_start), "little", signed=False)
    lenght = int.from_bytes(extract_chunk(data, pre_region_len + 1, 4, region_start), "little", signed=False)
    #print(pre_region_len)
    #print(lenght)
    headers = [""] * (lenght + pre_region_len)
    headers_text_start = region_start + (pre_region_len + 1) * 4 + (lenght) * 4 * 3 + 4
    for i in range(pre_region_len):
        idx = int.from_bytes(extract_chunk(data, i + 1, 4, region_start), "little", signed=False)
        headers[idx - 1] = None
    for i in range(lenght):
        idx = pre_region_len + 1 + i * 3 + 1
        hashlist = list(extract_chunk(data, idx, 4, region_start))
        headers_idx = int.from_bytes(extract_chunk(data, idx + 1, 4, region_start), "little", signed=False)
        headers_idx_end = headers_text_start + 4 + headers_idx
        while True:
            if data[headers_idx_end] == 0:
                break
            else:
                headers_idx_end += 1
        header_part = data[headers_text_start + 4 + headers_idx:headers_idx_end]
        header_idx = int.from_bytes(extract_chunk(data, idx + 2, 4, region_start), "little", signed=False) # Nota es distinto a headers_idx
        header_decode = header_part.decode('utf-8')
        headers[header_idx - 1] = header_decode
        hash_database.addToDatabase(header_decode, hashlist)
        print(extract_chunk(data, idx, 4, region_start).hex(), extract_chunk(data, idx + 1, 4, region_start).hex(), extract_chunk(data, idx + 2, 4, region_start).hex(), header_decode)
    return headers

def convertBjsonToJson(fp: str|Path):
    hash_database = MyDatabase("hash_database.json")
    if type(fp) == str:
        filepath = Path(fp)
    elif type(fp) == Path:
        filepath = fp
    else:
        raise ValueError()
    with open(filepath, "rb") as f:
        data_bytes = f.read()

    json_dict = None
    place_dir = []

    text_region_idx = int.from_bytes(extract_chunk(data_bytes, 0), "little", signed=False) * 3 + 1
    #lenght_text_region = int.from_bytes(extract_chunk(data_bytes, text_region_idx), "little", signed=False)
    print("Getting headers...")
    headers = getHeaders(data_bytes, hash_database)
    #sys.exit()

    print("Getting structure...")
    for i in range(int.from_bytes(extract_chunk(data_bytes, 0), "little", signed=False)):
        idx = i * 3 + 1
        type_extracted = int.from_bytes(extract_chunk(data_bytes, idx), "little", signed=False)
        if type_extracted == 6:
            # Object data type
            if json_dict == None:
                json_dict = {}
                tmp = []
                tmp.append(json_dict)
                tmp.append("array")
                tmp.append(int.from_bytes(extract_chunk(data_bytes, idx + 1), "little", signed=False))
                tmp.append(0)
                place_dir.append(tmp)
            else:
                tmp = place_dir[-1]
                dir = tmp[0]
                if tmp[1] == "array":
                    # Header
                    dir[f"{headers[i-1]}"] = {}
                    tmp2 = []
                    # Header in tmp
                    tmp2.append(dir[f"{headers[i-1]}"])
                    tmp2.append("array")
                    tmp2.append(int.from_bytes(extract_chunk(data_bytes, idx + 1), "little", signed=False))
                    tmp2.append(0)
                    place_dir.append(tmp2)
                elif tmp[1] == "list":
                    dir.append({})
                    tmp2 = []
                    tmp2.append(dir[-1])
                    tmp2.append("array")
                    tmp2.append(int.from_bytes(extract_chunk(data_bytes, idx + 1), "little", signed=False))
                    tmp2.append(0)
                    place_dir.append(tmp2)
                tmp[3] += 1
                if tmp[3] >= tmp[2]:
                    place_dir.pop(-2)
        elif type_extracted == 5:
            tmp = place_dir[-1]
            dir = tmp[0]
            if tmp[1] == "array":
                hashlist = list(extract_chunk(data_bytes, idx + 1))
                text_idx = int.from_bytes(extract_chunk(data_bytes, idx + 2), "little", signed=False)
                text_idx_end = ((text_region_idx + 1) * 4) + text_idx
                while True:
                    if data_bytes[text_idx_end] == 0:
                        break
                    else:
                        text_idx_end += 1
                text_part = data_bytes[((text_region_idx + 1) * 4) + text_idx:text_idx_end]
                # Header
                text_decode = text_part.decode("utf-8")
                dir[f"{headers[i-1]}"] = text_decode
                hash_database.addToDatabase(text_decode, hashlist)
            elif tmp[1] == "list":
                hashlist = list(extract_chunk(data_bytes, idx + 1))
                text_idx = int.from_bytes(extract_chunk(data_bytes, idx + 2), "little", signed=False)
                text_idx_end = ((text_region_idx + 1) * 4) + text_idx
                while True:
                    if data_bytes[text_idx_end] == 0:
                        break
                    else:
                        text_idx_end += 1
                text_part = data_bytes[((text_region_idx + 1) * 4) + text_idx:text_idx_end]
                text_decode = text_part.decode("utf-8")
                dir.append(text_decode)
                hash_database.addToDatabase(text_decode, hashlist)
            tmp[3] += 1
        elif type_extracted == 4:
            # Array data type
            if json_dict == None:
                json_dict = []
                tmp = []
                tmp.append(json_dict)
                tmp.append("list")
                tmp.append(int.from_bytes(extract_chunk(data_bytes, idx + 1), "little", signed=False))
                tmp.append(0)
                place_dir.append(tmp)
            else:
                tmp = place_dir[-1]
                dir = tmp[0]
                # Header
                dir[f"{headers[i-1]}"] = []
                tmp2 = []
                # Header in tmp
                tmp2.append(dir[f"{headers[i-1]}"])
                tmp2.append("list")
                tmp2.append(int.from_bytes(extract_chunk(data_bytes, idx + 1), "little", signed=False))
                tmp2.append(0)
                place_dir.append(tmp2)
                tmp[3] += 1
                if tmp[3] >= tmp[2]:
                    place_dir.pop(-2)
        elif type_extracted == 3:
            # Float data type
            tmp = place_dir[-1]
            dir = tmp[0]
            if tmp[1] == "array":
                float_num = bytes_to_float(extract_chunk(data_bytes, idx + 1), "little")
                # Header
                dir[f"{headers[i-1]}"] = float("{:.2f}".format(float_num))
            elif tmp[1] == "list":
                float_num = bytes_to_float(extract_chunk(data_bytes, idx + 1), "little")
                dir.append(float("{:.2f}".format(float_num)))
            tmp[3] += 1
        elif type_extracted == 2:
            # Integer data type
            tmp = place_dir[-1]
            dir = tmp[0]
            if tmp[1] == "array":
                # Header
                dir[f"{headers[i-1]}"] = bytes_to_int(extract_chunk(data_bytes, idx + 1), "little")
            elif tmp[1] == "list":
                dir.append(bytes_to_int(extract_chunk(data_bytes, idx + 1), "little"))
            tmp[3] += 1
        elif type_extracted == 1:
            # Boolean data type
            tmp = place_dir[-1]
            dir = tmp[0]
            if tmp[1] == "array":
                bool_num = int.from_bytes(extract_chunk(data_bytes, idx + 1), "little", signed=False)
                # With header
                if bool_num == 0:
                    dir[f"{headers[i-1]}"] = False
                elif bool_num == 1:
                    dir[f"{headers[i-1]}"] = True
            elif tmp[1] == "list":
                bool_num = int.from_bytes(extract_chunk(data_bytes, idx + 1), "little", signed=False)
                if bool_num == 0:
                    dir.append(False)
                elif bool_num == 1:
                    dir.append(True)
            tmp[3] += 1
        elif type_extracted == 0:
            # None data type
            tmp = place_dir[-1]
            dir = tmp[0]
            if tmp[1] == "array":
                # With header
                dir[f"{headers[i-1]}"] = None
            elif tmp[1] == "list":
                dir.append(None)
            tmp[3] += 1

        if len(place_dir) > 0:
            check = place_dir[-1]
            if check[3] >= check[2]:
                place_dir.pop(-1)

    json_string = json.dumps(json_dict, indent=4)
    hash_database.save()

    return json_string

def addObject(sdata: list, tdata: list, nhdata: list, hdata: list, htdata: list, header: str | None, data: dict, obj_close: int = 0, list_close: int = 0, g_count = 0, hashdb: MyDatabase = None):
    tmp_nhdata = []
    last_close_nhdata = []
    tmp_hdata = []
    last_close_hdata = []
    self_hdata = []
    sdata.extend(int_to_bytes(6, "little"))
    sdata.extend(int_to_bytes(len(data), "little"))
    end_idx = len(sdata)
    local_count = g_count
    #sdata.extend([0] * 4)
    if header == None and local_count != 0:
        tmp_nhdata.extend(int_to_bytes(g_count, "little"))
    if header != None:
        if hashdb.getValue(header):
            self_hdata.extend(hashdb.getValue(header))
        else:
            print(f"Missing hash value for {header}")
            sys.exit()
        self_hdata.extend(int_to_bytes(len(htdata) - 4, "little"))
        self_hdata.extend(int_to_bytes(g_count, "little"))
        htdata.extend(header.encode("utf-8"))
        htdata.append(0)
    g_count += 1
    for key in data:
        if type(data[key]) == bool:
            addBool(sdata, tmp_nhdata, tmp_hdata, htdata, key, data[key], g_count, hashdb=hashdb)
        elif type(data[key]) == int:
            addInt(sdata, tmp_nhdata, tmp_hdata, htdata, key, data[key], g_count, hashdb=hashdb)
        elif type(data[key]) == float:
            addFloat(sdata, tmp_nhdata, tmp_hdata, htdata, key, data[key], g_count, hashdb=hashdb)
        elif type(data[key]) == list:
            obj_hdata, last_close_nhdata, last_close_hdata, g_count, obj_close, list_close = addList(sdata, tdata, [], [], htdata, key, data[key], obj_close, list_close, g_count, hashdb=hashdb)
            nhdata.extend(last_close_nhdata)
            hdata.extend(last_close_hdata)
            tmp_hdata.extend(obj_hdata)
        elif type(data[key]) == str:
            addString(sdata, tdata, tmp_nhdata, tmp_hdata, htdata, key, data[key], g_count, hashdb=hashdb)
        elif type(data[key]) == dict:
            obj_hdata, last_close_nhdata, last_close_hdata, g_count, obj_close, list_close = addObject(sdata, tdata, [], [], htdata, key, data[key], obj_close, list_close, g_count, hashdb=hashdb)
            nhdata.extend(last_close_nhdata)
            hdata.extend(last_close_hdata)
            tmp_hdata.extend(obj_hdata)
        
        if type(data[key]) != dict and type(data[key]) != list:
            g_count += 1
    sdata[end_idx:4] = int_to_bytes(obj_close, "little")
    obj_count = len(data)
    nhdata.extend(tmp_nhdata)
    hdata.extend(tmp_hdata)
    return self_hdata, nhdata, hdata, g_count, obj_close + obj_count, list_close

def addList(sdata: list, tdata: list, nhdata: list, hdata: list, htdata: list, header: str | None, data: list, obj_close: int = 0, list_close: int = 0, g_count = 0, hashdb: MyDatabase = None):
    tmp_nhdata = []
    last_close_nhdata = []
    tmp_hdata = []
    last_close_hdata = []
    self_hdata = []
    sdata.extend(int_to_bytes(4, "little"))
    sdata.extend(int_to_bytes(len(data), "little"))
    end_idx = len(sdata)
    #sdata.extend([0] * 4)
    local_count = g_count
    if header == None and local_count != 0:
        tmp_nhdata.extend(int_to_bytes(g_count, "little"))
    if header != None:
        if hashdb.getValue(header):
            self_hdata.extend(hashdb.getValue(header))
        else:
            print(f"Missing hash value for {header}")
            sys.exit()
        self_hdata.extend(int_to_bytes(len(htdata) - 4, "little"))
        self_hdata.extend(int_to_bytes(g_count, "little"))
        htdata.extend(header.encode("utf-8"))
        htdata.append(0)
    g_count += 1
    for key in data:
        if type(key) == bool:
            addBool(sdata, tmp_nhdata, tmp_hdata, htdata, None, key, g_count)
        elif type(key) == int:
            addInt(sdata, tmp_nhdata, tmp_hdata, htdata, None, key, g_count)
        elif type(key) == float:
            addFloat(sdata, tmp_nhdata, tmp_hdata, htdata, None, key, g_count)
        elif type(key) == list:
            obj_hdata, last_close_nhdata, last_close_hdata, g_count, obj_close, list_close = addList(sdata, tdata, [], [], htdata, None, key, obj_close, list_close, g_count, hashdb=hashdb)
            nhdata.extend(last_close_nhdata[:-4])
            tmp_nhdata.extend(last_close_nhdata[-4:])
            hdata.extend(last_close_hdata)
        elif type(key) == str:
            addString(sdata, tdata, tmp_nhdata, hdata, htdata, None, key, g_count, hashdb=hashdb)
        elif type(key) == dict:
            obj_hdata, last_close_nhdata, last_close_hdata, g_count, obj_close, list_close = addObject(sdata, tdata, [], [], htdata, None, key, obj_close, list_close, g_count, hashdb=hashdb)
            nhdata.extend(last_close_nhdata[:-4])
            tmp_nhdata.extend(last_close_nhdata[-4:])
            hdata.extend(last_close_hdata)

        if type(key) != dict and type(key) != list:
            g_count += 1
    sdata[end_idx:4] = int_to_bytes(list_close, "little")
    list_count = len(data)
    nhdata.extend(tmp_nhdata)
    hdata.extend(tmp_hdata)
    return self_hdata, nhdata, hdata, g_count, obj_close, list_close + list_count

def addBool(sdata: list, nhdata: list, hdata: list, htdata: list, header: str | None, value: bool, count: int, hashdb: MyDatabase = None):
    sdata.extend(int_to_bytes(1, "little"))
    sdata.extend(int_to_bytes(bool_to_int(value), "little"))
    sdata.extend(int_to_bytes(0, "little"))
    if header == None:
        nhdata.extend(int_to_bytes(count, "little"))
    if header != None:
        if hashdb.getValue(header):
            hdata.extend(hashdb.getValue(header))
        else:
            print(f"Missing hash value for {header}")
            sys.exit()
        hdata.extend(int_to_bytes(len(htdata) - 4, "little"))
        hdata.extend(int_to_bytes(count, "little"))
        htdata.extend(header.encode("utf-8"))
        htdata.append(0)

def addInt(sdata: list, nhdata: list, hdata: list, htdata: list, header: str | None, value: int, count: int, hashdb: MyDatabase = None):
    sdata.extend(int_to_bytes(2, "little"))
    sdata.extend(int_to_bytes(value, "little"))
    sdata.extend(int_to_bytes(0, "little"))
    if header == None:
        nhdata.extend(int_to_bytes(count, "little"))
    if header != None:
        if hashdb.getValue(header):
            hdata.extend(hashdb.getValue(header))
        else:
            print(f"Missing hash value for {header}")
            sys.exit()
        hdata.extend(int_to_bytes(len(htdata) - 4, "little"))
        hdata.extend(int_to_bytes(count, "little"))
        htdata.extend(header.encode("utf-8"))
        htdata.append(0)

def addFloat(sdata: list, nhdata: list, hdata: list, htdata: list, header: str | None, value: float, count: int, hashdb: MyDatabase = None):
    sdata.extend(int_to_bytes(3, "little"))
    sdata.extend(float_to_bytes(value, "little"))
    sdata.extend(int_to_bytes(0, "little"))
    if header == None:
        nhdata.extend(int_to_bytes(count, "little"))
    if header != None:
        if hashdb.getValue(header):
            hdata.extend(hashdb.getValue(header))
        else:
            print(f"Missing hash value for {header}")
            sys.exit()
        hdata.extend(int_to_bytes(len(htdata) - 4, "little"))
        hdata.extend(int_to_bytes(count, "little"))
        htdata.extend(header.encode("utf-8"))
        htdata.append(0)

def addString(sdata: list, tdata: list, nhdata: list, hdata: list, htdata: list, header: str | None, value: str, count: int, hashdb: MyDatabase = None):
    sdata.extend(int_to_bytes(5, "little"))
    if hashdb.getValue(value):
        sdata.extend(hashdb.getValue(value))
    else:
        print(f"Missing hash value for {value}")
        sys.exit()
    sdata.extend(int_to_bytes(len(tdata) - 4, "little"))
    tdata.extend(value.encode('utf-8'))
    tdata.append(0)
    if header == None:
        nhdata.extend(int_to_bytes(count, "little"))
    if header != None:
        if hashdb.getValue(header):
            hdata.extend(hashdb.getValue(header))
        else:
            print(f"Missing hash value for {header}")
            sys.exit()
        hdata.extend(int_to_bytes(len(htdata) - 4, "little"))
        hdata.extend(int_to_bytes(count, "little"))
        htdata.extend(header.encode("utf-8"))
        htdata.append(0)

def convertJsonToBjson(fp: str):
    hash_database = MyDatabase("hash_database.json")
    filepath = Path(fp)
    with open(filepath, "r", encoding='utf-8') as f:
        json_file = json.loads(f.read())
    
    structure_data = [0] * 4
    text_data = [0] * 4
    no_headers_data = [0] * 4
    headers_data = [0] * 4
    headers_text_data = [0] * 4

    if type(json_file) == dict:
        addObject(structure_data, text_data, no_headers_data, headers_data, headers_text_data, None, json_file, hashdb=hash_database)
    elif type(json_file) == list:
        addList(structure_data, text_data, no_headers_data, headers_data, headers_text_data, None, json_file, hashdb=hash_database)
    
    structure_data[0:4] = uint_to_bytes(math.floor((len(structure_data) - 4) / (3 * 4)), "little")
    text_data[0:4] = uint_to_bytes(len(text_data) - 4, "little")
    no_headers_data[0:4] = uint_to_bytes(math.floor((len(no_headers_data) - 4) / 4), "little")
    headers_data[0:4] = uint_to_bytes(math.floor((len(headers_data) - 4) / (3 * 4)), "little")
    headers_text_data[0:4] = uint_to_bytes(len(headers_text_data) - 4, "little")

    output_data = []
    output_data.extend(structure_data)
    output_data.extend(text_data)
    output_data.extend(no_headers_data)
    output_data.extend(headers_data)
    output_data.extend(headers_text_data)

    with open(".\\filename.txt") as df:
        first = df.readline()
        getBaseName = os.path.basename(os.path.dirname(first))

    with open(f"{getBaseName}_updated.bjson", "wb") as f:
        f.write(bytearray(output_data))