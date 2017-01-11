__author__ = 'wuxiaoyu'

import pymel.core as pm
import maya.mel as mel

def inMeshConnect(src=None, dsts=None):
    """
    connect the outMesh of src object to the inMesh of dest objects
    :param src: `PyNode` source object
    :param dest:`list` destination objects
    :return:
    """
    if not src or not dests:
        sel = pm.ls(sl=True, type=["transform", "mesh"])
        if len(sel)<2:
            pm.warning("Please select one source object "
                       "and at least one target object.")
        else:
            src = sel[0]
            dsts = sel[1:]

    if src.nodeType() == "transform": src = src.getShape()
    for dst in dsts:
        if dst.nodeType() == "transform": dst = dst.getShape()
        src.outMesh.connect(dst.inMesh, force=True)


def editCamera():
    pass


def getLayerDisplayType():
    """
    get current layer type in layer editor
    :return: `string` layer type ("Display", "Render", "Anim")
    """
    gCurrentLayerEditor = pm.melGlobals["gCurrentLayerEditor"]
    pm.setParent(gCurrentLayerEditor)
    type = mel.eval("tabLayout -query -selectTab DisplayLayerUITabLayout")
    return {"DisplayLayerTab": "Display",
            "RenderLayerTab": "Render",
            "AnimLayerTab": "Anim"}[type]


def getLayerSelection():
    """
    get selected display layers
    :return: `list` selected layers
    """
    gCurrentLayerEditor = pm.melGlobals["gCurrentLayerEditor"]
    type = getLayerDisplayType()
    if type != "Display":
        pm.warning("Unsupported layer type. Works on display layers.")
        return []

    pm.setParent(gCurrentLayerEditor)
    selectionArray = []
    layoutName = "LayerEditor" + type + "LayerLayout"
    buttonArray = pm.layout(layoutName, query=True, childArray=True)
    for button in buttonArray:
        if pm.layerButton(button, query=True, select=True):
            selectionArray.append(button)
    return selectionArray

def deleteLayers():
    """
    delete selected display layers
    :return:
    """
    type = getLayerDisplayType()
    if type != "Display":
        pm.warning("Unsupported layer type. Works on display layers.")
        return []
    selectedLayers = getLayerSelection()
    for layer in selectedLayers:
        objs = pm.editDisplayLayerMembers(layer, query=True, fullNames=True)
        pm.delete(layer)
        if objs:
            for obj in objs:
                pm.setAttr(obj+".overrideEnabled", 0)