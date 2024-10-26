#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Random.Zebra (https://github.com/random-zebra/)
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

import logging
import os
import sys
import time
import io
from contextlib import redirect_stdout
from ipaddress import ip_address
from urllib.parse import urlparse
from typing import Any, Callable, Dict, Optional, Tuple

import simplejson as json
from PyQt5.QtCore import QObject, pyqtSignal, QSettings
from PyQt5.QtWidgets import QMessageBox

from constants import log_File, DefaultCache, MAX_INPUTS_NO_WARNING


def add_defaultKeys_to_dict(dictObj: Dict[str, Any], defaultObj: Dict[str, Any]) -> None:
    for key in defaultObj:
        if key not in dictObj:
            dictObj[key] = defaultObj[key]


QT_MESSAGE_TYPE: Dict[str, QMessageBox.Icon] = {
    "info": QMessageBox.Information,
    "warn": QMessageBox.Warning,
    "crit": QMessageBox.Critical,
    "quest": QMessageBox.Question
}


def checkRPCstring(urlstring: str) -> bool:
    try:
        o = urlparse(urlstring)
        if not o.scheme:
            raise ValueError("Wrong protocol. Set either http or https.")
        if not o.netloc:
            raise ValueError("Malformed host network location part.")
        if not o.port:
            raise ValueError("Wrong IP port number")
        if not o.username:
            raise ValueError("Malformed username")
        if not o.password:
            raise ValueError("Malformed password")
        return True
    except Exception as e:
        error_msg = "Unable to parse URL"
        printException(getCallerName(), getFunctionName(), error_msg, e)
        return False

def checkTxInputs(parentWindow: Any, num_of_inputs: int) -> Optional[int]:
    if num_of_inputs == 0:
        myPopUp_sb(parentWindow, "warn", 'Transaction NOT sent', "No UTXO to send")
        return None

    if num_of_inputs > MAX_INPUTS_NO_WARNING:
        warning = (f"Warning: Trying to spend {num_of_inputs} inputs.\n"
                   "A few minutes could be required for the transaction to be prepared and signed.\n\n"
                   "The hardware device must remain unlocked during the whole time "
                   "(it's advised to disable the auto-lock feature)\n\n"
                   "Do you wish to proceed?")
        title = f"PET4L - spending more than {MAX_INPUTS_NO_WARNING} inputs"
        return myPopUp(parentWindow, "warn", title, warning)

    return QMessageBox.Yes


def clean_for_html(text: Optional[str]) -> str:
    if text is None:
        return ""
    return text.replace("<", "{").replace(">", "}")


def clear_screen() -> None:
    os.system('clear')


def getCallerName(inDecorator: bool = False) -> Optional[str]:
    try:
        frame = sys._getframe(3 if inDecorator else 2)
        return frame.f_code.co_name
    except Exception:
        return None


def getFunctionName(inDecorator: bool = False) -> Optional[str]:
    try:
        frame = sys._getframe(2 if inDecorator else 1)
        return frame.f_code.co_name
    except Exception:
        return None


def getRemotePET4Lversion() -> str:
    import requests
    try:
        resp = requests.get("https://raw.githubusercontent.com/PIVX-Project/PET4L/master/src/version.txt")
        if resp.status_code == 200:
            data = resp.json()
            return data['number']
        else:
            raise ValueError("Invalid response from GitHub")
    except Exception:
        redirect_print("Invalid response getting version from GitHub\n")
        return "0.0.0"


def getVersion() -> Dict[str, Any]:
    version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'version.txt')
    with open(version_file, encoding="utf-8") as data_file:
        data = json.load(data_file)
    return data


def getTxidTxidn(txid: Optional[str], txidn: Optional[int]) -> Optional[str]:
    if txid is None or txidn is None:
        return None
    else:
        return f"{txid}-{txidn}"


def initLogs() -> None:
    filename = log_File
    filemode = 'w'
    format = '%(asctime)s - %(levelname)s - %(threadName)s | %(message)s'
    level = logging.DEBUG
    logging.basicConfig(filename=filename, filemode=filemode, format=format, level=level)


