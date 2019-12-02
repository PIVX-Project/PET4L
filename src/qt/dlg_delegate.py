#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from misc import getCallerName, getFunctionName, printException, persistCacheSetting, \
    redirect_print, DisconnectedException


class Delegate_dlg(QDialog):
    def __init__(self, tabRewards):
        QDialog.__init__(self, parent=tabRewards.caller)
        self.tabRewards = tabRewards
        self.setWindowTitle('Delegate coins for Cold Staking')
        self.initUI(tabRewards.caller)
        self.loadAmounts()
        self.loadAddresses()
        # connect ui buttons
        self.ui.btn_delegate.clicked.connect(lambda: self.onSend())
        self.ui.btn_cancel.clicked.connect(lambda: self.onCancel())


    def initUI(self, main_wnd):
        self.ui = Ui_DelegateDlg()
        self.ui.setupUi(self, main_wnd)


    def loadAmounts(self):
        self.ui.selectedRewardsLine.setText(self.tabRewards.ui.selectedRewardsLine.text())
        self.ui.feeLine.setText(self.tabRewards.ui.feeLine.text())


    def loadAddresses(self):
        comboBox = self.ui.comboBox_ownerAddress
        adds = []
        for x in self.tabRewards.selectedRewards:
            if x['receiver'] not in adds:
                adds.append(x['receiver'])
        comboBox.addItems(adds)
        # load last used destinations from cache
        self.ui.lineEdt_stakerAddress.setText(
            self.tabRewards.caller.parent.cache.get("lastStakerAddress"))


    def onCancel(self):
        # close dialog
        self.close()


    def onSend(self):
        owner_address = self.ui.comboBox_ownerAddress.itemText(self.ui.comboBox_ownerAddress.currentIndex())
        staker_address = self.ui.lineEdt_stakerAddress.text()
        # !TODO: check staker address
        self.tabRewards.caller.parent.cache["lastStakerAddress"] = persistCacheSetting(
            'cache_lastStakerAddress', staker_address)

        # Let's go
        try:
            self.tabRewards.ui.loadingLine.show()
            self.tabRewards.ui.loadingLinePercent.show()
            QApplication.processEvents()
            self.tabRewards.currFee = self.tabRewards.ui.feeLine.value() * 1e8
            # re-connect signals
            try:
                self.tabRewards.caller.hwdevice.api.sigTxdone.disconnect()
            except:
                pass
            try:
                self.tabRewards.caller.hwdevice.api.sigTxabort.disconnect()
            except:
                pass
            try:
                self.tabRewards.caller.hwdevice.api.tx_progress.disconnect()
            except:
                pass
            self.tabRewards.caller.hwdevice.api.sigTxdone.connect(self.tabRewards.FinishSend)
            self.tabRewards.caller.hwdevice.api.sigTxabort.connect(self.tabRewards.AbortSend)
            self.tabRewards.caller.hwdevice.api.tx_progress.connect(self.tabRewards.updateProgressPercent)

            try:
                self.tabRewards.txFinished = False
                self.tabRewards.caller.hwdevice.prepare_transfer_tx(self.tabRewards.caller,
                                                                    self.tabRewards.curr_path,
                                                                    self.tabRewards.selectedRewards,
                                                                    owner_address,
                                                                    self.tabRewards.currFee,
                                                                    self.tabRewards.useSwiftX(),
                                                                    self.tabRewards.caller.isTestnetRPC,
                                                                    staker_address)

            except DisconnectedException as e:
                self.tabRewards.caller.hwStatus = 0
                self.tabRewards.caller.updateHWleds()

            except Exception as e:
                err_msg = "Error while preparing transaction. <br>"
                err_msg += "Probably Blockchain wasn't synced when trying to fetch raw TXs.<br>"
                err_msg += "<b>Wait for full synchronization</b> then hit 'Clear/Reload'"
                printException(getCallerName(), getFunctionName(), err_msg, e.args)
        except Exception as e:
            redirect_print(e)


class Ui_DelegateDlg(object):
    def setupUi(self, DelegateDlg, main_wnd):
        DelegateDlg.setModal(True)
        DelegateDlg.setMinimumWidth(600)
        DelegateDlg.setMinimumHeight(190)
        self.layout = QVBoxLayout(DelegateDlg)
        layout = QFormLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(13)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        hBox = QHBoxLayout()
        self.selectedRewardsLine = QLabel()
        self.selectedRewardsLine.setMinimumWidth(200)
        self.selectedRewardsLine.setStyleSheet("color: purple")
        self.selectedRewardsLine.setToolTip("PIVX to delegate for cold staking")
        hBox.addWidget(self.selectedRewardsLine)
        hBox.addStretch(1)
        hBox.addWidget(QLabel("Fee"))
        self.feeLine = QLabel()
        self.feeLine.setMinimumWidth(200)
        self.feeLine.setStyleSheet("color: purple")
        self.feeLine.setToolTip("fee required to send the delegation")
        hBox.addWidget(self.feeLine)
        layout.addRow(QLabel("Selected amount"), hBox)
        self.lineEdt_stakerAddress = QLineEdit()
        self.lineEdt_stakerAddress.setToolTip("PIVX Staking address to delegate to")
        layout.addRow(QLabel("Staker address"), self.lineEdt_stakerAddress)
        self.comboBox_ownerAddress = QComboBox()
        self.comboBox_ownerAddress.setToolTip("Select owner address")
        layout.addRow(QLabel("Owner address"), self.comboBox_ownerAddress)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_delegate = QPushButton("Send delegation")
        self.btn_delegate.setFocus()
        hBox2 = QHBoxLayout()
        hBox2.addStretch(1)
        hBox2.addWidget(self.btn_cancel)
        hBox2.addWidget(self.btn_delegate)
        layout.addRow(hBox2)
        self.layout.addLayout(layout)