#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

import bitcoin
import hashlib

from constants import WIF_PREFIX, MAGIC_BYTE, TESTNET_WIF_PREFIX, TESTNET_MAGIC_BYTE, \
    STAKE_MAGIC_BYTE, TESTNET_STAKE_MAGIC_BYTE
from pivx_b58 import b58encode, b58decode


def double_sha256(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def single_sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def generate_privkey(isTestnet: bool = False) -> str:
    """
    Based on Andreas Antonopolous work from 'Mastering Bitcoin'.
    """
    valid = False
    privkey = ""
    while not valid:
        privkey = bitcoin.random_key()
        decoded_private_key = bitcoin.decode_privkey(privkey, 'hex')
        valid = 0 < decoded_private_key < bitcoin.N
    return base58fromhex(privkey, isTestnet)


def base58fromhex(hexstr: str, isTestnet: bool) -> str:
    base58_secret = TESTNET_WIF_PREFIX if isTestnet else WIF_PREFIX
    data = bytes([base58_secret]) + bytes.fromhex(hexstr)
    checksum = bitcoin.bin_dbl_sha256(data)[0:4]
    return b58encode(data + checksum)


def pubkey_to_address(pubkey: str, isTestnet: bool = False, isCold: bool = False) -> str:
    pubkey_bin = bytes.fromhex(pubkey)
    pkey_hash = bitcoin.bin_hash160(pubkey_bin)
    return pubkeyhash_to_address(pkey_hash, isTestnet, isCold)


def pubkeyhash_to_address(pkey_hash: bytes, isTestnet: bool = False, isCold: bool = False) -> str:
    if isCold:
        base58_secret = TESTNET_STAKE_MAGIC_BYTE if isTestnet else STAKE_MAGIC_BYTE
    else:
        base58_secret = TESTNET_MAGIC_BYTE if isTestnet else MAGIC_BYTE
    data = bytes([base58_secret]) + pkey_hash
    checksum = bitcoin.bin_dbl_sha256(data)[0:4]
    return b58encode(data + checksum)


def wif_to_privkey(string: str) -> str | None:
    wif_compressed = len(string) == 52
    pvkeyencoded = b58decode(string).hex()
    wifversion = pvkeyencoded[:2]
    checksum = pvkeyencoded[-8:]
    vs = bytes.fromhex(pvkeyencoded[:-8])
    check = double_sha256(vs)[0:4]

    if (wifversion == WIF_PREFIX.to_bytes(1, byteorder='big').hex() and checksum == check.hex()) or \
       (wifversion == TESTNET_WIF_PREFIX.to_bytes(1, byteorder='big').hex() and checksum == check.hex()):

        if wif_compressed:
            privkey = pvkeyencoded[2:-10]
        else:
            privkey = pvkeyencoded[2:-8]

        return privkey

    return None
