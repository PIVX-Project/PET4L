#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from PyQt5.QtWidgets import QApplication
from PyQt5.Qt import Qt, QPixmap, QSplashScreen, QProgressBar, QColor, QPalette, QLabel
from mainApp import App 
      
    
if __name__ == '__main__':
    # Create App
    app = QApplication(sys.argv)
    if getattr( sys, 'frozen', False ) :
        # running in a bundle
        imgDir = os.path.join(sys._MEIPASS, 'img')
        #log_File = os.path.join(sys._MEIPASS, 'img')
    else :
        # running live
        imgDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img')
        #log_File = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lastLogs.html')     
    
    ### --------------       
    
    # Create QMainWindow Widget
    ex = App(imgDir)

    # Execute App
    sys.exit(app.exec_())
    
    
