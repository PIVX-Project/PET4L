#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

import threading
import simplejson as json

from PyQt5.Qt import QApplication, Qt
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QHeaderView

from constants import MINIMUM_FEE
from misc import printDbg, printError, printException, getCallerName, getFunctionName, \
    persistCacheSetting, myPopUp, myPopUp_sb, DisconnectedException, checkTxInputs
from pivx_parser import ParseTx, IsPayToColdStaking, GetDelegatedStaker
from qt.gui_tabRewards import TabRewardsGui
from threads import ThreadFuns
from txCache import TxCache
from utils import checkPivxAddr


class TabRewards:
    def __init__(self, caller):
        self.caller = caller
        # --- Lock for loading UTXO thread
        self.runInThread = ThreadFuns.runInThread
        self.Lock = threading.Lock()

        # --- Initialize Selection
        self.selectedRewards = None
        self.feePerKb = MINIMUM_FEE
        self.suggestedFee = MINIMUM_FEE

        # --- Initialize GUI
        self.ui = TabRewardsGui(self.caller.imgDir)
        self.caller.tabRewards = self.ui
        self.ui.btn_Copy.setIcon(self.caller.copy_icon)

        # load cache
        self.ui.destinationLine.setText(self.caller.parent.cache.get("lastAddress"))
        self.ui.edt_hwAccount.setValue(self.caller.parent.cache["hwAcc"])
        self.ui.edt_spathFrom.setValue(self.caller.parent.cache["spathFrom"])
        self.ui.edt_spathTo.setValue(self.caller.parent.cache["spathTo"])
        self.ui.edt_internalExternal.setValue(self.caller.parent.cache["intExt"])

        self.updateFee()

        # Connect GUI buttons
        self.ui.addySelect.currentIndexChanged.connect(self.onChangeSelected)
        self.ui.rewardsList.box.itemClicked.connect(self.updateSelection)
        self.ui.btn_reload.clicked.connect(self.loadSelection)
        self.ui.btn_selectAllRewards.clicked.connect(self.onSelectAllRewards)
        self.ui.btn_deselectAllRewards.clicked.connect(self.onDeselectAllRewards)
        self.ui.btn_sendRewards.clicked.connect(self.onSendRewards)
        self.ui.btn_Cancel.clicked.connect(self.onCancel)
        self.ui.btn_Copy.clicked.connect(self.onCopy)

        # Connect Signals
        self.caller.sig_UTXOsLoading.connect(self.update_loading_utxos)

    def display_utxos(self):
        # update fee
        if self.caller.rpcConnected:
            self.feePerKb = self.caller.rpcClient.getFeePerKb()
            if self.feePerKb is None:
                self.feePerKb = MINIMUM_FEE
        else:
            self.feePerKb = MINIMUM_FEE

        rewards = self.caller.parent.db.getRewardsList(self.curr_addr)

        if rewards is not None:
            def item(value: str) -> QTableWidgetItem:
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                return item

            # Clear up old list
            self.ui.rewardsList.box.setRowCount(0)
            # Make room for new list
            self.ui.rewardsList.box.setRowCount(len(rewards))
            # Insert items
            for row, utxo in enumerate(rewards):
                txId = utxo.get('txid', None)
                pivxAmount = round(int(utxo.get('satoshis', 0)) / 1e8, 8)
                self.ui.rewardsList.box.setItem(row, 0, item(str(pivxAmount)))
                self.ui.rewardsList.box.setItem(row, 1, item(str(utxo.get('confirmations', None))))
                self.ui.rewardsList.box.setItem(row, 2, item(txId))
                self.ui.rewardsList.box.setItem(row, 3, item(str(utxo.get('vout', None))))
                self.ui.rewardsList.box.showRow(row)
                if utxo['staker'] != "":
                    self.ui.rewardsList.box.item(row, 2).setIcon(self.caller.coldStaking_icon)
                    self.ui.rewardsList.box.item(row, 2).setToolTip(f"Staked by <b>{utxo['staker']}</b>")

                # make immature rewards unselectable
                if utxo['coinstake']:
                    required = 16 if self.caller.isTestnetRPC else 101
                    if utxo['confirmations'] < required:
                        for i in range(4):
                            self.ui.rewardsList.box.item(row, i).setFlags(Qt.NoItemFlags)
                            ttip = self.ui.rewardsList.box.item(row, i).toolTip()
                            self.ui.rewardsList.box.item(row, i).setToolTip(
                                ttip + f"\n(Immature - {required} confirmations required)")

            self.ui.rewardsList.box.resizeColumnsToContents()

            if len(rewards) > 0:
                self.ui.rewardsList.statusLabel.setVisible(False)
                self.ui.rewardsList.box.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

            else:
                if not self.caller.rpcConnected:
                    self.ui.resetStatusLabel('<b style="color:red">PIVX wallet not connected</b>')
                else:
                    self.ui.resetStatusLabel(f'<b style="color:red">Found no Rewards for {self.curr_addr}</b>')

    def getSelection(self) -> list:
        # Get selected rows indexes
        items = self.ui.rewardsList.box.selectedItems()
        rows = {item.row() for item in items}
        indexes = list(rows)
        # Get UTXO info from DB for each
        selection = []
        for idx in indexes:
            txid = self.ui.rewardsList.box.item(idx, 2).text()
            txidn = int(self.ui.rewardsList.box.item(idx, 3).text())
            selection.append(self.caller.parent.db.getReward(txid, txidn))

        return selection

    def loadSelection(self):
        # Check dongle
        printDbg("Checking HW device")
        if self.caller.hwStatus != 2:
            myPopUp_sb(self.caller, "crit", 'PET4L - hw device check', "Connect to HW device first")
            printDbg(f"Unable to connect - hw status: {self.caller.hwStatus}")
            return None

        self.ui.addySelect.clear()
        ThreadFuns.runInThread(self.loadSelection_thread, ())

    def loadSelection_thread(self, ctrl):
        hwAcc = self.ui.edt_hwAccount.value()
        spathFrom = self.ui.edt_spathFrom.value()
        spathTo = self.ui.edt_spathTo.value()
        intExt = self.ui.edt_internalExternal.value()
        isTestnet = self.caller.isTestnetRPC

        # Save settings
        self.caller.parent.cache["hwAcc"] = persistCacheSetting('cache_hwAcc', hwAcc)
        self.caller.parent.cache["spathFrom"] = persistCacheSetting('cache_spathFrom', spathFrom)
        self.caller.parent.cache["spathTo"] = persistCacheSetting('cache_spathTo', spathTo)
        self.caller.parent.cache["intExt"] = persistCacheSetting('cache_intExt', intExt)

        for i in range(spathFrom, spathTo + 1):
            path = f"{hwAcc}'/{intExt}/{i}"
            address = self.caller.hwdevice.scanForAddress(hwAcc, i, intExt, isTestnet)
            try:
                balance = self.caller.apiClient.getBalance(address)
            except Exception as e:
                print(e)
                balance = 0

            itemLine = f"{path}  --  {address}"
            if balance:
                itemLine += f"   [{balance} PIV]"

            self.ui.addySelect.addItem(itemLine, [path, address, balance])

    def load_utxos_thread(self, ctrl):
        with self.Lock:
            # clear utxos DB
            printDbg("Updating UTXOs...")
            self.caller.parent.db.clearTable('UTXOS')

            if not self.caller.rpcConnected:
                printError(getCallerName(), getFunctionName(), 'PIVX daemon not connected - Unable to update UTXO list')
                return

            utxos = self.caller.apiClient.getAddressUtxos(self.curr_addr)
            total_num_of_utxos = len(utxos)

            curr_utxo = 0
            for u in utxos:
                u['receiver'] = self.curr_addr
                # Get raw tx
                u['rawtx'] = TxCache(self.caller)[u['txid']]
                if u['rawtx'] is None:
                    printDbg(f"Unable to get raw TX with hash={u['txid']} from RPC server.")
                    # Don't save UTXO if raw TX is unavailable
                    utxos.remove(u)
                u['staker'] = ""
                p2cs, u['coinstake'] = IsPayToColdStaking(u['rawtx'], u['vout'])
                if p2cs:
                    u['staker'] = GetDelegatedStaker(u['rawtx'], u['vout'], self.caller.isTestnetRPC)

                # Save utxo to db
                self.caller.parent.db.addReward(u)

                # emit percent
                percent = int(100 * curr_utxo / total_num_of_utxos)
                self.caller.sig_UTXOsLoading.emit(percent)
                curr_utxo += 1

            printDbg("--# REWARDS table updated")
            self.caller.sig_UTXOsLoading.emit(100)

    def onCancel(self):
        self.ui.rewardsList.box.clearSelection()
        self.selectedRewards = None
        self.ui.selectedRewardsLine.setText("0.0")
        self.suggestedFee = MINIMUM_FEE
        self.updateFee()
        self.AbortSend()

    def onCopy(self):
        if self.ui.addySelect.count() == 0:
            mess = "Nothing to copy. Load/Refresh addresses first."
            myPopUp_sb(self.caller, QMessageBox.Warning, 'PET4L - no address', mess)
            return
        cb = QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        ct = self.ui.addySelect.currentText()
        addy = ct.split("  --  ")[1].split("   ")[0].strip()
        cb.setText(addy, mode=cb.Clipboard)
        myPopUp_sb(self.caller, QMessageBox.Information, 'PET4L - copied', "address copied to the clipboard")

    def onChangeSelected(self):
        if self.ui.addySelect.currentIndex() >= 0:
            self.ui.resetStatusLabel()
            self.curr_path = self.ui.addySelect.itemData(self.ui.addySelect.currentIndex())[0]
            self.curr_addr = self.ui.addySelect.itemData(self.ui.addySelect.currentIndex())[1]
            self.curr_balance = self.ui.addySelect.itemData(self.ui.addySelect.currentIndex())[2]

            if self.curr_balance is not None:
                self.runInThread = ThreadFuns.runInThread(self.load_utxos_thread, (), self.display_utxos)

    def onSelectAllRewards(self):
        self.ui.rewardsList.box.selectAll()
        self.updateSelection()

    def onDeselectAllRewards(self):
        self.ui.rewardsList.box.clearSelection()
        self.updateSelection()

    def onSendRewards(self):
        self.dest_addr = self.ui.destinationLine.text().strip()
        self.currFee = self.ui.feeLine.value() * 1e8

        # Check HW device
        while self.caller.hwStatus != 2:
            mess = "HW device not connected. Try to connect?"
            ans = myPopUp(self.caller, QMessageBox.Question, 'PET4L - hw check', mess)
            if ans == QMessageBox.No:
                return
            # re connect
            self.caller.onCheckHw()
        if self.caller.hwStatus != 2:
            myPopUp_sb(self.caller, "crit", 'PET4L - hw device check', "Connect to HW device first")
            printDbg(f"Unable to connect to hardware device. The device status is: {self.caller.hwStatus}")
            return None

        # SEND
        self.SendRewards()

    def SendRewards(self, inputs=None, gui=None):
        # Default slots on tabRewards
        if gui is None:
            gui = self

        # re-connect signals
        try:
            self.caller.hwdevice.api.sigTxdone.disconnect()
        except Exception:
            pass
        try:
            self.caller.hwdevice.api.sigTxabort.disconnect()
        except Exception:
            pass
        try:
            self.caller.hwdevice.api.tx_progress.disconnect()
        except Exception:
            pass
        self.caller.hwdevice.api.sigTxdone.connect(gui.FinishSend)
        self.caller.hwdevice.api.sigTxabort.connect(gui.AbortSend)
        self.caller.hwdevice.api.tx_progress.connect(gui.updateProgressPercent)

        # Check destination Address
        if not checkPivxAddr(self.dest_addr, self.caller.isTestnetRPC):
            myPopUp_sb(self.caller, "crit", 'PET4L - PIVX address check', "The destination address is missing, or invalid.")
            return None

        if inputs is None:
            # send from single path
            num_of_inputs = len(self.selectedRewards)
        else:
            # bulk send
            num_of_inputs = sum(len(x['utxos']) for x in inputs)
        ans = checkTxInputs(self.caller, num_of_inputs)
        if ans is None or ans == QMessageBox.No:
            # emit sigTxAbort and return
            self.caller.hwdevice.api.sigTxabort.emit()
            return None

        # LET'S GO
        if inputs is None:
            printDbg(f"Sending from PIVX address  {self.curr_addr}  to PIVX address  {self.dest_addr} ")
        else:
            printDbg(f"Sweeping rewards to PIVX address {self.dest_addr} ")
        self.ui.rewardsList.statusLabel.hide()
        printDbg("Preparing transaction. Please wait...")
        self.ui.loadingLine.show()
        self.ui.loadingLinePercent.show()
        QApplication.processEvents()

        # save last destination address and swiftxCheck to cache and persist to settings
        self.caller.parent.cache["lastAddress"] = persistCacheSetting('cache_lastAddress', self.dest_addr)

        try:
            self.txFinished = False
            if inputs is None:
                # send from single path
                self.caller.hwdevice.prepare_transfer_tx(self.caller,
                                                         self.curr_path,
                                                         self.selectedRewards,
                                                         self.dest_addr,
                                                         self.currFee,
                                                         self.caller.isTestnetRPC)
            else:
                # bulk send
                self.caller.hwdevice.prepare_transfer_tx_bulk(self.caller,
                                                              inputs,
                                                              self.dest_addr,
                                                              self.currFee,
                                                              self.caller.isTestnetRPC)

        except DisconnectedException:
            self.caller.hwStatus = 0
            self.caller.updateHWleds()

        except Exception as e:
            err_msg = "Error while preparing transaction. <br>"
            err_msg += "Probably Blockchain wasn't synced when trying to fetch raw TXs.<br>"
            err_msg += "<b>Wait for full synchronization</b> then hit 'Load/Refresh'"
            printException(getCallerName(), getFunctionName(), err_msg, e.args)

    def removeSpentRewards(self):
        for utxo in self.selectedRewards:
            self.caller.parent.db.deleteReward(utxo['txid'], utxo['vout'])

    # Activated by signal sigTxdone from hwdevice
    def FinishSend(self, serialized_tx, amount_to_send):
        self.AbortSend()
        if not self.txFinished:
            try:
                self.txFinished = True
                tx_hex = serialized_tx.hex()
                printDbg("Raw signed transaction: " + tx_hex)
                printDbg("Amount to send :" + amount_to_send)

                if len(tx_hex) > 90000:
                    mess = "Transaction's length exceeds 90000 bytes. Select less UTXOs and try again."
                    self.caller.myPopUp2(QMessageBox.Warning, 'transaction Warning', mess)

                else:
                    decodedTx = None
                    try:
                        decodedTx = ParseTx(tx_hex, self.caller.isTestnetRPC)
                        destination = decodedTx.get("vout")[0].get("scriptPubKey").get("addresses")[0]
                        amount = decodedTx.get("vout")[0].get("value")
                        message = f'<p>Broadcast signed transaction?</p><p>Destination address:<br><b>{destination}</b></p>'
                        message += f'<p>Amount: <b>{round(amount / 1e8, 8)}</b> PIV<br>'
                        message += f'Fees: <b>{round(self.currFee / 1e8, 8)}</b> PIV <br>Size: <b>{len(tx_hex) / 2}</b> Bytes</p>'
                    except Exception as e:
                        printException(getCallerName(), getFunctionName(), "decoding exception", str(e))
                        message = '<p>Unable to decode TX- Broadcast anyway?</p>'

                    mess1 = QMessageBox(QMessageBox.Information, 'Send transaction', message)
                    if decodedTx is not None:
                        mess1.setDetailedText(json.dumps(decodedTx, indent=4, sort_keys=False))
                    mess1.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

                    reply = mess1.exec_()
                    if reply == QMessageBox.Yes:
                        txid = self.caller.rpcClient.sendRawTransaction(tx_hex)
                        if txid is None:
                            raise Exception("Unable to send TX - connection to RPC server lost.")
                        printDbg(f"Transaction sent. ID: {txid}")
                        mess2_text = "<p>Transaction successfully sent.</p>"
                        mess2 = QMessageBox(QMessageBox.Information, 'transaction Sent', mess2_text)
                        mess2.setDetailedText(txid)
                        mess2.exec_()
                        # remove spent rewards from DB
                        self.removeSpentRewards()
                        # reload utxos
                        self.display_utxos()
                        self.onCancel()

                    else:
                        myPopUp_sb(self.caller, "warn", 'Transaction NOT sent', "Transaction NOT sent")
                        self.onCancel()

            except Exception as e:
                err_msg = "Exception in FinishSend"
                printException(getCallerName(), getFunctionName(), err_msg, e.args)

    # Activated by signal sigTxabort from hwdevice
    def AbortSend(self):
        self.ui.loadingLine.hide()
        self.ui.loadingLinePercent.setValue(0)
        self.ui.loadingLinePercent.hide()

    def updateFee(self):
        self.ui.feeLine.setValue(self.suggestedFee)
        self.ui.feeLine.setEnabled(True)

    # Activated by signal tx_progress from hwdevice
    def updateProgressPercent(self, percent):
        self.ui.loadingLinePercent.setValue(percent)
        QApplication.processEvents()

    def updateSelection(self, clicked_item=None):
        total = 0
        self.selectedRewards = self.getSelection()
        numOfInputs = len(self.selectedRewards)
        if numOfInputs:
            for reward in self.selectedRewards:
                total += int(reward.get('satoshis'))

            # update suggested fee and selected rewards
            estimatedTxSize = (44 + numOfInputs * 148) * 1.0 / 1000  # kB
            feePerKb = self.caller.rpcClient.getFeePerKb()
            self.suggestedFee = round(feePerKb * estimatedTxSize, 8)
            printDbg(f"estimatedTxSize is {estimatedTxSize} kB")
            printDbg(f"suggested fee is {self.suggestedFee} PIV ({feePerKb} PIV/kB)")

            self.ui.selectedRewardsLine.setText(str(round(total / 1e8, 8)))

        else:
            self.ui.selectedRewardsLine.setText("")

        self.updateFee()

    def update_loading_utxos(self, percent):
        if percent < 100:
            self.ui.resetStatusLabel(f'<em><b style="color:purple">Checking explorer... {percent}%</b></em>')
        else:
            self.display_utxos()
