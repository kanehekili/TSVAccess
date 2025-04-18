#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Created on Nov 19, 2023
Registration Spinoff for handlich regisrated members.
Funktions like Checkin/Checkout, RFID RESET , Member blacklist and Abo service 
@author: matze
'''
import sys, traceback, argparse, os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt,QTimer
from PyQt6 import QtWidgets, QtGui, QtCore
# from PyQt6.QtCore import QRegularExpression
# from PyQt6.QtGui import QRegularExpressionValidator
from DBTools import OSTools
import DBTools
from datetime import datetime
import TsvDBCreator

WIN = None

from RegModel import Registration

class VideoWidget(QtWidgets.QFrame):
    """ A class for rendering video coming from OpenCV """
    # trigger = pyqtSignal(float, float, float)
    
    def __init__(self, parent):
        QtWidgets.QFrame.__init__(self, parent)
        self._defaultHeight = 576
        self._defaultWidth = 720
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self._image = None
        self.imageRatio = 16.0 / 9.0
        self.setFrameStyle(QtWidgets.QFrame.Shape.Panel | QtWidgets.QFrame.Shadow.Sunken)
        self.setLineWidth(1)

    def paintEvent(self, event):
        QtWidgets.QFrame.paintEvent(self, event)
        if self._image is None:
            return
        
        qSize = self.size()
        w = qSize.width()
        h = qSize.height()
        imgY = w / self.imageRatio
        if imgY > h:
            imgY = h
            imgX = self.imageRatio * h
            x = (w - imgX) / 2;
            y = 0
        else:
            imgX = w;
            x = 0
            y = (h - imgY) / 2
        
        painter = QtGui.QPainter(self)
        painter.drawImage(QtCore.QRectF(x, y, imgX, imgY), self._image)
        # painter.end()
        
    def sizeHint(self):
        return QtCore.QSize(self._defaultWidth, self._defaultHeight)

    def showFrame(self, aFrame):
        if aFrame is None:  # showing an error icon...
            self.showPicture('web/static/TSV-big.png')
            return
        
    def showPicture(self, path):
        with open(path, 'rb') as filedata:
            contents = filedata.read();
            self._image = QtGui.QImage()
            self._image.loadFromData(contents, format=None)
            box = self._image.rect()
            self.imageRatio = box.width() / float(box.height())
        self.update()
    
    def showImage(self, img):
        self._image = img
        box = self._image.rect()
        self.imageRatio = box.width() / float(box.height())
        self.update()
        
    def setVideoGeometry(self, ratio, rotation):
        if rotation > 0:
            self.imageRatio = 1.0 / float(ratio)
        else:
            self.imageRatio = float(ratio)       

    '''
    def updateUI(self, frameNumber, framecount, timeinfo):
        self.trigger.emit(frameNumber, framecount, timeinfo)
    '''


class QElidedLabel(QtWidgets.QLabel):

    def __init__(self, parent):
        QtWidgets.QLabel.__init__(self, parent)

    def minimumSizeHint(self):
        return self.sizeHint()

    def sizeHint(self):
        hint = self.fontMetrics().boundingRect(self.text()).size()
        qMargins = self.contentsMargins()
        l = qMargins.left()
        t = qMargins.top()
        r = qMargins.right()
        b = qMargins.bottom()
        margin = self.margin() * 2
        defaultSize = super(QElidedLabel, self).sizeHint()
        return QtCore.QSize(
            min(100, hint.width()) + l + r + margin,
            defaultSize.height() + self.fontMetrics().descent() + t + b + margin
            # min(self.fontMetrics().height(), hint.height()) + t + b + margin
        ) 

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        textDoc = QtGui.QTextDocument()
        metrics = QtGui.QFontMetrics(self.font())
        elided = metrics.elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width() - 10)
        textDoc.setPlainText(elided)
        textDoc.drawContents(painter)


# #Main App Window. 
class MainFrame(QtWidgets.QMainWindow):
    
    def __init__(self, qapp,roomName):
        self._isStarted = False
        self.__qapp = qapp
        self.model = Registration()
        self._roomLocation = roomName
        self.qtQueueRunning = False
        super(MainFrame, self).__init__()
        self.setWindowIcon(getAppIcon())
        self.initUI()
        self.centerWindow()
        self.setWindowTitle("Mitglieder Zugangskontrolle")
        self.show()
        qapp.applicationStateChanged.connect(self.__queueStarted)    

    def centerWindow(self):
        frameGm = self.frameGeometry()
        centerPoint = self.screen().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def __queueStarted(self, _state):
        if self.qtQueueRunning:
            return
        self.qtQueueRunning = True
        self.ui_VideoFrame.showFrame(None)
        self._initModel()
        
    def initUI(self):
        # #some default:
        # self.init_toolbar()
        self.ui_VideoFrame = VideoWidget(self)
        self.ui_VideoFrame.setToolTip("Anzeige des Mitglieds") 
        
        self.ui_SearchLabel = QtWidgets.QLabel(self)
        self.ui_SearchLabel.setText("Suche Nachname:")
        
        self.ui_SearchEdit = QtWidgets.QComboBox(self)
        self.ui_SearchEdit.setEditable(True)  # Is that right??
        # self.ui_SearchEdit.currentIndexChanged.connect(self._onSearchChanged)

        self.ui_SearchEdit.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert);
        self.ui_SearchEdit.completer().setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion);
        self.ui_SearchEdit.activated.connect(self._onSearchChanged)
        self.ui_SearchEdit.setToolTip("Nachnamen eingeben, um eine Person zu suchen")

        self.mbrframe = QtWidgets.QFrame()
        self.mbrframe.setFrameStyle(QtWidgets.QFrame.Shape.Box | QtWidgets.QFrame.Shadow.Sunken)
        self.mbrframe.setLineWidth(1)
        # self.mbrframe.setStyleSheet("QGroupBox{border: 1px solid gray; border-radius:5px; margin-left:5px; padding-top:12px;}")
        rowBox = QtWidgets.QVBoxLayout(self.mbrframe)
        nameBox = QtWidgets.QHBoxLayout(self.mbrframe)
        uidBox = QtWidgets.QHBoxLayout(self.mbrframe)
        accessBox = QtWidgets.QHBoxLayout(self.mbrframe)
        
        self.ui_FirstName = QtWidgets.QLabel(self)

        self.ui_LastName = QtWidgets.QLabel(self)
        self.ui_RFID = QtWidgets.QLabel(self)
        self.ui_Birthday = QtWidgets.QLabel(self)
        self.ui_Access = QtWidgets.QLabel(self)  # Mittig setzen und kein Prompt?? Dicker Font
        self.ui_Blocked = QtWidgets.QLabel(self)
        
        nameBox.addWidget(self.ui_FirstName)
        nameBox.addWidget(self.ui_LastName)
        uidBox.addWidget(self.ui_Birthday)
        uidBox.addWidget(self.ui_RFID)
        # accessBox.addWidget(access)
        accessBox.addWidget(self.ui_Access)
        accessBox.addWidget(self.ui_Blocked)
        rowBox.addLayout(nameBox)
        rowBox.addLayout(uidBox)
        rowBox.addLayout(accessBox)

        self.ckiframe = QtWidgets.QFrame()
        self.ckiframe.setFrameStyle(QtWidgets.QFrame.Shape.Box | QtWidgets.QFrame.Shadow.Sunken)
        self.ckiframe.setLineWidth(1)
        
        ckiLbl = QtWidgets.QLabel(self)
        ckiLbl.setText(f"Check in {self._roomLocation}")
        ckiLbl.setStyleSheet("QLabel { font: bold; color:#07A002;}");  # dark theme: #0AFF02
        # self.ui_ckiDisplay=QtWidgets.QLabel(self)
        self.ui_ckiDisplay = QElidedLabel(self)
        ckiBox = QtWidgets.QVBoxLayout(self.ckiframe)
        ckiHeaderBox = QtWidgets.QHBoxLayout(self.ckiframe)
        ckiBox.setContentsMargins(-1, 0, -1, -1);
        
        self.ui_ActivityCombo = QtWidgets.QComboBox(self)
        self.ui_ActivityCombo.currentIndexChanged.connect(self._onActivityChanged)
        self.ui_ActivityCombo.setToolTip("Wo soll eingecheckt werden")
        
        # ckiBox.addWidget(ckiLbl)
        ckiHeaderBox.addWidget(ckiLbl)
        ckiHeaderBox.addWidget(self.ui_ActivityCombo)
        ckiBox.addLayout(ckiHeaderBox)
        ckiBox.addWidget(self.ui_ckiDisplay)

        # self.btnframe = QtWidgets.QFrame()
        # self.btnframe.setFrameStyle(QtWidgets.QFrame.Shape.Box | QtWidgets.QFrame.Shadow.Sunken)
        # self.btnframe.setLineWidth(1)
        self.btnBox = QtWidgets.QHBoxLayout()
        self.btnBox.setSpacing(20)
        self.ui_ckiButton = QtWidgets.QPushButton("Checkin")
        self.ui_ckiButton.setIcon(QtGui.QIcon("./web/static/checkin.png"))
        self.ui_ckiButton.clicked.connect(self._onCKIClicked)
        self.ui_ckiButton.setToolTip("Ein- oder Auschecken") 
        
        self.ui_blockButton = QtWidgets.QPushButton("Sperren")
        self.ui_blockButton.setIcon(QtGui.QIcon("./web/static/halt.png"))
        self.ui_blockButton.clicked.connect(self._onBlockClicked)
        self.ui_blockButton.setToolTip("Nur ändern in Absprache mit GS!")
        
        '''
        Abo -> just an idea  
        
        self.aboframe = QtWidgets.QFrame()
        self.aboframe.setFrameStyle(QtWidgets.QFrame.Shape.Box | QtWidgets.QFrame.Shadow.Sunken)
        self.aboframe.setLineWidth(1)
        rowBox= QtWidgets.QVBoxLayout(self.aboframe)
        buyBox = QtWidgets.QHBoxLayout(self.aboframe)
        updateBox= QtWidgets.QHBoxLayout(self.aboframe)
        buy = QtWidgets.QLabel(self)
        buy.setText("10er Abo kaufen:")
        self.check_sauna = QtWidgets.QCheckBox("Sauna 10er Ticket (€)")
        buyBox.addWidget(buy)
        buyBox.addWidget(self.check_sauna) 
        fix = QtWidgets.QLabel(self)
        fix.setText("Abo korrigieren:")
        self.saunaCount = QtWidgets.QSpinBox()
        #self.saunaCount.setValue(4711)
        updateBox.addWidget(fix)
        updateBox.addWidget(self.saunaCount)
        rowBox.addLayout(buyBox)
        rowBox.addLayout(updateBox)
        '''
        
        self.ui_NewButton = QtWidgets.QPushButton()
        self.ui_NewButton.setText("Neu")
        self.ui_NewButton.setIcon(QtGui.QIcon("./web/static/new.png"))
        self.ui_NewButton.clicked.connect(self._onNewClicked)
        self.ui_NewButton.setToolTip("Weitere Suche starten")
        # self.ui_NewButton.setMinimumWidth(200)

        self.btnBox.addWidget(self.ui_NewButton)
        self.btnBox.addWidget(self.ui_ckiButton)
        self.btnBox.addWidget(self.ui_blockButton)

        box = self.makeGridLayout()
        
        # Without central widget it won't work
        wid = QtWidgets.QWidget(self)
        self.setCentralWidget(wid)    
        # TODO: self.resize
        wid.setLayout(box)
        self.resize(621, 755)  # fits for 640@480 camera resolution
        self._clearFields()

    def _initModel(self):
        QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
        res = self.model.connect()
        QApplication.restoreOverrideCursor()
        if not res:
            dlg = self.getErrorDialog("Datenbank Fehler ", "Datenbank nicht gefunden", "Es besteht keine Verbindung zur Datenbank. Bitte melden!", mail=False)
            dlg.buttonClicked.connect(self._onErrorDialogClicked)
            dlg.show()
        else:
            memberList = self.model.getMembers()
            self.fillSearchCombo(memberList)
            self.fillActivityCombo()

        self.setInitialFocus()  # #ggf controller again
            
        return res

    def _onErrorDialogClicked(self, _):
        self.close()

    def _onBlockClicked(self, _):
        mbr = self.ui_SearchEdit.currentData()
        if mbr:
            mbr.flag = not mbr.flag
            self.model.updateMember(mbr)
            self._clearFields()
        
    def _onCKIClicked(self, _):
        mbr = self.ui_SearchEdit.currentData()
        if mbr:
            now = datetime.now().isoformat()
            Log.info("Member:%s CKI/CKO", mbr.primKeyString())
            cfgEntry = self.currentLocationConfig().configForUserGroup(mbr.access)
            if cfgEntry:
                self.model.saveAccessDate(mbr, now, cfgEntry)
                self._clearFields()
            else:
                Log.warning("No location entry found for CKI. Why is button enabled?")

    def _onActivityChanged(self, _):
        mbr = self.ui_SearchEdit.currentData()
        if mbr:
            QTimer.singleShot(0, lambda: self._updateCheckinData(mbr))

    def setInitialFocus(self): 
        self.ui_SearchEdit.setFocus()
        self.ui_SearchEdit.setStyleSheet("QComboBox { padding: 2px; border-radius: 4px; border: 2px solid rgb(0,160,0);}");

    def fillSearchCombo(self, memberList):
        sortedList = sorted(memberList, key=lambda mbr: mbr.searchName())
        self.ui_SearchEdit.clear()
        self.ui_SearchEdit.addItem("", None)
        for member in sortedList:
            entry = member.searchName()
            self.ui_SearchEdit.addItem(entry, member)
    
    #store all configs for Room Kraftraum Else we would have to select Room and actitivity       
    def fillActivityCombo(self):
        # themes=self.model.configs.allActivities()
        allConfig = self.model.configs.configs
        cfgDic = {}
        for cfg in allConfig:
            # No prepaid support or rooms yet:
            if cfg.room != self._roomLocation and cfg.activity != TsvDBCreator.ACTIVITY_SAUNA:
                continue
            #far future: selective checkin for every room: comboText= cfg.activity+"->"+cfg.room
            res = cfgDic.get(cfg.activity, [])
            res.append(cfg)
            cfgDic[cfg.activity] = res

            
        for key, value in cfgDic.items():
            kx = TsvDBCreator.Konfig([])
            kx.configs=value
            self.ui_ActivityCombo.addItem(key,kx )
        #self.ui_ActivityCombo.setCurrentIndex(0)
            
    def makeGridLayout(self):
        # fromRow(y) - fromColumn(x)  rowSpan(height) columnSpan(width), ggf alignment
        gridLayout = QtWidgets.QGridLayout()
        gridLayout.addWidget(self.ui_VideoFrame, 0, 1, 4, -1);

        gridLayout.addWidget(self.ui_SearchLabel, 4, 1, 1, 1)
        gridLayout.addWidget(self.ui_SearchEdit, 4, 2, 1, 4)
        
        # gridLayout.addWidget(self.ui_FaceCheck, 4, 6, 1, 1)
        # gridLayout.addWidget(self.ui_PhotoButton, 4, 7, 1, 1)
        
        line = QtWidgets.QFrame();
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine);
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken);
    
        gridLayout.addWidget(line, 5, 1, 1, -1)
        
        # gridLayout.addWidget(self.ui_IDLabel, 7, 1, 1, 1)
        # gridLayout.addWidget(self.ui_IDEdit, 7, 2, 1, 5)

        # gridLayout.addWidget(self.ui_FirstNameLabel, 8, 1, 1, 1)
        # gridLayout.addWidget(self.ui_FirstNameEdit, 8, 2, 1, 5)

        # gridLayout.addWidget(self.ui_LastNameLabel, 9, 1, 1, 1)
        # gridLayout.addWidget(self.ui_LastNameEdit, 9, 2, 1, 5)

        # gridLayout.addWidget(self.ui_RFIDLabel, 10, 1, 1, 1)
        # gridLayout.addWidget(self.ui_RFID, 10, 2, 1, 5)
        
        # gridLayout.addWidget(self.ui_AccessLabel, 11, 1, 1, 1)
        # gridLayout.addWidget(self.ui_AccessCombo, 11, 2, 1, 2)
        # gridLayout.addWidget(self.ui_BirthLabel, 11, 4, 1, 3)
        
        gridLayout.addWidget(self.mbrframe, 7, 1, 4, -1)
        gridLayout.addWidget(self.ckiframe, 12, 1, 2, -1)
        # gridLayout.addWidget(self.btnframe,14,1,2,-1)
        # gridLayout.addWidget(self.aboframe,14,1,2,-1)
        
        line = QtWidgets.QFrame();
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine);
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken);
        
        # gridLayout.addWidget(line, 17, 1, 1, -1)
        gridLayout.addLayout(self.btnBox, 15, 1, 2, -1)
        '''
        gridLayout.addWidget(self.ui_NewButton, 17, 1, 1, 2, QtCore.Qt.AlignmentFlag.AlignLeft)
        gridLayout.addWidget(self.ui_ckiButton, 17, 3, 1, 2, QtCore.Qt.AlignmentFlag.AlignCenter)
        gridLayout.addWidget(self.ui_blockButton, 17, 4, 1, 2, QtCore.Qt.AlignmentFlag.AlignRight)
        '''
        
        gridLayout.setRowStretch(1, 1)

        return gridLayout

    def getErrorDialog(self, text, infoText, detailedText, mail=True):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        dlg.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        dlg.setWindowTitle("Fehler")
        dlg.setText(text)
        dlg.setInformativeText(infoText)
        dlg.setDetailedText(detailedText)
        dlg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        spacer = QtWidgets.QSpacerItem(300, 1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        layout = dlg.layout()
        layout.addItem(spacer, layout.rowCount(), 0, 1, layout.columnCount())
        msg = infoText + "\n DETAIL:" + detailedText
        if mail:
            self.model.mailError(msg)
        return dlg
    
    def getMessageDialog(self, text, infoText):
        # dlg = DialogBox(self)
        dlg = QtWidgets.QMessageBox(self)
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Information)
        dlg.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        dlg.setWindowTitle("Hinweis")
        dlg.setText(text)
        dlg.setInformativeText(infoText)
        dlg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        # Workaround to resize a qt dialog. WTF!
        spacer = QtWidgets.QSpacerItem(300, 1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        layout = dlg.layout()
        layout.addItem(spacer, layout.rowCount(), 0, 1, layout.columnCount())
        
        # dlg.setMinimumSize(450, 0)
        return dlg;        
    
    def getQuestionDialog(self, title, text):
        buttonReply = QtWidgets.QMessageBox().question(self, title, text,);
        return buttonReply == QtWidgets.QMessageBox.StandardButton.Yes

    def _clearFields(self):
        self.ui_SearchEdit.clearEditText()
        self.ui_FirstName.setText("Vorname")
        self.ui_LastName.setText("Nachname")
        self.ui_Access.setText('Merkmal')   
        self.ui_Birthday.setText("Burtstag")
        self.ui_RFID.setText("0")
        self.ui_Blocked.setText("Kein Zugang")
        self.ui_VideoFrame.showFrame(None)
        self.ui_ckiDisplay.setText("|")
        self.setButtons(False)
        
    def setButtons(self, areEnabled):
        # TODO: cki and cko should depend current day: odd=cki, even= cki
        self.ui_ckiButton.setEnabled(areEnabled)
        self.ui_blockButton.setEnabled(areEnabled)

    def _updateCKIButton(self, ckiCount,activity):
        if (ckiCount % 2) == 0:
            self.ui_ckiButton.setIcon(QtGui.QIcon("./web/static/checkin.png"))
            self.ui_ckiButton.setText("Checkin")
        else:
            if activity in Registration.CHECKABLE_ACTIVITY:
                self.ui_ckiButton.setIcon(QtGui.QIcon("./web/static/checkout.png"))
                self.ui_ckiButton.setText("Checkout")
            else:
                self.ui_ckiButton.setEnabled(False)
                return                
        self.ui_ckiButton.setEnabled(True)    
            
            
    
    def _updateBlockButton(self, mbr):
        self.ui_blockButton.setEnabled(True)
        if mbr.flag == 0:
            self.ui_blockButton.setIcon(QtGui.QIcon("./web/static/halt.png"))
            self.ui_blockButton.setText("Sperren")
        else:
            self.ui_blockButton.setIcon(QtGui.QIcon("./web/static/Ok.png"))
            self.ui_blockButton.setText("Entsperren")
            
        # setIcon
    
    def currentLocationConfig(self):
        config = self.ui_ActivityCombo.currentData()
        return config #Konfig with correponding entries
        
    def _updateCheckinData(self, mbr):
        # A Konfig with correponding entries:
        konfig = self.currentLocationConfig() 
        #find the correct entry for the current activity:
        foundEntry = konfig.configForUserGroup(mbr.access)
        primentry = konfig.configs[0]
        blockState = "Zugang gesperrt"
        ckiText = "-"
        if foundEntry:    
            res = self.model.todaysAccessDateStrings(mbr.id, foundEntry.activity,foundEntry.room)
            ckiText = "-" if len(res) == 0 else ','.join(res) 
            #!self.ui_ckiDisplay.setText(ckiText)
            aboOK,aboMsg = self.model.isValidAboAccess(mbr,foundEntry)
            if not aboOK:
                Log.warning("Abo data:%s",aboMsg)
                self.ui_ckiButton.setEnabled(False)
                self._displayUpdateResult(aboMsg, ckiText)
                return                
            
            feeError = self.model.haveFeesBeenPaid(mbr, foundEntry.paySection)
            if not feeError:
                blockState= "Zugang gültig "
                if foundEntry.paySection in TsvDBCreator.PREPAID_INDICATOR:
                    blockState = f"{blockState}[{aboMsg}]"
                self._updateCKIButton(len(res),foundEntry.activity)
                self._displayUpdateResult(blockState, ckiText)
                return
            Log.warning("Member invalid fee")
            self.ui_ckiButton.setEnabled(False)
            self._displayUpdateResult("Nicht bezahlt",ckiText)
            return
        else:
            ckiText = "Kein Zugang für Bereich %s:Ticket nicht für aktuellen Zeitpunkt oder Ort"% (primentry.activity)
            self.ui_ckiButton.setEnabled(False)
            self._displayUpdateResult(blockState, ckiText)
        Log.warning("member update fail:%s",ckiText)   

    def _displayUpdateResult(self,blockState,ckiText):
        self.ui_Blocked.setText(blockState)
        self.ui_ckiDisplay.setText(ckiText)

    def _displayMemberFace(self, member):
        raw = self.model.loadPicture(member)
        if raw == None:
            self.getErrorDialog("Verbindungsproblem", "Bilder sind nicht erreichbar", "Der Server, der die Bilder  liefern soll ist nicht erreichbar - Der Fehler wurde per eMail gemeldet").show()
            return False
        if raw == self.model.NOT_FOUND:
            self.ui_VideoFrame.showFrame(None)
            return True
            
        try:
            img = QtGui.QImage()
            img.loadFromData(raw)
            self.ui_VideoFrame.showImage(img)
        except:
            Log.exception("Pic load failed")
            return False
        return True

    def setMemberFields(self, mbr):  # TODO
        self.ui_FirstName.setText(mbr.firstName)
        self.ui_LastName.setText(mbr.lastName)
        acc = '-' if not mbr.access else mbr.access 
        self.ui_Access.setText(acc)
        self.ui_Birthday.setText(mbr.birthdayString())
        # vorsicht! rfid kann null sein - nicht eingecheckt...
        tecCode = "-" if not mbr.rfidString() else mbr.rfidString()
        self.ui_RFID.setText(tecCode + " / " + mbr.primKeyString())
        # prepaid = mbr.currentAbo[1]
        # self.saunaCount.setValue(prepaid)

    @QtCore.pyqtSlot(int)
    def _onSearchChanged(self, idx):
        mbr = self.ui_SearchEdit.itemData(idx)
        if mbr:
            Log.debug("Member selected:%s", mbr.primKeyString())
            self.setMemberFields(mbr)
            if not (mbr.picpath and self._displayMemberFace(mbr)):
                Log.warning("Unregistered:%s!", mbr.primKeyString())
                self.ui_VideoFrame.showFrame(None)
                self.ui_Blocked.setText("Nicht registriert")
                self.setButtons(False)
                return

            # valid
            QTimer.singleShot(0, lambda: self._updateCheckinData(mbr))
            self._updateBlockButton(mbr)

    @QtCore.pyqtSlot()
    def _onNewClicked(self):
        self.ui_SearchEdit.setCurrentIndex(-1)
        self._clearFields()  
        self.setInitialFocus()   

        
def getAppIcon():
    return QtGui.QIcon('./web/static/tsv_logo_100.png')


def handle_exception(exc_type, exc_value, exc_traceback):
    """ handle all exceptions """
    if WIN is not None:
        infoText = str(exc_value)
        detailText = "*".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        WIN.getErrorDialog("Unexpected error", infoText, detailText).show()
        Log.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


def parse():
    parser = argparse.ArgumentParser(description="MemberControl")
    parser.add_argument('-d', dest="debug", action='store_true', help="Debug logs")
    parser.add_argument('-r', dest="room", type=str, default=TsvDBCreator.LOC_KRAFTRAUM, help="Room from Konfig (Kraftraum)")
    return parser.parse_args()    


def main(args):

    # todo speed up camera lookup. check log and promote: -c nbr
    if OSTools.checkIfInstanceRunning("TsvMemberControl"):
        print("App already running")
        sys.exit()
        
    try:
        global Log
        global WIN
        wd = OSTools.getLocalPath(__file__)
        OSTools.setMainWorkDir(wd)
        OSTools.setupRotatingLogger("TSVMC", args.debug)
        Log = DBTools.Log
        if args.debug:
            OSTools.setLogLevel("Debug")
        else:
            OSTools.setLogLevel("Info")
        Log.info("--- Start TsvMemberControl ---")
        argv = sys.argv
        app = QApplication(argv)
        app.setWindowIcon(getAppIcon())
        room = args.room
        WIN = MainFrame(app,room)  # keep python reference!
        # ONLY windoze, if ever: app.setStyleSheet(winStyle())
        # app.setStyle(QtWidgets.QStyleFactory.create("Fusion"));
        app.exec()
        # logging.shutdown()
    except:
        with open('/tmp/error.log', 'a') as f:
            f.write(traceback.format_exc())
        traceback.print_exc(file=sys.stdout)
        Log.exception("Error in main:")
        # ex_type, ex_value, ex_traceback
        sys_tuple = sys.exc_info()
        QtWidgets.QMessageBox.critical(None, "Error!", str(sys_tuple[1]))


if __name__ == '__main__':
    sys.excepthook = handle_exception
    sys.exit(main(parse()))
    pass
