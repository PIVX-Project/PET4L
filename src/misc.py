#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

import logging
import os
import sys
import time
from contextlib import redirect_stdout
from ipaddress import ip_address
from urllib.parse import urlparse

import simplejson as json
from PyQt5.QtCore import QObject, pyqtSignal, QSettings
from PyQt5.QtWidgets import QMessageBox

from constants import log_File, DefaultCache, wqueue, MAX_INPUTS_NO_WARNING


def add_defaultKeys_to_dict(dictObj, defaultObj):
    for key in defaultObj:
        if key not in dictObj:
            dictObj[key] = defaultObj[key]


QT_MESSAGE_TYPE = {
    "info": QMessageBox.Information,
    "warn": QMessageBox.Warning,
    "crit": QMessageBox.Critical,
    "quest": QMessageBox.Question
}


def checkRPCstring(urlstring):
    try:
        o = urlparse(urlstring)
        if o.scheme is None or o.scheme == '':
            raise Exception("Wrong protocol. Set either http or https.")
        if o.netloc is None or o.netloc == '':
            raise Exception("Malformed host network location part.")
        if o.port is None or o.port == '':
            raise Exception("Wrong IP port number")
        if o.username is None:
            raise Exception("Malformed username")
        if o.password is None:
            raise Exception("Malformed password")
        return True

    except Exception as e:
        error_msg = "Unable to parse URL"
        printException(getCallerName(), getFunctionName(), error_msg, e)
        return False

def checkTxInputs(parentWindow, num_of_inputs):
    if num_of_inputs == 0:
        myPopUp_sb(parentWindow, "warn", 'Transaction NOT sent', "No UTXO to send")
        return None

    if num_of_inputs > MAX_INPUTS_NO_WARNING:
        warning = "Warning: Trying to spend %d inputs.\nA few minutes could be required " \
                  "for the transaction to be prepared and signed.\n\nThe hardware device must remain unlocked " \
                  "during the whole time (it's advised to disable the auto-lock feature)\n\n" \
                  "Do you wish to proceed?" % num_of_inputs
        title = "PET4L - spending more than %d inputs" % MAX_INPUTS_NO_WARNING
        return myPopUp(parentWindow, "warn", title, warning)

    return QMessageBox.Yes


def clean_for_html(text):
    if text is None:
        return ""
    return text.replace("<", "{").replace(">", "}")


def clear_screen():
    os.system('clear')


def getCallerName(inDecorator=False):
    try:
        if inDecorator:
            return sys._getframe(3).f_code.co_name
        return sys._getframe(2).f_code.co_name
    except Exception:
        return None


def getFunctionName(inDecorator=False):
    try:
        if inDecorator:
            return sys._getframe(2).f_code.co_name
        return sys._getframe(1).f_code.co_name
    except Exception:
        return None


def getRemotePET4Lversion():
    import requests
    try:
        resp = requests.get("https://raw.githubusercontent.com/PIVX-Project/PET4L/master/src/version.txt")
        if resp.status_code == 200:
            data = resp.json()
            return data['number']
        else:
            raise Exception

    except Exception:
        redirect_print("Invalid response getting version from GitHub\n")
        return "0.0.0"


def getVersion():
    version_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'version.txt')
    with open(version_file, encoding="utf-8") as data_file:
        data = json.load(data_file)

    return data


def getTxidTxidn(txid, txidn):
    if txid is None or txidn is None:
        return None
    else:
        return txid + '-' + str(txidn)


def initLogs():
    filename = log_File
    filemode = 'w'
    format = '%(asctime)s - %(levelname)s - %(threadName)s | %(message)s'
    level = logging.DEBUG
    logging.basicConfig(filename=filename,
                        filemode=filemode,
                        format=format,
                        level=level
                        )


