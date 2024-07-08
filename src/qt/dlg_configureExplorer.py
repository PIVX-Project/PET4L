#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2024 Liquid369 (https://github.com/liquid369/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

from PyQt5.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QLabel, \
    QListWidget, QFrame, QFormLayout, QComboBox, QLineEdit, QListWidgetItem, \
    QWidget, QPushButton, QMessageBox

from misc import myPopUp

class ConfigureExplorerServers_dlg(QDialog):
    def __init__(self, main_wnd):
        QDialog.__init__(self, parent=main_wnd)
        self.main_wnd = main_wnd
        self.setWindowTitle('Explorer Servers Configuration')
        self.changing_index = None
        self.initUI()
        self.loadServers()
        self.main_wnd.mainWindow.sig_ExplorerListReloaded.connect(self.loadServers)

    def clearEditFrame(self):
        self.ui.url_edt.clear()

    def initUI(self):
        self.ui = Ui_ConfigureExplorerServersDlg()
        self.ui.setupUi(self)

    def insert_server_list(self, server):
        id = server['id']
        index = self.main_wnd.mainWindow.getExplorerListIndex(server)
        server_line = QWidget()
        server_row = QHBoxLayout()
        server_text = server['url']
        if not server['isCustom']:
            server_text = "<em style='color: purple'>%s</em>" % server_text
        server_row.addWidget(QLabel(server_text))
        server_row.addStretch(1)
        #  -- Edit button
        editBtn = QPushButton()
        editBtn.setIcon(self.main_wnd.mainWindow.editMN_icon)
        editBtn.setToolTip("Edit server configuration")
        if not server['isCustom']:
            editBtn.setDisabled(True)
            editBtn.setToolTip('Default servers are not editable')
        editBtn.clicked.connect(lambda: self.onAddServer(index))
        server_row.addWidget(editBtn)
        #  -- Remove button
        removeBtn = QPushButton()
        removeBtn.setIcon(self.main_wnd.mainWindow.removeMN_icon)
        removeBtn.setToolTip("Remove server configuration")
        if not server['isCustom']:
            removeBtn.setDisabled(True)
            removeBtn.setToolTip('Cannot remove default servers')
        removeBtn.clicked.connect(lambda: self.onRemoveServer(index))
        server_row.addWidget(removeBtn)
        #  --
        server_line.setLayout(server_row)
        self.serverItems[id] = QListWidgetItem()
        self.serverItems[id].setSizeHint(server_line.sizeHint())
        self.ui.serversBox.addItem(self.serverItems[id])
        self.ui.serversBox.setItemWidget(self.serverItems[id], server_line)

    def loadServers(self):
        # Clear serversBox
        self.ui.serversBox.clear()
        # Fill serversBox
        self.serverItems = {}
        for server in self.main_wnd.mainWindow.explorerServersList:
            self.insert_server_list(server)

    def loadEditFrame(self, index):
        server = self.main_wnd.mainWindow.explorerServersList[index]
        self.ui.url_edt.setText(server['url'])

    def onAddServer(self, index=None):
        # Save current index (None for new entry)
        self.changing_index = index
        # Hide 'Add' and 'Close' buttons and disable serversBox
        self.ui.addServer_btn.hide()
        self.ui.close_btn.hide()
        self.ui.serversBox.setEnabled(False)
        # Show edit-frame
        self.ui.editFrame.setHidden(False)
        # If we are adding a new server, clear edit-frame
        if index is None:
            self.clearEditFrame()
        # else pre-load data
        else:
            self.loadEditFrame(index)

    def onCancel(self):
        # Show 'Add' and 'Close' buttons and enable serversBox
        self.ui.addServer_btn.show()
        self.ui.close_btn.show()
        self.ui.serversBox.setEnabled(True)
        # Hide edit-frame
        self.ui.editFrame.setHidden(True)
        # Clear edit-frame
        self.clearEditFrame()

    def onClose(self):
        # close dialog
        self.close()

    def onRemoveServer(self, index):
        mess = "Are you sure you want to remove server with index %d (%s) from list?" % (
            index, self.main_wnd.mainWindow.explorerServersList[index].get('url'))
        ans = myPopUp(self, QMessageBox.Question, 'PET4L - remove server', mess)
        if ans == QMessageBox.Yes:
            # Remove entry from database
            id = self.main_wnd.mainWindow.explorerServersList[index].get('id')
            self.main_wnd.db.removeExplorerServer(id)

    def onSave(self):
        # Get new config data
        url = self.ui.url_edt.text()
        # Check malformed URL
        if url:
            if self.changing_index is None:
                # Save new entry in DB.
                self.main_wnd.db.addExplorerServer(url)
            else:
                # Edit existing entry in DB.
                id = self.main_wnd.mainWindow.explorerServersList[self.changing_index].get('id')
                self.main_wnd.db.editExplorerServer(url, id)

            # call onCancel
            self.onCancel()


class Ui_ConfigureExplorerServersDlg(object):
    def setupUi(self, ConfigureExplorerServersDlg):
        ConfigureExplorerServersDlg.setModal(True)
        #  -- Layout
        self.layout = QVBoxLayout(ConfigureExplorerServersDlg)
        self.layout.setSpacing(10)
        #  -- Servers List
        self.serversBox = QListWidget()
        self.layout.addWidget(self.serversBox)
        #  -- 'Add Server' button
        self.addServer_btn = QPushButton("Add Explorer Server")
        self.layout.addWidget(self.addServer_btn)
        #  -- 'Close' button
        hBox = QHBoxLayout()
        hBox.addStretch(1)
        self.close_btn = QPushButton("Close")
        hBox.addWidget(self.close_btn)
        self.layout.addLayout(hBox)
        #  -- Edit section
        self.editFrame = QFrame()
        frameLayout = QFormLayout()
        frameLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        frameLayout.setContentsMargins(5, 10, 5, 5)
        frameLayout.setSpacing(7)
        self.url_edt = QLineEdit()
        frameLayout.addRow(QLabel("Explorer URL"), self.url_edt)
        hBox2 = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn = QPushButton("Save")
        hBox2.addWidget(self.cancel_btn)
        hBox2.addWidget(self.save_btn)
        frameLayout.addRow(hBox2)
        self.editFrame.setLayout(frameLayout)
        self.layout.addWidget(self.editFrame)
        self.editFrame.setHidden(True)
        ConfigureExplorerServersDlg.setMinimumWidth(500)
        ConfigureExplorerServersDlg.setMinimumHeight(500)
        # Connect main buttons
        self.addServer_btn.clicked.connect(lambda: ConfigureExplorerServersDlg.onAddServer())
        self.close_btn.clicked.connect(lambda: ConfigureExplorerServersDlg.onClose())
        self.cancel_btn.clicked.connect(lambda: ConfigureExplorerServersDlg.onCancel())
        self.save_btn.clicked.connect(lambda: ConfigureExplorerServersDlg.onSave())
