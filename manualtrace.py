import sys

from skimage import  morphology
from scipy import ndimage

import cv2
import numpy as np
import os, glob
import random
from PyQt5 import uic, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QPen, QFont, QColor
from PyQt5.QtWidgets import *
import PyQt5.QtWidgets as QtWidgets
from ui import *

class Win_Main(QMainWindow):

    def __init__(self):
        super().__init__()

# Private variables
        self.scale = 1
        self.mousehold = False
        self.mouseleftclick = False
        self.workingdir = None
        self.savedir = None
        self.vipirfiles = None
        self.labeledfiles = None
        self.filename = None

        self.cursorCircle = None

        self.binaryI = None
        self.orgI = None
        self.xtraceI = None
        self.otraceI = None
        
        self.o_pmap = None
        self.x_pmap = None
        self.org_pmap = None
        self.bin_pmap = None
# UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

# graphicsView setup
        self.scene = QGraphicsScene()
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.show()

        self.ui.graphicsView.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.ui.graphicsView.wheelEvent = self.wheelZoom
        self.ui.graphicsView.mousePressEvent = self.viewMousePressEvent
        self.ui.graphicsView.mouseMoveEvent = self.viewMouseMoveEvent
        self.ui.graphicsView.mouseReleaseEvent = self.viewMouseReleaseEvent

