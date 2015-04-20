# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QDriller - Utilities
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
import math
import csv
import numpy as np
import collections
import bisect

from qgis.core import *
from qgis.gui import *


class DrillholeCoordBuilder:
    #a class which calculates the XYZ coords for an entire drillhole
    #creates a series of x,y,z coordinates from an intial collar location and a series of downhole surveys
    #the resultiing ordered dictionary uses downhole length as its key, and a list of [X,Y,Z] coords as the item
    
    def __init__(self, collar, survey):
        self.Xo = float(collar[0])
        self.Yo = float(collar[1])
        self.Zo = float(collar[2])
        self.survey = survey
        #print "survey dict", survey
        self.temp={0:[self.Xo, self.Yo, self.Zo]} #sets up the collar coordinate
       # self.results = collections.OrderedDict()
        #create the list of 3D co-ordinates downhole
            
       
        skeys = len(survey.keys())
        if skeys > 1:
            k = 0
            while k < (skeys-1):
                slist = survey[k]
                sampfrom = float(slist[0])
                
                dip = float(slist[1])
                azi = float(slist[2])
                try:
                    slist2 = survey[k+1]
                    sampto=float(slist2[0])
                except KeyError:
                    sampto = float(collar[3]) #make the last sampto the EOH depth
                   
                coords = self.calc(sampfrom, sampto, dip, azi)
                self.Xo=coords[0]
                self.Yo=coords[1]
                self.Zo=coords[2]
                self.temp[sampto] = coords
                k=k+1
        else:
            slist = survey[0]
            sampfrom = float(slist[0])
            dip = float(slist[1])
            azi = float(slist[2])
            sampto = float(collar[3]) #make the last sampto the EOH depth
            
            coords = self.calc(sampfrom, sampto, dip, azi)
            self.Xo=coords[0]
            self.Yo=coords[1]
            self.Zo=coords[2]
            self.temp[sampto] = coords
         
        #convert into an ordered dictionary (sequential downhole depth) to help with searchability
        self.results = collections.OrderedDict(sorted(self.temp.items()))
        
    def calc(self, sampfrom, sampto, dip, azi):
        #calculates the coordinates at the sampto downhole length using the previous coord as a start poit
        #ie the sampfrom location
        rdip = math.radians(dip)  
        razi = math.radians(azi)

        downholelength = sampto - sampfrom
        segadvance = math.cos(rdip) * downholelength
        X = self.Xo + math.sin(razi) * segadvance
        Y = self.Yo + math.cos(razi) * segadvance
        Z = self.Zo - math.sin(rdip) * downholelength
        coords = [X,Y,Z]
        return coords

