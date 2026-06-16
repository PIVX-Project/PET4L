#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

import requests
from misc import getCallerName, getFunctionName, printException, printDbg


def process_blockbook_exceptions(func):
    def process_blockbook_exceptions_int(*args, **kwargs):
        client = args[0]
        try:
            return func(*args, **kwargs)
        except Exception as e:
            message = "BlockBook Client exception on %s" % client.url
            printException(getCallerName(True), getFunctionName(True), message, str(e))
            # Primary explorer failed: retry against the other explorers
            # configured for this network (e.g. zkbitcoin) before giving up.
            for new_url in client.getFallbackUrls():
                printDbg("Trying backup explorer %s" % new_url)
                try:
                    client.url = new_url
                    return func(*args, **kwargs)
                except Exception:
                    continue
            # All explorers failed: re-raise so ApiClient can fall back further.
            raise

    return process_blockbook_exceptions_int


class BlockBookClient:
    def __init__(self, main_wnd, isTestnet=False):
        self.main_wnd = main_wnd
        self.isTestnet = isTestnet
        self.url = ""
        self.loadURL()

    def network(self):
        return 'testnet' if self.isTestnet else 'mainnet'

    def loadURL(self):
        self.url = self.main_wnd.getExplorerURL(self.network())
        printDbg(f"Using Explorer URL: {self.url}")

    def getFallbackUrls(self):
        # Return the other explorer URLs for this network (current one excluded).
        try:
            urls = self.main_wnd.getExplorerURLList(self.network())
        except Exception:
            return []
        return [u for u in urls if u != self.url]

    def updateBaseUrl(self, new_url):
        # Update the explorer URL
        self.url = new_url
        printDbg(f"Explorer URL updated to: {self.url}")

    def checkResponse(self, method, param=""):
        # rstrip avoids a double slash when the URL already ends with '/'
        url = self.url.rstrip('/') + "/api/%s" % method
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
