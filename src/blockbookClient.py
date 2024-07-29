#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

import requests

from misc import getCallerName, getFunctionName, printException, myPopUp, printDbg

def process_blockbook_exceptions(func):
    def process_blockbook_exceptions_int(*args, **kwargs):
        client = args[0]
        try:
            return func(*args, **kwargs)
        except Exception as e:
            message = "BlockBook Client exception on %s" % (client.url)
            printException(getCallerName(True), getFunctionName(True), message, str(e))
            myPopUp(None, QMessageBox.Critical, "Explorer Error", "Failed to connect to Explorer URL: %s\n%s" % (client.url, str(e)))
            raise

    return process_blockbook_exceptions_int


class BlockBookClient:
    def __init__(self, main_wnd, isTestnet=False):
        self.main_wnd = main_wnd
        self.isTestnet = isTestnet
        self.url = ""
        self.loadURL()

    def loadURL(self):
        if self.isTestnet:
            self.url = self.main_wnd.getExplorerURL('testnet')
        else:
            self.url = self.main_wnd.getExplorerURL('mainnet')
        printDbg(f"Using Explorer URL: {self.url}")

    def checkResponse(self, method, param=""):
        url = self.url + "/api/%s" % method
        if param != "":
            url += "/%s" % param
        resp = requests.get(url, data={}, verify=True)
        if resp.status_code == 200:
            data = resp.json()
            return data
        raise Exception("Invalid response")

    @process_blockbook_exceptions
    def getAddressUtxos(self, address):
        utxos = self.checkResponse("utxo", address)
        for u in utxos:
            u["script"] = ""
        return utxos

    @process_blockbook_exceptions
    def getBalance(self, address):
        return self.checkResponse("address", address)["balance"]
