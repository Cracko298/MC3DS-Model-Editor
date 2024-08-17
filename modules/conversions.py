import struct

def int_to_bytes(num: int, byteorder: str) -> bytes:
    if byteorder == "big" or byteorder == "little":
        binary_num = num.to_bytes(4, byteorder=byteorder, signed=True)
        return binary_num
    else:
        raise ValueError(f"invalid byteorder '{byteorder}'")

def uint_to_bytes(num: int, byteorder: str) -> bytes:
    if byteorder == "big" or byteorder == "little":
        binary_num = num.to_bytes(4, byteorder=byteorder, signed=False)
        return binary_num
    else:
        raise ValueError(f"invalid byteorder '{byteorder}'")

def bytes_to_int(bytes: bytearray, byteorder: str) -> int:
    if byteorder == "big" or byteorder == "little":
        int_num = int.from_bytes(bytes, byteorder=byteorder, signed=True)
        return int_num
    else:
        raise ValueError(f"invalid byteorder '{byteorder}'")

def float_to_bytes(num: float, byteorder: str) -> bytes:
    # Convierte el número a formato de 32 bits de punto flotante (float)
    if byteorder == "little":
        binary_num = struct.pack('<f', num)
    elif byteorder == "big":
        binary_num = struct.pack('>f', num)
    else:
        raise ValueError(f"invalid byteorder '{byteorder}'")
    
    return binary_num

def bytes_to_float(num: bytes, byteorder: str) -> float:
    # Convierte el número a formato de 32 bits de punto flotante (float)
    if byteorder == "little":
        decimal_num = struct.unpack('<f', num)
    elif byteorder == "big":
        decimal_num = struct.unpack('>f', num)
    else:
        raise ValueError(f"invalid byteorder '{byteorder}'")
        
    return decimal_num[0]

def bool_to_int(value: bool):
    if value == True:
        return 1
    else:
        return 0
