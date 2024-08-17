import sys
# From stack overflow (https://stackoverflow.com/questions/70177888/jenkins-one-at-a-time-hash-trying-to-make-python-code-reproduce-javascript-cod)
def calculateChecksum(keyString: str):
    # Credits(modified code): Bob Jenkins (http://www.burtleburtle.net/bob/hash/doobs.html)
    # See also: https://en.wikipedia.org/wiki/Jenkins_hash_function
    # Takes a string of any size and returns an avalanching hash string of 8 hex characters.
    hash = 0
    # for (charIndex = 0; charIndex < keyString.length; ++charIndex):
    for char in keyString:
        hash += ord(char.encode("utf-8"))
        hash &= 0xFFFFFFFF
        hash += hash << 10
        hash &= 0xFFFFFFFF
        hash ^= hash >> 6
        hash &= 0xFFFFFFFF
    hash += hash << 3
    hash &= 0xFFFFFFFF
    hash ^= hash >> 11
    hash &= 0xFFFFFFFF
    hash += hash << 15
    hash &= 0xFFFFFFFF
    # # 4,294,967,295 is 0xffffffff, the maximum 32 bit unsigned integer value, used here as a mask.
    return hex((hash & 4294967295))

# This is mine :)
def getLittleJOAAThash(text: str):
    hash = calculateChecksum(text)
    if len(hash[2:]) % 2 != 0:
        hex_value = '0' + hash[2:]
    else:
        hex_value = hash[2:]
    little_version = bytes.fromhex(hex_value)[::-1]
    if len(little_version) < 4:
        little_version = little_version + b'\0'
    return little_version