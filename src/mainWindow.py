#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

import logging
import os

from time import strftime, gmtime
import threading

from PyQt5.QtCore import pyqtSignal, Qt, QThread
from PyQt5.QtGui import QPixmap, QColor, QPalette, QTextCursor, QFont, QIcon
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QGroupBox, QVBoxLayout, \
    QFileDialog, QTextEdit, QTabWidget, QLabel, QSplitter

from apiClient import ApiClient
from constants import starting_height, DefaultCache, wqueue, \
    DEFAULT_MAINNET_EXPLORER, DEFAULT_TESTNET_EXPLORER
from hwdevice import HWdevice
from misc import printDbg, printException, printOK, getCallerName, getFunctionName, \
    WriteStreamReceiver, now, persistCacheSetting, myPopUp_sb, getRemotePET4Lversion

from tabRewards import TabRewards
from qt.guiHeader import GuiHeader
from rpcClient import RpcClient
from threads import ThreadFuns
from watchdogThreads import RpcWatchdog


class MainWindow(QWidget):
    # signal: clear RPC status label and icons (emitted by updateRPCstatus)
    sig_clearRPCstatus = pyqtSignal()

    # signal: RPC status (for server id) is changed (emitted by updateRPCstatus)
    sig_RPCstatusUpdated = pyqtSignal(int, bool)

    # signal: RPC list has been reloaded (emitted by updateRPClist)
    sig_RPClistReloaded = pyqtSignal()

    # signal: UTXO list loading percent (emitted by load_utxos_thread in tabRewards)
    sig_UTXOsLoading = pyqtSignal(int)

    def __init__(self, parent, imgDir):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.imgDir = imgDir
        self.runInThread = ThreadFuns.runInThread
        self.lock = threading.Lock()

        # -- Create clients and statuses
        self.hwStatus = 0
        self.hwModel = 0
        self.hwStatusMess = "Not Connected"
        self.rpcClient = None
        self.rpcConnected = False
        self.updatingRPCbox = False
        self.updatingExplorerbox = False
        self.rpcStatusMess = "Not Connected"
        self.isBlockchainSynced = False
        # Changes when an RPC client is connected (affecting API client)
        self.isTestnetRPC = self.parent.cache['isTestnetRPC']

        # -- Load icons & images
        self.loadIcons()
        # -- Create main layout
        self.layout = QVBoxLayout()
        self.header = GuiHeader(self)
        self.initConsole()
        self.layout.addWidget(self.header)

        # -- Load RPC Servers list (init selection and self.isTestnet)
        self.updateRPClist()
        # -- Load Explorer Servers list
        self.explorerServersList = []
        self.updateExplorerList()

        # -- Init HW selection
        self.header.hwDevices.setCurrentIndex(self.parent.cache['selectedHW_index'])

        # -- init HW Client
        self.hwdevice = HWdevice(self)

        # -- init Api Client
        self.apiClient = ApiClient(self)

        # -- Create Queue to redirect stdout
        self.queue = wqueue

        # -- Init last logs
        logging.debug("STARTING PET4L")

        # -- Create the thread to update console log for stdout
        self.consoleLogThread = QThread()
        self.myWSReceiver = WriteStreamReceiver(self.queue)
        self.myWSReceiver.mysignal.connect(self.append_to_console)
        self.myWSReceiver.moveToThread(self.consoleLogThread)
        self.consoleLogThread.started.connect(self.myWSReceiver.run)
        self.consoleLogThread.start()
        printDbg("Console Log thread started")

        # -- Initialize tabs (single QLayout here)
        self.tabs = QTabWidget()
        self.t_rewards = TabRewards(self)
        # -- Add tabs
        self.tabs.addTab(self.tabRewards, self.parent.spmtIcon, "Spend")
        # -- Draw Tabs
        self.splitter = QSplitter(Qt.Vertical)
        # -- Add tabs and console to Layout
        self.splitter.addWidget(self.tabs)
        self.splitter.addWidget(self.console)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([2, 1])
        self.layout.addWidget(self.splitter)

        # -- Set Layout
        self.setLayout(self.layout)

        # -- Init Settings
        self.initSettings()

        # -- Connect buttons/signals
        self.connButtons()

        # -- Create RPC Whatchdog
        self.rpc_watchdogThread = QThread()
        self.myRpcWd = RpcWatchdog(self)
        self.myRpcWd.moveToThread(self.rpc_watchdogThread)
        self.rpc_watchdogThread.started.connect(self.myRpcWd.run)

        # -- Let's go
        self.mnode_to_change = None
        printOK("Hello! Welcome to " + parent.title)

    def append_to_console(self, text):
        self.consoleArea.moveCursor(QTextCursor.End)
        self.consoleArea.insertHtml(text)

    def clearHWstatus(self, message=''):
        self.hwStatus = 0
        self.hwStatusMess = "Not Connected"
        self.header.hwLed.setPixmap(self.ledGrayH_icon)
        if message != '':
            self.hwStatus = 1
            myPopUp_sb(self, "crit", "hw device Disconnected", message)

    def clearRPCstatus(self):
        with self.lock:
            self.rpcConnected = False
            self.header.lastPingBox.setHidden(False)
            self.header.rpcLed.setPixmap(self.ledGrayH_icon)
            self.header.lastBlockLabel.setText("<em>Connecting...</em>")
            self.header.lastPingIcon.setPixmap(self.connRed_icon)
            self.header.responseTimeLabel.setText("--")
            self.header.responseTimeLabel.setStyleSheet("color: red")
            self.header.lastPingIcon.setStyleSheet("color: red")

    def connButtons(self):
        self.header.button_checkRpc.clicked.connect(lambda: self.onCheckRpc())
        self.header.button_checkHw.clicked.connect(lambda: self.onCheckHw())
        self.header.rpcClientsBox.currentIndexChanged.connect(self.onChangeSelectedRPC)
        self.header.hwDevices.currentIndexChanged.connect(self.onChangeSelectedHW)
        self.header.explorerClientsBox.currentIndexChanged.connect(self.onChangeSelectedExplorer)
        # -- Connect signals
        self.sig_clearRPCstatus.connect(self.clearRPCstatus)
        self.sig_RPCstatusUpdated.connect(self.showRPCstatus)
        self.parent.sig_changed_rpcServers.connect(self.updateRPClist)
        self.parent.sig_ExplorerListReloaded.connect(self.updateExplorerList)

    def getRPCserver(self):
        itemData = self.header.rpcClientsBox.itemData(self.header.rpcClientsBox.currentIndex())
        rpc_index = self.header.rpcClientsBox.currentIndex()
        rpc_protocol = itemData["protocol"]
        rpc_host = itemData["host"]
        rpc_user = itemData["user"]
        rpc_password = itemData["password"]

        return rpc_index, rpc_protocol, rpc_host, rpc_user, rpc_password

    def getServerListIndex(self, server):
        return self.header.rpcClientsBox.findData(server)

    def initConsole(self):
        self.console = QGroupBox()
        self.console.setTitle("Console Log")
        layout = QVBoxLayout()
        self.btn_consoleToggle = QPushButton('Hide')
        self.btn_consoleToggle.setToolTip('Show/Hide console')
        self.btn_consoleToggle.clicked.connect(lambda: self.onToggleConsole())
        consoleHeader = QHBoxLayout()
        consoleHeader.addWidget(self.btn_consoleToggle)
        self.consoleSaveButton = QPushButton('Save')
        self.consoleSaveButton.clicked.connect(lambda: self.onSaveConsole())
        consoleHeader.addWidget(self.consoleSaveButton)
        self.btn_consoleClean = QPushButton('Clean')
        self.btn_consoleClean.setToolTip('Clean console log area')
        self.btn_consoleClean.clicked.connect(lambda: self.onCleanConsole())
        consoleHeader.addWidget(self.btn_consoleClean)
        consoleHeader.addStretch(1)
        self.versionLabel = QLabel("--")
        self.versionLabel.setOpenExternalLinks(True)
        consoleHeader.addWidget(self.versionLabel)
        self.btn_checkVersion = QPushButton("Check PET4L version")
        self.btn_checkVersion.setToolTip("Check latest stable release of PET4L")
        self.btn_checkVersion.clicked.connect(lambda: self.onCheckVersion())
        consoleHeader.addWidget(self.btn_checkVersion)
        layout.addLayout(consoleHeader)
        self.consoleArea = QTextEdit()
        self.consoleArea.setReadOnly(True)
        almostBlack = QColor(40, 40, 40)
        palette = QPalette()
        palette.setColor(QPalette.Base, almostBlack)
        green = QColor(0, 255, 0)
        palette.setColor(QPalette.Text, green)
        self.consoleArea.setPalette(palette)
        layout.addWidget(self.consoleArea)
        self.console.setLayout(layout)

    def initSettings(self):
        self.splitter.setSizes([self.parent.cache.get("splitter_x"), self.parent.cache.get("splitter_y")])
        # -- Hide console if it was previously hidden
        if self.parent.cache.get("console_hidden"):
            self.onToggleConsole()

    def loadIcons(self):
        # Load Icons
        self.ledPurpleH_icon = QPixmap(os.path.join(self.imgDir, 'icon_purpleLedH.png')).scaledToHeight(17, Qt.SmoothTransformation)
        self.ledGrayH_icon = QPixmap(os.path.join(self.imgDir, 'icon_grayLedH.png')).scaledToHeight(17, Qt.SmoothTransformation)
        self.ledHalfPurpleH_icon = QPixmap(os.path.join(self.imgDir, 'icon_halfPurpleLedH.png')).scaledToHeight(17, Qt.SmoothTransformation)
        self.lastBlock_icon = QPixmap(os.path.join(self.imgDir, 'icon_lastBlock.png')).scaledToHeight(15, Qt.SmoothTransformation)
        self.connGreen_icon = QPixmap(os.path.join(self.imgDir, 'icon_greenConn.png')).scaledToHeight(15, Qt.SmoothTransformation)
        self.connRed_icon = QPixmap(os.path.join(self.imgDir, 'icon_redConn.png')).scaledToHeight(15, Qt.SmoothTransformation)
        self.connOrange_icon = QPixmap(os.path.join(self.imgDir, 'icon_orangeConn.png')).scaledToHeight(15, Qt.SmoothTransformation)
        self.removeMN_icon = QIcon(os.path.join(self.imgDir, 'icon_delete.png'))
        self.editMN_icon = QIcon(os.path.join(self.imgDir, 'icon_edit.png'))
        self.ledgerImg = QPixmap(os.path.join(self.imgDir, 'ledger.png'))
        self.trezorImg = QPixmap(os.path.join(self.imgDir, 'trezorModT.png'))
        self.trezorOneImg = QPixmap(os.path.join(self.imgDir, 'trezorOne.png'))
        self.coldStaking_icon = QIcon(os.path.join(self.imgDir, 'icon_coldstaking.png'))
        self.copy_icon = QIcon(os.path.join(self.imgDir, 'icon_copy.png'))

    def onCheckHw(self):
        printDbg("Checking for HW device...")
        self.updateHWstatus(None)
        self.showHWstatus()

    def onCheckRpc(self):
        self.runInThread(self.updateRPCstatus, (True,), )

    def onCheckVersion(self):
        printDbg("Checking PET4L version...")
        self.versionLabel.setText("--")
        self.runInThread(self.checkVersion, (), self.updateVersion)

    def checkVersion(self, ctrl):
        local_version = self.parent.version['number'].split('.')
        self.gitVersion = getRemotePET4Lversion()
        remote_version = self.gitVersion.split('.')

        if (remote_version[0] > local_version[0]) or \
                (remote_version[0] == local_version[0] and remote_version[1] > local_version[1]) or \
                (remote_version[0] == local_version[0] and remote_version[1] == local_version[1] and remote_version[2] >
                 local_version[2]):
            self.versionMess = '<b style="color:red">New Version Available:</b> %s  ' % (self.gitVersion)
            self.versionMess += '(<a href="https://github.com/PIVX-Project/PET4L/releases/">download</a>)'
        else:
            self.versionMess = "You have the latest version of PET4L"

    def updateVersion(self):
        if self.versionMess is not None:
            self.versionLabel.setText(self.versionMess)
        printOK("Remote version: %s" % str(self.gitVersion))

    def onChangeSelectedHW(self, i):
        # Clear status
        self.clearHWstatus()

        # Persist setting
        self.parent.cache['selectedHW_index'] = persistCacheSetting('cache_HWindex', i)

    def onChangeSelectedRPC(self, i):
        # Don't update when we are clearing the box
        if not self.updatingRPCbox:
            # persist setting
            self.parent.cache['selectedRPC_index'] = persistCacheSetting('cache_RPCindex', i)
            self.runInThread(self.updateRPCstatus, (True,), )

    def onCleanConsole(self):
        self.consoleArea.clear()

    def onSaveConsole(self):
        timestamp = strftime('%Y-%m-%d_%H-%M-%S', gmtime(now()))
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self, "Save Logs to file", "PET4L_Logs_%s.txt" % timestamp, "All Files (*);; Text Files (*.txt)", options=options)
        try:
            if fileName:
                printOK("Saving logs to %s" % fileName)
                log_file = open(fileName, 'w+', encoding="utf-8")
                log_text = self.consoleArea.toPlainText()
                log_file.write(log_text)
                log_file.close()

        except Exception as e:
            err_msg = "error writing Log file"
            printException(getCallerName(), getFunctionName(), err_msg, e.args)

    def onToggleConsole(self):
        if self.btn_consoleToggle.text() == 'Hide':
            self.btn_consoleToggle.setText('Show')
            self.consoleArea.hide()
            self.console.setMinimumHeight(70)
            self.console.setMaximumHeight(70)
        else:
            self.console.setMinimumHeight(70)
            self.console.setMaximumHeight(starting_height)
            self.btn_consoleToggle.setText('Hide')
            self.consoleArea.show()

    def showHWstatus(self):
        self.updateHWleds()
        myPopUp_sb(self, "info", 'PET4L - hw check', "%s" % self.hwStatusMess)

    def showRPCstatus(self, server_index, fDebug):
        # Update displayed status only if selected server is not changed
        if server_index == self.header.rpcClientsBox.currentIndex():
            self.updateRPCled(fDebug)
            if fDebug:
                myPopUp_sb(self, "info", 'PET4L - rpc check', "%s" % self.rpcStatusMess)

    def updateHWleds(self):
        if self.hwStatus == 1:
            self.header.hwLed.setPixmap(self.ledHalfPurpleH_icon)
        elif self.hwStatus == 2:
            self.header.hwLed.setPixmap(self.ledPurpleH_icon)
        else:
            self.header.hwLed.setPixmap(self.ledGrayH_icon)
        self.header.hwLed.setToolTip(self.hwStatusMess)

    def updateHWstatus(self, ctrl):
        # re-initialize device
        try:
            self.hwdevice.initDevice(self.header.hwDevices.currentIndex())
            self.hwModel, self.hwStatus, self.hwStatusMess = self.hwdevice.getStatus()
        except Exception as e:
            printDbg(str(e))
            pass

        printDbg("status:%s - mess: %s" % (self.hwStatus, self.hwStatusMess))

    def updateLastBlockLabel(self):
        text = '--'
        if self.rpcLastBlock == 1:
            text = "Loading block index..."
        elif self.rpcConnected and self.rpcLastBlock > 0:
            text = str(self.rpcLastBlock)
            if not self.isBlockchainSynced:
                text += " (Synchronizing)"

        self.header.lastBlockLabel.setText(text)

    def updateLastBlockPing(self):
        if not self.rpcConnected:
            self.header.lastPingBox.setHidden(True)
        else:
            self.header.lastPingBox.setHidden(False)
            if self.rpcResponseTime > 2:
                color = "red"
                self.header.lastPingIcon.setPixmap(self.connRed_icon)
            elif self.rpcResponseTime > 1:
                color = "orange"
                self.header.lastPingIcon.setPixmap(self.connOrange_icon)
            else:
                color = "green"
                self.header.lastPingIcon.setPixmap(self.connGreen_icon)
            if self.rpcResponseTime is not None:
                self.header.responseTimeLabel.setText("%.3f" % self.rpcResponseTime)
                self.header.responseTimeLabel.setStyleSheet("color: %s" % color)
                self.header.lastPingIcon.setStyleSheet("color: %s" % color)

    def updateRPCled(self, fDebug=False):
        if self.rpcConnected:
            self.header.rpcLed.setPixmap(self.ledPurpleH_icon)
            if fDebug:
                printDbg("Connected to RPC server.")
        else:
            if self.rpcLastBlock == 1:
                self.header.rpcLed.setPixmap(self.ledHalfPurpleH_icon)
                if fDebug:
                    printDbg("Connected to RPC server - Still syncing...")
            else:
                self.header.rpcLed.setPixmap(self.ledGrayH_icon)
                if fDebug:
                    printDbg("Connection to RPC server failed.")

        self.header.rpcLed.setToolTip(self.rpcStatusMess)
        self.updateLastBlockLabel()
        self.updateLastBlockPing()

    def updateRPClist(self):
        # Clear old stuff
        self.updatingRPCbox = True
        self.header.rpcClientsBox.clear()
        public_servers = self.parent.db.getRPCServers(custom=False)
        custom_servers = self.parent.db.getRPCServers(custom=True)
        self.rpcServersList = public_servers + custom_servers
        # Add public servers (italics)
        italicsFont = QFont("Times", italic=True)
        for s in public_servers:
            url = s["protocol"] + "://" + s["host"].split(':')[0]
            self.header.rpcClientsBox.addItem(url, s)
            self.header.rpcClientsBox.setItemData(self.getServerListIndex(s), italicsFont, Qt.FontRole)
        # Add Local Wallet (bold)
        boldFont = QFont("Times")
        boldFont.setBold(True)
        self.header.rpcClientsBox.addItem("Local Wallet", custom_servers[0])
        self.header.rpcClientsBox.setItemData(self.getServerListIndex(custom_servers[0]), boldFont, Qt.FontRole)
        # Add custom servers
        for s in custom_servers[1:]:
            url = s["protocol"] + "://" + s["host"].split(':')[0]
            self.header.rpcClientsBox.addItem(url, s)
        # reset index
        if self.parent.cache['selectedRPC_index'] >= self.header.rpcClientsBox.count():
            # (if manually removed from the config files) replace default index
            self.parent.cache['selectedRPC_index'] = persistCacheSetting('cache_RPCindex', DefaultCache["selectedRPC_index"])

        self.header.rpcClientsBox.setCurrentIndex(self.parent.cache['selectedRPC_index'])
        self.updatingRPCbox = False
        # reload servers in configure dialog
        self.sig_RPClistReloaded.emit()

    def explorerCacheKey(self):
        # Selection is remembered per network so switching networks never
        # remaps to an unrelated explorer.
        return 'selectedExplorer_testnet' if self.isTestnetRPC else 'selectedExplorer_mainnet'

    def explorerSettingsKey(self):
        return 'cache_ExplorerTestnet' if self.isTestnetRPC else 'cache_ExplorerMainnet'

    def setSelectedExplorer(self, url):
        # Persist the selected explorer URL for the active network.
        self.parent.cache[self.explorerCacheKey()] = persistCacheSetting(self.explorerSettingsKey(), url)

    def updateExplorerList(self):
        # Full list (both networks) backs the configuration dialog...
        self.explorerServersList = self.parent.db.getExplorerServers()
        # ...while the header dropdown only offers explorers for the active
        # network, so a testnet explorer isn't a selectable no-op on mainnet.
        network_explorers = [e for e in self.explorerServersList
                             if bool(e['isTestnet']) == self.isTestnetRPC]

        # Repopulate the explorer box. Guard so that the programmatic
        # clear()/addItem() calls don't fire onChangeSelectedExplorer.
        self.updatingExplorerbox = True
        self.header.explorerClientsBox.clear()
        for explorer in network_explorers:
            self.header.explorerClientsBox.addItem(explorer["url"], explorer)

        # Restore the selection saved for THIS network, matched by URL (the
        # combo's item text). Indices are per-network here, so a saved URL is
        # the only stable handle across networks and reordering.
        saved_url = self.parent.cache.get(self.explorerCacheKey())
        index = self.header.explorerClientsBox.findText(saved_url) if saved_url else -1
        if index < 0:
            index = 0  # saved explorer no longer available -> first for network
        self.header.explorerClientsBox.setCurrentIndex(index)
        self.updatingExplorerbox = False

        # Persist whatever ended up selected so the cache reflects reality, then
        # sync the api client. We do this explicitly because the guard above
        # swallowed the currentIndexChanged signal.
        selected_explorer = self.header.explorerClientsBox.currentData()
        if selected_explorer:
            self.setSelectedExplorer(selected_explorer['url'])
        self.applySelectedExplorer()

    def applySelectedExplorer(self):
        selected_explorer = self.header.explorerClientsBox.currentData()
        if selected_explorer:
            url = selected_explorer['url']
            self.header.activeExplorerLabel.setText("Active Explorer: <b>%s</b>" % url)
        else:
            # No explorer configured for this network: fall back to the default.
            network = 'testnet' if self.isTestnetRPC else 'mainnet'
            url = self.getExplorerURL(network)
            self.header.activeExplorerLabel.setText("Active Explorer: <b>None</b>")
        printDbg("Active Explorer URL: %s" % url)
        if getattr(self, 'apiClient', None) is not None:
            self.apiClient.updateExplorerUrl(url)

    def onChangeSelectedExplorer(self, i):
        # Don't react while we are programmatically repopulating the box
        if self.updatingExplorerbox:
            return

        selected_explorer = self.header.explorerClientsBox.itemData(i)
        if selected_explorer:
            explorer_url = selected_explorer.get('url', '')
            # Persist the new selection for the active network
            self.setSelectedExplorer(explorer_url)
            # Point the api client at the newly selected explorer
            if getattr(self, 'apiClient', None) is not None:
                self.apiClient.updateExplorerUrl(explorer_url)
            printDbg("Explorer changed to: %s" % explorer_url)
            self.header.activeExplorerLabel.setText("Active Explorer: <b>%s</b>" % explorer_url)
        else:
            printDbg("No explorer selected")
            self.header.activeExplorerLabel.setText("Active Explorer: <b>None</b>")

    def getExplorerURLList(self, network):
        # All configured explorer URLs for the given network, defaults if none.
        isTestnet = (network == 'testnet')
        urls = [e['url'] for e in self.explorerServersList if bool(e['isTestnet']) == isTestnet]
        if not urls:
            printDbg("No explorers configured for %s, using default." % network)
            urls = [DEFAULT_TESTNET_EXPLORER if isTestnet else DEFAULT_MAINNET_EXPLORER]
        return urls

    def getExplorerURL(self, network):
        # Honour the persisted per-network selection, falling back to the first
        # explorer for that network. Reads only cache/list state (no Qt widget),
        # so it is safe to call from the RPC worker thread when ApiClient is
        # rebuilt on a network switch.
        cache_key = 'selectedExplorer_testnet' if network == 'testnet' else 'selectedExplorer_mainnet'
        saved_url = self.parent.cache.get(cache_key)
        urls = self.getExplorerURLList(network)
        if saved_url and saved_url in urls:
            return saved_url
        return urls[0]

    def updateRPCstatus(self, ctrl, fDebug=False):
        rpc_index, rpc_protocol, rpc_host, rpc_user, rpc_password = self.getRPCserver()
        if fDebug:
            printDbg("Trying to connect to RPC %s://%s..." % (rpc_protocol, rpc_host))

        try:
            rpcClient = RpcClient(rpc_protocol, rpc_host, rpc_user, rpc_password)
            status, statusMess, lastBlock, r_time1, isTestnet = rpcClient.getStatus()
            isBlockchainSynced, r_time2 = rpcClient.isBlockchainSynced()
        except Exception as e:
            printException(getCallerName(), getFunctionName(), "exception updating RPC status:", str(e))
            # clear status
            self.rpcClient = None
            self.sig_clearRPCstatus.emit()
            return

        rpcResponseTime = None
        if r_time1 is not None and r_time2 != 0:
            rpcResponseTime = round((r_time1 + r_time2) / 2, 3)

        # Do not update status if the user has selected a different server since the start of updateRPCStatus()
        if rpc_index != self.header.rpcClientsBox.currentIndex():
            return

        networkChanged = False
        with self.lock:
            self.rpcClient = rpcClient
            self.rpcConnected = status
            self.rpcLastBlock = lastBlock
            self.rpcStatusMess = statusMess
            self.isBlockchainSynced = isBlockchainSynced
            self.rpcResponseTime = rpcResponseTime
            # if testnet flag is changed, update api client and persist setting
            if isTestnet != self.isTestnetRPC:
                self.isTestnetRPC = isTestnet
                self.parent.cache['isTestnetRPC'] = persistCacheSetting('isTestnetRPC', isTestnet)
                self.apiClient = ApiClient(self)
                networkChanged = True
        self.sig_RPCstatusUpdated.emit(rpc_index, fDebug)
        # We are on a worker thread here: refresh the explorer dropdown for the
        # new network via the (queued) signal so it runs on the GUI thread.
        if networkChanged:
            self.parent.sig_ExplorerListReloaded.emit()
