#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

from PyQt5.QtWidgets import QPushButton, QLabel, QGridLayout, QHBoxLayout, QComboBox, QWidget

from constants import HW_devices
from PyQt5.Qt import QSizePolicy


class GuiHeader(QWidget):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        # --- 1) Check Box
        self.centralBox = QGridLayout()
        self.centralBox.setContentsMargins(0, 0, 0, 0)
        # --- 1a) Select & Check RPC
        label1 = QLabel("PIVX server")
        self.centralBox.addWidget(label1, 0, 0)
        self.rpcClientsBox = QComboBox()
        self.rpcClientsBox.setToolTip("Select RPC server.")
        self.centralBox.addWidget(self.rpcClientsBox, 0, 1)
        self.button_checkRpc = QPushButton("Connect/Update")
        self.button_checkRpc.setToolTip("try to connect to RPC server")
        self.centralBox.addWidget(self.button_checkRpc, 0, 2)
        self.rpcLed = QLabel()
        self.rpcLed.setToolTip(f"{caller.rpcStatusMess}")
        self.rpcLed.setPixmap(caller.ledGrayH_icon)
        self.centralBox.addWidget(self.rpcLed, 0, 3)
        self.lastPingBox = QWidget()
        sp_retain = QSizePolicy()
        sp_retain.setRetainSizeWhenHidden(True)
        self.lastPingBox.setSizePolicy(sp_retain)
        self.lastPingBox.setContentsMargins(0, 0, 0, 0)
        lastPingBoxLayout = QHBoxLayout()
        self.lastPingIcon = QLabel()
        self.lastPingIcon.setToolTip("Last ping server response time.\n(The lower, the better)")
        self.lastPingIcon.setPixmap(caller.connRed_icon)
        lastPingBoxLayout.addWidget(self.lastPingIcon)
        self.responseTimeLabel = QLabel()
        self.responseTimeLabel.setToolTip("Last ping server response time.\n(The lower, the better)")
        lastPingBoxLayout.addWidget(self.responseTimeLabel)
        lastPingBoxLayout.addSpacing(10)
        self.lastBlockIcon = QLabel()
        self.lastBlockIcon.setToolTip("Last ping block number")
        self.lastBlockIcon.setPixmap(caller.lastBlock_icon)
        lastPingBoxLayout.addWidget(self.lastBlockIcon)
        self.lastBlockLabel = QLabel()
        self.lastBlockLabel.setToolTip("Last ping block number")
        lastPingBoxLayout.addWidget(self.lastBlockLabel)
        self.lastPingBox.setLayout(lastPingBoxLayout)
        self.centralBox.addWidget(self.lastPingBox, 0, 4)
        # -- 1b) Select & Check hardware
        label3 = QLabel("Hardware Device")
        self.centralBox.addWidget(label3, 1, 0)
        self.hwDevices = QComboBox()
        self.hwDevices.setToolTip("Select hardware device")
        self.hwDevices.addItems([x[0] for x in HW_devices])
        self.centralBox.addWidget(self.hwDevices, 1, 1)
        self.button_checkHw = QPushButton("Connect")
        self.button_checkHw.setToolTip("try to connect to Hardware Wallet")
        self.centralBox.addWidget(self.button_checkHw, 1, 2)
        self.hwLed = QLabel()
        self.hwLed.setToolTip(f"status: {caller.hwStatusMess}")
        self.hwLed.setPixmap(caller.ledGrayH_icon)
        self.centralBox.addWidget(self.hwLed, 1, 3)
        layout.addLayout(self.centralBox)
        layout.addStretch(1)
        self.setLayout(layout)
