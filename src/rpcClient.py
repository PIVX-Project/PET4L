#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

from bitcoinrpc.authproxy import AuthServiceProxy

import http.client as httplib
import ssl
import threading
from typing import Union

from constants import DEFAULT_PROTOCOL_VERSION, MINIMUM_FEE
from misc import getCallerName, getFunctionName, printException, printDbg, now, timeThis


def process_RPC_exceptions(func):
    def process_RPC_exceptions_int(*args, **kwargs):
        try:
            args[0].httpConnection.connect()
            return func(*args, **kwargs)
        except Exception as e:
            message = "Exception in RPC client"
            printException(getCallerName(True), getFunctionName(True), message, str(e))
        finally:
            try:
                args[0].httpConnection.close()
            except Exception as e:
                printDbg(e)
                pass

    return process_RPC_exceptions_int


class RpcClient:

    def __init__(self, rpc_protocol: str, rpc_host: str, rpc_user: str, rpc_password: str):
        # Lock for threads
        self.lock = threading.RLock()

        self.rpc_url = f"{rpc_protocol}://{rpc_user}:{rpc_password}@{rpc_host}"

        if ":" in rpc_host:
            host, port_str = rpc_host.split(":")
            try:
                port = int(port_str)
            except ValueError:
                raise ValueError(f"Invalid port specified: {port_str}")
        else:
            host = rpc_host
            port = None

        self.httpConnection: Union[httplib.HTTPConnection, httplib.HTTPSConnection]

        if rpc_protocol == "https":
            self.httpConnection = httplib.HTTPSConnection(host, port, timeout=20, context=ssl._create_unverified_context())
        else:
            self.httpConnection = httplib.HTTPConnection(host, port, timeout=20)

        self.conn = AuthServiceProxy(self.rpc_url, timeout=1000, connection=self.httpConnection)

    @process_RPC_exceptions
    def getBlockCount(self) -> int:
        with self.lock:
            return self.conn.getblockcount()

    @process_RPC_exceptions
    def getBlockHash(self, blockNum: int) -> str:
        with self.lock:
            return self.conn.getblockhash(blockNum)

    @process_RPC_exceptions
    def getBudgetVotes(self, proposal: str) -> dict:
        with self.lock:
            return self.conn.getbudgetvotes(proposal)

    @process_RPC_exceptions
    def getFeePerKb(self) -> float:
        with self.lock:
            # get transaction data from last 200 blocks
            feePerKb = float(self.conn.getfeeinfo(200)['feeperkb'])
            return feePerKb if feePerKb > MINIMUM_FEE else MINIMUM_FEE

    @process_RPC_exceptions
    def getMNStatus(self, address: str) -> dict:
        with self.lock:
            mnStatusList = self.conn.listmasternodes(address)
            if not mnStatusList:
                return {}
            mnStatus = mnStatusList[0]
            mnStatus['mnCount'] = self.conn.getmasternodecount()['enabled']
            return mnStatus

    @process_RPC_exceptions
    def getMasternodeCount(self) -> dict:
        with self.lock:
            return self.conn.getmasternodecount()

    @process_RPC_exceptions
    def getMasternodes(self) -> dict:
        printDbg("RPC: Getting masternode list...")
        mnList = {}
        score = []
        with self.lock:
            masternodes = self.conn.listmasternodes()

        for mn in masternodes:
            if mn.get('status') == 'ENABLED':
                # compute masternode score
                if mn.get('lastpaid') == 0:
                    mn['score'] = mn.get('activetime')
                else:
                    lastpaid_ago = now() - mn.get('lastpaid')
                    mn['score'] = min(lastpaid_ago, mn.get('activetime'))
            else:
                mn['score'] = 0

            score.append(mn)

        # sort masternodes by decreasing score
        score.sort(key=lambda x: x['score'], reverse=True)

        # save masternode position in the payment queue
        for mn in masternodes:
            mn['queue_pos'] = score.index(mn)

        mnList['masternodes'] = masternodes

        return mnList

    @process_RPC_exceptions
    def getNextSuperBlock(self) -> int:
        with self.lock:
            return self.conn.getnextsuperblock()

    @process_RPC_exceptions
    def getProposalsProjection(self) -> list:
        printDbg("RPC: Getting proposals projection...")
        proposals = []
        with self.lock:
            # get budget projection JSON data
            data = self.conn.getbudgetprojection()

        for p in data:
            # create proposal-projection dictionary
            new_proposal = {
                'Name': p.get('Name'),
                'Allotted': float(p.get("Alloted")),
                'Votes': p.get('Yeas') - p.get('Nays'),
                'Total_Allotted': float(p.get('TotalBudgetAlloted'))
            }
            # append dictionary to list
            proposals.append(new_proposal)

        # return proposals list
        return proposals

    @process_RPC_exceptions
    def getProtocolVersion(self) -> int:
        with self.lock:
            prot_version = self.conn.getinfo().get('protocolversion')
            return int(prot_version) if prot_version else DEFAULT_PROTOCOL_VERSION

    @process_RPC_exceptions
    def getRawTransaction(self, txid: str) -> str:
        with self.lock:
            return self.conn.getrawtransaction(txid)

    @process_RPC_exceptions
    def getStatus(self) -> tuple[bool, str, int, float, bool]:
        status = False
        statusMess = "Unable to connect to a PIVX RPC server.\nEither the local PIVX wallet is not open, or the remote RPC server is not responding."
        n = 0
        response_time = None
        with self.lock:
            isTestnet = self.conn.getinfo()['testnet']
            n, response_time = timeThis(self.conn.getblockcount)
            if n is None:
                n = 0

        if n > 0:
            status = True
            statusMess = "Connected to PIVX Blockchain"

        return status, statusMess, n, response_time, isTestnet

    @process_RPC_exceptions
    def isBlockchainSynced(self) -> tuple[bool, float]:
        with self.lock:
            status, response_time = timeThis(self.conn.mnsync, 'status')
            if status is not None:
                return status.get("IsBlockchainSynced"), response_time
            return False, response_time

    @process_RPC_exceptions
    def mnBudgetRawVote(self, mn_tx_hash: str, mn_tx_index: int, proposal_hash: str, vote: str, time: int, vote_sig: str) -> str:
        with self.lock:
            return self.conn.mnbudgetrawvote(mn_tx_hash, mn_tx_index, proposal_hash, vote, time, vote_sig)

    @process_RPC_exceptions
    def decodemasternodebroadcast(self, work: str) -> str:
        printDbg("RPC: Decoding masternode broadcast...")
        with self.lock:
            return self.conn.decodemasternodebroadcast(work.strip())

    @process_RPC_exceptions
    def relaymasternodebroadcast(self, work: str) -> str:
        printDbg("RPC: Relaying masternode broadcast...")
        with self.lock:
            return self.conn.relaymasternodebroadcast(work.strip())

    @process_RPC_exceptions
    def sendRawTransaction(self, tx_hex: str) -> str:
        printDbg("RPC: Sending raw transaction...")
        with self.lock:
            return self.conn.sendrawtransaction(tx_hex, True)

    @process_RPC_exceptions
    def verifyMessage(self, pivxaddress: str, signature: str, message: str) -> bool:
        printDbg("RPC: Verifying message...")
        with self.lock:
            return self.conn.verifymessage(pivxaddress, signature, message)