def ipport(ip: Optional[str], port: Optional[str]) -> Optional[str]:
    if ip is None or port is None:
        return None
    elif ip.endswith('.onion'):
        return f"{ip}:{port}"
    else:
        ipAddr = ip_address(ip)
        if ipAddr.version == 4:
            return f"{ip}:{port}"
        elif ipAddr.version == 6:
            return f"[{ip}]:{port}"
        else:
            raise ValueError("Invalid IP version number")


def myPopUp(parentWindow: Any, messType: str, messTitle: str, messText: str, defaultButton: QMessageBox.StandardButton = QMessageBox.No) -> int:
    message_type = QT_MESSAGE_TYPE.get(messType, QMessageBox.Question)
    mess = QMessageBox(message_type, messTitle, messText, defaultButton, parent=parentWindow)
    mess.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    mess.setDefaultButton(defaultButton)
    return mess.exec_()


def myPopUp_sb(parentWindow: Any, messType: str, messTitle: str, messText: str, singleButton: QMessageBox.StandardButton = QMessageBox.Ok) -> int:
    message_type = QT_MESSAGE_TYPE.get(messType, QMessageBox.Information)
    mess = QMessageBox(message_type, messTitle, messText, singleButton, parent=parentWindow)
    mess.setStandardButtons(singleButton)
    return mess.exec_()


def is_hex(s: str) -> bool:
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def now() -> int:
    return int(time.time())


def persistCacheSetting(cache_key: str, cache_value: Any) -> Any:
    settings = QSettings('PIVX', 'PET4L')
    if not settings.contains(cache_key):
        printDbg(f"Cache key {cache_key} not found")
        printOK("Adding new cache key to settings...")
    settings.setValue(cache_key, json.dumps(cache_value) if isinstance(cache_value, (list, dict)) else cache_value)
    return cache_value


def printDbg(what: str) -> None:
    logging.info(what)
    log_line = printDbg_msg(what)
    redirect_print(log_line)


def printDbg_msg(what: str) -> str:
    what = clean_for_html(what)
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now()))
    log_line = f'<b style="color: yellow">{timestamp}</b> : {what}<br>'
    return log_line


def printError(caller_name: Optional[str], function_name: Optional[str], what: str) -> None:
    logging.error(f"{caller_name} | {function_name} | {what}")
    log_line = printException_msg(caller_name, function_name, what, None, True)
    redirect_print(log_line)


def printException(caller_name: Optional[str], function_name: Optional[str], err_msg: str, errargs: Optional[Any] = None) -> None:
    what = err_msg
    if errargs is not None:
        what += f" ==> {errargs}"
    logging.warning(f"{caller_name} | {function_name} | {what}")
    text = printException_msg(caller_name, function_name, err_msg, errargs)
    redirect_print(text)


def printException_msg(caller_name: Optional[str], function_name: Optional[str], err_msg: str, errargs: Optional[Any] = None, is_error: bool = False) -> str:
    msg = '<b style="color: red">ERROR</b><br>' if is_error else '<b style="color: red">EXCEPTION</b><br>'
    msg += f'<span style="color:white">caller</span>   : {caller_name}<br>'
    msg += f'<span style="color:white">function</span> : {function_name}<br>'
    msg += '<span style="color:red">'
    if errargs:
        msg += f'err: {errargs}<br>'
    msg += f'===> {err_msg}</span><br>'
    return msg


def printOK(what: str) -> None:
    logging.debug(what)
    msg = f'<b style="color: #cc33ff">===> {what}</b><br>'
    redirect_print(msg)


def splitString(text: str, n: int) -> str:
    arr = [text[i:i + n] for i in range(0, len(text), n)]
    return '\n'.join(arr)