class IntervalCoordBuilder:
#a class which calculates the XYZ coords for a specified interval of a given drillhole
#data parsed is the drillhole XYZ dictionary (ordered, keys=downhole depth) and the sart and end of the desired interval
    def __init__(self, drillholedata, sampfrom, sampto):
        #initialise instance variables
        self.dhdata = drillholedata #the XYZ dictionary for the target drillhole
        self.keylist= self.dhdata.keys()
        #print"keylist", self.keylist
        self.sampfrom = sampfrom
        self.sampto = sampto
        #initialise result container which will be used to build geometries
        self.intervalcoords= collections.OrderedDict()
        #execute algorithm to create coords
        self.createCoordList()
    
    def downholeLocator(self, downholedepth):
        #a function to retrieve XYZ coordinates of any given downhole depth
        dhd = downholedepth #the target downhole depth to find
        #print "DHdepth", dhd
        idx = bisect.bisect(self.keylist, dhd) -1 #search for the insertion point suitable for target depth, and give index of closests uphole entry    
        #print "idx", idx
        upholenode = self.keylist[idx] #the dh depth of the closest node uphole of target
        #print"upholenode", upholenode
        dholenode = self.keylist[idx+1]
        #print "dholenode", dholenode
        dhlength = dholenode - upholenode
        extension = dhd-upholenode #the distance past the node to reach desired dh depth
        uhncoord = self.dhdata[upholenode] #retrieve the XYZ coords of the uphole node
        dhncoord = self.dhdata[dholenode]
        #print " node coords", uhncoord, dhncoord
        #the following uses round as a hack to avoid floating point issues with 1 and -1 in the trig functions
        alpha =  math.acos(round((dhncoord[2]-uhncoord[2])/dhlength, 10))
        theta = math.asin(round((dhncoord[0]-uhncoord[0])/dhlength, 10))
        phi = math.asin(round((dhncoord[1]-uhncoord[1])/dhlength, 10))
       
        #calculate the coords for the target dhl using the uphole node and the now known angles
        Xdhl = uhncoord[0] +math.sin(theta)* extension
        Ydhl = uhncoord[1] + math.sin(phi) * extension
        Zdhl = uhncoord[2] + math.cos(alpha) * extension
            
        return [Xdhl, Ydhl, Zdhl]

    def gatherNodes(self):
        #function to collect the coordinates (specifically the dict keys) that fall in the target interval
        inInterval = []
        for k in self.keylist:
            if k >= self.sampfrom and k<=self.sampto:
                inInterval.append(k)
        return inInterval

    def createCoordList(self):
        #create the list of XYZ coords that represents the drillhole interval
        #result is a dictionary of coords (list) with downhole depth as key

        #get start coord
        if self.dhdata.has_key(self.sampfrom):
            pass #this entry will be picked up by gatherNodes
        else:
            self.intervalcoords[self.sampfrom] = self.downholeLocator(self.sampfrom)
        #get middle coords
        for i in self.gatherNodes():
            self.intervalcoords[i]=self.dhdata[i]        

        #getend coord
        if self.dhdata.has_key(self.sampto):
            pass #this entry was picked up by gatherNodes
        else:
            self.intervalcoords[self.sampto] = self.downholeLocator(self.sampto)

