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
        email                : kontakt at lnhwater dot dk
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
from qgis.core import *
from qgis.core import NULL
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox, QProgressBar
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from mops_module_name_dialog import importDialog
from mops_module_save import saveDialog
from mops_module_export_shapefiles import exportShapefilesDialog
from mops_module_export_polygon_to_text import exportPolygonToTextDialog
from mops_module_export_style import exportStyle
from mops_module_export_polygonChanges import exportPolygonChanges
from mops_module_calculate_raster import calculateRaster
from os.path import isfile, join, expanduser, isdir
import os.path
from os import listdir
import codecs
import traceback
import glob


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
        self.dlg.pushButton.clicked.connect(lambda: self.select_input_folder(self.dlg))
        self.dlg2 = saveDialog()
        self.dlg2.pushButton.clicked.connect(lambda: self.select_output_textfile(self.dlg2))
        self.dlg3 = exportShapefilesDialog()
        self.dlg3.pushButton.clicked.connect(lambda: self.select_output_folder(self.dlg3))
        self.dlg4 = exportPolygonToTextDialog()
        self.dlg4.pushButton.clicked.connect(lambda: self.select_output_folder(self.dlg4))
        self.dlg5 = exportPolygonChanges()
        self.dlg5.pushButton.clicked.connect(self.select_output_dlg5)
        self.dlg6 = exportStyle()
        self.dlg6.pushButton.clicked.connect(lambda: self.select_output_folder(self.dlg6))
        self.dlg7 = calculateRaster()
        self.dlg7.pushButton.clicked.connect(lambda: self.select_output_folder(self.dlg7))
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
            text=self.tr(u'Save lines and points to textfile'),
            callback=self.exportdlg,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Save polygon layers to textfiles'),
            callback=self.exportPolygons,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Save selected layers as Shapefiles'),
            callback=self.exportShapefiles,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Save changes made in the polygon layer'),
            callback=self.savePolygonChanges,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Save or import styles'),
            callback=self.exportOrSaveStyle,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Calculate raster'),
            callback=self.calculateRaster,
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

    def calculateRaster(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg7,18,21)
        # show the dialog
        self.dlg7.show()
        # Run the dialog event loop
        result = self.dlg7.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            folderpath = self.dlg7.textEdit.currentText()
            self.updateRecentPaths(folderpath,18,21,recentPaths)
            #Get the dtm
            try:
                dtm_header = []
                h = 6
                dtm_data = []
                with open(folderpath + "\\dtm.txt") as fp:
                    for line in fp:
                        if h>0:
                            dtm_header.append(line)
                            h-=1
                        else:
                            dtm_data.append(line)
                dtm_data_lists = []
                for line in dtm_data:
                    list = []
                    for number in line.rstrip('\n').rstrip().split(" "):
                        list.append(number)
                    dtm_data_lists.append(list)
                #Get the hole data
                hole_header = []
                h = 6
                hole_data = []
                with open(folderpath + "\\hole.txt") as fp:
                    for line in fp:
                        if h>0:
                            hole_header.append(line)
                            h-=1
                        else:
                            hole_data.append(line)
                hole_data_lists = []
                for line in hole_data:
                    list = []
                    for number in line.rstrip('\n').rstrip().split(" "):
                        list.append(number)
                    hole_data_lists.append(list)
                #Get the hmax for hole
                hmax_header = []
                h = 1
                hmax_data = []
                with open(folderpath + "\\hmax_hole.txt") as fp:
                    for line in fp:
                        if h>0:
                            hmax_header.append(line)
                            h-=1
                        else:
                            hmax_data.append(line)
                #The no_data needs to be replaced by 0 and all MUIDs be replaced by a value
                replace = [hole_header[-1].rstrip('\n').split(" ")[-1]]
                replaceWith = ["0"]
                for line in hmax_data:
                    list = line.rstrip('\n').split("\t")
                    replace.append(list[0])
                    replaceWith.append(list[1])
                #Replace numbers in hole
                for i1, list in enumerate(hole_data_lists):
                    for i2, num in enumerate(list):
                        for i3, num2 in enumerate(replace):
                            if num == num2:
                                list[i2] = replaceWith[i3]
                                break
                no_data = replace[0]
                #Calculate
                for idx, list in enumerate(dtm_data_lists):
                    currentHoleList = hole_data_lists[idx]
                    for i, num in enumerate(list):
                        num2 = float(currentHoleList[i])
                        num1 = float(num)
                        num1 = num1 - num2
                        if num1 < 0:
                            list[i] = no_data
                        else: 
                            list[i] = str(num1)
                #Print the result to a new textfile
                listOfLines = []
                for list in dtm_data_lists:
                    listOfLines.append(" ".join(list))
                lineToWrite = ""
                for line in dtm_header:
                    lineToWrite += line
                lineToWrite += "\n".join(listOfLines)
                output_file = open(folderpath + "\\raster_result.txt", 'w')
                output_file.write(lineToWrite)
                output_file.close()
                layer = QgsRasterLayer(folderpath + "\\raster_result.txt", "Raster result")
                QgsMapLayerRegistry.instance().addMapLayer(layer)
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg,"Error","The filepath could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))

    def savePolygonChanges(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg5,15,18)
        # show the dialog
        self.dlg5.show()
        # Run the dialog event loop
        result = self.dlg5.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            filepath = self.dlg5.textEdit.currentText()
            self.updateRecentPaths(filepath,15,18,recentPaths)
            #Do stuff
            try:
                for small in self.iface.legendInterface().layers():
                    if small.wkbType()==3:
                        if small.name()[-5:] == "SMALL":
                            large = QgsVectorLayer(filepath, "namedoesnotmatter", "ogr")
                            text_file = open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\temp\\temp.txt", "r")
                            smallUnmodifiedMopsIDs = text_file.read().split('\n')[:-1]
                            text_file.close()
                            dict_large = {}
                            for f in large.getFeatures():
                                dict_large[f['MopsID']] = f
                            newFeatures = []
                            for k, v in dict_large.iteritems():
                                if k not in smallUnmodifiedMopsIDs:
                                    newFeatures.append(v)
                            newFeatures.extend(small.getFeatures())
                            new_layer = QgsVectorLayer("Polygon?crs=epsg:3044", "duplicated_layer", "memory")
                            new_layer_data = new_layer.dataProvider()
                            attr = large.dataProvider().fields().toList()
                            new_layer_data.addAttributes(attr)
                            new_layer.updateFields()
                            new_layer_data.addFeatures(newFeatures)

                            QgsVectorFileWriter.writeAsVectorFormat(new_layer, filepath[:-4] + "_NEW" + ".shp","utf-8", large.crs() ,"ESRI Shapefile")
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg,"Error","The folder could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))

    def exportOrSaveStyle(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg6,12,15)
        # show the dialog
        self.dlg6.choice_import.click()
        self.dlg6.show()
        # Run the dialog event loop
        result = self.dlg6.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            folderpath = self.dlg6.textEdit.currentText()
            fileCounter = len(glob.glob1(folderpath,"*.qml"))
            reply = QMessageBox.Yes
            if fileCounter > 0:
                reply = QMessageBox.question(self.iface.mainWindow(), 'Warning', 
                 'This folder already contain styles. Styles with identical names will be overwritten.\nAre you sure you want to continue?', QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.updateRecentPaths(folderpath,12,15,recentPaths)
                #Do the work
                try:
                    if self.dlg6.choice_save.isChecked():
                        #Save styles in chosen folder
                        for layer in self.iface.legendInterface().layers():
                            layer.saveNamedStyle(folderpath + "\\" + layer.name() + ".qml")
                    else:
                        #Import styles from chosen folder
                        for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                            if file[-4:] == ".qml":
                                for layer in QgsMapLayerRegistry.instance().mapLayersByName(file[:-4]):
                                    layer.loadNamedStyle(folderpath + "\\" + file)
                        self.iface.mapCanvas().refreshAllLayers()
                except (WindowsError, IOError):
                    QMessageBox.about(self.dlg,"Error","The folder could not be found")
                except:
                    QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))


    #to textfile
    def exportPolygons(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg4,6,9)
        # show the dialog
        self.dlg4.show()
        # Run the dialog event loop
        result = self.dlg4.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            folderpath = self.dlg4.textEdit.currentText()
            self.updateRecentPaths(folderpath,6,9,recentPaths)
            #Do the work
            try:
                layers = self.iface.legendInterface().layers()
                for layer in layers:
                    if layer.wkbType()==3:
                        output_file = codecs.open(folderpath + "\\" + layer.name() + ".txt", 'w',encoding='utf-8')
                        output_file.write("CatchID, Sqn, X, Y\n")
                        for feature in layer.getFeatures():
                            id = feature.attributes()[0]
                            i = 1
                            geo = feature.geometry()
                            #The first item of polygon is the polyline of the outer ring
                            if geo.isMultipart():
                                multi_polygon = geo.asMultiPolygon()
                                j = 1
                                for polygon in geo.asMultiPolygon():
                                    for point in polygon[0]:
                                        output_file.write(id + "&&" + str(j) + "\t" + str(i) + "\t" + str(point.x()) + "\t" + str(point.y()) + "\n")
                                        i += 1
                                    j+=1
                            else:
                                polygon = geo.asPolygon()
                                for point in polygon[0]:
                                    output_file.write(id + "&&1" + "\t" + str(i) + "\t" + str(point.x()) + "\t" + str(point.y()) + "\n")
                                    i += 1

                        output_file.close()
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg,"Error","The folder could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))

    def exportShapefiles(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg3,3,6)
        # show the dialog
        self.dlg3.show()
        # Run the dialog event loop
        result = self.dlg3.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            folderpath = self.dlg3.textEdit.currentText()
            self.updateRecentPaths(folderpath,3,6,recentPaths)
            try:
                #Save layers as shapefiles
                layers = self.iface.legendInterface().selectedLayers()
                for layer in layers:
                    if type(layer) is QgsVectorLayer:
                        QgsVectorFileWriter.writeAsVectorFormat(layer,
                            folderpath + "\\" + layer.name() + ".shp","ascii", layer.crs() ,"ESRI Shapefile")
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg,"Error","The folder could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))

    def moveLines(self, layerId, geoMap):
        pointLayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        pr = pointLayer.dataProvider()
        changedPoints = {}
        for featureId, geo in geoMap.items():
            for feature in pointLayer.getFeatures(QgsFeatureRequest(featureId)):
                #Update pointLayer attribute values for X and Y
                changedAttributes = {}
                changedAttributes[pointLayer.fieldNameIndex('X_POINT')] = float(geo.asPoint().x())
                changedAttributes[pointLayer.fieldNameIndex('Y_POINT')] = float(geo.asPoint().y())
                changedPoints[featureId] = changedAttributes
                #Get and snap all relevant lines
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
        pr.changeAttributeValues(changedPoints)
        self.iface.mapCanvas().refreshAllLayers()

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
        recentPaths = self.getRecentPaths(self.dlg,0,3)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            folderpath = self.dlg.textEdit.currentText()
            #Update combobox of recent paths by adding the new one
            self.updateRecentPaths(folderpath,0,3,recentPaths)

            #Adding progress bar
            self.iface.messageBar().clearWidgets()
            progressMessageBar = self.iface.messageBar()
            progress = QProgressBar()
            progress.setMaximum(100) 
            progress.setTextVisible(True)
            progressMessageBar.pushWidget(progress)

            #Adding a layer group
            group = QgsProject.instance().layerTreeRoot().addGroup(os.path.basename(os.path.normpath(folderpath)))
            errorList = ""
            #Go through all files in the folder and find the text file
            try:
                #Add the points
                j = 0
                progress.setFormat("Loading nodes..")
                for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                    if file[-4:] == ".txt":
                        input = open(folderpath + "\\" + file, 'r')
                        inputline = input.readline()
                        i=1
                        while (inputline != "ENDOFFILE"):
                            if inputline == "POINTS\n":
                                errorList = self.points(input, group, errorList)
                                progress.setValue(100/3/3*i)
                                i+=1
                            elif inputline == "LINES\n":
                                j+=1
                            inputline = input.readline()
                        input.close()
                #Go through all files in the folder and find the text file
                #Add the lines
                #This is done after, because the lines will need the points for field configuration
                progress.setFormat("Loading links..")
                for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                    if file[-4:] == ".txt":
                        input = open(folderpath + "\\" + file, 'r')
                        inputline = input.readline()
                        i=1
                        while (inputline != "ENDOFFILE"):
                            if inputline == "LINES\n":
                                errorList = self.lines(input, group,errorList)
                                progress.setValue(100/3+100/3/j*i)
                                i+=1
                            inputline = input.readline()
                        input.close()
                #Get the polygon layer by a shapefile and create new "small polygon layer"
                for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                    if file[-4:] == ".shp":
                        progress.setFormat("Loading polygons..")
                        progress.setValue(80)
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
                        small = QgsVectorLayer("Polygon?crs=epsg:3044&field=MopsID:string(40)", large.name()+"_SMALL", "memory")
                        pr = small.dataProvider()
                        pr.addFeatures(newFeatures)
                        small.updateExtents()
                        #Load in the "small polygon layer" in the bottom of the layer table
                        QgsMapLayerRegistry.instance().addMapLayer(small, False)
                        QgsProject.instance().layerTreeRoot().addLayer(small)
                        #Save MopsIDs of the small polygon layer, this is for later use if the user chooses to save changes made in the polygon layer
                        aFile = open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\temp\\temp.txt",'w')
                        for k, v in dict_b.iteritems():
                            aFile.write("%s\n" %v)
                        aFile.close()
                #Setting styles if there
                folderpath = folderpath + "\\Style\\"
                if isdir(folderpath):
                    progress.setFormat("Applying styles..")
                    progress.setValue(90)
                    for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                        if file[-4:] == ".qml":
                            for layer in QgsMapLayerRegistry.instance().mapLayersByName(file[0:-4]):
                                layer.loadNamedStyle(folderpath+file)
                #If there's no style folder, use default style
                else:
                    stylepath = expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\DefaultStyles\\"
                    progress.setFormat("Applying styles..")
                    progress.setValue(90)
                    for file in [f for f in listdir(stylepath) if isfile(join(stylepath, f))]:
                        if file[-4:] == ".qml":
                            for layer in QgsMapLayerRegistry.instance().mapLayersByName(file[0:-4]):
                                layer.loadNamedStyle(stylepath+file)
                self.iface.mapCanvas().refreshAllLayers()
                #Sorting layers
                layerList = [c.layer() for c in group.children()]
                my_order = {"Node":0,"Link":1,"Pump":2,"Weir":3,"Orifice":4,"Valve":5,"Catchment":6,"CatchCon":7,"Load":8,"LoadCon":9}
                sortedList = sorted(layerList,key=lambda val: my_order[val.name()])
                for idx, lyr in enumerate(sortedList):
                    group.insertLayer(idx, lyr)
                group.removeChildren(len(layerList),len(layerList))
                #Display message if there were errors
                if errorList:
                    QMessageBox.about(self.dlg,"Error","The following line(s) were not added due to error:\n\n"+errorList)
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg,"Error","The folder could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))
            #removing progressBar
            self.iface.messageBar().clearWidgets()  

    #For importing
    def points(self,input, group, errorList):
        name = input.readline().rstrip('\n')
        #Set the attribute names and types
        attributes = input.readline().rstrip('\n').split(";;")
        uri = "Point?crs=epsg:3044" + self.createuri(attributes)
        vl = QgsVectorLayer(uri, name, "memory")
        vl.committedGeometriesChanges.connect(self.moveLines)
        vl.editFormConfig().setReadOnly(vl.fieldNameIndex('X_POINT'),True)
        vl.editFormConfig().setReadOnly(vl.fieldNameIndex('Y_POINT'),True)
        pr = vl.dataProvider()
        #Get all the data
        data = []
        inputline = input.readline()
        while (inputline != "ENDOFPOINTS\n"):
            data.append(inputline)
            inputline = input.readline()
        #Insert the data into the layer
        for line in data:
            try:
                fet = QgsFeature()
                lineList = line.rstrip('\n').split(";;")
                if len(lineList) != len(attributes):
                    raise
                #Read last 2 elements and use them for geometry
                y = float(lineList[-1])
                x = float(lineList[-2])
                fet.setGeometry(QgsGeometry.fromPoint(QgsPoint(x, y)))
                #Changing "NULL" to QGIS.Null
                lineList2 = []
                for item in lineList:
                    if item == "NULL":
                        item = NULL
                    lineList2.append(item)
                fet.setAttributes(lineList2)
                pr.addFeatures( [ fet ] )
                vl.updateExtents()
            except:
                errorList += line + "\n"
                #QMessageBox.about(self.dlg,"Error","The following line was not added due to an error: "+line)
        QgsMapLayerRegistry.instance().addMapLayer(vl,False)   
        group.addLayer(vl)
        return errorList

    #For importing
    def lines(self,input,group, errorList):
        name = input.readline().rstrip('\n')
        #Set the attribute names and types
        attributes = input.readline().rstrip('\n').split(";;")
        del attributes[-1:]
        uri = "LineString?crs=epsg:3044" + self.createuri(attributes)
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
            try:
                lineArray = line.rstrip('\n').split(";;")
                #Getting coordinates
                cordList = lineArray.pop().split("::")
                if len(lineArray) != len(attributes):
                    raise
                geoList = []
                for cord in cordList:
                    xy = cord.split("..")
                    geoList.append(QgsPoint(float(xy[0]),float(xy[1])))
                fet = QgsFeature()
                fet.setGeometry(QgsGeometry.fromPolyline(geoList))
                #Changing "NULL" to NULL
                lineArray2 = []
                for item in lineArray:
                    if item == "NULL":
                        item = NULL
                    lineArray2.append(item)
                fet.setAttributes(lineArray2)
                pr.addFeatures( [ fet ] )
                vl.updateExtents()
            except:
                errorList += line + "\n"
                #QMessageBox.about(self.dlg,"Error","The following line was not added due to an error: "+line)  
        vl.committedAttributeValuesChanges.connect(self.moveLinesToNewNodes)
        QgsMapLayerRegistry.instance().addMapLayer(vl,False)
        group.addLayer(vl)
        return errorList

    def exportdlg(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg2,9,12)
        # show the dialog
        self.dlg2.show()
        # Run the dialog event loop
        result = self.dlg2.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            filepath = self.dlg2.textEdit.currentText()
            self.updateRecentPaths(filepath,9,12,recentPaths)
            #Do the work
            try:
                output_file = codecs.open(filepath, 'w',encoding='utf-8')
                layers = self.iface.legendInterface().layers()
                for layer in layers:
                    if type(layer) is QgsVectorLayer:
                        if layer.wkbType()==1:
                            self.writePoint(layer,output_file)
                        if layer.wkbType()==2:
                            self.writeLine(layer,output_file)
                output_file.write("ENDOFFILE")
                output_file.close()
            except (WindowsError):
                QMessageBox.about(self.dlg,"Error","The filepath could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))

    def writePoint(self,layer,output_file):
        #print type and name
        output_file.write("POINTS\n")
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
        line = line[:-2] + "\n"
        output_file.write(line)
        #print features
        for f in layer.getFeatures():
            line = ';;'.join(unicode(f[x]) for x in fieldnames) + '\n'
            output_file.write(line)
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
            output_file.write(line)
        output_file.write("ENDOFLINES\n")

    
    def select_input_folder(self, dialog):
        foldername = QFileDialog.getExistingDirectory(dialog, "Select input folder ", dialog.textEdit.currentText(), QFileDialog.DontUseNativeDialog)
        dialog.textEdit.lineEdit().setText(foldername)
    
    def select_output_textfile(self, dialog):
        filename = QFileDialog.getSaveFileName(dialog, "Select output file ",dialog.textEdit.currentText(), '*.txt')
        dialog.textEdit.lineEdit().setText(filename)

    def select_output_folder(self, dialog):
        foldername = QFileDialog.getExistingDirectory(dialog, "Select output folder ", dialog.textEdit.currentText(), QFileDialog.DontUseNativeDialog)
        dialog.textEdit.lineEdit().setText(foldername)

    def select_output_dlg5(self):
        filename = QFileDialog.getOpenFileName(self.dlg5, "Select larger layer ","", '*.shp')
        self.dlg5.textEdit.lineEdit().setText(filename)

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

    def getRecentPaths(self,dialog,lowNum,highNum):
        recentFile = codecs.open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt", 'r', encoding='utf-8')
        content = recentFile.readlines()
        recentFile.close()
        content = [x.strip() for x in content]
        dialog.textEdit.clear()
        dialog.textEdit.addItems(content[lowNum:highNum])
        return content

    def updateRecentPaths(self,folderpath,lowNum,highNum,content):
        #If it's not in recentPaths or at the bottom, add it to the top of the list 
        if folderpath not in content[lowNum:highNum] or folderpath == content[lowNum+2]:
            content[lowNum+2] = content[lowNum+1]
            content[lowNum+1] = content[lowNum]
            content[lowNum] = folderpath
            output_file = codecs.open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt", 'w', encoding='utf-8')
            for line in content:
                output_file.write(line+"\n")
            output_file.close()
        #If it's in the middle
        elif content.index(folderpath)-lowNum == 1:
            content[lowNum+1] = content[lowNum]
            content[lowNum] = folderpath
            output_file = codecs.open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt", 'w', encoding='utf-8')
            for line in content:
                output_file.write(line+"\n")
            output_file.close()