def readCacheSettings() -> Dict[str, Any]:
    settings = QSettings('PIVX', 'PET4L')
    try:
        cache = {
            "lastAddress": settings.value('cache_lastAddress', DefaultCache["lastAddress"], type=str),
            "window_width": settings.value('cache_winWidth', DefaultCache["window_width"], type=int),
            "window_height": settings.value('cache_winHeight', DefaultCache["window_height"], type=int),
            "splitter_x": settings.value('cache_splitterX', DefaultCache["splitter_x"], type=int),
            "splitter_y": settings.value('cache_splitterY', DefaultCache["splitter_y"], type=int),
            "console_hidden": settings.value('cache_consoleHidden', DefaultCache["console_hidden"], type=bool),
            "selectedHW_index": settings.value('cache_HWindex', DefaultCache["selectedHW_index"], type=int),
            "selectedRPC_index": settings.value('cache_RPCindex', DefaultCache["selectedRPC_index"], type=int),
            "isTestnetRPC": settings.value('cache_isTestnetRPC', DefaultCache["isTestnetRPC"], type=bool),
            "hwAcc": settings.value('cache_hwAcc', DefaultCache["hwAcc"], type=int),
            "spathFrom": settings.value('cache_spathFrom', DefaultCache["spathFrom"], type=int),
            "spathTo": settings.value('cache_spathTo', DefaultCache["spathTo"], type=int),
            "intExt": settings.value('cache_intExt', DefaultCache["intExt"], type=int)
        }
        add_defaultKeys_to_dict(cache, DefaultCache)
        return cache
    except Exception:
        return DefaultCache


def redirect_print(what: str) -> None:
    with io.StringIO() as buffer:
        with redirect_stdout(buffer):
            print(what)


def saveCacheSettings(cache: Dict[str, Any]) -> None:
    settings = QSettings('PIVX', 'PET4L')
    settings.setValue('cache_lastAddress', cache.get('lastAddress'))
    settings.setValue('cache_winWidth', cache.get('window_width'))
    settings.setValue('cache_winHeight', cache.get('window_height'))
    settings.setValue('cache_splitterX', cache.get('splitter_x'))
    settings.setValue('cache_splitterY', cache.get('splitter_y'))
    settings.setValue('cache_consoleHidden', cache.get('console_hidden'))
    settings.setValue('cache_HWindex', cache.get('selectedHW_index'))
    settings.setValue('cache_RPCindex', cache.get('selectedRPC_index'))
    settings.setValue('cache_isTestnetRPC', cache.get('isTestnetRPC'))
    settings.setValue('cache_hwAcc', cache.get('hwAcc'))
    settings.setValue('cache_spathFrom', cache.get('spathFrom'))
    settings.setValue('cache_spathTo', cache.get('spathTo'))
    settings.setValue('cache_intExt', cache.get('intExt'))


def sec_to_time(seconds: int) -> str:
    days, seconds = divmod(seconds, 86400)
    hrs, seconds = divmod(seconds, 3600)
    mins, seconds = divmod(seconds, 60)
    return f"{days} days, {hrs} hrs, {mins} mins, {seconds} secs"


def timeThis(function: Callable[..., Any], *args: Any) -> Tuple[Optional[Any], Optional[float]]:
    try:
        start = time.perf_counter()
        val = function(*args)
        end = time.perf_counter()
        return val, (end - start)
    except Exception:
        return None, None


class DisconnectedException(Exception):
    def __init__(self, message: str, hwDevice: Any):
        # Call the base class constructor
        super().__init__(message)
        # clear device
        hwDevice.closeDevice(message)


# Stream object to redirect sys.stdout and sys.stderr to a queue
class WriteStream:
    def __init__(self, queue: Any):
        self.queue = queue

    def write(self, text: str) -> None:
        self.queue.put(text)

    def flush(self) -> None:
        pass


class WrapperWriteStream:
    def __init__(self, write_stream: WriteStream):
        self.write_stream = write_stream

    def write(self, message: str) -> int:
        self.write_stream.write(message)
        return len(message)

    def flush(self) -> None:
        self.write_stream.flush()


# QObject (to be run in QThread) that blocks until data is available
# and then emits a QtSignal to the main thread.
class WriteStreamReceiver(QObject):
    mysignal = pyqtSignal(str)

    def __init__(self, queue: Any, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.queue = queue

    def run(self) -> None:
        while True:
            text = self.queue.get()
            self.mysignal.emit(text)
