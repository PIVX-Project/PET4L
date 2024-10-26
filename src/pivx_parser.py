#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

from typing import Dict, Tuple, List, Literal, Any, TypedDict
from misc import getCallerName, getFunctionName, printException
import utils
from pivx_hashlib import pubkeyhash_to_address


class HexParser:
    def __init__(self, hex_str: str):
        self.cursor = 0
        self.hex_str = hex_str

    def readInt(self, nbytes: int, byteorder: Literal['little', 'big'] = 'big', signed: bool = False) -> int:
        if self.cursor + nbytes * 2 > len(self.hex_str):
            raise Exception("HexParser range error")
        b = bytes.fromhex(self.hex_str[self.cursor:self.cursor + nbytes * 2])
        res = int.from_bytes(b, byteorder=byteorder, signed=signed)
        self.cursor += nbytes * 2
        return res

    def readVarInt(self) -> int:
        r = self.readInt(1)
        if r == 253:
            return self.readInt(2, "little")
        elif r == 254:
            return self.readInt(4, "little")
        elif r == 255:
            return self.readInt(8, "little")
        return r

    def readString(self, nbytes: int, byteorder: str = "big") -> str:
        if self.cursor + nbytes * 2 > len(self.hex_str):
            raise Exception("HexParser range error")
        res = self.hex_str[self.cursor:self.cursor + nbytes * 2]
        self.cursor += nbytes * 2
        if byteorder == "little":
            splits = [res[i:i + 2] for i in range(0, len(res), 2)]
            return ''.join(splits[::-1])
        return res


class VinType(TypedDict, total=False):
    txid: str
    vout: int
    scriptSig: Dict[str, str]
    sequence: int
    coinbase: str


class VoutType(TypedDict):
    value: int
    scriptPubKey: Dict[str, Any]


class TxType(TypedDict):
    version: int
    vin: List[VinType]
    vout: List[VoutType]
    locktime: int


def IsCoinBase(vin: VinType) -> bool:
    return vin["txid"] == "0" * 64 and vin["vout"] == 4294967295 and vin["scriptSig"]["hex"][:2] != "c2"


def ParseTxInput(p: HexParser) -> VinType:
    vin: VinType = {
        "txid": p.readString(32, "little"),
        "vout": p.readInt(4, "little"),
        "scriptSig": {
            "hex": p.readString(p.readVarInt(), "big")
        },
        "sequence": p.readInt(4, "little")
    }
    if IsCoinBase(vin):
        del vin["txid"]
        del vin["vout"]
        vin["coinbase"] = vin["scriptSig"]["hex"]
        del vin["scriptSig"]

    return vin


def ParseTxOutput(p: HexParser, isTestnet: bool = False) -> VoutType:
    vout: VoutType = {
        "value": p.readInt(8, "little"),
        "scriptPubKey": {
            "hex": p.readString(p.readVarInt(), "big"),
            "addresses": []
        }
    }
    try:
        locking_script = bytes.fromhex(vout["scriptPubKey"]["hex"])
        if len(locking_script) in [25, 35, 51]:
            add_bytes = utils.extract_pkh_from_locking_script(locking_script)
            address = pubkeyhash_to_address(add_bytes, isTestnet)
            vout["scriptPubKey"]["addresses"].append(address)
    except Exception as e:
        printException(getCallerName(True), getFunctionName(True), "error parsing output", str(e))
    return vout


def ParseTx(hex_string: str, isTestnet: bool = False) -> TxType:
    p = HexParser(hex_string)
    tx: TxType = {
        "version": p.readInt(4, "little"),
        "vin": [ParseTxInput(p) for _ in range(p.readVarInt())],
        "vout": [ParseTxOutput(p, isTestnet) for _ in range(p.readVarInt())],
        "locktime": p.readInt(4, "little")
    }
    return tx


def IsPayToColdStaking(rawtx: str, out_n: int) -> Tuple[bool, bool]:
    tx = ParseTx(rawtx)
    script = tx['vout'][out_n]["scriptPubKey"]["hex"]
    return utils.IsPayToColdStaking(bytes.fromhex(script)), IsCoinStake(tx)


def IsCoinStake(json_tx: TxType) -> bool:
    return json_tx['vout'][0]["scriptPubKey"]["hex"] == ""


def GetDelegatedStaker(rawtx: str, out_n: int, isTestnet: bool) -> str:
    tx = ParseTx(rawtx)
    script = tx['vout'][out_n]["scriptPubKey"]["hex"]
    if not utils.IsPayToColdStaking(bytes.fromhex(script)):
        return ""
    pkh = utils.GetDelegatedStaker(bytes.fromhex(script))
    return pubkeyhash_to_address(pkh, isTestnet, isCold=True)