class LogDrawer:
#class to draw attributed traces of drillholes from tabular log data
    def __init__(self, drillholedata, logfile, outlogfile, plan=True, sectionplane=None, crs=None, loadcanvas=True):
        self.holecoords = drillholedata #set the XYZ coord data for the drillhole dataset
        self.logfile = logfile #path of the target logfile
        self.outlogfile = outlogfile  #path for output file
        self.projectCRS = crs
        self.loadcanvas = loadcanvas
        self.tlayer = self.createEmptyLog()
        self.plantoggle = plan
        self.sectionplane = sectionplane
        self.logBuilder()
        
    def createEmptyLog(self):
        #function to create a memory layer with correct field types from the csv logfile
        
        csvfile = open(self.logfile, 'rb')
        reader = csv.reader(csvfile)
        header = reader.next()
        # Get sample
        sample = reader.next()
        fieldsample = dict(zip(header, sample))
        #print "fieldsample", fieldsample
        fieldnametypes = {}
        # create dict of fieldname:type
        for key in fieldsample.keys():
            try:
                float(fieldsample[key])
                fieldtype = 'real'
            except ValueError:
                fieldtype = 'string'
            fieldnametypes[key] = fieldtype
        # Build up the URI needed to create memory layer
        uri = "templog?"
        for fld in header:
            uri += 'field={}:{}&'.format(fld, fieldnametypes[fld])
        tlayer = QgsVectorLayer(uri, "templayer", "memory")
        return tlayer

    def logBuilder(self):
        #a function to take an attribute table with drillhole log data and create traces for each entry

        #load the log file 
        logdata = QgsVectorLayer(self.logfile, 'magsus', 'ogr')
        tprov=self.tlayer.dataProvider()
        logprov=logdata.dataProvider()  #probably dont need this  DELETE?
        #create iterator
        logiter = logdata.getFeatures()
        #create the new shapefile 
        writer = QgsVectorFileWriter(self.outlogfile, "CP1250",tprov.fields(), QGis.WKBLineString, self.projectCRS,'ESRI Shapefile')
        #iterate over all log entries and create the trace geometries into the new shapefile
        for logfeature in logiter:
            #initialise variables
            holeid = logfeature.attributes()[logfeature.fieldNameIndex('HoleID')]
            lsampfrom =float( logfeature.attributes()[logfeature.fieldNameIndex('From')])
            lsampto = float(logfeature.attributes()[logfeature.fieldNameIndex('To')])
            logtrace= None  #reset the logtrace container in case of error from previous iteration
            #check that hole is included in subset to be drawn, then draw interval
            if self.holecoords.has_key(holeid):
                #print "holeXYZ", holeXYZ
                #print"from", lsampfrom
                #print"to", lsampto
                try:
                    holeXYZ = self.holecoords[holeid]
                    loginterval = IntervalCoordBuilder(holeXYZ, lsampfrom, lsampto)
                    logresultinterval= loginterval.intervalcoords
                    #print "interval", logresultinterval
                    #create the geometry from the interval coords
                    if self.plantoggle:
                    #create layers in plan view
                        logtrace = planGeomBuilder(logresultinterval)
                    else:
                        logtrace = sectionGeomBuilder(logresultinterval, self.sectionplane)
                        
                except (IndexError, ValueError) as e:
                    msg = "Something wrong with log data in %s at %s to %s: %s" % (holeid, lsampfrom, lsampto, e)
                    print msg
                except KeyError:
                    msg = "Data for hole that does not exist %s" % (holeid)
                    print msg
                #create a new feature, set geometry from above and add the attributes from original data table
                logfeat=QgsFeature()
                try:
                    logfeat.setGeometry(logtrace)
                    logfeat.setAttributes(logfeature.attributes())
                    writer.addFeature(logfeat)
                except TypeError as e:
                    print "geometry could not be made for %s %s %s %s" % (holeid, lsampfrom, lsampto, e)
                #logfeatures.append(logfeat)
        del writer
        
        if self.loadcanvas:
            name = os.path.splitext(os.path.basename(self.outlogfile))[0]
            loglayer =QgsVectorLayer(self.outlogfile, name, 'ogr')
            QgsMapLayerRegistry.instance().addMapLayer(loglayer)

            
class ProfileFromRaster:
    def __init__(self, originX, originY, azi, sectionlength, rasterlayer, outfile):
        
        rpr = rasterlayer.dataProvider()
        razi = math.radians(azi)
        origin = QgsPoint(originX, originY)
        traverseList = [origin]
        pixSize = rasterlayer.rasterUnitsPerPixelX()
        advance = 2 * pixSize
        progress = advance
        while progress < sectionlength:
            newx = originX + math.sin(razi) * progress
            newy = originY + math.cos(razi) * progress
            newpoint = QgsPoint(newx, newy)
            traverseList.append(newpoint)
            progress += advance
            
        progress = 0
        nodestring = []
        for point in traverseList:
            sectionX = progress
            ele = rpr.identify(point, 1).results()
            for band, value in ele.items():
                node = QgsPoint(sectionX, value)
                nodestring.append(node)
            progress += advance

        linestring = QgsGeometry.fromPolyline(nodestring)
        vlayer = QgsVectorLayer("linestring?crs=epsg:4328", "profile", "memory")
        vpr = vlayer.dataProvider()
        writer = QgsVectorFileWriter(outfile, "CP1250", vpr.fields(), QGis.WKBLineString, vpr.crs(), "ESRI Shapefile")
        feat = QgsFeature()
        feat.setGeometry(linestring)
        writer.addFeature(feat)
        del writer
       


def planGeomBuilder(coordlist):
    #takes a dictionary of lists (XYZ) coords. and creates a list of XY coord pairs(ie for plan view.
    #this is then converted into a QGS polyline object that can then be written to a layer
    #keys are unimportant
    nodestring =[]
    for index in coordlist:
        coordsXYZ=coordlist[index]
        node =QgsPoint(coordsXYZ[0], coordsXYZ[1])
        nodestring.append(node)
    linestring = QgsGeometry.fromPolyline(nodestring)
    return linestring   

