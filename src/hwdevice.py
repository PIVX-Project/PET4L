#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

import logging

from PyQt5.QtCore import QObject, pyqtSignal

from constants import HW_devices
from ledgerClient import LedgerApi
from misc import printOK, printDbg
from time import sleep
from trezorClient import TrezorApi

def check_api_init(func):
    def func_int(*args, **kwargs):
        hwDevice = args[0]
        if hwDevice.api is None:
            logging.warning(f"{func.__name__}: hwDevice.api is None")
            raise Exception("HW device: client not initialized")
        return func(*args, **kwargs)
    return func_int

class HWdevice(QObject):
    # signal: sig1 (thread) is done - emitted by signMessageFinish
    sig1done = pyqtSignal(str)

    def __init__(self, main_wnd, *args, **kwargs):
        printDbg("HW: Initializing Class...")
        super().__init__(*args, **kwargs)
        self.main_wnd = main_wnd
        self.api = None
        printOK("HW: Class initialized")

    def initDevice(self, hw_index):
        printDbg(f"HW: initializing hw device with index {hw_index}")
        if hw_index >= len(HW_devices):
            raise Exception("Invalid HW index")

        # Select API
        api_index = HW_devices[hw_index][1]
        if api_index == 0:
            self.api = LedgerApi(self.main_wnd)
        else:
            self.api = TrezorApi(hw_index, self.main_wnd)

        # Init device & connect signals
        self.api.initDevice()
        self.sig1done = self.api.sig1done
        self.api.sig_disconnected.connect(self.main_wnd.clearHWstatus)
        printOK(f"HW: hw device with index {hw_index} initialized")

    @check_api_init
    def clearDevice(self):
        printDbg("HW: Clearing HW device...")
        self.api.closeDevice('')
        printOK("HW: device cleared")

    # Status codes:
    # 0 - not connected
    # 1 - not initialized
    # 2 - fine
    @check_api_init
    def getStatus(self):
        printDbg("HW: checking device status...")
        printOK(f"Status: {self.api.status}")
        return self.api.model, self.api.status, self.api.messages[self.api.status]

    def prepare_transfer_tx(self, caller, bip32_path, utxos_to_spend, dest_address, tx_fee, isTestnet=False):
        rewardsArray = []
        mnode = {
            'path': bip32_path,
            'utxos': utxos_to_spend
        }
        rewardsArray.append(mnode)
        self.prepare_transfer_tx_bulk(caller, rewardsArray, dest_address, tx_fee, isTestnet)

    @check_api_init
    def prepare_transfer_tx_bulk(self, caller, rewardsArray, dest_address, tx_fee, isTestnet=False):
        printDbg("HW: Preparing transfer TX")
        self.api.prepare_transfer_tx_bulk(caller, rewardsArray, dest_address, tx_fee, isTestnet)

    @check_api_init
    def scanForAddress(self, hwAcc, spath, intExt=0, isTestnet=False):
        printOK(f"HW: Scanning for Address n. {spath} on account n. {hwAcc}")
        return self.api.scanForAddress(hwAcc, spath, intExt, isTestnet)

    @check_api_init
    def scanForBip32(self, account, address, starting_spath=0, spath_count=10, isTestnet=False):
        printOK(f"HW: Scanning for Bip32 path of address: {address}")
        found = False
        spath = -1

        for i in range(starting_spath, starting_spath + spath_count):
            printDbg(f"HW: checking path... {account}'/0/{i}")
            curr_addr = self.api.scanForAddress(account, i, isTestnet)

            if curr_addr == address:
                found = True
                spath = i
                break

            sleep(0.01)

        return found, spath

    @check_api_init
    def scanForPubKey(self, account, spath, isTestnet=False):
        printOK(f"HW: Scanning for PubKey of address n. {spath} on account n. {account}")
        return self.api.scanForPubKey(account, spath, isTestnet)

    @check_api_init
    def signMess(self, caller, path, message, isTestnet=False):
        printDbg("HW: Signing message...")
        self.api.signMess(caller, path, message, isTestnet)
        printOK("HW: Message signed")
