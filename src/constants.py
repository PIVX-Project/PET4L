#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

import os
from queue import Queue

wqueue = Queue()

APPDATA_DIRNAME = ".PET4L-DATA"

MPATH_LEDGER = "44'/77'/"
MPATH_TREZOR = "44'/119'/"
MPATH_TESTNET = "44'/1'/"
WIF_PREFIX = 212 # 212 = d4
MAGIC_BYTE = 30
STAKE_MAGIC_BYTE = 63
TESTNET_WIF_PREFIX = 239
TESTNET_MAGIC_BYTE = 139
TESTNET_STAKE_MAGIC_BYTE = 73
DEFAULT_PROTOCOL_VERSION = 70915
MINIMUM_FEE = 0.0001    # minimum PIV/kB
starting_width = 1033
starting_height = 585
home_dir = os.path.expanduser('~')
user_dir = os.path.join(home_dir, APPDATA_DIRNAME)
log_File = os.path.join(user_dir, 'debug.log')
database_File = os.path.join(user_dir, 'application.db')

DefaultCache = {
    "lastAddress": "",
    "window_width": starting_width,
    "window_height": starting_height,
    "splitter_x": 342,
    "splitter_y": 133,
    "console_hidden": False,
    "useSwiftX": False,
    "selectedHW_index": 0,
    "selectedRPC_index": 0,
    "isTestnetRPC": False,
    "hwAcc": 0,
    "spathFrom": 0,
    "spathTo": 10,
    "intExt": 0
    }

trusted_RPC_Servers = [
    ["https", "amsterdam.randomzebra.party:8080", "spmtUser_ams", "WUss6sr8956S5Paex254"],
    ["https", "losangeles.randomzebra.party:8080", "spmtUser_la", "8X88u7TuefPm7mQaJY52"],
    ["https", "singapore.randomzebra.party:8080", "spmtUser_sing", "ZyD936tm9dvqmMP8A777"]]


HW_devices = [
    # (model name, api index)
    ("LEDGER Nano", 0),
    ("TREZOR One", 1),
    ("TREZOR Model T", 1)
]
