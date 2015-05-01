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


def makeComposition(canvas):
    #get pointer to the renderer
    render = canvas.mapRenderer()
    layers = canvas.layers()
    layerlist = []
    for lyr in layers:
        layerlist.append(lyr.id())
        
    render.setLayerSet(layerlist)
    #initialise composition
    c = QgsComposition(render)
    x, y = 0, 0
    w, h = c.paperWidth(), c.paperHeight()
    composerMap = QgsComposerMap(c, x ,y, w, h)
    c.addItem(composerMap)
    
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
    sourceArea = QtCore.QRectF(0, 0, c.paperWidth(), c.paperHeight())
    targetArea = QtCore.QRectF(0, 0, width, height)
    c.render(imagePainter, targetArea, sourceArea)
    imagePainter.end()

    image.save(r"E:\Github\out.png", "png")