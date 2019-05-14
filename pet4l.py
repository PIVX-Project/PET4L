#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys


if __name__ == '__main__':
    # parse input if there's `--clear[?]Data` flags
    import argparse
    parser = argparse.ArgumentParser(description='PET4L')
    parser.add_argument('--clearAppData', dest='clearAppData', action='store_true',
                        help='clear all previously saved application data')
    parser.set_defaults(clearAppData=False)
    args = parser.parse_args()

    if getattr(sys, 'frozen', False):
        # running in a bundle
        sys.path.append(os.path.join(sys._MEIPASS, 'src'))
        imgDir = os.path.join(sys._MEIPASS, 'img')

        # if linux export qt plugins path
        if sys.platform == 'linux':
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt', 'plugins')

    else:
        # running live
        sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
        imgDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img')

    from PyQt5.QtWidgets import QApplication
    from mainApp import App

    # Create App
    app = QApplication(sys.argv)

    ### --------------

    # Create QMainWindow Widget
    ex = App(imgDir, args)

    # Execute App
    app.exec_()
    try:
        app.deleteLater()
    except Exception as e:
        print(e)

    sys.exit()