def sectionGeomBuilder(coordlist, sectionplane):
#a function that takes a dictionary of lists (XYZ) and creates a list of
#coordinate pairs within the defined vertical plane. plane is a list of 
#origon (x,y) and azimuth of the target vertical section [x,y,azi]
    nodestring = []
    for index in coordlist:
        coordsXYZ = coordlist[index]
        tarpoint = [coordsXYZ[0], coordsXYZ[1]]
        delX = tarpoint[0] -sectionplane[0]
        delY =  tarpoint[1] - sectionplane[1]
        dist = math.sqrt( delX**2  +  delY**2)
        #calculate the angle from origin to tarpoint
        alpha = math.atan2(delY, delX) 
        #calculate the angle between the point and the plane 90- azi to set radians to start at north
        beta = alpha - math.radians(90 - sectionplane[2] )
        #calculate the along section coord using beta and distance from origin
        xS = math.cos(beta) * dist
        #NOTE the "normal distance" to the point will be sin(beta)*dist. this may be usefulto exploit for making envelopes
        # ie could use as a screening criteria and not include any nodes that are too far. may need to be careful to handle
        # empty geometries that will be made in the logs, perhaps with some sort of flagging system
        node = QgsPoint(xS, coordsXYZ[2])
        nodestring.append(node)
    linestring = QgsGeometry.fromPolyline(nodestring)
    return linestring
        
def readFromFile(collarfile, surveyfile):
#read collar and survey files into drillholes dict file
    collars = []
    drillholes = {}
    with open(collarfile, 'r') as col:
        next(col)
        readercol=csv.reader(col)
            
        for holeid,x,y,z,EOH in readercol:
            #print "holeid", holeid
            collars=[x,y,z,EOH]
            a = holeid
            i=0
                    
            with open(surveyfile, 'r') as sur:
                next(sur)
                readersur = csv.reader(sur)
                surveys={}
                for hole, depth,dip,azi in readersur:
                    if hole ==a:
                        surv = [depth, dip, azi]
                        surveys[i]=surv
                        i=i+1
                #print"survey from file", surveys
                #determine if desurvey is appropriate (ie more than one survey)
                if len(surveys.keys())>1:
                    desurvey = densifySurvey(surveys)    #run desurvey/densify algorithm
                else:
                    desurvey = surveys
                #print "survey", surveys
                #print "desurvey",desurvey
                drillholes[holeid] = [collars, desurvey]
                #print "drillhole %s loaded and desurveyed" % (holeid) 
    #print drillholes
    return drillholes
	
def densifySurvey(data):
    #a drillhole desurvey tool using simple smooth interpolation of dip and azimuth 
    #between survey points. data is a dict {idx:[depth, dip, azi]} where index  starts at 0 and increments
    d=data
    i=len(d.keys())-1
    entry=0
    newkey=0 # a key variable for creating the new dictionary
    densurvey = {}
    #this works as long as the survey dictionary keys are sequential starting from 0
    while (entry< i):
        next=entry +1 
        list=d[entry]
        list2=d[next] #the next survey in the sequence)
        dh1 = float(list[0])
        dh2= float(list2[0])
        dip1=float(list[1])
        dip2=float(list2[1])
        azi1=float(list[2])
        azi2 = float(list2[2])
        #print dhl, dip1, dip2, azi1, azi2
        #print "iteration", entry
        
        interpdhlList=np.linspace(dh1, dh2, num =10) #create the extra downhole locations
        #need some handling of azis moving between 359 and 001
        if abs(azi1 - azi2) > 300: #detect when azi's are either side of 360
            if azi1 <180:
                azi1 = azi1+360   #add 360 to the smaller number to get a continuous number line to interpolate
            else:
                azi2 = azi2 +360
                
        for item, objects in enumerate(interpdhlList):
            try:
                dipInterp =np.interp(float(objects),[dh1,dh2], [dip1,dip2]) #object is the current dhl to calculate for
                aziInterp =np.interp(float(objects),[dh1,dh2], [azi1,azi2])
                if aziInterp >360:     #correct for azi's greater than 360
                    aziInterp = aziInterp-360
                    
                interpsurv = [objects, dipInterp, aziInterp]
                densurvey[newkey]=interpsurv
                newkey=newkey+1
                #print interpsurv
            except IndexError:
                pass
        entry = entry +1
    
    #this will disturb single survey dictionaries (causing the first key to be 1, so
    #it is best this function is not run on holes with single survey
    newkey=newkey+1 
    #add on final survey entry (from last survey to end of hole) as cant be interpolated
    
    densurvey[newkey]=d[entry]
    return densurvey  
	