def ipport(ip, port):
    if ip is None or port is None:
        return None
    elif ip.endswith('.onion'):
        return ip + ':' + port
    else:
        ipAddr = ip_address(ip)
        if ipAddr.version == 4:
            return ip + ':' + port
        elif ipAddr.version == 6:
            return "[" + ip + "]:" + port
        else:
            raise Exception("invalid IP version number")


def myPopUp(parentWindow, messType, messTitle, messText, defaultButton=QMessageBox.No):
    if messType in QT_MESSAGE_TYPE:
        type = QT_MESSAGE_TYPE[messType]
    else:
        type = QMessageBox.Question
    mess = QMessageBox(type, messTitle, messText, defaultButton, parent=parentWindow)
    mess.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    mess.setDefaultButton(defaultButton)
    return mess.exec_()


def myPopUp_sb(parentWindow, messType, messTitle, messText, singleButton=QMessageBox.Ok):
    if messType in QT_MESSAGE_TYPE:
        type = QT_MESSAGE_TYPE[messType]
    else:
        type = QMessageBox.Information
    mess = QMessageBox(type, messTitle, messText, singleButton, parent=parentWindow)
    mess.setStandardButtons(singleButton | singleButton)
    return mess.exec_()


def is_hex(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def now():
    return int(time.time())


def persistCacheSetting(cache_key, cache_value):
    settings = QSettings('PIVX', 'PET4L')
    if not settings.contains(cache_key):
        printDbg("Cache key %s not found" % str(cache_key))
        printOK("Adding new cache key to settings...")

    if type(cache_value) in [list, dict]:
        settings.setValue(cache_key, json.dumps(cache_value))
    else:
        settings.setValue(cache_key, cache_value)

    return cache_value


def printDbg(what):
    logging.info(what)
    log_line = printDbg_msg(what)
    redirect_print(log_line)


def printDbg_msg(what):
    what = clean_for_html(what)
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now()))
    log_line = '<b style="color: yellow">{}</b> : {}<br>'.format(timestamp, what)
    return log_line


def printError(
        caller_name,
        function_name,
        what
):
    logging.error("%s | %s | %s" % (caller_name, function_name, what))
    log_line = printException_msg(caller_name, function_name, what, None, True)
    redirect_print(log_line)


def printException(
        caller_name,
        function_name,
        err_msg,
        errargs=None
):
    what = err_msg
    if errargs is not None:
        what += " ==> %s" % str(errargs)
    logging.warning("%s | %s | %s" % (caller_name, function_name, what))
    text = printException_msg(caller_name, function_name, err_msg, errargs)
    redirect_print(text)


def printException_msg(
        caller_name,
        function_name,
        err_msg,
        errargs=None,
        is_error=False
):
    if is_error:
        msg = '<b style="color: red">ERROR</b><br>'
    else:
        msg = '<b style="color: red">EXCEPTION</b><br>'
    msg += '<span style="color:white">caller</span>   : %s<br>' % caller_name
    msg += '<span style="color:white">function</span> : %s<br>' % function_name
    msg += '<span style="color:red">'
    if errargs:
        msg += 'err: %s<br>' % str(errargs)

    msg += '===> %s</span><br>' % err_msg
    return msg


def printOK(what):
    logging.debug(what)
    msg = '<b style="color: #cc33ff">===> ' + what + '</b><br>'
    redirect_print(msg)


def splitString(text, n):
    arr = [text[i:i + n] for i in range(0, len(text), n)]
    return '\n'.join(arr)


