import math
import platform
import threading
import time
from datetime import datetime

import pytz

from PyQt5 import QtCore, QtGui, QtWidgets, Qt
from PyQt5.QtCore import QMetaObject

from MachineDeviceInfo import MachineDeviceInfo
from ResetMachine import MachineIDResetter
from CursorAuthManager import CursorAuthManager

from CursorZsApi import *
from email_code_util_sifu import get_sifu_code
from go import go_cursor_help, ExitCursor, open_cursor
from failUI import FailedDialog
from rebootUI import RebootDialog
from successUI import SuccessdDialog
import sys

from tupo41 import tupo41


class Ui_MainWindow(object):
    def __init__(self):
        super().__init__()
        self.device_code = None  # Declare the global variable
        self.device_pwd = None
        self.device_code_md5 = None
        self.loginType = None
        self.email = None
        self.token = None
        self.pwd = None
        # 新增Pro类型和Pro总次数
        self.pro_type = 0  # 0=auto, 1=pro
        self.pro_count = 0  # pro总次数
        # 切换功能相关 -QW
        self.qh_type = None  # 是否允许切换：1=允许切换，0=不允许
        self.current_pro_type = None  # 当前账号类型：0=Auto, 1=Pro

    def setupUi(self, MainWindow):

        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(900, 501)

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_11 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_11.setSpacing(0)
        self.verticalLayout_11.setObjectName("verticalLayout_11")

        self.widget = QtWidgets.QWidget(self.centralwidget)
        self.widget.setStyleSheet("QWidget#widget{\n"
                                  "    border-radius:30px;\n"
                                  "    background-color:rgb(248, 252, 254);\n"
                                  "}")
        self.widget.setObjectName("widget")
        self.verticalLayout_12 = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout_12.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_12.setSpacing(0)
        self.verticalLayout_12.setObjectName("verticalLayout_12")

        self.widget_28 = QtWidgets.QWidget(self.widget)
        self.widget_28.setObjectName("widget_28")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.widget_28)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.widget_29 = QtWidgets.QWidget(self.widget_28)
        self.widget_29.setObjectName("widget_29")
        self.horizontalLayout_17 = QtWidgets.QHBoxLayout(self.widget_29)
        self.horizontalLayout_17.setContentsMargins(9, 9, 0, 0)
        self.horizontalLayout_17.setSpacing(0)
        self.horizontalLayout_17.setObjectName("horizontalLayout_17")
        self.toolButton = QtWidgets.QToolButton(self.widget_29)
        self.toolButton.setMinimumSize(QtCore.QSize(72, 22))
        self.toolButton.setStyleSheet("QToolButton{\n"
                                      "    background-color:rgb(248, 252, 254);\n"
                                      "    color:#7A808D;\n"
                                      "    border-radius: 3px;\n"
                                      "    border: 1px solid rgba(45, 128, 248, 0);\n"
                                      "}\n"
                                      "QToolButton:hover{\n"
                                      "    background-color:rgba(45, 128, 248, 0);\n"
                                      "}\n"
                                      "QToolButton::pressed{\n"
                                      "    background-color:rgba(45, 128, 248, 0);\n"
                                      "    padding-left: 2px;\n"
                                      "    padding-top: 2px;\n"
                                      "}")
        self.toolButton.setObjectName("toolButton")
        self.toolButton.setVisible(False)  # 隐藏工具按钮 -QW
        self.horizontalLayout_17.addWidget(self.toolButton)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_17.addItem(spacerItem)
        self.horizontalLayout_2.addWidget(self.widget_29)
        self.widget_30 = QtWidgets.QWidget(self.widget_28)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_30.sizePolicy().hasHeightForWidth())
        self.widget_30.setSizePolicy(sizePolicy)
        self.widget_30.setObjectName("widget_30")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.widget_30)
        self.gridLayout_2.setContentsMargins(0, 0, 20, 20)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.pushButton_min = QtWidgets.QPushButton(self.widget_30)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_min.sizePolicy().hasHeightForWidth())
        self.pushButton_min.setSizePolicy(sizePolicy)
        self.pushButton_min.setMinimumSize(QtCore.QSize(22, 22))
        self.pushButton_min.setMaximumSize(QtCore.QSize(22, 22))
        self.pushButton_min.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9aa0a6;
                font: 14pt;
                border-radius: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(45, 128, 248), stop:1 rgb(66, 133, 244));
                color: white;
                font: bold 14pt;
            }
            QPushButton:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(35, 118, 238), stop:1 rgb(56, 123, 234));
                color: white;
            }
        """)
        self.pushButton_min.setObjectName("pushButton_min")
        self.gridLayout_2.addWidget(self.pushButton_min, 0, 0, 1, 1)
        self.pushButton_close = QtWidgets.QPushButton(self.widget_30)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_close.sizePolicy().hasHeightForWidth())
        self.pushButton_close.setSizePolicy(sizePolicy)
        self.pushButton_close.setMinimumSize(QtCore.QSize(22, 22))
        self.pushButton_close.setMaximumSize(QtCore.QSize(22, 22))
        self.pushButton_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9aa0a6;
                font: 12pt;
                border-radius: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(255, 82, 82), stop:1 rgb(255, 107, 107));
                color: white;
                font: bold 12pt;
            }
            QPushButton:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(235, 62, 62), stop:1 rgb(235, 87, 87));
                color: white;
            }
        """)
        self.pushButton_close.setObjectName("pushButton_close")
        self.gridLayout_2.addWidget(self.pushButton_close, 0, 1, 1, 1)
        self.horizontalLayout_2.addWidget(self.widget_30)
        self.verticalLayout_12.addWidget(self.widget_28)
        self.widget_27 = QtWidgets.QWidget(self.widget)
        self.widget_27.setObjectName("widget_27")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget_27)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.widget_2 = QtWidgets.QWidget(self.widget_27)
        self.widget_2.setMinimumSize(QtCore.QSize(400, 0))
        self.widget_2.setObjectName("widget_2")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.widget_2)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.widget_5 = QtWidgets.QWidget(self.widget_2)
        self.widget_5.setObjectName("widget_5")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.widget_5)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget_6 = QtWidgets.QWidget(self.widget_5)
        self.widget_6.setMinimumSize(QtCore.QSize(0, 100))
        self.widget_6.setMaximumSize(QtCore.QSize(16777215, 100))
        self.widget_6.setObjectName("widget_6")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.widget_6)
        self.horizontalLayout_5.setContentsMargins(12, 0, 0, 0)
        self.horizontalLayout_5.setSpacing(20)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.widget_10 = QtWidgets.QWidget(self.widget_6)
        self.widget_10.setMinimumSize(QtCore.QSize(70, 60))
        self.widget_10.setMaximumSize(QtCore.QSize(70, 16777215))
        self.widget_10.setObjectName("widget_10")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.widget_10)
        self.horizontalLayout_6.setContentsMargins(9, 0, 0, 9)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.label_2 = QtWidgets.QLabel(self.widget_10)
        self.label_2.setMinimumSize(QtCore.QSize(55, 55))
        self.label_2.setMaximumSize(QtCore.QSize(55, 55))
        self.label_2.setStyleSheet("border-image: url(:/icon/Group 5038.png);")
        self.label_2.setText("")
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_6.addWidget(self.label_2)
        self.horizontalLayout_5.addWidget(self.widget_10)
        self.widget_11 = QtWidgets.QWidget(self.widget_6)
        self.widget_11.setObjectName("widget_11")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.widget_11)
        self.verticalLayout_2.setContentsMargins(0, 10, 0, 10)
        self.verticalLayout_2.setSpacing(6)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.pushButton = QtWidgets.QPushButton(self.widget_11)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton.sizePolicy().hasHeightForWidth())
        self.pushButton.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(18)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.pushButton.setFont(font)
        self.pushButton.setStyleSheet(
            "QPushButton#pushButton{color:qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101)); background-color:transparent; border:1px solid transparent; text-align: left; font: bold 26pt; margin-top: 10px;}")
        self.pushButton.setObjectName("pushButton")
        self.verticalLayout_2.addWidget(self.pushButton)
        self.label_3 = QtWidgets.QLabel(self.widget_11)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(12)
        self.label_3.setFont(font)
        self.label_3.setStyleSheet("color:#9CA3AF;")
        self.label_3.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.label_3.setObjectName("label_3")
        self.verticalLayout_2.addWidget(self.label_3)
        self.horizontalLayout_5.addWidget(self.widget_11)
        self.verticalLayout.addWidget(self.widget_6)
        self.widget_7 = QtWidgets.QWidget(self.widget_5)
        self.widget_7.setMinimumSize(QtCore.QSize(0, 170))
        # 移除最大高度限制，让公告区域可以向下自动扩展 -QW
        # self.widget_7.setMaximumSize(QtCore.QSize(16777215, 170))
        self.widget_7.setObjectName("widget_7")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.widget_7)
        self.verticalLayout_3.setContentsMargins(9, 5, 9, 0)
        self.verticalLayout_3.setSpacing(6)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.label_4 = QtWidgets.QLabel(self.widget_7)
        self.label_4.setMinimumSize(QtCore.QSize(0, 45))
        self.label_4.setMaximumSize(QtCore.QSize(16777215, 45))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(18)
        font.setBold(True)
        font.setWeight(75)
        self.label_4.setFont(font)
        self.label_4.setStyleSheet("""
            color: #333333;
            padding-left: 12px;
        """)
        self.label_4.setObjectName("label_4")
        self.verticalLayout_3.addWidget(self.label_4)
        self.label_5 = QtWidgets.QLabel(self.widget_7)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(14)
        self.label_5.setFont(font)
        self.label_5.setStyleSheet("""
            padding-left: 12px;
            padding-right: 12px;
            color: #555555;
            line-height: 1.6;
        """)
        self.label_5.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.label_5.setWordWrap(True)
        self.label_5.setObjectName("label_5")
        self.verticalLayout_3.addWidget(self.label_5)
        self.verticalLayout.addWidget(self.widget_7)
        self.widget_8 = QtWidgets.QWidget(self.widget_5)
        self.widget_8.setObjectName("widget_8")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.widget_8)
        self.verticalLayout_4.setContentsMargins(9, 9, 9, 9)
        self.verticalLayout_4.setSpacing(6)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.widget_9 = QtWidgets.QWidget(self.widget_8)
        self.widget_9.setMinimumSize(QtCore.QSize(0, 30))
        self.widget_9.setMaximumSize(QtCore.QSize(16777215, 30))
        self.widget_9.setObjectName("widget_9")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout(self.widget_9)
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.label_6 = QtWidgets.QLabel(self.widget_9)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(18)
        font.setBold(True)
        font.setWeight(50)
        self.label_6.setFont(font)
        self.label_6.setStyleSheet("color:#7A808D;\n"
                                   "padding-left: 12px;")
        self.label_6.setObjectName("label_6")
        self.horizontalLayout_7.addWidget(self.label_6)
        self.pushButton_refresh_quota = QtWidgets.QPushButton(self.widget_9)
        self.pushButton_refresh_quota.setMinimumSize(QtCore.QSize(80, 30))
        self.pushButton_refresh_quota.setMaximumSize(QtCore.QSize(80, 30))

        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_refresh_quota.setFont(font)
        self.pushButton_refresh_quota.setStyleSheet("QPushButton#pushButton_refresh_quota{\n"
                                                    "    background-color:rgb(45, 128, 248);\n"
                                                    "    color:white;\n"
                                                    "    border-radius:15px;\n"
                                                    "    border:0px solid rgb(45, 128, 248);\n"
                                                    "}\n"
                                                    "QPushButton::pressed{\n"
                                                    "    padding-left: 2px;\n"
                                                    "    padding-top: 2px;\n"
                                                    "}\n"
                                                    "")
        self.pushButton_refresh_quota.setText("刷新额度")
        self.pushButton_refresh_quota.setObjectName("pushButton_refresh_quota")
        self.pushButton_refresh_quota.setVisible(False)  # 隐藏刷新额度按钮
        self.horizontalLayout_7.addWidget(self.pushButton_refresh_quota)
        self.pushButton_refresh_quota.clicked.connect(self.refresh_count)
        self.verticalLayout_4.addWidget(self.widget_9)
        self.widget_12 = QtWidgets.QWidget(self.widget_8)
        self.widget_12.setObjectName("widget_12")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.widget_12)
        self.verticalLayout_5.setContentsMargins(12, 0, 12, 0)
        self.verticalLayout_5.setSpacing(0)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        # ===== 剩余额度监控区域已隐藏 =====
        # self.widget_13 = QtWidgets.QWidget(self.widget_12)
        # self.widget_13.setMinimumSize(QtCore.QSize(0, 100))
        # self.widget_13.setMaximumSize(QtCore.QSize(16777215, 100))
        # self.widget_13.setStyleSheet("QWidget#widget_13{\n"
        #                              "    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,stop:0 transparent,stop:1 rgba(0, 0, 0, 50));\n"
        #                              "    border-radius: 25px;\n"
        #                              "}")
        # self.widget_13.setObjectName("widget_13")
        # self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.widget_13)
        # self.verticalLayout_6.setContentsMargins(1, 1, 1, 1)
        # self.verticalLayout_6.setSpacing(0)
        # self.verticalLayout_6.setObjectName("verticalLayout_6")
        # self.widget_14 = QtWidgets.QWidget(self.widget_13)
        # self.widget_14.setMinimumSize(QtCore.QSize(0, 49))
        # self.widget_14.setMaximumSize(QtCore.QSize(16777215, 49))
        # self.widget_14.setStyleSheet("QWidget#widget_14{\n"
        #                              "    background-color:white;\n"
        #                              "    border-top-left-radius:24px;\n"
        #                              "    border-top-right-radius:24px;\n"
        #                              "}")
        # self.widget_14.setObjectName("widget_14")
        # self.horizontalLayout_8 = QtWidgets.QHBoxLayout(self.widget_14)
        # self.horizontalLayout_8.setContentsMargins(10, 20, 10, 0)
        # self.horizontalLayout_8.setSpacing(3)
        # self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        # self.label_7 = QtWidgets.QLabel(self.widget_14)
        # self.label_7.setMinimumSize(QtCore.QSize(10, 10))
        # self.label_7.setMaximumSize(QtCore.QSize(10, 10))
        # self.label_7.setStyleSheet("background-color:rgb(45, 127, 249);\n"
        #                            "border-radius:5px")
        # self.label_7.setText("")
        # self.label_7.setObjectName("label_7")
        # self.horizontalLayout_8.addWidget(self.label_7)
        # self.label_8 = QtWidgets.QLabel(self.widget_14)
        # font = QtGui.QFont()
        # font.setFamily("PingFang SC")
        # font.setPointSize(16)
        # self.label_8.setFont(font)
        # self.label_8.setStyleSheet("color:#7A808D;")
        # self.label_8.setObjectName("label_8")
        # self.horizontalLayout_8.addWidget(self.label_8)
        # spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        # self.horizontalLayout_8.addItem(spacerItem1)
        # self.label_12 = QtWidgets.QLabel(self.widget_14)
        # font = QtGui.QFont()
        # font.setFamily("PingFang SC")
        # self.label_12.setFont(font)
        # self.label_12.setStyleSheet("color:rgb(45, 128, 248);")
        # self.label_12.setObjectName("label_12")
        # self.horizontalLayout_8.addWidget(self.label_12)
        # self.label_9 = QtWidgets.QLabel(self.widget_14)
        # self.label_9.setObjectName("label_9")
        # self.horizontalLayout_8.addWidget(self.label_9)
        # self.label_10 = QtWidgets.QLabel(self.widget_14)
        # font = QtGui.QFont()
        # font.setFamily("PingFang SC")
        # self.label_10.setFont(font)
        # self.label_10.setStyleSheet("color:rgb(23, 200, 101);")
        # self.label_10.setObjectName("label_10")
        # self.horizontalLayout_8.addWidget(self.label_10)
        # self.label_11 = QtWidgets.QLabel(self.widget_14)
        # font = QtGui.QFont()
        # font.setFamily("PingFang SC")
        # self.label_11.setFont(font)
        # self.label_11.setStyleSheet("color:#7A808D;")
        # self.label_11.setObjectName("label_11")
        # self.horizontalLayout_8.addWidget(self.label_11)
        # self.verticalLayout_6.addWidget(self.widget_14)
        # self.widget_15 = QtWidgets.QWidget(self.widget_13)
        # self.widget_15.setMinimumSize(QtCore.QSize(0, 49))
        # self.widget_15.setMaximumSize(QtCore.QSize(16777215, 49))
        # self.widget_15.setStyleSheet("QWidget#widget_15{\n"
        #                              "    background-color:white;\n"
        #                              "    border-bottom-left-radius:24px;\n"
        #                              "    border-bottom-right-radius:24px;\n"
        #                              "}")
        # self.widget_15.setObjectName("widget_15")
        # self.horizontalLayout_9 = QtWidgets.QHBoxLayout(self.widget_15)
        # self.horizontalLayout_9.setContentsMargins(-1, 0, -1, -1)
        # self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        # self.progressBar = QtWidgets.QProgressBar(self.widget_15)
        # self.progressBar.setMinimumSize(QtCore.QSize(0, 22))
        # self.progressBar.setMaximumSize(QtCore.QSize(16777215, 22))
        # self.progressBar.setStyleSheet("QProgressBar{\n"
        #                                "    border:2px solid #F3F4F6;\n"
        #                                "    border-radius:12px;\n"
        #                                "    background-color:#F3F4F6;\n"
        #                                "    text-align:center;\n"
        #                                "    color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgba(0, 200, 200, 255), stop:1 rgba(155, 235, 155, 255));\n"
        #                                "    padding-left: 60px;\n"
        #                                "}\n"
        #                                "QProgressBar::chunk{\n"
        #                                "    color: white;\n"
        #                                "    border-radius:9px;     background: QLinearGradient(x1:0,y1:0,x2:1,y2:0,stop:0 rgb(45, 128, 248),stop:1 rgb(23, 200, 101));\n"
        #                                "}")
        # self.progressBar.setProperty("value", 100)
        # self.progressBar.setObjectName("progressBar")
        # self.horizontalLayout_9.addWidget(self.progressBar)
        # self.verticalLayout_6.addWidget(self.widget_15)
        # self.verticalLayout_5.addWidget(self.widget_13)
        spacerItem2 = QtWidgets.QSpacerItem(20, 33, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_5.addItem(spacerItem2)
        self.label_25 = QtWidgets.QLabel(self.widget_12)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(16)
        font.setBold(False)
        font.setWeight(50)
        self.label_25.setFont(font)
        self.label_25.setStyleSheet("color:#7A808D;\n"
                                    "padding-left: 12px;")
        self.label_25.setObjectName("label_25")
        self.verticalLayout_5.addWidget(self.label_25)
        spacerItem3 = QtWidgets.QSpacerItem(20, 33, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_5.addItem(spacerItem3)
        self.verticalLayout_4.addWidget(self.widget_12)
        self.verticalLayout.addWidget(self.widget_8)
        self.horizontalLayout_3.addWidget(self.widget_5)
        self.widget_4 = QtWidgets.QWidget(self.widget_2)
        self.widget_4.setMinimumSize(QtCore.QSize(4, 0))
        self.widget_4.setMaximumSize(QtCore.QSize(4, 16777215))
        self.widget_4.setObjectName("widget_4")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.widget_4)
        self.horizontalLayout_4.setContentsMargins(0, 66, 0, 66)
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.label = QtWidgets.QLabel(self.widget_4)
        self.label.setStyleSheet(
            "background-color:qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));\n"
            "border-radius:2px")
        self.label.setText("")
        self.label.setObjectName("label")
        self.horizontalLayout_4.addWidget(self.label)
        self.horizontalLayout_3.addWidget(self.widget_4)
        self.horizontalLayout.addWidget(self.widget_2)
        self.widget_3 = QtWidgets.QWidget(self.widget_27)
        self.widget_3.setMinimumSize(QtCore.QSize(500, 0))
        self.widget_3.setObjectName("widget_3")
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout(self.widget_3)
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_10.setSpacing(0)
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.widget_16 = QtWidgets.QWidget(self.widget_3)
        self.widget_16.setObjectName("widget_16")
        self.verticalLayout_7 = QtWidgets.QVBoxLayout(self.widget_16)
        self.verticalLayout_7.setContentsMargins(9, 9, 9, 9)
        self.verticalLayout_7.setSpacing(0)
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.widget_17 = QtWidgets.QWidget(self.widget_16)
        self.widget_17.setMinimumSize(QtCore.QSize(0, 108))
        self.widget_17.setMaximumSize(QtCore.QSize(16777215, 108))
        self.widget_17.setObjectName("widget_17")
        self.verticalLayout_8 = QtWidgets.QVBoxLayout(self.widget_17)
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_8.setSpacing(0)
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.label_13 = QtWidgets.QLabel(self.widget_17)
        self.label_13.setMinimumSize(QtCore.QSize(0, 30))
        self.label_13.setMaximumSize(QtCore.QSize(16777215, 30))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(18)
        self.label_13.setFont(font)
        self.label_13.setStyleSheet("color:#7A808D;")
        self.label_13.setObjectName("label_13")
        self.verticalLayout_8.addWidget(self.label_13)
        self.widget_21 = QtWidgets.QWidget(self.widget_17)
        self.widget_21.setMinimumSize(QtCore.QSize(0, 60))
        self.widget_21.setMaximumSize(QtCore.QSize(16777215, 60))
        self.widget_21.setStyleSheet("""
            QWidget#widget_21 {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #f8f9fa, stop:1 #f0f2f5);
                border-radius: 16px;
                border: 1px solid #e8eaed;
            }
        """)
        self.widget_21.setObjectName("widget_21")
        self.horizontalLayout_11 = QtWidgets.QHBoxLayout(self.widget_21)
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        self.label_14 = QtWidgets.QLabel(self.widget_21)
        self.label_14.setMinimumSize(QtCore.QSize(40, 40))
        self.label_14.setMaximumSize(QtCore.QSize(40, 40))
        self.label_14.setStyleSheet("border-image: url(:/icon/指纹_3x.png);")
        self.label_14.setText("")
        self.label_14.setObjectName("label_14")
        self.horizontalLayout_11.addWidget(self.label_14)
        self.label_15 = QtWidgets.QLabel(self.widget_21)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        self.label_15.setFont(font)
        self.label_15.setStyleSheet("color:#7A808D;")
        self.label_15.setObjectName("label_15")
        self.horizontalLayout_11.addWidget(self.label_15)
        self.pushButton_2 = QtWidgets.QPushButton(self.widget_21)
        self.pushButton_2.setMinimumSize(QtCore.QSize(40, 40))
        self.pushButton_2.setMaximumSize(QtCore.QSize(40, 40))
        self.pushButton_2.setStyleSheet("""
            QPushButton#pushButton_2 {
                background-color: #f8f9fa;
                border-radius: 12px;
                border: 1px solid #e8eaed;
            }
            QPushButton#pushButton_2:hover {
                background-color: #e8f0fe;
                border: 1px solid rgb(45, 128, 248);
            }
            QPushButton#pushButton_2:pressed {
                background-color: #d2e3fc;
                padding-left: 1px;
                padding-top: 1px;
            }
        """)
        self.pushButton_2.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icon/复制.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pushButton_2.setIcon(icon)
        self.pushButton_2.setIconSize(QtCore.QSize(35, 35))
        self.pushButton_2.setObjectName("pushButton_2")
        self.horizontalLayout_11.addWidget(self.pushButton_2)
        self.verticalLayout_8.addWidget(self.widget_21)
        self.verticalLayout_7.addWidget(self.widget_17)
        self.widget_18 = QtWidgets.QWidget(self.widget_16)
        self.widget_18.setStyleSheet("QWidget#widget_18{\n"
                                     "    border: 9px solid transparent;\n"
                                     "    border-image: qradialgradient(\n"
                                     "        spread: pad,\n"
                                     "        cx: 0.5, cy: 0.5,\n"
                                     "        radius: 0.5,\n"
                                     "        fx: 0.5, fy: 0.5,\n"
                                     "        stop: 0 rgb(45, 128, 248),\n"
                                     "        stop: 0.35 rgb(45, 128, 248),\n"
                                     "        stop: 0.4 rgb(45, 128, 248),\n"
                                     "        stop: 0.425 rgb(45, 128, 248),\n"
                                     "        stop: 0.88 rgb(45, 128, 248),\n"
                                     "        stop: 1 rgba(255, 255, 255, 0)\n"
                                     "    ) 9 stretch;\n"
                                     "}")
        self.widget_18.setObjectName("widget_18")
        self.horizontalLayout_15 = QtWidgets.QHBoxLayout(self.widget_18)
        self.horizontalLayout_15.setObjectName("horizontalLayout_15")
        self.widget_23 = QtWidgets.QWidget(self.widget_18)
        self.widget_23.setStyleSheet("""
            QWidget#widget_23 {
                background-color: white;
                border-radius: 20px;
            }
        """)
        self.widget_23.setObjectName("widget_23")
        self.gridLayout = QtWidgets.QGridLayout(self.widget_23)
        self.gridLayout.setContentsMargins(15, 12, 15, 12)
        self.gridLayout.setHorizontalSpacing(20)
        self.gridLayout.setVerticalSpacing(8)
        self.gridLayout.setObjectName("gridLayout")
        # 设置两列等宽
        self.gridLayout.setColumnStretch(0, 1)
        self.gridLayout.setColumnStretch(1, 1)
        
        # ===== 左侧区域：会员等级 + 账号类型 =====
        self.widget_24 = QtWidgets.QWidget(self.widget_23)
        self.widget_24.setObjectName("widget_24")
        self.verticalLayout_9 = QtWidgets.QVBoxLayout(self.widget_24)
        self.verticalLayout_9.setContentsMargins(0, 5, 0, 5)
        self.verticalLayout_9.setSpacing(4)
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        
        # 会员等级标题
        self.label_16 = QtWidgets.QLabel(self.widget_24)
        self.label_16.setStyleSheet("color:#9CA3AF; font-size: 12px;")
        self.label_16.setObjectName("label_16")
        self.verticalLayout_9.addWidget(self.label_16)
        
        # 会员等级值
        self.label_19 = QtWidgets.QLabel(self.widget_24)
        self.label_19.setStyleSheet("color:#EF4444; font-size: 14px; font-weight: bold;")
        self.label_19.setObjectName("label_19")
        self.verticalLayout_9.addWidget(self.label_19)
        
        # 账号类型标题
        self.label_pro_type = QtWidgets.QLabel(self.widget_24)
        self.label_pro_type.setStyleSheet("color:#9CA3AF; font-size: 12px; margin-top: 8px;")
        self.label_pro_type.setObjectName("label_pro_type")
        self.verticalLayout_9.addWidget(self.label_pro_type)
        
        # 账号类型值和切换按钮的水平布局
        self.widget_pro_type_row = QtWidgets.QWidget(self.widget_24)
        self.widget_pro_type_row.setObjectName("widget_pro_type_row")
        self.horizontalLayout_pro_type = QtWidgets.QHBoxLayout(self.widget_pro_type_row)
        self.horizontalLayout_pro_type.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_pro_type.setSpacing(8)
        self.horizontalLayout_pro_type.setObjectName("horizontalLayout_pro_type")
        
        # 账号类型值
        self.label_pro_type_value = QtWidgets.QLabel(self.widget_pro_type_row)
        self.label_pro_type_value.setStyleSheet("color:#4285F4; font-size: 14px; font-weight: bold;")
        self.label_pro_type_value.setObjectName("label_pro_type_value")
        self.horizontalLayout_pro_type.addWidget(self.label_pro_type_value)
        
        # 切换按钮 (仅在 qh_type=1 时显示)
        self.btn_switch_pro_type = QtWidgets.QPushButton(self.widget_pro_type_row)
        self.btn_switch_pro_type.setMinimumSize(QtCore.QSize(50, 22))
        self.btn_switch_pro_type.setMaximumSize(QtCore.QSize(50, 22))
        self.btn_switch_pro_type.setStyleSheet("""
            QPushButton {
                background-color: rgb(45, 128, 248);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: rgb(35, 108, 228);
            }
            QPushButton:pressed {
                background-color: rgb(25, 88, 208);
            }
            QPushButton:disabled {
                background-color: rgb(180, 180, 180);
            }
        """)
        self.btn_switch_pro_type.setText("切换")
        self.btn_switch_pro_type.setObjectName("btn_switch_pro_type")
        self.btn_switch_pro_type.setVisible(False)
        self.horizontalLayout_pro_type.addWidget(self.btn_switch_pro_type)
        self.horizontalLayout_pro_type.addStretch()
        
        self.verticalLayout_9.addWidget(self.widget_pro_type_row)
        self.gridLayout.addWidget(self.widget_24, 1, 0, 1, 1)
        
        # ===== 右侧区域：激活时间 + 到期时间 =====
        self.widget_25 = QtWidgets.QWidget(self.widget_23)
        self.widget_25.setObjectName("widget_25")
        self.verticalLayout_10 = QtWidgets.QVBoxLayout(self.widget_25)
        self.verticalLayout_10.setContentsMargins(0, 5, 0, 5)
        self.verticalLayout_10.setSpacing(4)
        self.verticalLayout_10.setObjectName("verticalLayout_10")
        
        # 激活时间标题
        self.label_23 = QtWidgets.QLabel(self.widget_25)
        self.label_23.setStyleSheet("color:#9CA3AF; font-size: 12px;")
        self.label_23.setObjectName("label_23")
        self.verticalLayout_10.addWidget(self.label_23)
        
        # 激活时间值
        self.label_22 = QtWidgets.QLabel(self.widget_25)
        self.label_22.setStyleSheet("color:#374151; font-size: 14px; font-weight: bold;")
        self.label_22.setObjectName("label_22")
        self.verticalLayout_10.addWidget(self.label_22)
        
        # 到期时间标题
        self.label_18 = QtWidgets.QLabel(self.widget_25)
        self.label_18.setStyleSheet("color:#9CA3AF; font-size: 12px; margin-top: 8px;")
        self.label_18.setObjectName("label_18")
        self.verticalLayout_10.addWidget(self.label_18)
        
        # 到期时间值
        self.label_17 = QtWidgets.QLabel(self.widget_25)
        self.label_17.setStyleSheet("color:#374151; font-size: 14px; font-weight: bold;")
        self.label_17.setObjectName("label_17")
        self.verticalLayout_10.addWidget(self.label_17)

        self.gridLayout.addWidget(self.widget_25, 1, 1, 1, 1)
        
        # ===== 顶部标题区域：会员状态 + 刷新按钮 =====
        self.widget_26 = QtWidgets.QWidget(self.widget_23)
        self.widget_26.setObjectName("widget_26")
        self.horizontalLayout_16 = QtWidgets.QHBoxLayout(self.widget_26)
        self.horizontalLayout_16.setContentsMargins(0, 0, 0, 8)
        self.horizontalLayout_16.setSpacing(10)
        self.horizontalLayout_16.setObjectName("horizontalLayout_16")
        
        # 会员状态标题
        self.label_24 = QtWidgets.QLabel(self.widget_26)
        self.label_24.setStyleSheet("""
            color: #374151;
            font-size: 16px;
            font-weight: bold;
        """)
        self.label_24.setObjectName("label_24")
        self.horizontalLayout_16.addWidget(self.label_24)
        
        # 刷新会员信息按钮
        self.btn_refresh_member = QtWidgets.QPushButton(self.widget_26)
        self.btn_refresh_member.setMinimumSize(QtCore.QSize(55, 24))
        self.btn_refresh_member.setMaximumSize(QtCore.QSize(55, 24))
        self.btn_refresh_member.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_refresh_member.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(45, 128, 248), stop:1 rgb(66, 133, 244));
                color: white;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 8px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(35, 118, 238), stop:1 rgb(56, 123, 234));
            }
            QPushButton:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(25, 108, 228), stop:1 rgb(46, 113, 224));
            }
        """)
        self.btn_refresh_member.setObjectName("btn_refresh_member")
        self.horizontalLayout_16.addWidget(self.btn_refresh_member)
        
        # 添加弹簧
        spacerItem_member = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_16.addItem(spacerItem_member)
        
        self.gridLayout.addWidget(self.widget_26, 0, 0, 1, 2)
        self.horizontalLayout_15.addWidget(self.widget_23)
        self.verticalLayout_7.addWidget(self.widget_18)
        self.widget_19 = QtWidgets.QWidget(self.widget_16)
        self.widget_19.setMinimumSize(QtCore.QSize(0, 60))
        self.widget_19.setMaximumSize(QtCore.QSize(16777215, 60))
        self.widget_19.setObjectName("widget_19")
        self.horizontalLayout_14 = QtWidgets.QHBoxLayout(self.widget_19)
        self.horizontalLayout_14.setContentsMargins(9, 0, 9, 0)
        self.horizontalLayout_14.setSpacing(0)
        self.horizontalLayout_14.setObjectName("horizontalLayout_14")
        self.widget_22 = QtWidgets.QWidget(self.widget_19)
        self.widget_22.setMinimumSize(QtCore.QSize(0, 50))
        self.widget_22.setStyleSheet("""
            QWidget#widget_22 {
                background-color: white;
                border-radius: 16px;
                border: 1px solid #e8eaed;
            }
        """)
        self.widget_22.setObjectName("widget_22")
        self.horizontalLayout_13 = QtWidgets.QHBoxLayout(self.widget_22)
        self.horizontalLayout_13.setContentsMargins(9, 9, 9, 9)
        self.horizontalLayout_13.setSpacing(6)
        self.horizontalLayout_13.setObjectName("horizontalLayout_13")
        self.lineEdit = QtWidgets.QLineEdit(self.widget_22)
        self.lineEdit.setMinimumSize(QtCore.QSize(0, 40))
        self.lineEdit.setMaximumSize(QtCore.QSize(16777215, 40))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(16)
        font.setBold(False)
        font.setWeight(50)
        self.lineEdit.setFont(font)
        self.lineEdit.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e8eaed;
                padding-left: 12px;
                padding-right: 12px;
                border-radius: 12px;
                color: #333333;
                background-color: white;
                selection-background-color: rgb(45, 128, 248);
                selection-color: white;
            }
            QLineEdit:hover {
                border: 2px solid #c4c9cf;
            }
            QLineEdit:focus {
                border: 2px solid rgb(45, 128, 248);
                background-color: #fafcff;
            }
            QLineEdit::placeholder {
                color: #9aa0a6;
            }
        """)
        self.lineEdit.setText("")
        self.lineEdit.setObjectName("lineEdit")
        # 确保激活码输入框能容纳足够长的内容 -QW
        self.lineEdit.setMaxLength(1000)      # 设置最大长度为1000字符
        # 注意：不设置setValidator(None)，避免影响textChanged信号
        self.lineEdit.setInputMask('')        # 清除输入掩码
        self.horizontalLayout_13.addWidget(self.lineEdit)
        spacerItem4 = QtWidgets.QSpacerItem(9, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_13.addItem(spacerItem4)
        self.pushButton_5 = QtWidgets.QPushButton(self.widget_22)
        self.pushButton_5.setMinimumSize(QtCore.QSize(110, 40))
        self.pushButton_5.setMaximumSize(QtCore.QSize(120, 40))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_5.setFont(font)
        self.pushButton_5.setStyleSheet("""
            QPushButton#pushButton_5 {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(45, 128, 248), stop:1 rgb(66, 133, 244));
                color: white;
                border-radius: 12px;
                border: none;
                font-weight: bold;
            }
            QPushButton#pushButton_5:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(35, 118, 238), stop:1 rgb(56, 123, 234));
            }
            QPushButton#pushButton_5:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(25, 108, 228), stop:1 rgb(46, 113, 224));
                padding-left: 1px;
                padding-top: 1px;
            }
        """)
        self.pushButton_5.setIconSize(QtCore.QSize(35, 35))
        self.pushButton_5.setObjectName("pushButton_5")
        self.horizontalLayout_13.addWidget(self.pushButton_5)
        self.horizontalLayout_14.addWidget(self.widget_22)

        self.label_26 = QtWidgets.QLabel(self.widget_26)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")  # Replace "PingFang SC" with "Arial" or another existing font
        font.setPointSize(10)  # Set the font size
        font.setBold(True)
        font.setWeight(75)
        self.label_26.setFont(font)
        self.label_26.setStyleSheet("color:#7A808D; margin-top: 5px;")
        self.label_26.setAlignment(QtCore.Qt.AlignRight)  # Align text to the right
        self.label_26.setObjectName("label_26")
        self.horizontalLayout_16.addWidget(self.label_26)

        self.verticalLayout_7.addWidget(self.widget_19)
        self.widget_20 = QtWidgets.QWidget(self.widget_16)
        self.widget_20.setMinimumSize(QtCore.QSize(0, 70))
        self.widget_20.setMaximumSize(QtCore.QSize(16777215, 70))
        self.widget_20.setObjectName("widget_20")
        self.horizontalLayout_12 = QtWidgets.QHBoxLayout(self.widget_20)
        self.horizontalLayout_12.setObjectName("horizontalLayout_12")
        spacerItem5 = QtWidgets.QSpacerItem(9, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_12.addItem(spacerItem5)
        self.pushButton_3 = QtWidgets.QPushButton(self.widget_20)
        self.pushButton_3.setMinimumSize(QtCore.QSize(0, 50))
        self.pushButton_3.setMaximumSize(QtCore.QSize(16777215, 50))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(22)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_3.setFont(font)
        self.pushButton_3.setStyleSheet("""
            QPushButton#pushButton_3 {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(45, 128, 248), stop:0.5 rgb(34, 164, 175), stop:1 rgb(23, 200, 101));
                color: white;
                border-radius: 20px;
                border: none;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton#pushButton_3:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(35, 118, 238), stop:0.5 rgb(24, 154, 165), stop:1 rgb(13, 190, 91));
            }
            QPushButton#pushButton_3:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(25, 108, 228), stop:0.5 rgb(14, 144, 155), stop:1 rgb(3, 180, 81));
                padding-left: 1px;
                padding-top: 1px;
            }
        """)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/icon/刷新 (2) 1.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pushButton_3.setIcon(icon1)
        self.pushButton_3.setIconSize(QtCore.QSize(20, 20))
        self.pushButton_3.setObjectName("pushButton_3")
        self.horizontalLayout_12.addWidget(self.pushButton_3)
        self.pushButton_8 = QtWidgets.QPushButton(self.widget_20)
        self.pushButton_8.setMinimumSize(QtCore.QSize(0, 50))
        self.pushButton_8.setMaximumSize(QtCore.QSize(16777215, 50))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(22)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_8.setFont(font)
        self.pushButton_8.setVisible(False)  # 显示按钮
        self.pushButton_8.setStyleSheet("QPushButton#pushButton_8{\n"
                                        "    background-color:qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));\n"
                                        "    color:rgba(255,255,255,200);\n"
                                        "    border-radius:18px;\n"
                                        "    border:0px solid rgb(45, 128, 248);\n"
                                        "}\n"
                                        "QPushButton::pressed{\n"
                                        "    padding-left: 2px;\n"
                                        "    padding-top: 2px;\n"
                                        "}\n"
                                        "")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/icon/刷新 (2) 1.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pushButton_8.setIcon(icon1)
        self.pushButton_8.setIconSize(QtCore.QSize(20, 20))
        self.pushButton_8.setObjectName("pushButton_8")
        self.horizontalLayout_12.addWidget(self.pushButton_8)

        spacerItem6 = QtWidgets.QSpacerItem(9, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_12.addItem(spacerItem6)
        self.pushButton_4 = QtWidgets.QPushButton(self.widget_20)
        self.pushButton_4.setMinimumSize(QtCore.QSize(0, 50))
        self.pushButton_4.setMaximumSize(QtCore.QSize(16777215, 50))
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(22)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_4.setFont(font)
        self.pushButton_4.setStyleSheet("""
            QPushButton#pushButton_4 {
                background-color: white;
                color: rgb(45, 128, 248);
                border-radius: 20px;
                border: 2px solid rgb(45, 128, 248);
                font-weight: bold;
            }
            QPushButton#pushButton_4:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(45, 128, 248), stop:1 rgb(66, 133, 244));
                color: white;
                border: none;
            }
            QPushButton#pushButton_4:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(35, 118, 238), stop:1 rgb(56, 123, 234));
                color: white;
                border: none;
                padding-left: 1px;
                padding-top: 1px;
            }
            QPushButton#pushButton_4:checked {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgb(45, 128, 248), stop:1 rgb(23, 200, 101));
                color: white;
                border: none;
            }
        """)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/icon/工作时间.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pushButton_4.setIcon(icon2)
        self.pushButton_4.setIconSize(QtCore.QSize(20, 20))
        self.pushButton_4.setCheckable(True)
        self.pushButton_4.setAutoRepeat(False)
        self.pushButton_4.setObjectName("pushButton_4")
        self.horizontalLayout_12.addWidget(self.pushButton_4)

        spacerItem7 = QtWidgets.QSpacerItem(9, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_12.addItem(spacerItem7)
        self.verticalLayout_7.addWidget(self.widget_20)
        spacerItem8 = QtWidgets.QSpacerItem(20, 18, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout_7.addItem(spacerItem8)
        self.horizontalLayout_10.addWidget(self.widget_16)
        self.horizontalLayout.addWidget(self.widget_3)
        self.verticalLayout_12.addWidget(self.widget_27)
        self.verticalLayout_11.addWidget(self.widget)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        if platform.system() == "Darwin":

            # On macOS, set the close button to minimize the window.
            self.pushButton_close.clicked.connect(lambda: sys.exit(0))
        else:
            # On Windows, keep the default behavior to close the window.
            self.pushButton_close.clicked.connect(MainWindow.close)

        self.pushButton_min.clicked.connect(MainWindow.showMinimized)  # type: ignore
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.label_email = QtWidgets.QLabel(self.widget_26)
        font = QtGui.QFont()
        font.setFamily("PingFang SC")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        self.label_email.setFont(font)
        self.label_email.setStyleSheet("color:#7A808D;")
        self.label_email.setObjectName("label_email")
        self.horizontalLayout_16.addWidget(self.label_email)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        # 设置窗口标题，包含版本号 -QW
        import config
        window_title = f"Cursor助手 v{config.APP_VERSION}"
        MainWindow.setWindowTitle(_translate("MainWindow", window_title))
        
        # self.toolButton.setText(_translate("MainWindow", "帮助"))  # 已隐藏 -QW
        self.pushButton_min.setText(_translate("MainWindow", "－"))
        self.pushButton_close.setText(_translate("MainWindow", "×"))
        self.pushButton.setText(_translate("MainWindow", "Cursor登录助手"))
        
        # 动态设置版本号显示 -QW
        import config
        version_text = f"Version {config.APP_VERSION}"
        self.label_3.setText(_translate("MainWindow", version_text))
        self.label_4.setText(_translate("MainWindow", "快速开始"))
        self.label_5.setText(
            _translate("MainWindow",
                       "欢迎使用Cursor登录助手，输入激活码点击\"激活设备\"进行激活。\n如果CursorAi无法正常使用，请点击\"刷新Cursor\"按钮。\n自动刷新功能需要程序在后台运行。\n \n感谢您的使用。如有任何问题，请联系我们。"))
        # ===== 剩余额度监控区域文本设置已隐藏 =====
        # self.label_6.setText(_translate("MainWindow", "当前账号额度监控"))
        # self.label_8.setText(_translate("MainWindow", "剩余额度"))
        # self.label_12.setText(_translate("MainWindow", "0"))
        # self.label_9.setText(_translate("MainWindow", "/"))
        # self.label_10.setText(_translate("MainWindow", "1000"))
        # self.label_11.setText(_translate("MainWindow", "次数"))
        # self.progressBar.setFormat(_translate("MainWindow", "%p%"))
        self.label_25.setText(_translate("MainWindow", "连接服务器失败，请关闭科学上网，重启登录助手"))
        self.label_26.setText(_translate("MainWindow", ""))

        self.label_13.setText(_translate("MainWindow", "设备号"))
        self.label_15.setText(_translate("MainWindow", "96b80deb862aad219e001047389b9235"))
        self.label_16.setText(_translate("MainWindow", "会员等级"))
        self.label_19.setText(_translate("MainWindow", "未激活"))
        self.label_pro_type.setText(_translate("MainWindow", "账号类型"))
        self.label_pro_type_value.setText(_translate("MainWindow", "-"))
        self.btn_switch_pro_type.clicked.connect(self.on_switch_pro_type_clicked)  # 连接切换账号类型按钮 -QW
        self.label_18.setText(_translate("MainWindow", "到期时间"))
        self.label_17.setText(_translate("MainWindow", "-"))
        self.label_23.setText(_translate("MainWindow", "激活时间"))
        self.label_22.setText(_translate("MainWindow", "-"))

        self.label_24.setText(_translate("MainWindow", "会员状态"))
        self.btn_refresh_member.setText(_translate("MainWindow", "刷新"))
        self.btn_refresh_member.clicked.connect(self.refresh_member_info)
        self.lineEdit.setPlaceholderText(_translate("MainWindow", "请输入激活码"))
        # 连接textChanged信号来自动去除空格
        self.lineEdit.textChanged.connect(self.remove_spaces_from_activation_code)
        self.pushButton_5.setText(_translate("MainWindow", "激活"))
        self.pushButton_5.clicked.connect(self.activate)
        self.pushButton_3.setText(_translate("MainWindow", "刷新Cursor"))
        self.pushButton_3.clicked.connect(self.refresh_cursor)
        self.pushButton_4.setText(_translate("MainWindow", "突破"))
        self.pushButton_4.toggled.connect(self.change_jiqima)
        self.pushButton_8.setText(_translate("MainWindow", "获取密码"))
        self.pushButton_8.clicked.connect(self.toggle_auto_refresh_cursor)

        self.initCursor()

        # 获取代理联系方式

    def get_dl_lxfs(self, dl_id):
        api = CursorZsApi()
        code, dl_lx = api.get_dl_lxfs(dl_id)
        if code == '200':
            self.label_25.setText(dl_lx)

    def reboot_dailog(self):
        dialog = RebootDialog(msg='Cursor即将重启，请确认代码已经保存成功')
        return dialog.reboot_dialog()

    def yb_show_success_dialog(self, msg):
        QMetaObject.invokeMethod(self, "_show_success_dialog", Qt.QueuedConnection, QtCore.Q_ARG(str, msg))

    def show_success_dialog(self, msg):
        self.success_dialog = SuccessdDialog(msg=msg)
        self.success_dialog.setWindowModality(QtCore.Qt.ApplicationModal)  # 设置为模态对话框
        self.success_dialog.show()

    def show_fail_dialog(self, msg):
        self.fail_dialog = FailedDialog(msg=msg)
        self.fail_dialog.setWindowModality(QtCore.Qt.ApplicationModal)  # 设置为模态对话框
        self.fail_dialog.show()

    # def show_pwd_dialog(self):
    #     self.pwd_dialog = PasswordDialog()
    #     if self.pwd_dialog.exec_() == QtWidgets.QDialog.Accepted:
    #         self.device_pwd = self.pwd_dialog.get_password()
    #         print("输入密码为:", self.device_pwd)
    # ===== 剩余额度监控相关函数已隐藏 =====
    # progressBar
    # def edit_progressBar(self, sum, use):
    #     self.label_12.setText(str(use))
    #     self.label_10.setText(str(sum))
    #     remaining_percentage = ((use) / sum) * 100
    #     self.progressBar.setValue(int(remaining_percentage))
    #     self.edit_label_remaining(str(use))

    # 设置设备标识
    def edit_label_15(self, device_id):
        self.label_15.setText(str(device_id))

    # 设置会员等级
    def edit_label_19(self, dl_lx):
        self.label_19.setText(str(dl_lx))

    def get_labl_19(self):
        return self.label_19.text()
        # 设置激活时间

    def edit_label_jihuotime(self, jihuotime):
        self.label_22.setText(str(jihuotime))

    # 设置到期时间
    def edit_label_endtime(self, endtime):
        self.label_17.setText(str(endtime))

    # 设置Pro类型和Pro总次数显示
    def edit_pro_type_display(self, pro_type, pro_count):
        """设置Pro类型和Pro总次数显示"""
        self.pro_type = pro_type
        self.pro_count = pro_count
        
        # 根据pro_type显示不同的标识
        if pro_type == 1:
            # Pro类型：只显示Pro标识
            count_text = "Pro"
            type_style = "color: #4285F4; font-size: 14px; font-weight: bold;"
        else:
            # Auto类型：只显示Auto
            count_text = "Auto"
            type_style = "color: #34A853; font-size: 14px; font-weight: bold;"
        
        self.label_pro_type_value.setText(count_text)
        self.label_pro_type_value.setStyleSheet(type_style)



    def set_email(self, email):
        # 隐藏当前登录账号显示 -QW
        self.label_26.setText("")

    def update_history_tab_visibility(self, pro_type):
        """根据pro_type更新历史账号标签页的显示状态 -QW
        
        Args:
            pro_type (int): 0=auto（隐藏历史账号标签页），1=pro（显示历史账号标签页）
        """
        self.pro_type = pro_type
        print(f"[main_ui] 📌 设置pro_type={pro_type}")
        
        # 如果存在tab_manager，调用其更新方法
        if hasattr(self, 'tab_manager') and self.tab_manager:
            try:
                self.tab_manager.update_history_tab_visibility(pro_type)
                print(f"[main_ui] ✅ 已调用tab_manager更新历史账号标签页显示状态")
            except Exception as e:
                print(f"[main_ui] ⚠️ 调用tab_manager更新失败: {str(e)}")

    # 更新切换按钮显示状态 -QW
    def update_switch_button_visibility(self):
        """根据qh_type控制切换按钮的显示/隐藏
        qh_type=1时显示切换按钮，qh_type=0或None时隐藏
        """
        if hasattr(self, 'btn_switch_pro_type'):
            # 支持整数和字符串类型的比较 -QW
            if self.qh_type == 1 or self.qh_type == "1":
                self.btn_switch_pro_type.setVisible(True)
                print(f"[切换按钮] qh_type={self.qh_type}，显示切换按钮")
            else:
                self.btn_switch_pro_type.setVisible(False)
                print(f"[切换按钮] qh_type={self.qh_type}，隐藏切换按钮")
    
    # 切换账号类型按钮点击事件 -QW
    def on_switch_pro_type_clicked(self):
        """切换账号类型（Auto <-> Pro）"""
        print(f"[切换账号类型] 当前账号类型: pro_type={self.current_pro_type}")
        
        # 确定目标类型：如果当前是Auto(0)则切换到Pro(1)，否则切换到Auto(0)
        if self.current_pro_type == 0:
            target_pro_type = 1
            target_name = "Pro"
        else:
            target_pro_type = 0
            target_name = "Auto"
        
        print(f"[切换账号类型] 准备切换到: {target_name} (pro_type={target_pro_type})")
        
        # 禁用按钮防止重复点击 -QW
        self.btn_switch_pro_type.setEnabled(False)
        self.btn_switch_pro_type.setText("切换中")
        
        # 保存引用供回调使用 -QW
        self._switch_target_pro_type = target_pro_type
        
        # 在后台线程中执行切换 -QW
        import threading
        def do_switch():
            try:
                from CursorZsApi import CursorZsApi
                api = CursorZsApi()
                code, result = api.switch_pro_type(self.device_code, self.device_code_md5, target_pro_type)
                
                # 保存结果供主线程使用 -QW
                self._switch_result_code = code
                self._switch_result_msg = result
                
                # 使用QTimer在主线程中更新UI -QW
                QtCore.QTimer.singleShot(0, self._on_switch_complete)
                
            except Exception as e:
                print(f"[切换账号类型] ❌ 切换异常: {str(e)}")
                self._switch_result_code = '500'
                self._switch_result_msg = str(e)
                QtCore.QTimer.singleShot(0, self._on_switch_complete)
        
        # 启动后台线程 -QW
        switch_thread = threading.Thread(target=do_switch)
        switch_thread.daemon = True
        switch_thread.start()
    
    def _on_switch_complete(self):
        """切换完成后的回调，在主线程中执行 -QW"""
        try:
            # 恢复按钮状态 -QW
            self.btn_switch_pro_type.setEnabled(True)
            self.btn_switch_pro_type.setText("切换")
            
            code = getattr(self, '_switch_result_code', '500')
            result = getattr(self, '_switch_result_msg', '未知错误')
            
            if code == '200':
                print(f"[切换账号类型] ✅ 切换成功: {result}")
                # 刷新会员状态以更新显示 -QW
                self.refresh_member_info()
            else:
                print(f"[切换账号类型] ❌ 切换失败: {result}")
                self.show_success_dialog(msg=f"切换失败: {result}")
        except Exception as e:
            print(f"[切换账号类型] ❌ 回调异常: {str(e)}")

    def refresh_member_info(self):
        """刷新会员状态信息 -QW"""
        try:
            print("[main_ui] 🔄 开始刷新会员状态...")
            self.initCursor()
            # 同时刷新历史账号列表 -QW
            self.refresh_history_accounts_list()
            self.show_success_dialog(msg='会员状态已刷新')
            print("[main_ui] ✅ 会员状态刷新成功")
        except Exception as e:
            print(f"[main_ui] ❌ 刷新会员状态失败: {str(e)}")
            self.show_fail_dialog(msg=f'刷新失败: {str(e)}')

    def refresh_history_accounts_list(self):
        """刷新历史账号列表 -QW"""
        try:
            if hasattr(self, 'tab_manager') and self.tab_manager:
                if hasattr(self.tab_manager, 'refresh_history_accounts'):
                    self.tab_manager.refresh_history_accounts()
                    print("[main_ui] ✅ 已刷新历史账号列表")
        except Exception as e:
            print(f"[main_ui] ⚠️ 刷新历史账号列表失败: {str(e)}")

    def set_content(self, id, fallback_id=None):
        """获取公告内容，如果获取失败且有fallback_id则尝试获取fallback
        
        公告内容处理规则：
        - 检测到 "----" 时，将其作为换行标志，替换为换行符
        """
        api = CursorZsApi()
        code, dl_lx = api.get_dl_lxfs(id)
        if code == '200' and dl_lx:
            # 将 "----" 替换为换行符 -QW
            formatted_content = dl_lx.replace("----", "\n")
            self.label_5.setText(formatted_content)
        elif fallback_id:
            # 尝试获取fallback公告
            code2, dl_lx2 = api.get_dl_lxfs(fallback_id)
            if code2 == '200' and dl_lx2:
                # 将 "----" 替换为换行符 -QW
                formatted_content = dl_lx2.replace("----", "\n")
                self.label_5.setText(formatted_content)

    def initCursor(self):
        self.get_dl_lxfs('57264c5654d6470a94c5f581b0959f72')
        self.start_check()
        self.edit_label_15(self.device_code_md5)
        api = CursorZsApi()
        code, result_dict = api.initCursorLoginZs30(self.device_code, self.device_code_md5)
        print("code:", code)
        print("result_dict:", result_dict)
        if code == '500':
            # 默认显示Auto公告
            self.set_content('996c8b97292742f4959dd5450fe76bf0')
            jihuo = "未激活"
            self.edit_label_19(jihuo)
            self.edit_label_jihuotime("-")
            self.edit_label_endtime("-")
            self.label_pro_type_value.setText("-")
            return

        if result_dict is None:
            # 默认显示Auto公告
            self.set_content('996c8b97292742f4959dd5450fe76bf0')
            jihuo = "未激活"
            self.edit_label_19(jihuo)
            self.edit_label_jihuotime("-")
            self.edit_label_endtime("-")
            self.label_pro_type_value.setText("-")
        else:
            # 根据pro_type获取对应的公告
            pro_type = result_dict.get("pro_type", 0)
            
            # 保存当前pro_type和qh_type -QW
            self.current_pro_type = pro_type
            self.qh_type = result_dict.get("qh_type")
            print(f"[initCursor] pro_type={pro_type}, qh_type={self.qh_type}")
            
            if pro_type == 1:
                # Pro用户显示Pro公告，如果Pro公告不存在则回退到Auto公告
                self.set_content('996c8b97292742f4959dd5450fe76bf0_pro', '996c8b97292742f4959dd5450fe76bf0')
            else:
                # Auto用户显示Auto公告
                self.set_content('996c8b97292742f4959dd5450fe76bf0')
            sum_count = result_dict["sum_count"]
            over_count = result_dict["over_count"]
            # self.edit_progressBar(sum_count, over_count)
            level_name = result_dict["level_name"]
            self.email = result_dict["email"]
            self.pwd = result_dict["pwd"]
            self.edit_label_19(level_name)
            self.set_email(self.email)
            # 设置Pro类型和Pro总次数显示（pro_type已在上面获取）
            pro_count = result_dict.get("pro_count", 0)
            self.edit_pro_type_display(pro_type, pro_count)
            # 根据pro_type更新历史账号标签页的显示状态（Auto类型不显示）
            self.update_history_tab_visibility(pro_type)
            # 根据qh_type控制切换按钮显示 -QW
            self.update_switch_button_visibility()
            try:
                startTime = datetime.fromisoformat(result_dict["start_time"].replace("Z", "+00:00"))
                startTimeSh = startTime.astimezone(pytz.timezone('Asia/Shanghai'))  # Replace with your local time zone
                self.edit_label_jihuotime(startTimeSh.strftime("%Y-%m-%d"))
            except Exception as e:
                if startTime:
                    self.edit_label_jihuotime(startTime.strftime("%Y-%m-%d"))
            endTime = None
            try:
                endTime = datetime.fromisoformat(result_dict["end_time"].replace("Z", "+00:00"))
                endTimeSh = endTime.astimezone(pytz.timezone('Asia/Shanghai'))  # Replace with your local time zone
                self.edit_label_endtime(endTimeSh.strftime("%Y-%m-%d"))
            except Exception as e:
                if endTime:
                    self.edit_label_endtime(endTime.strftime("%Y-%m-%d"))
            self.loginType = result_dict['loginType']
            if self.loginType == 1:
                pass
            elif self.loginType == 2:
                _translate = QtCore.QCoreApplication.translate
                self.pushButton_3.setText(_translate("MainWindow", "执行自动登录"))
                self.pushButton_4.setVisible(False)
                self.pushButton_8.setVisible(True)

    # 刷新额度
    def refresh_count(self):
        level = self.get_labl_19()
        if level == '未激活':
            self.show_success_dialog(msg='设备未激活')
            return
        api = CursorZsApi()
        code, result_dict = api.refresh_count30(self.device_code, self.device_code_md5)
        print("code:", code)
        print("result_dict:", result_dict)
        if code == '500':
            self.show_success_dialog(result_dict)
            return
        # if result_dict is None:
        #     return
        if result_dict is not None:
            sum_count = result_dict["sum_count"]
            over_count = result_dict["over_count"]
            # self.edit_progressBar(sum_count, over_count)

    def change_jiqima(self):
        """重置机器码功能 -QW"""
        # 创建自定义确认对话框（与登录助手风格一致）-QW
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("提示")
        dialog.setFixedSize(320, 200)
        dialog.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        dialog.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # 主容器 -QW
        main_widget = QtWidgets.QWidget(dialog)
        main_widget.setGeometry(0, 0, 320, 200)
        main_widget.setStyleSheet("""
            QWidget#main_widget {
                border-radius: 30px;
                background-color: rgb(248, 252, 254);
                border: 2px solid black;
            }
        """)
        main_widget.setObjectName("main_widget")
        
        # 主布局 -QW
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(10)
        
        # 标题区域 -QW
        title_widget = QtWidgets.QWidget()
        title_layout = QtWidgets.QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # 警告图标 -QW
        icon_label = QtWidgets.QLabel()
        icon_label.setFixedSize(28, 28)
        icon_label.setStyleSheet("border-image: url(:/icon/警告.png);")
        title_layout.addWidget(icon_label)
        
        # 标题文字 -QW
        title_label = QtWidgets.QLabel("重置机器码")
        title_font = QtGui.QFont("PingFang SC", 15)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: rgb(45, 128, 248);")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        main_layout.addWidget(title_widget)
        
        # 提示内容 -QW
        content_label = QtWidgets.QLabel("此操作用于解决机器码问题，请勿随意点击！\n\n⚠️ Pro账号用户请勿重置机器码！\n如果您是Pro账号用户，请点击「取消」按钮。")
        content_font = QtGui.QFont("PingFang SC", 12)
        content_label.setFont(content_font)
        content_label.setStyleSheet("color: #333333;")
        content_label.setWordWrap(True)
        content_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        main_layout.addWidget(content_label)
        
        main_layout.addStretch()
        
        # 按钮区域 -QW
        btn_widget = QtWidgets.QWidget()
        btn_layout = QtWidgets.QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(15)
        
        btn_layout.addStretch()
        
        # 取消按钮 -QW
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.setFixedSize(90, 32)
        cancel_font = QtGui.QFont("PingFang SC", 12)
        cancel_font.setBold(True)
        cancel_btn.setFont(cancel_font)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: rgb(45, 128, 248);
                border-radius: 9px;
                border: 2px solid rgb(45, 128, 248);
            }
            QPushButton:hover {
                background-color: rgb(45, 128, 248);
                color: white;
            }
            QPushButton:pressed {
                background-color: rgb(35, 118, 238);
                color: white;
            }
        """)
        cancel_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        btn_layout.addWidget(cancel_btn)
        
        # 重置按钮 -QW
        reset_btn = QtWidgets.QPushButton("重置机器码")
        reset_btn.setFixedSize(100, 32)
        reset_font = QtGui.QFont("PingFang SC", 12)
        reset_font.setBold(True)
        reset_btn.setFont(reset_font)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: rgb(45, 128, 248);
                color: white;
                border-radius: 9px;
                border: none;
            }
            QPushButton:hover {
                background-color: rgb(35, 118, 238);
            }
            QPushButton:pressed {
                background-color: rgb(25, 108, 228);
            }
        """)
        reset_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        btn_layout.addWidget(reset_btn)
        
        btn_layout.addStretch()
        
        main_layout.addWidget(btn_widget)
        
        # 用户选择结果 -QW
        user_confirmed = [False]
        
        def on_cancel():
            user_confirmed[0] = False
            dialog.close()
        
        def on_reset():
            user_confirmed[0] = True
            dialog.close()
        
        cancel_btn.clicked.connect(on_cancel)
        reset_btn.clicked.connect(on_reset)
        
        # 显示对话框 -QW
        dialog.exec_()
        
        # 判断用户选择 -QW
        if not user_confirmed[0]:
            print("[突破按钮] 用户取消操作")
            # 取消按钮的选中状态（阻止信号避免再次触发）-QW
            self.pushButton_4.blockSignals(True)
            self.pushButton_4.setChecked(False)
            self.pushButton_4.blockSignals(False)
            return
        
        # 用户选择重置机器码，执行实际操作 -QW
        print("[突破按钮] 用户确认重置机器码，开始执行...")
        try:
            ExitCursor()
            import toomany
            toomany.run()
            tupo41()
            self.show_success_dialog(msg='机器码重置成功')
            open_cursor()
            return
        except ModuleNotFoundError:
            self.show_fail_dialog(msg='需要管理员权限才能执行重置功能')
            return
        except Exception as e:
            self.show_fail_dialog(msg=f'机器码重置失败: {str(e)}')
            return

    def activate(self):
        # 检查当前会员等级
        activation_code = self.lineEdit.text()
        if activation_code == "":
            # 弹框提示 请输入激活码
            self.show_success_dialog(msg='请输入激活码后，再点击激活按钮')
            return
        api = CursorZsApi()
        code, msg = api.activate30(self.device_code, activation_code, self.device_code_md5)
        if code == '500':
            # 弹框提示 激活失败，请检查激活码是否正确
            self.show_success_dialog(msg=msg)
            self.lineEdit.setText("")
            return
        else:
            # 弹框提示 激活成功
            self.initCursor()
            self.show_success_dialog(msg=msg)
            self.lineEdit.setText("")

    def refresh_cursor(self):
        level = self.get_labl_19()
        if level == '青铜':
            self.show_success_dialog(msg='设备未激活')
            return
        bool = self.get_Email()
        if bool == True:
            if self.loginType == 1:
                pass
                self.update_cursor_auth(email=self.email, access_token=self.token, refresh_token=self.token)
                try:
                    tupo41()
                    open_cursor()
                    # 刷新Cursor后，更新会员状态信息和历史账号列表 -QW
                    self.initCursor()
                    self.refresh_history_accounts_list()
                except ModuleNotFoundError:
                    self.show_fail_dialog(msg='tupo41模块未找到')
                except Exception as e:
                    self.show_fail_dialog(msg=f'刷新Cursor时出错: {str(e)}')
            elif self.loginType == 2:
                self.show_success_dialog(msg='获取成功，点击获取密码按钮')
                # 刷新Cursor后，更新会员状态信息和历史账号列表 -QW
                self.initCursor()
                self.refresh_history_accounts_list()

    # 获取邮箱
    def get_Email(self):
        if self.loginType == 1:

            bool = self.reboot_dailog()
            print(bool)
            if bool:
                api = CursorZsApi()
                code, result_dict = api.get_credentials30(self.device_code, self.device_code_md5)
                print("code:", code)
                print("result_dict:", result_dict)
                if (code == '500'):
                    # 弹框提示 请勿频繁多次点击哦
                    self.show_success_dialog(msg=result_dict)
                    return False
                ExitCursor()
                resetter = MachineIDResetter()
                resetter.reset_machine_ids()
                self.email = result_dict.get("email")
                self.token = result_dict.get("token")
                self.pwd = result_dict.get("pwd")
                # 弹框提示 刷新成功
                # self.show_success_dialog(msg='刷新成功')
                self.set_email(self.email)
            else:
                return False
        elif self.loginType == 2:
            api = CursorZsApi()
            code, result_dict = api.get_credentials30(self.device_code, self.device_code_md5)
            print("code:", code)
            print("result_dict:", result_dict)
            if (code == '500'):
                # 弹框提示 请勿频繁多次点击哦
                self.show_success_dialog(msg=result_dict)
                return False
            ExitCursor()
            resetter = MachineIDResetter()
            resetter.reset_machine_ids()
            self.email = result_dict.get("email")
            self.token = result_dict.get("token")
            self.pwd = result_dict.get("pwd")
            # 弹框提示 刷新成功
            # self.show_success_dialog(msg='刷新成功')
            self.set_email(self.email)
        return True

    def execute_login_logic(self):
        ExitCursor()
        auth_manager = CursorAuthManager()
        auth_manager.update_auth(self.email, self.token, self.token)
        token = auth_manager.get_cursor_token()
        email = auth_manager.get_cursor_email()
        print(email,token)
        open_cursor()
        print("执行登录逻辑")

    def update_cursor_auth(self, email=None, access_token=None, refresh_token=None):

        # 更新cursor认证信息
        auth_manager = CursorAuthManager()
        return auth_manager.update_auth(email, access_token, refresh_token)

    def toggle_auto_refresh_cursor(self, checked):
        level = self.get_labl_19()
        if level == '青铜':
            self.show_success_dialog(msg='设备未激活')
            return
        if self.loginType == 1:
            if checked:
                self.auto_refresh_flag = True
                self.auto_refresh_thread = threading.Thread(target=self.auto_refresh_cursor)
                self.auto_refresh_thread.start()
                self.show_success_dialog(msg='自动刷新启用成功')
        elif self.loginType == 2:
            print(self.email)
            print(self.pwd)
            code = None
            try:
                code = get_sifu_code(self.email)
            except Exception as e:
                print("获取验证码失败")
                code = ""

            msg = f'请手动登录\n邮箱：{self.email}\n密码：{self.pwd}\n验证码: {code}'
            # Create and show dialog if it doesn't exist
            if not hasattr(self, 'success_dialog') or not self.success_dialog.isVisible():
                self.success_dialog = SuccessdDialog(msg=msg)
                self.success_dialog.setWindowModality(QtCore.Qt.ApplicationModal)
                self.success_dialog.show()
            else:
                # Update existing visible dialog
                self.success_dialog.update_message(msg)

    def auto_refresh_cursor(self):
        while self.auto_refresh_flag:
            bool = self.get_cursor_use()
            if bool == False:
                api = CursorZsApi()
                code, result_dict = api.get_credentials30(self.device_code, self.device_code_md5)
                print("code:", code)
                print("result_dict:", result_dict)
                if (code == '500'):
                    # 弹框提示 请勿频繁多次点击哦
                    # self.yb_show_success_dialog(result_dict)
                    return
                else:
                    ExitCursor()
                    resetter = MachineIDResetter()
                    resetter.reset_machine_ids()
                    email = result_dict.get("email")
                    token = result_dict.get("token")

                    self.update_cursor_auth(email=email, access_token=token, refresh_token=token)
                    open_cursor()
            time.sleep(30)
            print("30s自动刷新")

    def get_cursor_use(self):
        try:
            auth_manager = CursorAuthManager()
            token = auth_manager.get_cursor_token()
            # print("当前token为：" + token)
            api = CursorZsApi()
            code, msg = api.get_code_email_quota(token)
            msg = int(msg)  # Ensure msg is converted to an integer
            print("当前账号使用次数为" + str(msg))
            if code == '200' and msg <= 50:
                return True
            else:
                return False
        except Exception as e:
            print("换号")
            return False

    def start_check(self):
        device_info = MachineDeviceInfo()
        self.device_code = device_info.get_serial_number()
        self.device_code_md5 = device_info.get_md5_value(self.device_code)
        print("设备码：", self.device_code)
        print("设备码MD5：", self.device_code_md5)
        # pwd = None
        # system = platform.system()
        # Initialize the database
        #
        # if system == "Darwin":
        #     db = SkyCursorDb()
        #     pwd = db.query_data()
        #     if pwd == None:
        #         self.show_pwd_dialog()
        #         item = {'pwd': self.device_pwd}
        #         db.save_data(item)
        #         self.device_pwd = pwd
        #     else:
        #         self.device_pwd = pwd
        # else:
        #     pass

    def remove_spaces_from_activation_code(self):
        """
        自动去除激活码输入框中的所有空格（包括开头、中间、末尾）
        """
        # 获取当前激活码
        current_text = self.lineEdit.text()
        # 去除所有空格：包括普通空格、制表符、换行符等空白字符 -QW
        cleaned_text = ''.join(current_text.split())
        
        # 只有在清理后的文本与原文本不同时才更新，避免无限循环
        if cleaned_text != current_text:
            # 保存当前光标位置
            cursor_position = self.lineEdit.cursorPosition()
            # 计算被移除的空格数量
            spaces_removed = len(current_text) - len(cleaned_text)
            # 更新文本
            self.lineEdit.setText(cleaned_text)
            # 恢复光标位置，考虑被移除的空格
            new_cursor_position = max(0, cursor_position - spaces_removed)
            self.lineEdit.setCursorPosition(new_cursor_position)


import icon_rc

if __name__ == "__main__":

    import sys

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())