def calcXYZ(drillholes):
#calculate XYZ coords for all drillholes
    drillholeXYZ={}
    for holes in drillholes:
        holedata = drillholes[holes]
        collar = holedata[0]
        survey =holedata[1]
        trace = DrillholeCoordBuilder(collar, survey)
        drillholeXYZ[holes] = trace.results
        #print "drillhole %s built" % (holes)
    return drillholeXYZ
    
def writeTraceLayer(drillXYZ, outfile, plan=True, sectionplane=None, loadcanvas=True, crs=None): 
    #create a layer to hold plan drill traces
    crsString = crs.authid()
    uri = "LineString?field=HoleID:string&crs={}".format(crsString)
    layer = QgsVectorLayer(uri, "Drill traces", "memory")
    pr = layer.dataProvider()
    print outfile
    writer = QgsVectorFileWriter(outfile, "CP1250", pr.fields(), QGis.WKBLineString, crs, "ESRI Shapefile")
    #add features to layer

    for holes in drillXYZ:
        holedat = drillXYZ[holes]
        if plan:
            trace = planGeomBuilder(holedat)
        else:
            trace = sectionGeomBuilder(holedat, sectionplane)
            
        feat=QgsFeature()
        try:
            feat.setGeometry(trace)
        except TypeError:
            msg = "Hole %s has invalid geometry" % (holes)
            print msg
        feat.setAttributes([str(holes)])
        writer.addFeature(feat)
        
    del writer
      
    #add layer to map canvas  
    if loadcanvas:
        name = os.path.splitext(os.path.basename(outfile))[0]
        layer= QgsVectorLayer(outfile, name, "ogr" )
        QgsMapLayerRegistry.instance().addMapLayer(layer)

def createCollarLayer(drillholes, outfile, loadcanvas=True, crs=None):
    #function to create a shapefile of the collar locations
    crsString = crs.authid()
    uri = "temp?field=HoleID:string&field=Easting:real&field=Northing:real&field=Elevation:real&field=EOH:real&crs={}".format(crsString)
    templayer = QgsVectorLayer(uri, "Collars", "memory")
    temprov = templayer.dataProvider()
    writer = QgsVectorFileWriter(outfile, "CP1250", temprov.fields(), QGis.WKBPoint, crs, "ESRI Shapefile")

    for features in drillholes:
        collardat = drillholes[features]
        point = QgsPoint(float(collardat[0][0]), float(collardat[0][1]))
        feat=QgsFeature()
        feat.setGeometry(QgsGeometry.fromPoint(point))
        feat.setAttributes([0, features])
        feat.setAttributes([1, float(collardat[0][0])])
        feat.setAttributes([1, float(collardat[0][1])])
        feat.setAttributes([1, float(collardat[0][2])])
        feat.setAttributes([1, float(collardat[0][3])])
        writer.addFeature(feat)
        
    del writer

    if loadcanvas:
        name = os.path.splitext(os.path.basename(outfile))[0]
        layer= QgsVectorLayer(outfile, name, "ogr" )
        QgsMapLayerRegistry.instance().addMapLayer(layer)
        