# button action
        self.ui.openPathButton.clicked.connect(self.setFilePathAction)
        self.ui.newImageButton.clicked.connect(self.openNewVipirFile)
        self.ui.nextImageButton.clicked.connect(self.openNextVipirFile)
        self.ui.prevImageButton.clicked.connect(self.openPrevVipirFile)
        self.ui.brushButton.clicked.connect(self.switchMouseAction)
        self.ui.brushSizeSlider.valueChanged.connect(self.changeSliderValueAction)
        self.ui.showXButton.clicked.connect(self.showXtraceAction)
        self.ui.showOButton.clicked.connect(self.showOtraceAction)
        self.ui.saveButton.clicked.connect(self.saveVipirfile)
        self.ui.showOriginalButton.clicked.connect(self.showOriginalAction)
        self.ui.showBinaryButton.clicked.connect(self.showBinaryAction)

    def wheelZoom(self, event):
        factor = 1
        if event.angleDelta().y() > 0 and self.scale < 20:
            factor = 1.25
        elif self.scale > 0.8:
            factor = 0.8
        self.scale *= factor
        self.ui.graphicsView.scale(factor,factor)

    def drawTraces(self, x, y, O_X, draw=True):
        
        if O_X == 'o':
            trace = self.otraceI
            pmap = self.o_pmap
        if O_X == 'x':
            trace = self.xtraceI
            pmap = self.x_pmap
        pmap = self.scene.removeItem(pmap)
        y = trace.shape[0] - 1 - y
        diameter = self.ui.brushSizeSlider.value()
        for i in range(y-diameter//2, y+diameter//2):
            for j in range(x-diameter//2, x+diameter//2):
                if i >= trace.shape[0] or j >= trace.shape[1] or i<0 or j<0:
                    continue
                if (i-y)**2 + (j-x)**2 < (diameter/2)**2 :
                    trace[i,j] = self.binaryI[i,j] if draw else 0

        frame = np.zeros([trace.shape[0],trace.shape[1],4])
        frame[:,:,1 if O_X == 'o' else 2] = np.flip(trace,axis=0)
        frame[:,:,3] = np.flip(trace,axis=0)
        frame = (frame*255).astype(np.uint8)
        pix = self.getPixMap(frame, alpha=True)
        pmap = self.scene.addPixmap(pix)
        pmap.setZValue(2 if O_X == 'x' else 3)
        if O_X == 'o':
            self.o_pmap = pmap
        if O_X == 'x':
            self.x_pmap = pmap
        return 

    def drawItemMouseMove(self, event):
        pos = self.ui.graphicsView.mapToScene(event.pos())
        x = int(pos.x())
        y = int(pos.y())

        draw = self.mouseleftclick
        if self.ui.showOButton.isChecked() ^ self.ui.showXButton.isChecked():
            if self.ui.showOButton.isChecked() and self.o_pmap is not None:
                self.drawTraces(x,y,'o',draw)
            if self.ui.showXButton.isChecked() and self.x_pmap is not None:
                self.drawTraces(x,y,'x',draw)

        return
    
    def drawItemMousePress(self, event):
        pos = self.ui.graphicsView.mapToScene(event.pos())
        x = int(pos.x())
        y = int(pos.y())

        draw = (event.button() == Qt.LeftButton)
        if self.ui.showOButton.isChecked() ^ self.ui.showXButton.isChecked():
            if self.ui.showOButton.isChecked() and self.o_pmap is not None:
                self.drawTraces(x,y,'o',draw)
            if self.ui.showXButton.isChecked() and self.x_pmap is not None:
                self.drawTraces(x,y,'x',draw)
        return
    
    def viewMouseMoveEvent(self, event):
        pos = self.ui.graphicsView.mapToScene(event.pos())
        x = int(pos.x())
        y = int(pos.y())
        # diameter = self.ui.brushSizeSlider.value()
        diameter = 0
        if x >= diameter/2 and y>= diameter/2 and x < self.scene.width()-diameter/2 and y < self.scene.height()-diameter/2:
            if self.cursorCircle is not None: 
                self.cursorCircle.setPos(pos)

        if self.mousehold and self.ui.brushButton.isChecked(): self.drawItemMouseMove(event)
        QGraphicsView.mouseMoveEvent(self.ui.graphicsView, event)

    
    def viewMousePressEvent(self, event):
        self.mousehold = True
        self.mouseleftclick = (event.button() == Qt.LeftButton)
        # print('pressing mouse button')
        if self.ui.brushButton.isChecked(): self.drawItemMousePress(event)
        QGraphicsView.mousePressEvent(self.ui.graphicsView, event)

    def viewMouseReleaseEvent(self, event):
        self.mousehold = False
        # print('releasing mouse button')
        QGraphicsView.mouseReleaseEvent(self.ui.graphicsView, event)

    def showXtraceAction(self, event):
        self.setCursorCircleColor()
        if self.ui.showXButton.isChecked():
            if self.x_pmap is not None:
                self.x_pmap.setZValue(2)
        else:
            if self.x_pmap is not None:
                self.x_pmap.setZValue(-1)
        return
    
    def showOtraceAction(self, event):
        self.setCursorCircleColor()
        if self.ui.showOButton.isChecked():
            if self.o_pmap is not None:
                self.o_pmap.setZValue(3)
        else:
            if self.o_pmap is not None:
                self.o_pmap.setZValue(-1)
        return
    
    def setCursorCircleColor(self):
        if self.cursorCircle is not None:
            pen = QPen(QColor(255 if self.ui.showXButton.isChecked() else 0, 255 if self.ui.showOButton.isChecked() else 0, 0))
            pen.setWidthF(1.0)
            self.cursorCircle.setPen(pen)
        return
    
    def showOriginalAction(self, event):
        if self.bin_pmap is not None:
            self.bin_pmap.setZValue(-1)
        return 
    
    def showBinaryAction(self, event):
        if self.bin_pmap is not None:
            self.bin_pmap.setZValue(1)
        return     
    
    def openNewVipirFile(self, event):
        if self.vipirfiles is None:
            return
        if self.vipirfiles.shape[0] == 0:
            return
        # if self.filename is None:
        #     self.filename = self.vipirfiles[0]
        # else:
        #     idx = np.where(self.vipirfiles == self.filename)[0][0] + 1
        #     if idx == self.vipirfiles.shape[0]-1 : idx = 0
        #     self.filename = self.vipirfiles[idx]
        while(1):
            self.filename = self.vipirfiles[random.randint(0,self.vipirfiles.shape[0]-1)]
            if self.filename not in self.labeledfiles:
                break

        self.loadVipirFile(os.path.join(self.workingdir, self.filename))
        self.ui.filenameEdit.setText(self.filename)
        self.ui.brushButton.setChecked(False)
        self.switchMouseAction()
        return
        
    def openLabeledVipirFile(self, next_or_prev):
        if self.labeledfiles is None:
            return
        if self.labeledfiles.shape[0] == 0:
            return 
        if self.filename is None or (self.filename not in self.labeledfiles):
            self.filename = self.labeledfiles[-1]

        idx = np.where(self.labeledfiles == self.filename)[0][0]
        idx = idx + next_or_prev
        if idx == self.labeledfiles.shape[0]:
            idx = 0
        if idx == -1:
            idx = self.labeledfiles.shape[0]-1
            
        self.filename = self.labeledfiles[idx]
        self.loadVipirFile(os.path.join(self.savedir, self.filename))
        self.ui.filenameEdit.setText(self.filename)
        self.ui.brushButton.setChecked(False)
        self.switchMouseAction()
        return
    
    def openPrevVipirFile(self, event):
        self.openLabeledVipirFile(-1)
        return

    def openNextVipirFile(self, event):
        self.openLabeledVipirFile(1)
        return

    def changeSliderValueAction(self, event):
        diameter = self.ui.brushSizeSlider.value()
        self.ui.brushSizeLabel.setText(f'Brush Size {diameter}')
        if self.ui.brushButton.isChecked():
            if self.cursorCircle is not None: 
                self.cursorCircle.setRect(-diameter/2, -diameter/2, diameter, diameter)

    def switchMouseAction(self, event = None):
        if self.ui.brushButton.isChecked():
            
            diameter = self.ui.brushSizeSlider.value()
            current_circle = QGraphicsEllipseItem(-diameter/2, -diameter/2, diameter, diameter)
            pen = QPen(QColor(255 if self.ui.showXButton.isChecked() else 0, 255 if self.ui.showOButton.isChecked() else 0, 0))
            pen.setWidthF(1.0)
            current_circle.setPen(pen)
            current_circle.setZValue(4)
            self.scene.addItem(current_circle)
            self.cursorCircle = current_circle

            self.ui.graphicsView.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self.ui.graphicsView.viewport().setCursor(QtCore.Qt.CrossCursor)

        else:
            if self.cursorCircle is not None: 
                self.scene.removeItem(self.cursorCircle)
            self.ui.graphicsView.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.ui.graphicsView.viewport().setCursor(QtCore.Qt.ClosedHandCursor)



    def setFilePathAction(self, event = None, filepath = None):
        if filepath is None:
            # filepath, _ = QFileDialog.getOpenFileName(self, "", "", "Parameter Files (*.npy)")
            filepath = QFileDialog.getExistingDirectory(self, "", "")
            print(filepath)
            if not os.path.isdir(filepath): #os.path.isfile(filepath):
                return
            self.ui.filepathEdit.setText(filepath)
            self.setupWorkingDir(filepath)

    def setupWorkingDir(self, filepath):
        self.workingdir = filepath
        self.savedir = os.path.join(filepath,'labeled')
        if not os.path.exists(self.savedir):
            os.mkdir(self.savedir)

        self.vipirfiles = np.array(glob.glob1(self.workingdir,'*.npy'))
        self.vipirfiles.sort()
        self.ui.fileTotalNumEdit.setText(f'{self.vipirfiles.shape[0]}')
        self.labeledfiles = np.array(glob.glob1(self.savedir,'*.npy'))
        self.labeledfiles.sort()
        self.ui.fileLabeledNumEdit.setText(f'{self.labeledfiles.shape[0]}')

    def getPixMap(self, frame, alpha = None) -> QImage:
        # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel =  frame.shape
        if alpha is None:
            bytesPerLine =  width*3
            frame = QImage(frame.data, width, height, bytesPerLine, QImage.Format_RGB888)
        else:
            bytesPerLine =  width*4
            frame = QImage(frame.data, width, height, bytesPerLine, QImage.Format_ARGB32)
        return QPixmap.fromImage(frame)
    
    def loadVipirFile(self, filename):
        self.scene.clear()
        # if self.cursorCircle is not None:
        self.cursorCircle = None
        self.binaryI = None
        self.orgI = None
        self.xtraceI = None
        self.otraceI = None
        self.o_pmap = None
        self.x_pmap = None

        data = np.load(filename, allow_pickle=True)[()]
        
        self.orgI = np.log10(data['original']+1)
        frame = np.flip(self.orgI, axis=0)
        frame = np.stack([frame for _ in range(3)], axis=2)
        frame = (frame/frame.max()*255).astype(np.uint8)
        
        pix = self.getPixMap(frame)
        self.org_pmap = self.scene.addPixmap(pix)
        self.org_pmap.setZValue(0)


        self.binaryI = getBinaryIonogram(data['original'])
        frame = np.flip(self.binaryI, axis=0)
        frame = np.stack([frame for _ in range(4)], axis=2)
        # print(frame.min())
        frame = (frame*255).astype(np.uint8)
        pix = self.getPixMap(frame, alpha=True)
        self.bin_pmap = self.scene.addPixmap(pix)
        self.bin_pmap.setZValue(1)

        if 'otrace' in data:
            self.otraceI = data['otrace']
        else:
            self.otraceI = np.zeros_like(self.binaryI)

        if 'xtrace' in data:
            self.xtraceI = data['xtrace']
        else:
            self.xtraceI = np.zeros_like(self.binaryI)
        
        # self.otraceI[0:50,0:50] = 1
        frame = np.flip(self.otraceI, axis=0)
        frame = np.stack([frame for _ in range(4)], axis=2)
        frame[:,:,0] = 0
        frame[:,:,2] = 0
        frame = (frame*255).astype(np.uint8)
        opix = self.getPixMap(frame, alpha=True)
        self.o_pmap = self.scene.addPixmap(opix)
        self.o_pmap.setZValue(3 if self.ui.showOButton.isChecked() else -1)

        # self.xtraceI[-50:,-50:] = 1
        frame = np.flip(self.xtraceI, axis=0)
        frame = np.stack([frame for _ in range(4)], axis=2)
        frame[:,:,0] = 0
        frame[:,:,1] = 0
        frame = (frame*255).astype(np.uint8)
        xpix = self.getPixMap(frame, alpha=True)
        self.x_pmap = self.scene.addPixmap(xpix)
        self.x_pmap.setZValue(2 if self.ui.showXButton.isChecked() else -1)

    def saveVipirfile(self, event):
        data = np.load(os.path.join(self.workingdir, self.filename) , allow_pickle=True)[()]
        data['otrace'] = self.otraceI
        data['xtrace'] = self.xtraceI
        np.save(os.path.join(self.savedir, self.filename), data)

        self.labeledfiles = np.array(glob.glob1(self.savedir,'*.npy'))
        self.labeledfiles.sort()
        self.ui.fileLabeledNumEdit.setText(f'{self.labeledfiles.shape[0]}')

        return 
    
def getBinaryIonogram(original):
    crop_region = np.zeros_like(original)
    crop_region[120:-10,30:390] = 1

    original -= (np.min(original)-1)
    original[np.isnan(original)] = 1
    temp1 = np.log10(original)

    sigma1 = 0.85
    sigma2 = 3

    gauss1 = ndimage.gaussian_filter(temp1,sigma1)
    gauss2 = ndimage.gaussian_filter(temp1,sigma2)
    out = gauss1-gauss2
    thresh = out > np.percentile(out,80,axis=0)
    temp3 = morphology.remove_small_objects(thresh, min_size=20, connectivity=1)
    mask_full = temp3 * crop_region
    return mask_full

    


if __name__ == "__main__":
    app = QApplication([])
    wm = Win_Main()
    wm.show()
    app.exec_()