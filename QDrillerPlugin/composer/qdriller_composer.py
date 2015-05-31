# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QDrillerDialog
                                 A QGIS plugin
 Drillhole visualisation tools
                             -------------------
        begin                : 2015-03-30
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Alex Brown
        email                : email
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import sys

from PyQt4 import QtGui, uic, QtCore, Qt
from PyQt4.QtGui import * 

from qgis.core import *
from qgis.gui import *

COM_FORM_CLASS, _ = uic.loadUiType(os.path.join(
os.path.dirname(__file__), 'composerbase.ui'))

class SectionComposer(QMainWindow, COM_FORM_CLASS ):

    def __init__(self, sectioncanvas, maincanvas, parent=None):
        """Constructor."""
        super(QDrillerDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        self.sectionCanvas = sectioncanvas
        self.mainCanvas = mainCanvas
        
    
    #initialise main section composition
    
    #get pointer to section info
    
    #initialise GUI
    
    #function to add linked plan composerMap
    
    #funstions to get the gui to run
    
    #function to save composition to various forms
    
    #

def makeComposition(canvas, maincanvas):
    #get pointer to the section renderer
    render = canvas.mapSettings()
    planrender = maincanvas.mapSettings()

    #initialise composition
    c = QgsComposition(render)
    cp = QgsComposition(planrender)
    cp.setPlotStyle(QgsComposition.Print)
    
    #add section map item
    x, y = 0, 0
    w, h = c.paperWidth(), (c.paperHeight()/2)
    composerMap = QgsComposerMap(c, x ,y, w, h)
    c.addComposerMap(composerMap)
    
    
    #add plan map item
    x, y = 0, c.paperHeight()/2
    w, h = c.paperWidth(), (c.paperHeight()/2)
    composerMapPlan = QgsComposerMap(cp, x ,y, w, h)
    composerMapPlan.setFrameEnabled(True)
    c.addComposerMap(composerMapPlan)
    
    #myWin = QMainWindow()
    #cview = QgsComposerView(myWin)
    #cview.setComposition(c)
    #cvWin = cview.composerWindow()
    #cvWin.show()
    #return
    dpi = c.printResolution()
    dpmm = dpi / 25.4
    width = int(dpmm * c.paperWidth())
    height = int(dpmm * c.paperHeight())

    # create output image and initialize it
    image = QImage(QtCore.QSize(width, height), QImage.Format_ARGB32)
    image.setDotsPerMeterX(dpmm * 1000)
    image.setDotsPerMeterY(dpmm * 1000)
    image.fill(0)

    # render the composition
    imagePainter = QPainter(image)
    print "painter background", imagePainter.backgroundMode()
    c.renderPage(imagePainter,0)
    
    #try with draw function
    #sectsize = QtCore.QSizeF(width, (height/2))
    plansize = QtCore.QSizeF(width, (height/2))
    #sectextent = canvas.extent()
    planextent = maincanvas.extent()
    
    #composerMap.draw(imagePainter, sectextent, sectsize, dpi)
    #composerMapPlan.draw(imagePainter, planextent, plansize, dpi)
    
    
    
    #cp.renderPage(imagePainter,0)
    imagePainter.end()

    image.save(r"E:\Github\out.tiff", "tiff")
