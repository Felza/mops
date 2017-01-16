# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mops
                                 A QGIS plugin
 N/A
                              -------------------
        begin                : 2016-10-22
        git sha              : $Format:%H$
        copyright            : (C) 2016 by LNH Water
        email                : kontakt@lnhwater.dk
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
from PyQt4.QtCore import *
#from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPoint, QgsMapLayerRegistry, QgsVectorFileWriter
from qgis.core import *
from PyQt4.QtGui import QAction, QIcon, QFileDialog
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from mops_module_name_dialog import importDialog
from mops_module_save import saveDialog
from mops_module_export_shapefiles import exportShapefilesDialog
from mops_module_export_polygon_to_text import exportPolygonToTextDialog
from os.path import isfile, join, expanduser
import os.path
from os import listdir


class mops:
    """QGIS Plugin Implementation."""


    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'mops_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes

        self.actions = []
        self.menu = self.tr(u'&MOPS plugin')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'mops')
        self.toolbar.setObjectName(u'mops')
        

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('mops', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """
        # Create the dialog (after translation) and keep reference
        self.dlg = importDialog()
        self.dlg.pushButton.clicked.connect(self.select_input_folder)
        self.dlg2 = saveDialog()
        self.dlg2.pushButton.clicked.connect(self.select_output_file)
        self.dlg3 = exportShapefilesDialog()
        self.dlg3.pushButton.clicked.connect(self.select_output_dlg3)
        self.dlg4 = exportPolygonToTextDialog()
        self.dlg4.pushButton.clicked.connect(self.select_output_dlg4)
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/mops/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Import'),
            callback=self.importdlg,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Export lines and points to textfile'),
            callback=self.exportdlg,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Export polygon layers to textfiles'),
            callback=self.exportPolygons,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Save all layers as Shapefiles'),
            callback=self.exportShapefiles,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&MOPS plugin'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def exportPolygons(self):
        #Getting recentpaths
        with open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt") as f:
            content = f.readlines()
        content = [x.strip() for x in content]
        self.dlg4.textEdit.clear()
        self.dlg4.textEdit.addItems(content[6:9])
        # show the dialog
        self.dlg4.show()
        # Run the dialog event loop
        result = self.dlg4.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            folderpath = self.dlg4.textEdit.currentText()
            if folderpath not in content[6:9]:
                content[8] = content[7]
                content[7] = content[6]
                content[6] = folderpath
                output_file = open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt", 'w')
                for line in content:
                    output_file.write(line+"\n")
                output_file.close()
            layers = self.iface.legendInterface().layers()
            for layer in layers:
                if layer.wkbType()==3:
                    output_file = open(folderpath + "\\" + layer.name() + ".txt", 'w')
                    output_file.write("CatchID, Sqn, X, Y\n")
                    for feature in layer.getFeatures():
                        id = feature.attributes()[0]
                        polygon = feature.geometry().asPolygon()
                        i = 1
                        #The first item of polygon is the polyline of the outer ring
                        if polygon:
                            for point in polygon[0]:
                                output_file.write(id + "\t" + str(i) + "\t" + str(point.x()) + "\t" + str(point.y()) + "\n")
                                i += 1
                        else:
                            #This feature has no geometry
                            print(id)
                    output_file.close()


    def exportShapefiles(self):
        #Getting recentpaths
        with open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt") as f:
            content = f.readlines()
        content = [x.strip() for x in content]
        self.dlg3.textEdit.clear()
        self.dlg3.textEdit.addItems(content[3:6])
        # show the dialog
        self.dlg3.show()
        # Run the dialog event loop
        result = self.dlg3.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            folderpath = self.dlg3.textEdit.currentText()
            if folderpath not in content[3:6]:
                content[5] = content[4]
                content[4] = content[3]
                content[3] = folderpath
                output_file = open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt", 'w')
                for line in content:
                    output_file.write(line+"\n")
                output_file.close()
            #Save layers as shapefiles
            layers = self.iface.legendInterface().layers()
            for layer in layers:
                QgsVectorFileWriter.writeAsVectorFormat(layer,
                    folderpath + "\\" + layer.name() + ".shp","utf-8", layer.crs() ,"ESRI Shapefile")


    def moveLines(self, layerId, geoMap):
        pointLayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        for featureId, geo in geoMap.items():
            for feature in pointLayer.getFeatures(QgsFeatureRequest(featureId)):
                layers = self.iface.legendInterface().layers()
                for lineLayer in layers:
                    if lineLayer.wkbType()==2:
                        lineLayer.startEditing()
                        #Fix all "fromnodes" for Catchment
                        if pointLayer.name() == "Catchment":
                            if lineLayer.name() == "CatchCon":
                                catchmuid = feature['CatchMUID']
                                expr = QgsExpression( "\"CatchID\"='{}'".format(catchmuid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[1:]
                                    points.insert(0,feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                        #Fix all "fromnodes" for Load
                        elif pointLayer.name() == "Load":
                            if lineLayer.name() == "LoadCon":
                                muid = feature['MUID']
                                expr = QgsExpression( "\"MUID\"='{}'".format(muid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[1:]
                                    points.insert(0,feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                        elif pointLayer.name() == "Node":
                            #Fix all from- and tonode for Node
                            muid = feature['MUID']
                            if lineLayer.name() == "CatchCon":
                                expr = QgsExpression( "\"NodeID\"='{}'".format(muid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[:-1]
                                    points.append(feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                            elif lineLayer.name() == "LoadCon":
                                expr = QgsExpression( "\"MOUSENodeID\"='{}'".format(muid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[:-1]
                                    points.append(feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                            else:
                                expr = QgsExpression( "\"FROMNODE\"='{}'".format(muid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[1:]
                                    points.insert(0,feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                                expr = QgsExpression( "\"TONODE\"='{}'".format(muid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[:-1]
                                    points.append(feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                        lineLayer.commitChanges()


    def moveLinesToNewNodes(self, layerId, changedAttributesMap):
        lineLayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        layerName = lineLayer.name()
        pr = lineLayer.dataProvider()
        for featureId, qgsAttributeMap in changedAttributesMap.items():
            fromChanged = False
            #Getting the line feature
            for f in lineLayer.getFeatures(QgsFeatureRequest(featureId)):
                lineFeature = f
            for fieldID, newValue in qgsAttributeMap.items():
                field = lineLayer.attributeDisplayName(fieldID)
                if layerName=="CatchCon":
                    if field == "CatchID":
                        catchLayer = QgsMapLayerRegistry.instance().mapLayersByName("Catchment")[0]
                        expr = QgsExpression( "\"CatchMUID\"='{}'".format(newValue))
                        for catchFeature in catchLayer.getFeatures( QgsFeatureRequest(expr)):
                            points = lineFeature.geometry().asPolyline()
                            points = points[1:]
                            points.insert(0,catchFeature.geometry().asPoint())
                            geoMap = {}
                            geoMap[featureId] = QgsGeometry.fromPolyline(points)
                            pr.changeGeometryValues(geoMap)
                            fromChanged = True
                    if field == "NodeID":
                        nodeLayer = QgsMapLayerRegistry.instance().mapLayersByName("Node")[0]
                        expr = QgsExpression( "\"MUID\"='{}'".format(newValue))
                        for nodeFeature in nodeLayer.getFeatures( QgsFeatureRequest(expr)):
                            if not fromChanged:                                
                                points = lineFeature.geometry().asPolyline()
                            points = points[:-1]
                            points.append(nodeFeature.geometry().asPoint())
                            geoMap = {}
                            geoMap[featureId] = QgsGeometry.fromPolyline(points)
                            pr.changeGeometryValues(geoMap)
                elif layerName=="LoadCon":
                    if field == "MUID":
                        loadLayer = QgsMapLayerRegistry.instance().mapLayersByName("Load")[0]
                        expr = QgsExpression( "\"MUID\"='{}'".format(newValue))
                        for loadFeature in loadLayer.getFeatures( QgsFeatureRequest(expr)):
                            points = lineFeature.geometry().asPolyline()
                            points = points[1:]
                            points.insert(0,loadFeature.geometry().asPoint())
                            geoMap = {}
                            geoMap[featureId] = QgsGeometry.fromPolyline(points)
                            pr.changeGeometryValues(geoMap)
                            fromChanged = True
                    if field == "MOUSENodeID":
                        nodeLayer = QgsMapLayerRegistry.instance().mapLayersByName("Node")[0]
                        expr = QgsExpression( "\"MUID\"='{}'".format(newValue))
                        for nodeFeature in nodeLayer.getFeatures( QgsFeatureRequest(expr)):
                            if not fromChanged:                                
                                points = lineFeature.geometry().asPolyline()
                            points = points[:-1]
                            points.append(nodeFeature.geometry().asPoint())
                            geoMap = {}
                            geoMap[featureId] = QgsGeometry.fromPolyline(points)
                            pr.changeGeometryValues(geoMap)
                else:
                    nodeLayer = QgsMapLayerRegistry.instance().mapLayersByName("Node")[0]
                    expr = QgsExpression( "\"MUID\"='{}'".format(newValue))
                    for nodeFeature in nodeLayer.getFeatures( QgsFeatureRequest(expr)):
                        if field == "FROMNODE":
                            points = lineFeature.geometry().asPolyline()
                            points = points[1:]
                            points.insert(0,nodeFeature.geometry().asPoint())
                            geoMap = {}
                            geoMap[featureId] = QgsGeometry.fromPolyline(points)
                            pr.changeGeometryValues(geoMap)
                            fromChanged = True
                        if field == "TONODE":
                            if not fromChanged:                                
                                points = lineFeature.geometry().asPolyline()
                            points = points[:-1]
                            points.append(nodeFeature.geometry().asPoint())
                            geoMap = {}
                            geoMap[featureId] = QgsGeometry.fromPolyline(points)
                            pr.changeGeometryValues(geoMap)
        lineLayer.updateExtents()
            

    def importdlg(self):
        #Getting recentpaths
        with open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt") as f:
            content = f.readlines()
        content = [x.strip() for x in content]
        self.dlg.textEdit.clear()
        self.dlg.textEdit.addItems(content[0:3])
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            folderpath = self.dlg.textEdit.currentText()
            if folderpath not in content[0:3]:
                content[2] = content[1]
                content[1] = content[0]
                content[0] = folderpath
                output_file = open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt", 'w')
                for line in content:
                    output_file.write(line+"\n")
                output_file.close()
            #Go through all files in the folder and find the text file
            #Add the points
            for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                if file[-4:] == ".txt":
                    input = open(folderpath + "\\" + file, 'r')
                    inputline = input.readline()
                    while (inputline != "ENDOFFILE"):
                        if inputline == "POINT\n":
                            self.points(input)
                        inputline = input.readline()
            #Go through all files in the folder and find the text file
            #Add the lines
            #This is done after, because the lines will need the points for field configuration
            for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                if file[-4:] == ".txt":
                    input = open(folderpath + "\\" + file, 'r')
                    inputline = input.readline()
                    while (inputline != "ENDOFFILE"):
                        if inputline == "LINES\n":
                            self.lines(input)
                        inputline = input.readline()
            #Get the polygon layer by a shapefile and create new "small polygon layer"
            for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                if file[-4:] == ".shp":
                    large = QgsVectorLayer(folderpath + "\\" + file, file[:-4], "ogr")
                    dict_a = {}
                    dict_feat_a = {}
                    for feat in large.getFeatures():
                        dict_a[feat.id()] = feat['MopsID']
                        dict_feat_a[feat.id()] = feat
                    catchLayer = QgsMapLayerRegistry.instance().mapLayersByName("Catchment")[0]
                    dict_b = {}
                    for ft in catchLayer.getFeatures():
                        dict_b[ft.id()] = ft['CatchMUID']
                    int_list = list(set(dict_a.values()) & set(dict_b.values()))
                    newFeatures = []

                    for k, v in dict_a.iteritems():
                        if v  in int_list:
                            newFeatures.append(dict_feat_a[k])

                    small = QgsVectorLayer("Polygon?crs=epsg:4326&field=MopsID:string(40)", large.name(), "memory")
                    pr = small.dataProvider()
                    pr.addFeatures(newFeatures)
                    small.updateExtents()
                    #Load in the "small polygon layer" in the bottom of the layer table
                    QgsMapLayerRegistry.instance().addMapLayer(small, False)
                    QgsProject.instance().layerTreeRoot().addLayer(small)

    #For importing
    def points(self,input):
        name = input.readline().rstrip('\n')
        #Set the attribute names and types
        attributes = input.readline().rstrip('\n').split(";;")
        del attributes[-2:]
        uri = "Point?crs=epsg:4326" + self.createuri(attributes)
        vl = QgsVectorLayer(uri, name, "memory")
        vl.committedGeometriesChanges.connect(self.moveLines)
        pr = vl.dataProvider()
        #Get all the data
        data = []
        inputline = input.readline()
        while (inputline != "ENDOFPOINTS\n"):
            data.append(inputline)
            inputline = input.readline()
        #Insert the data into the layer
        for line in data:
            fet = QgsFeature()
            lineList = line.rstrip('\n').split(";;")
            #Remove last 2 elements and use them for geometry
            y = float(lineList.pop())
            x = float(lineList.pop())
            fet.setGeometry(QgsGeometry.fromPoint(QgsPoint(x, y)))
            fet.setAttributes(lineList)
            pr.addFeatures( [ fet ] )
            vl.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(vl)

    #For importing
    def lines(self,input):
        name = input.readline().rstrip('\n')
        #Set the attribute names and types
        attributes = input.readline().rstrip('\n').split(";;")
        del attributes[-1:]
        uri = "LineString?crs=epsg:4326" + self.createuri(attributes)
        vl = QgsVectorLayer(uri, name, "memory")
        ############## creating ValueMaps for all kind of from- and tonodes, so only relevant points can be chosen
        nodeLayer = QgsMapLayerRegistry.instance().mapLayersByName("Node")[0]
        nodeIDs = {}
        for feature in nodeLayer.getFeatures():
            f = feature['MUID']
            nodeIDs[f] = f
        if name == 'CatchCon':
            catchmentLayer = QgsMapLayerRegistry.instance().mapLayersByName("Catchment")[0]
            catchmentIDs = {}
            for feature in catchmentLayer.getFeatures():
                f = feature['CatchMUID']
                catchmentIDs[f] = f
            vl.setEditorWidgetV2(vl.fieldNameIndex('CatchID'),'ValueMap')
            vl.setEditorWidgetV2(vl.fieldNameIndex('NodeID'),'ValueMap')
            vl.setEditorWidgetV2Config(vl.fieldNameIndex('CatchID'),catchmentIDs)
            vl.setEditorWidgetV2Config(vl.fieldNameIndex('NodeID'),nodeIDs)
        elif name == 'LoadCon':
            loadLayer = QgsMapLayerRegistry.instance().mapLayersByName("Load")[0]
            loadIDs = {}
            for feature in loadLayer.getFeatures():
                f = feature['MUID']
                loadIDs[f] = f
            vl.setEditorWidgetV2(vl.fieldNameIndex('MUID'),'ValueMap')
            vl.setEditorWidgetV2(vl.fieldNameIndex('MOUSENodeID'),'ValueMap')
            vl.setEditorWidgetV2Config(vl.fieldNameIndex('FROMUIDMNODE'),loadIDs)
            vl.setEditorWidgetV2Config(vl.fieldNameIndex('MOUSENodeID'),nodeIDs)
        else:
            vl.setEditorWidgetV2(vl.fieldNameIndex('FROMNODE'),'ValueMap')
            vl.setEditorWidgetV2(vl.fieldNameIndex('TONODE'),'ValueMap')
            vl.setEditorWidgetV2Config(vl.fieldNameIndex('FROMNODE'),nodeIDs)
            vl.setEditorWidgetV2Config(vl.fieldNameIndex('TONODE'),nodeIDs)
        ##############
        pr = vl.dataProvider()
        data = []
        inputline = input.readline()
        while (inputline != "ENDOFLINES\n"):
            data.append(inputline)
            inputline = input.readline()
        for line in data:
            lineArray = line.rstrip('\n').split(";;")
            #Getting coordinates
            cordList = lineArray.pop().split("::")
            geoList = []
            for cord in cordList:
                xy = cord.split("..")
                geoList.append(QgsPoint(float(xy[0]),float(xy[1])))
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPolyline(geoList))
            fet.setAttributes(lineArray)
            pr.addFeatures( [ fet ] )
            vl.updateExtents()
        vl.committedAttributeValuesChanges.connect(self.moveLinesToNewNodes)
        QgsMapLayerRegistry.instance().addMapLayer(vl)

    def exportdlg(self):
        #Getting recentpaths
        with open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt") as f:
            content = f.readlines()
        content = [x.strip() for x in content]
        self.dlg2.textEdit.clear()
        self.dlg2.textEdit.addItems(content[9:12])
        # show the dialog
        self.dlg2.show()
        # Run the dialog event loop
        result = self.dlg2.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            filepath = self.dlg2.textEdit.currentText()
            if filepath not in content[9:12]:
                content[11] = content[10]
                content[10] = content[9]
                content[9] = filepath
                output_file = open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt", 'w')
                for line in content:
                    output_file.write(line+"\n")
                output_file.close()
            output_file = open(filepath, 'w')
            layers = self.iface.legendInterface().layers()
            for layer in layers:
                if layer.wkbType()==1:
                    self.writePoint(layer,output_file)
                if layer.wkbType()==2:
                    self.writeLine(layer,output_file)
            output_file.write("ENDOFFILE")
            output_file.close()

    def writePoint(self,layer,output_file):
        #print type and name
        output_file.write("POINT\n")
        output_file.write(layer.name() + '\n')
        #print heading of features
        fields = layer.pendingFields()
        fieldnames = [field.name() for field in fields]
        line = ""
        for field in fields:
            line += field.name() + ".." + field.typeName()
            if field.typeName() == "string":
                line += "::" + str(field.length())
            line += ";;"
        #add coordinates heading
        line += "X_POINT;;Y_POINT\n"
        output_file.write(line)
        #print features
        for f in layer.getFeatures():
            line = ';;'.join(unicode(f[x]) for x in fieldnames)
            geom = f.geometry()
            line += ";;" + str(geom.asPoint().x()) + ";;" + str(geom.asPoint().y()) + "\n"
            unicode_line = line.encode('utf-8')
            output_file.write(unicode_line)
        output_file.write("ENDOFPOINTS\n")
        
    def writeLine(self,layer,output_file):
        #print type and name
        output_file.write("LINES\n")
        output_file.write(layer.name() + '\n')
        #print heading of features
        fields = layer.pendingFields()
        fieldnames = [field.name() for field in fields]
        line = ""
        for field in fields:
            line += field.name() + ".." + field.typeName()
            if field.typeName() == "string":
                line += "::" + str(field.length())
            line += ";;"
        #add coordinates heading
        line += "Points\n"
        output_file.write(line)
        #print features
        for f in layer.getFeatures():
            line = ';;'.join(unicode(f[x]) for x in fieldnames) + ";;"
            geom = f.geometry()
            for point in geom.asPolyline():
                line += str(point.x()) + ".." + str(point.y()) + "::"
            line = line[:-2] + "\n"
            unicode_line = line.encode('utf-8')
            output_file.write(unicode_line)
        output_file.write("ENDOFLINES\n")

    def select_output_file(self):
        filename = QFileDialog.getSaveFileName(self.dlg2, "Select output file ","", '*.txt')
        self.dlg2.textEdit.lineEdit().setText(filename)

    """def select_input_file(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Select input file ","", '*.txt')
        self.dlg.textEdit.setText(filename)"""
    
    def select_input_folder(self):
        foldername = QFileDialog.getExistingDirectory(self.dlg, "Select input folder ", expanduser("~"), QFileDialog.ShowDirsOnly)
        self.dlg.textEdit.lineEdit().setText(foldername)
    
    def select_output_dlg3(self):
        foldername = QFileDialog.getExistingDirectory(self.dlg3, "Select output folder ", expanduser("~"), QFileDialog.ShowDirsOnly)
        self.dlg3.textEdit.lineEdit().setText(foldername)

    def select_output_dlg4(self):
        foldername = QFileDialog.getExistingDirectory(self.dlg4, "Select output folder ", expanduser("~"), QFileDialog.ShowDirsOnly)
        self.dlg4.textEdit.lineEdit().setText(foldername)

    def createuri(self, attributes):
        uri = "";
        for attribute in attributes:
            attributeSplit = attribute.split("..")
            if "string" in attributeSplit[1]:
                as2 = attributeSplit[1].split("::")
                uri = uri + "&field=" + attributeSplit[0] + ":string(" + as2[1] + ")"
            elif "integer" in attributeSplit[1]:
                uri = uri + "&field=" + attributeSplit[0] + ":integer"
            elif "double" in attributeSplit[1]:
                uri = uri + "&field=" + attributeSplit[0] + ":double"
        return uri

