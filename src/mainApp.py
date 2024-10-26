#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

import logging
import os
import signal

from PyQt5.QtCore import pyqtSignal, QSettings
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QAction
from time import time

from database import Database
from misc import printDbg, initLogs, saveCacheSettings, readCacheSettings, getVersion
from mainWindow import MainWindow
from constants import user_dir, SECONDS_IN_2_MONTHS
from qt.dlg_configureRPCservers import ConfigureRPCserversDlg
from qt.dlg_signmessage import SignMessageDlg


class ServiceExit(Exception):
    """
    Custom exception which is used to trigger the clean exit
    of all running threads and the main program.
    """
    pass


def service_shutdown(signum, frame):
    print(f'Caught signal {signum}')
    raise ServiceExit


class App(QMainWindow):
    # Signal emitted from database
    sig_changed_rpcServers = pyqtSignal()

    def __init__(self, imgDir, app, start_args):
        # Create the userdir if it doesn't exist
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)

        # Initialize Logs
        initLogs()
        super().__init__()
        self.app = app

        # Register the signal handlers
        signal.signal(signal.SIGTERM, service_shutdown)
        signal.signal(signal.SIGINT, service_shutdown)

        # Get version and title
        self.version = getVersion()
        self.title = f'PET4L - PIVX Emergency Tool For Ledger - v.{self.version["number"]}-{self.version["tag"]}'

        # Open database
        self.db = Database(self)
        self.db.openDB()

        # Check for startup args (clear data)
        if start_args.clearAppData:
            settings = QSettings('PIVX', 'PET4L')
            settings.clear()

        if start_args.clearTxCache:
            self.db.clearTable('RAWTXES')

        # Clear DB
        self.db.clearTable('UTXOS')

        # Remove raw txes updated earlier than two months ago (if not already cleared)
        if not start_args.clearTxCache:
            self.db.clearRawTxes(time() - SECONDS_IN_2_MONTHS)

        # Read cached app data
        self.cache = readCacheSettings()

        # Initialize user interface
        self.initUI(imgDir)

    def initUI(self, imgDir):
        # Set title and geometry
        self.setWindowTitle(self.title)
        self.resize(self.cache.get("window_width"), self.cache.get("window_height"))
        # Set Icons
        self.spmtIcon = QIcon(os.path.join(imgDir, 'spmtLogo_shield.png'))
        self.pivx_icon = QIcon(os.path.join(imgDir, 'icon_pivx.png'))
        self.script_icon = QIcon(os.path.join(imgDir, 'icon_script.png'))
        self.setWindowIcon(self.spmtIcon)
        # Create main window
        self.mainWindow = MainWindow(self, imgDir)
        self.setCentralWidget(self.mainWindow)
        # Add RPC server menu
        mainMenu = self.menuBar()
        confMenu = mainMenu.addMenu('Setup')
        self.rpcConfMenu = QAction(self.pivx_icon, 'RPC Servers config...', self)
        self.rpcConfMenu.triggered.connect(self.onEditRPCServer)
        confMenu.addAction(self.rpcConfMenu)
        toolsMenu = mainMenu.addMenu('Tools')
        self.signVerifyAction = QAction('Sign/Verify message', self)
        self.signVerifyAction.triggered.connect(self.onSignVerifyMessage)
        toolsMenu.addAction(self.signVerifyAction)
        # Show
        self.show()
        self.activateWindow()

    def closeEvent(self, event):
        # Terminate the running threads.
        # Set the shutdown flag on each thread to trigger a clean shutdown of each thread.
        self.mainWindow.myRpcWd.shutdown_flag.set()
        logging.debug("Saving stuff & closing...")
        try:
            self.mainWindow.hwdevice.clearDevice()
        except Exception as e:
            logging.warning(str(e))

        # Update window/splitter size
        self.cache['window_width'] = self.width()
        self.cache['window_height'] = self.height()
        self.cache['splitter_x'] = self.mainWindow.splitter.sizes()[0]
        self.cache['splitter_y'] = self.mainWindow.splitter.sizes()[1]
        self.cache['console_hidden'] = (self.mainWindow.btn_consoleToggle.text() == 'Show')

        # persist cache
        saveCacheSettings(self.cache)

        # clear / close DB
        self.db.removeTable('UTXOS')
        self.db.close()

        # Adios
        print("Bye Bye.")
        return super().closeEvent(event)

    def onEditRPCServer(self):
        # Create Dialog
        ui = ConfigureRPCserversDlg(self)
        if ui.exec():
            printDbg("Configuring RPC Servers...")

    def onSignVerifyMessage(self):
        # Create Dialog
        ui = SignMessageDlg(self.mainWindow)
        if ui.exec():
            printDbg("Sign/Verify message...")
