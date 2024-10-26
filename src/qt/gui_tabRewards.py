#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

import sys
import os.path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QHBoxLayout, QGroupBox, QVBoxLayout, QLineEdit, QComboBox,
    QProgressBar, QLabel, QFormLayout, QDoubleSpinBox, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QSpinBox
)

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))


class TabRewardsGui(QWidget):
    def __init__(self, imgDir, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.imgDir = imgDir
        self.initRewardsForm()
        mainVertical = QVBoxLayout()
        mainVertical.addWidget(self.rewardsForm)
        buttonbox = QHBoxLayout()
        buttonbox.addStretch(1)
        buttonbox.addWidget(self.btn_Cancel)
        mainVertical.addLayout(buttonbox)
        self.setLayout(mainVertical)

    def initRewardsForm(self):
        self.rewardsForm = QGroupBox()
        layout = QFormLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(13)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # --- ROW 1
        line1 = QHBoxLayout()
        line1.addWidget(QLabel("Account HW"))
        self.edt_hwAccount = QSpinBox()
        self.edt_hwAccount.setMaximum(9999)
        self.edt_hwAccount.setFixedWidth(50)
        self.edt_hwAccount.setToolTip("account number of the hardware wallet.\nIf unsure put 0")
        self.edt_hwAccount.setValue(0)
        line1.addWidget(self.edt_hwAccount)
        line1.addWidget(QLabel("spath from"))
        self.edt_spathFrom = QSpinBox()
        self.edt_spathFrom.setMaximum(9999)
        self.edt_spathFrom.setFixedWidth(50)
        self.edt_spathFrom.setToolTip("starting address n.")
        self.edt_spathFrom.setValue(0)
        line1.addWidget(self.edt_spathFrom)
        line1.addWidget(QLabel("spath to"))
        self.edt_spathTo = QSpinBox()
        self.edt_spathTo.setMaximum(9999)
        self.edt_spathTo.setFixedWidth(50)
        self.edt_spathTo.setToolTip("ending address n.")
        self.edt_spathTo.setValue(10)
        line1.addWidget(self.edt_spathTo)
        line1.addWidget(QLabel("internal/external"))
        self.edt_internalExternal = QSpinBox()
        self.edt_internalExternal.setFixedWidth(50)
        self.edt_internalExternal.setToolTip("ending address n.")
        self.edt_internalExternal.setValue(0)
        self.edt_internalExternal.setMaximum(1)
        line1.addWidget(self.edt_internalExternal)
        line1.addStretch(1)
        self.btn_reload = QPushButton("Load/Refresh")
        self.btn_reload.setToolTip("Reload data from ledger device")
        line1.addWidget(self.btn_reload)
        layout.addRow(line1)

        #  --- ROW 2: address and copy btn
        hBox = QHBoxLayout()
        self.addySelect = QComboBox()
        self.addySelect.setToolTip("Select Address")
        hBox.addWidget(self.addySelect)
        self.btn_Copy = QPushButton()
        self.btn_Copy.setMaximumWidth(45)
        self.btn_Copy.setToolTip("Copy address to clipboard")
        hBox.addWidget(self.btn_Copy)
        layout.addRow(hBox)

        #  --- ROW 3: UTXOs
        self.rewardsList = QVBoxLayout()
        self.rewardsList.statusLabel = QLabel('<b style="color:red">Reload Rewards</b>')
        self.rewardsList.statusLabel.setVisible(True)
        self.rewardsList.addWidget(self.rewardsList.statusLabel)
        self.rewardsList.box = QTableWidget()
        self.rewardsList.box.setMinimumHeight(230)
        self.rewardsList.box.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.rewardsList.box.setSelectionMode(QAbstractItemView.MultiSelection)
        self.rewardsList.box.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rewardsList.box.setShowGrid(True)
        self.rewardsList.box.setColumnCount(4)
        self.rewardsList.box.setRowCount(0)
        self.rewardsList.box.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.rewardsList.box.verticalHeader().hide()

        item = QTableWidgetItem()
        item.setText("PIVs")
        item.setTextAlignment(Qt.AlignCenter)
        self.rewardsList.box.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem()
        item.setText("Confirmations")
        item.setTextAlignment(Qt.AlignCenter)
        self.rewardsList.box.setHorizontalHeaderItem(1, item)
        item = QTableWidgetItem()
        item.setText("TX Hash")
        item.setTextAlignment(Qt.AlignCenter)
        self.rewardsList.box.setHorizontalHeaderItem(2, item)
        item = QTableWidgetItem()
        item.setText("TX Output N")
        item.setTextAlignment(Qt.AlignCenter)
        self.rewardsList.box.setHorizontalHeaderItem(3, item)

        self.rewardsList.addWidget(self.rewardsList.box)
        layout.addRow(self.rewardsList)

        # --- ROW 3
        hBox2 = QHBoxLayout()
        self.btn_selectAllRewards = QPushButton("Select All")
        self.btn_selectAllRewards.setToolTip("Select all available UTXOs")
        hBox2.addWidget(self.btn_selectAllRewards)
        self.btn_deselectAllRewards = QPushButton("Deselect All")
        self.btn_deselectAllRewards.setToolTip("Deselect current selection")
        hBox2.addWidget(self.btn_deselectAllRewards)
        hBox2.addWidget(QLabel("Selected UTXOs"))
        self.selectedRewardsLine = QLabel()
        self.selectedRewardsLine.setMinimumWidth(200)
        self.selectedRewardsLine.setStyleSheet("color: purple")
        self.selectedRewardsLine.setToolTip("PIVX to move away")
        hBox2.addWidget(self.selectedRewardsLine)
        hBox2.addStretch(1)
        layout.addRow(hBox2)

        # --- ROW 4
        hBox3 = QHBoxLayout()
        self.destinationLine = QLineEdit()
        self.destinationLine.setToolTip("PIVX address to send PIV to")
        hBox3.addWidget(self.destinationLine)
        hBox3.addWidget(QLabel("Fee"))
        self.feeLine = QDoubleSpinBox()
        self.feeLine.setDecimals(8)
        self.feeLine.setPrefix("PIV  ")
        self.feeLine.setToolTip("Insert a small fee amount")
        self.feeLine.setFixedWidth(150)
        self.feeLine.setSingleStep(0.001)
        hBox3.addWidget(self.feeLine)
        self.btn_sendRewards = QPushButton("Send")
        hBox3.addWidget(self.btn_sendRewards)
        layout.addRow(QLabel("Destination Address"), hBox3)

        hBox4 = QHBoxLayout()
        hBox4.addStretch(1)
        self.loadingLine = QLabel("<b style='color:red'>Preparing TX.</b> Completed: ")
        self.loadingLinePercent = QProgressBar()
        self.loadingLinePercent.setMaximumWidth(200)
        self.loadingLinePercent.setMaximumHeight(10)
        self.loadingLinePercent.setRange(0, 100)
        hBox4.addWidget(self.loadingLine)
        hBox4.addWidget(self.loadingLinePercent)
        self.loadingLine.hide()
        self.loadingLinePercent.hide()
        layout.addRow(hBox4)

        # --- Set Layout
        self.rewardsForm.setLayout(layout)

        # --- ROW 5
        self.btn_Cancel = QPushButton("Clear")

    def resetStatusLabel(self, message=None):
        if message is None:
            self.rewardsList.statusLabel.setText('<em><b style="color:purple">Checking explorer...</b></em>')
        else:
            self.rewardsList.statusLabel.setText(message)
        self.rewardsList.statusLabel.setVisible(True)
