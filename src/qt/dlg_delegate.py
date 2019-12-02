#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from misc import myPopUp, myPopUp_sb, getCallerName, getFunctionName, printException
from pivx_hashlib import pubkey_to_address
from threads import ThreadFuns
from utils import checkPivxAddr, ecdsa_verify_addr

class Delegate_dlg(QDialog):
    def __init__(self, tabRewards):
        QDialog.__init__(self, parent=tabRewards.caller)
        self.tabRewards = tabRewards
        self.setWindowTitle('Delegate coins for Cold Staking')
        self.initUI(tabRewards.caller)
        self.loadAmounts()
        self.loadAddresses()

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
        self.btn_delegate = QPushButton("Send delegation")
        hBox2 = QHBoxLayout()
        hBox2.addStretch(1)
        hBox2.addWidget(self.btn_delegate)
        layout.addRow(hBox2)
        self.layout.addLayout(layout)