def readCacheSettings():
    settings = QSettings('PIVX', 'PET4L')
    try:
        cache = {}
        cache["lastAddress"] = settings.value('cache_lastAddress', DefaultCache["lastAddress"], type=str)
        cache["window_width"] = settings.value('cache_winWidth', DefaultCache["window_width"], type=int)
        cache["window_height"] = settings.value('cache_winHeight', DefaultCache["window_height"], type=int)
        cache["splitter_x"] = settings.value('cache_splitterX', DefaultCache["splitter_x"], type=int)
        cache["splitter_y"] = settings.value('cache_splitterY', DefaultCache["splitter_y"], type=int)
        cache["console_hidden"] = settings.value('cache_consoleHidden', DefaultCache["console_hidden"], type=bool)
        cache["selectedHW_index"] = settings.value('cache_HWindex', DefaultCache["selectedHW_index"], type=int)
        cache["selectedRPC_index"] = settings.value('cache_RPCindex', DefaultCache["selectedRPC_index"], type=int)
        cache["selectedExplorer_index"] = settings.value('cache_Explorerindex', DefaultCache["selectedExplorer_index"], type=int)
        cache["isTestnetRPC"] = settings.value('cache_isTestnetRPC', DefaultCache["isTestnetRPC"], type=bool)
        cache["hwAcc"] = settings.value('cache_hwAcc', DefaultCache["hwAcc"], type=int)
        cache["spathFrom"] = settings.value('cache_spathFrom', DefaultCache["spathFrom"], type=int)
        cache["spathTo"] = settings.value('cache_spathTo', DefaultCache["spathTo"], type=int)
        cache["intExt"] = settings.value('cache_intExt', DefaultCache["intExt"], type=int)
        add_defaultKeys_to_dict(cache, DefaultCache)
        return cache
    except:
        return DefaultCache


def redirect_print(what):
    with redirect_stdout(WriteStream(wqueue)):
        print(what)


def saveCacheSettings(cache):
    settings = QSettings('PIVX', 'PET4L')
    settings.setValue('cache_lastAddress', cache.get('lastAddress'))
    settings.setValue('cache_winWidth', cache.get('window_width'))
    settings.setValue('cache_winHeight', cache.get('window_height'))
    settings.setValue('cache_splitterX', cache.get('splitter_x'))
    settings.setValue('cache_splitterY', cache.get('splitter_y'))
    settings.setValue('cache_consoleHidden', cache.get('console_hidden'))
    settings.setValue('cache_HWindex', cache.get('selectedHW_index'))
    settings.setValue('cache_RPCindex', cache.get('selectedRPC_index'))
    settings.setValue('cache_Explorerindex', cache.get('selectedExplorer_index'))
    settings.setValue('cache_isTestnetRPC', cache.get('isTestnetRPC'))
    settings.setValue('cache_hwAcc', cache.get('hwAcc'))
    settings.setValue('cache_spathFrom', cache.get('spathFrom'))
    settings.setValue('cache_spathTo', cache.get('spathTo'))
    settings.setValue('cache_intExt', cache.get('intExt'))


def sec_to_time(seconds):
    days = seconds // 86400
    seconds -= days * 86400
    hrs = seconds // 3600
    seconds -= hrs * 3600
    mins = seconds // 60
    seconds -= mins * 60
    return "{} days, {} hrs, {} mins, {} secs".format(days, hrs, mins, seconds)


def timeThis(function, *args):
    try:
        start = time.clock()
        val = function(*args)
        end = time.clock()
        return val, (end - start)
    except Exception:
        return None, None


class DisconnectedException(Exception):
    def __init__(self, message, hwDevice):
        # Call the base class constructor
        super().__init__(message)
        # clear device
        hwDevice.closeDevice(message)


# Stream object to redirect sys.stdout and sys.stderr to a queue
class WriteStream(object):
    def __init__(self, queue):
        self.queue = queue

    def write(self, text):
        self.queue.put(text)

    def flush(self):
        pass


# QObject (to be run in QThread) that blocks until data is available
# and then emits a QtSignal to the main thread.
class WriteStreamReceiver(QObject):
    mysignal = pyqtSignal(str)

    def __init__(self, queue, *args, **kwargs):
        QObject.__init__(self, *args, **kwargs)
        self.queue = queue

    def run(self):
        while True:
            text = self.queue.get()
            self.mysignal.emit(text)
