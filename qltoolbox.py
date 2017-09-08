__author__ = 'wuxiaoyu'

import pymel.core as pm
from maya import OpenMayaUI as omui
import maya.mel as mel
import os
import qlutils
import mayautils
try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    from PySide2 import __version__
    from shiboken2 import wrapInstance
except ImportError:
    from PySide.QtCore import *
    from PySide.QtGui import *
    from PySide.QtUiTools import *
    from PySide import __version__
    from shiboken import wrapInstance

map(reload,[qlutils, mayautils])

mayaMainWindowPtr = omui.MQtUtil.mainWindow()
mayaMainWindow = wrapInstance(long(mayaMainWindowPtr), QWidget)


_win = None
def show():
    global _win
    if _win == None:
        _win = QLToolBoxUI()
    _win.show()

class QLToolBoxUI(QWidget):

    def __init__(self, *args, **kwargs):
        super(QLToolBoxUI, self).__init__(*args, **kwargs)

        # load qualoth plugin if it's not loaded
        if not pm.pluginInfo("qualoth", query=True, loaded=True):
            try:
                pm.loadPlugin("qualoth")
            except:
                pm.error("Unable to load qualoth plugin")
                return False

        # Parent widget under Maya main window
        self.setParent(mayaMainWindow)
        self.setWindowFlags(Qt.Window)

        # Set the object name
        self.setObjectName('QLToolBoxUI_uniqueId')
        self.setWindowTitle('QLToolBox')
        self._initUI()

        self._copiedMapValue = []

    def _initUI(self):
        loader = QUiLoader()
        currentDir = os.path.dirname(__file__)
        uiFile = QFile(currentDir+"/qltoolbox.ui")
        uiFile.open(QFile.ReadOnly)
        self.ui = loader.load(uiFile, parentWidget=self)
        uiFile.close()

        # self.ui = qltoolboxui.Ui_qlToolTabWidget()
        # self.ui.setupUi(self)

        # map tool tab
        self._updateQLObjComboBox()
        self.ui.paintMapButton.clicked.connect(self._setMapPaintContext)
        self.ui.resetMapButton.clicked.connect(self._doResetMap)
        self.ui.exportMapButton.clicked.connect(self._doExportMap)
        self.ui.importMapButton.clicked.connect(self._doImportMap)
        self.ui.normalizeMapButton.clicked.connect(self._doNormalizeMap)
        self.ui.copyButton.clicked.connect(self._doCopyMap)
        self.ui.pasteButton.clicked.connect(self._doPasteMap)
        self.ui.mirrorMapButton.clicked.connect(self._doMirrorMap)
        self.ui.qlObjectComboBox.currentIndexChanged.connect(self._updateMapList)
        self.ui.showPaintedCheckBox.stateChanged.connect(self._updateMapList)

        # utilities tab
        self.ui.exportPropertyButton.clicked.connect(self._doExportMaterialProperty)
        self.ui.importPropertyButton.clicked.connect(self._doImportMaterialProperty)
        self.ui.inmeshConnectButton.clicked.connect(self._doInmeshConnect)
        self.ui.cameraZoomButton.clicked.connect(self._doCameraZoom)
        self.ui.clearCacheButton.clicked.connect(self._doClearCache)
        self.ui.truncateCacheButton.clicked.connect(self._doTruncateCache)
        self.ui.updateInitialStatesButton.clicked.connect(self._doUpdateInitialStates)

        # selection button group
        self.ui.selectSolverButton.clicked.connect(self._doSelectSolver)
        self.ui.selectClothNodeButton.clicked.connect(self._doSelectClothNode)
        self.ui.selectInMeshButton.clicked.connect(self._doSelectInMesh)
        self.ui.selectOutMeshButton.clicked.connect(self._doSelectOutMesh)
        self.ui.selectRestShapeButton.clicked.connect(self._doSelectRestShape)
        self.ui.selectColliderNodeButton.clicked.connect(self._doSelectColliderNode)
        self.ui.selectColliderMeshButton.clicked.connect(self._doSelectColliderMesh)
        self.ui.selectColliderOffsetButton.clicked.connect(self._doSelectColliderOffset)
        self.ui.selectConstraintsButton.clicked.connect(self._doSelectConstraints)
        self.ui.selectSpringsButton.clicked.connect(self._doSelectSprings)

        # cache blend tab
        self.ui.loadCacheButton.clicked.connect(self._doCacheBlend)
        self.ui.createMeshMixerButton.clicked.connect(self._doCreateMeshMixer)
        self.ui.bakeMeshButton.clicked.connect(self._doBakeMesh)

    def _getSelectedMapAttrs(self):
        attrList = []
        selectedItems = self.ui.mapListWidget.selectedItems()
        for item in selectedItems:
            print attrList.append(item.text())

        # for idx in range(self.ui.mapListWidget.count()):
        #     item = self.ui.mapListWidget.item(idx)
        #     if item.checkState() == Qt.Checked:
        #         attrList.append(item.text())
        return attrList

    def _doResetMap(self):
        attrs = self._getSelectedMapAttrs()
        if not attrs or QMessageBox.question(self, "Reset Map",
                             "Reset the selected maps?",
                             QMessageBox.Ok,
                             QMessageBox.Cancel) == QMessageBox.Cancel:
            return None
        qlutils.resetMap(self._getCurrentQLObject(), attrs)
        self._setMapPaintContext()
        self._updateMapList()

    def _doExportMap(self):
        target = self._getCurrentQLObject()
        if not target: return None
        filePath = pm.fileDialog2(fileFilter="*.map", dialogStyle=2)
        if filePath:
            attrList = self._getSelectedMapAttrs()
            if not attrList:
                attrList = qlutils.mapAttrs
            qlutils.exportMap(target, filePath[0], attrList)

    def _doImportMap(self):
        target = self._getCurrentQLObject()
        if not target: return None
        filePath = pm.fileDialog2(fileFilter="*.map", dialogStyle=2, fileMode=1)
        if filePath:
            attrList = self._getSelectedMapAttrs()
            if not attrList:
                attrList = qlutils.mapAttrs
            qlutils.importMap(target, filePath[0], attrList)

    def _setMapPaintContext(self):
        mapItem = self.ui.mapListWidget.currentItem()
        if not mapItem: return
        mapName = mapItem.text()

        targetNode = self._getCurrentQLObject()
        if targetNode.nodeType() == "qlClothShape":
            pm.select(targetNode.outputMesh.connections(type="mesh"))
        else:
            pm.select(targetNode.output.connections(type="mesh"))

        mapValue = pm.getAttr("{0}.{1}".format(targetNode.name(), mapName))
        attr_min, attr_max = 0, max(mapValue)

        mel.eval('artSetToolAndSelectAttr("artAttrCtx", "{0}.{1}.{2}");'
                .format(targetNode.nodeType(), targetNode.name(), mapName))
        if attr_max == 0: return
        mel.eval('artAttrCtx -e -colorrangelower {0} `currentCtx`'.format(attr_min))
        mel.eval('artAttrCtx -e -colorrangeupper {0} `currentCtx`'.format(attr_max))
        mel.eval('artAttrCtx -e -maxvalue {0} `currentCtx`'.format(attr_max))
        pm.toolPropertyWindow()


    def _doNormalizeMap(self):
        attrs = self._getSelectedMapAttrs()
        if not attrs or QMessageBox.question(self, "Normalize Map",
                             "Normalize the selected maps?",
                             QMessageBox.Ok,
                             QMessageBox.Cancel) == QMessageBox.Cancel:
            return None
        qlutils.normalizeMap(self._getCurrentQLObject(), attrs)
        self._setMapPaintContext()


    def _updateQLObjComboBox(self):
        qlObjects = pm.ls(type=["qlClothShape", "qlColliderShape"])
        self.ui.qlObjectComboBox.clear()
        for obj in qlObjects:
            self.ui.qlObjectComboBox.addItem(obj.name())

        selected = pm.ls(sl=True,
                         type=["qlClothShape", "qlColliderShape", "transform", "mesh"])
        if selected:
            qlNode = qlutils.getQLClothNode(selected[0])
            if not qlNode:
                qlNode = qlutils.getQLColliderNode(selected[0])
            if qlNode:
                self.ui.qlObjectComboBox.setCurrentIndex(
                    self.ui.qlObjectComboBox.findText(qlNode.name()))
        self._updateMapList()

    def _updateMapList(self):

        # get attr list
        target = self._getCurrentQLObject()
        if not target: return None
        attrList = qlutils.mapAttrs[qlutils.getQLType(target)]

        if self.ui.showPaintedCheckBox.isChecked():
            tmpList = []
            if qlutils.getQLType(target) == qlutils.qlTypes[0]: #cloth
                print "cloth type", target
                for attr in attrList:
                    if pm.getAttr("{0}.{1}Flag".format(target.name(), attr)):
                        print pm.getAttr("{0}.{1}Flag".format(target.name(), attr))
                        tmpList.append(attr)
            elif qlutils.getQLType(target) == qlutils.qlTypes[1]: #collider
                print "collider type", target
                for attr in attrList:
                    defaultValue = 0 if attr == "priorityMap" else 1
                    attrMap = pm.getAttr("{0}.{1}".format(target.name(), attr))
                    attrMapFlag = [attrMap[i] for i in range(len(attrMap)) if attrMap[i] != defaultValue]
                    if len(attrMapFlag) != 0:
                        tmpList.append(attr)
                print tmpList
            attrList = tmpList

        # update list widget
        mapList = self.ui.mapListWidget
        mapList.clear()
        for attr in attrList:
            QListWidgetItem(attr, mapList)

        # clear copied map value
        # self._copiedMapValue = []

    def _doCopyMap(self):
        target = self._getCurrentQLObject()
        if not target: return None
        selAttr = self._getSelectedMapAttrs()
        if len(selAttr) > 0:
            self._copiedMapValue = pm.getAttr(target.name()+"."+selAttr[0])

        # TODO copy map based on position

    def _doPasteMap(self):
        target = self._getCurrentQLObject()
        if not target: return None
        selAttr = self._getSelectedMapAttrs()
        if len(selAttr) > 0:
            for attr in selAttr:
                pm.setAttr(target.name()+"."+attr, self._copiedMapValue)

        # TODO paste map based on position


    def _doMirrorMap(self):
        target = self._getCurrentQLObject()
        if not target: return None
        selAttr = self._getSelectedMapAttrs()
        axis = ["x", "y", "z"][self.ui.mirrorAxisComboBox.currentIndex()]
        direction = "+" if self.ui.mirrorDirCheckBox.isChecked() else "-"
        qlutils.mirrorQLMap(direction+axis, target, selAttr)


    def _doExportMaterialProperty(self):
        sel = pm.ls(sl=True, type=["transform", "mesh", "qlCloth"])
        if not sel or not qlutils.getQLClothNode(sel[0]):
            pm.warning("Please select one cloth object to export material property.")
            return None

        filePath = pm.fileDialog2(fileFilter="*.property", dialogStyle=2)
        if filePath:
            qlutils.exportMaterialProperties(filePath, sel[0])


    def _doImportMaterialProperty(self):
        sel = pm.ls(sl=True, type=["transform", "mesh", "qlCloth"])
        if not sel or not qlutils.getQLClothNode(sel[0]):
            pm.warning("Please select one cloth object to import material property.")
            return None
        filePath = pm.fileDialog2(fileFilter="*.property", dialogStyle=2, fileMode=1)
        if filePath:
            qlutils.importMaterialProperties(filePath, sel[0])


    def _doInmeshConnect(self):
        sel = pm.ls(sl=True, type=["transform", "mesh"])
        if len(sel)<2:
            pm.warning("Please select one source mesh and at least one target mesh.")
            return None
        mayautils.inMeshConnect(sel[0], sel[1:])

    def _getCurrentQLObject(self):
        objectName = self.ui.qlObjectComboBox.currentText()
        return pm.PyNode(objectName) if objectName else None


    def _doCacheBlend(self):
        sel = pm.ls(sl=True, type=["transform", "mesh"])
        if not sel \
           or sel[0].nodeType() == "transfrom" and sel[0].getShape().nodeType() != "mesh":
            pm.warning("Please select cloth mesh to create cache blend.")
            return None

        cachePath = pm.fileDialog2(dialogStyle=2, fileMode=1)
        if not cachePath:
            return None

        clothMesh = sel[0] if sel[0].nodeType() == "transform" else sel[0].getParent()

        timeNode = pm.PyNode("time1")
        blendOutMesh = pm.duplicate(clothMesh, name=clothMesh.name()+"_blend1")[0]
        cacheInMesh = pm.duplicate(clothMesh, name=clothMesh.name()+"_orig_blend1")[0]
        cacheInMesh.hide()
        qlCacheNode = pm.createNode("qlCache")
        cacheInMesh.outMesh.connect(qlCacheNode.input)
        qlCacheNode.output.connect(blendOutMesh.inMesh)
        timeNode.outTime.connect(qlCacheNode.time)
        qlCacheNode.cacheName.set(cachePath)
        qlCacheNode.perFrameCache.set(1)
        qlCacheNode.startTime.set(pm.playbackOptions(query=True, minTime=True))


    def _doCreateMeshMixer(self):
        pm.mel.qlCreateMeshMixer()


    def _doBakeMesh(self):
        pm.mel.qlBakeMeshPerFrame()


    def _doUpdateInitialStates(self):
        qlutils.updateInitialStates()


    def _doConnectRestShapes(self):
        pass

    def _doCameraZoom(self):
        pass
        # cameratools.CbCamCrop()


    def _doClearCache(self):
        pm.mel.qlClearCache()

    def _doTruncateCache(self):
        pm.mel.qlTruncateCache()

    def _doSelectSolver(self):
        pm.mel.qlConvertSelectionToSolvers()

    def _doSelectClothNode(self):
        pm.mel.qlConvertSelectionToClothes()

    def _doSelectInMesh(self):
        sel = pm.ls(sl=True)
        if not sel: return None
        pm.select(qlutils.getQLClothInMesh(sel[0]))

    def _doSelectOutMesh(self):
        sel = pm.ls(sl=True)
        if not sel: return None
        pm.select(qlutils.getQLClothOutMesh(sel[0]))

    def _doSelectRestShape(self):
        sel = pm.ls(sl=True)
        if not sel: return None
        pm.select(qlutils.getQLRestShape(sel[0]))

    def _doSelectColliderNode(self):
        sel = pm.ls(sl=True)
        if not sel: return None
        pm.select(qlutils.getQLColliderNode(sel[0]))

    def _doSelectColliderMesh(self):
        sel = pm.ls(sl=True)
        if not sel: return None
        pm.select(qlutils.getQLColliderMesh(sel[0]))

    def _doSelectColliderOffset(self):
        sel = pm.ls(sl=True)
        if not sel: return None
        pm.select(qlutils.getQLColliderOffset(sel[0]))

    def _doSelectConstraints(self):
        pm.mel.qlConvertSelectionToConstraints()

    def _doSelectSprings(self):
        pm.mel.qlConvertSelectionToSprings()