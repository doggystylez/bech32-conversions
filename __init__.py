# heavily relies on the bech32 python package. please find copyright notice below

# Copyright (c) 2017 Pieter Wuille
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from typing import Iterable, List, Optional, Tuple, Union
from struct import pack

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

def bech32_polymod(values: Iterable[int]) -> int:
    generator = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ value
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk

def bech32_hrp_expand(hrp: str) -> List[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

def bech32_verify_checksum(hrp: str, data: Iterable[int]) -> bool:
    return bech32_polymod(bech32_hrp_expand(hrp) + list(data)) == 1

def bech32_create_checksum(hrp: str, data: Iterable[int]) -> List[int]:
    values = bech32_hrp_expand(hrp) + list(data)
    polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

def bech32_encode(hrp: str, data: Iterable[int]) -> str:
    combined = list(data) + bech32_create_checksum(hrp, data)
    return hrp + "1" + "".join([CHARSET[d] for d in combined])

def bech32_decode(bech: str) -> Union[Tuple[None, None], Tuple[str, List[int]]]:
    if (any(ord(x) < 33 or ord(x) > 126 for x in bech)) or (
        bech.lower() != bech and bech.upper() != bech
    ):
        return (None, None)
    bech = bech.lower()
    pos = bech.rfind("1")
    if pos < 1 or pos > 83 or pos + 7 > len(bech):
        return (None, None)
    if not all(x in CHARSET for x in bech[pos + 1 :]):
        return (None, None)
    hrp = bech[:pos]
    data = [CHARSET.find(x) for x in bech[pos + 1 :]]
    if not bech32_verify_checksum(hrp, data):
        return (None, None)
    return (hrp, data[:-6])

def convertbits(data: Iterable[int], frombits: int, tobits: int, pad: bool = True) -> Optional[List[int]]:
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret

def decode(hrp: str, addr: str) -> Union[Tuple[None, None], Tuple[int, List[int]]]:
    hrpgot, data = bech32_decode(addr)
    if hrpgot != hrp:
        return (None, None)
    assert data is not None
    decoded = convertbits(data[1:], 5, 8, False)
    if decoded is None or len(decoded) < 2 or len(decoded) > 40:
        return (None, None)
    if data[0] > 16:
        return (None, None)
    if data[0] == 0 and len(decoded) != 20 and len(decoded) != 32:
        return (None, None)
    return (data[0], decoded)

def encode(hrp: str, witver: int, witprog: Iterable[int]) -> Optional[str]:
    five_bit_witprog = convertbits(witprog, 8, 5)
    if five_bit_witprog is None:
        return None
    ret = bech32_encode(hrp, [witver] + five_bit_witprog)
    if decode(hrp, ret) == (None, None):
        return None
    return ret

# hex > bytes > byte array > bech32

# hex to bytes ✔️
def hex_to_bytes(hex):
    return bytes.fromhex(hex)

# hex to byte array ✔️
def hex_to_byte_array(hex):
    return bytes_to_byte_array(hex_to_bytes(hex))

# hex to bech32 ✔️
def hex_to_bech(hrp, hex):
    return bytes_to_bech(hrp, hex_to_bytes(hex))

# bytes to hex ✔️
def bytes_to_hex(bytes):
    return bytes.hex()

# bytes to byte array ✔️
def bytes_to_byte_array(bytes):
    return convertbits(bytes, 8, 5, True)

# bytes to bech32 ✔️
def bytes_to_bech(hrp, bytes):
    return byte_array_to_bech(hrp, bytes_to_byte_array(bytes))

# byte array to hex ✔️
def byte_array_to_hex(byte_array):
    hex = pack("i" * 20, *convertbits(byte_array, 5, 8, False)).hex()
    return "".join([hex[i:i + 2] for i in range(0, len(hex), 8)])

# byte array to bytes ✔️
def byte_array_to_bytes(byte_array):
    return hex_to_bytes(byte_array_to_hex(byte_array))

# byte array to bech32 ✔️
def byte_array_to_bech(hrp, byte_array):
    return bech32_encode(hrp, byte_array)

# bech32 to hex ✔️
def bech_to_hex(bech32):
    return byte_array_to_hex(bech_to_byte_array(bech32))

# bech32 to bytes ✔️
def bech_to_bytes(bech32):
    return hex_to_bytes(bech_to_hex(bech32))

# bech32 to byte array ✔️
def bech_to_byte_array(bech32):
    return bech32_decode(bech32)[1]

# bech32 to bech32 ✔️
def bech_to_bech(bech32, hrp):
    return byte_array_to_bech(hrp, bech_to_byte_array(bech32))

# bech32 to hrp ✔️
def bech_to_hrp(bech32):
    return bech32_decode(bech32)[0]
