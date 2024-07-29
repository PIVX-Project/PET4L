#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

import os
from queue import Queue

wqueue = Queue()  # type: Queue[str]

APPDATA_DIRNAME = ".PET4L-DATA"

MPATH_LEDGER = "44'/77'/"
MPATH_TREZOR = "44'/119'/"
MPATH_TESTNET = "44'/1'/"
WIF_PREFIX = 212  # 212 = d4
MAGIC_BYTE = 30
STAKE_MAGIC_BYTE = 63
TESTNET_WIF_PREFIX = 239
TESTNET_MAGIC_BYTE = 139
TESTNET_STAKE_MAGIC_BYTE = 73
DEFAULT_PROTOCOL_VERSION = 70915
MINIMUM_FEE = 0.0001    # minimum PIV/kB
SECONDS_IN_2_MONTHS = 60 * 24 * 60 * 60
MAX_INPUTS_NO_WARNING = 75
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
    "selectedExplorer_index": 0,
    "selectedHW_index": 0,
    "selectedRPC_index": 0,
    "isTestnetRPC": False,
    "hwAcc": 0,
    "spathFrom": 0,
    "spathTo": 10,
    "intExt": 0
}

trusted_RPC_Servers = [
    ["https", "lithuania.fuzzbawls.pw:8080", "spmtUser", "WUss6sr8956S5Paex254"],
    ["https", "latvia.fuzzbawls.pw:8080", "spmtUser", "8X88u7TuefPm7mQaJY52"],
    ["https", "charlotte.fuzzbawls.pw:8080", "spmtUser", "ZyD936tm9dvqmMP8A777"]]

trusted_explorers = [
    ["https://explorer.duddino.com/", False, False],
    ["https://testnet.duddino.com/", True, False],
    ["https://zkbitcoin.com/", False, False]
]

HW_devices = [
    # (model name, api index)
    ("LEDGER Nano", 0),
    ("TREZOR One", 1),
    ("TREZOR Model T", 1)
]
