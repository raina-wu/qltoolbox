__author__ = 'wuxiaoyu'

import pymel.core as pm
import json
import sys

# if pm.pluginInfo('qualoth',loaded=True, query=True):
#     pass
# else:
#     pm.loadPlugin('qualoth.so')


qlTypes = ['cloth', 'collision']
mapAttrs = {}
mapAttrs['cloth'] = [
                        'airDragMap',
                        'bendMap',
                        'bendDampMap',
                        'densityMap',
                        'fieldMap',
                        'frictionMap',
                        'lengthScaleMap',
                        'plasticityMap',
                        'pressureMap',
                        'proximityCriterionMap',
                        'rubberMap',
                        'selfCollisionMap',
                        'shearMap',
                        'solidCollisionMap',
                        'solutionMap',
                        'stretchMap',
                        'softConstraintMap',
                        'stretchDampMap',
                        'viscousDampMap',
                        'wrinkleMap'
                    ]
mapAttrs['collision'] = [
                            'offsetMap',
                            'collisionMap',
                            'frictionMap',
                            'priorityMap'
                        ]

materialProperties = [
                        'lengthScale',
                        'density',
                        'stretch',
                        'shear',
                        'stretchDamp',
                        'bend',
                        'bendDamp',
                        'bendYield',
                        'bendPlasticity',
                        'airDrag',
                        'rubber',
                        'viscousDamp',
                        'friction',
                        'pressure',
                        'overrideGravity',
                        'gravity0',
                        'gravity1',
                        'gravity2',
                        'overrideCompression',
                        'compression',
                        'anisotropicControl',
                        'uStretchScale',
                        'vStretchScale',
                        'hysteresisName'
                        ]

def resetMap(target, attrList=None):
    """
    reset maps
    :param target: `PyNode` qualoth node which the maps belong to
    :param attrList: `list` list of map attributes
    :return:
    """
    attrList = mapAttrs if not attrList else attrList
    for attr in attrList:
        mapValues = pm.getAttr(target.name()+"."+attr)
        pm.setAttr(target.name()+"."+attr, [1.0]*len(mapValues))
        pm.setAttr(target.name()+"."+attr+"Flag", False)


def normalizeMap(target, attrList=None):
    """
    normalize map value
    :param target: qualoth node which the map belong to
    :param attrList: map list
    :return:
    """
    attrList = mapAttrs if not attrList else attrList
    for attr in attrList:
        mapValues = pm.getAttr(target.name()+"."+attr)
        maxValue = max(mapValues)
        if maxValue == 0: continue
        normalizedValues = map(lambda value:value/maxValue, mapValues)
        pm.setAttr(target.name()+"."+attr, normalizedValues)

        globalAttr = attr[:-3]
        newAttrValue = pm.getAttr(target.name()+"."+globalAttr) * maxValue
        pm.setAttr(target.name()+"."+globalAttr, newAttrValue)

def getQLType(target=None):
    if getQLClothNode(target):
        return qlTypes[0]
    elif getQLColliderNode(target):
        return qlTypes[1]
    else:
        return None


def getQLInputMesh(target):
    """
    get input mesh of the qualoth cloth or collider
    :param target: `PyNode` target cloth or collider
    :return: `PyNode` the input mesh node
    """
    targetType = getQLType(target)
    if targetType not in qlTypes:
        return None

    if targetType == qlTypes[0]:
        qlCloth = getQLClothNode(target)
        qlConverter = qlCloth.inputGeometry.connections(type="qlConverter")[0]
        return  qlConverter.input.connections(type="mesh", shapes=True)[0]
    else:
        qlCollider = getQLColliderNode(target)
        qlTriangulate = qlCollider.input.connections(type="qlTriangulate")[0]
        return qlTriangulate.input.connections(type="mesh", shapes=True)[0]


def buildSymmetryMap(srcAxis, srcVertices):
    """
    build a symmetry map for the source vertices
    :param srcAxis: `string` axis to mirror from (+x, -x, +y, -y, +z, -z)
    :param srcVertices: `list` source vertices MeshVertex list
    :return: `dict` symmetry Map
    """

    # filter source vertices to contain only vertices in source axis
    axisIdx = {"x":0, "y":1, "z":2}[srcAxis[-1]]
    direction = {"-":-1, "+":1}[srcAxis[0]]
    tmpSrcVertices = []
    for vertex in srcVertices:
        if vertex.getPosition(space="object")[axisIdx]*direction > 0:
            tmpSrcVertices.append(vertex)
    srcVertices = tmpSrcVertices
    if len(srcVertices) < 1:
        return None


    # build symmetry map based on input mesh
    # {srcVert:mirrorVert}
    # {MeshVertex(qlCollider1Offset.vtx[277]):MeshVertex(qlCollider1Offset.vtx[155])}
    symMap = {}
    for vertex in srcVertices:
        # # use input mesh to calculate symmetry map
        # mesh = getQLInputMesh(vertex.node())
        # vertex = mesh.vtx[vertex.indices()[0]]
        mesh = vertex.node()

        # get mirrored vertex position
        vPosition = vertex.getPosition(space="object")
        vPosition[axisIdx] = vPosition[axisIdx] * -1

        # get mirrored vertex id based on position
        polyId = mesh.getClosestPoint(vPosition, space="object")[1]
        polyVerts = mesh.f[polyId].getVertices()
        minDist = sys.float_info.max
        minVId = polyId
        for vId in polyVerts:
            dist = (mesh.vtx[vId].getPosition()-vPosition).length()
            if  dist < minDist:
                minDist = dist
                minVId = vId
        symMap[vertex] = mesh.vtx[minVId]

    return symMap


def mirrorQLMap(srcAxis, target, attrList=None, symmetryMap=None):
    """
    mirror qualoth attribute map (cloth, collider)
    :param srcAxis: `string` axis to mirror from (+x, -x, +y, -y, +z, -z)
    :param target: `list` or `PyNode` target MeshVertex list or mesh
    :param attrList: `list` target attribute list
    :param symmetryMap: `dict` symmetry map for the target vertices or mesh
    :return:
    """
    # prepare target MeshVertex list
    # use input mesh to calculate symmetrical info
    if isinstance(target, list):
        mesh = getQLInputMesh(target[0].node())
        target = pm.ls(target, fl=True)
        targetVerts = []
        for v in target:
            targetVerts.append(mesh.vtx[v.indices()[0]])
    else:
        mesh = getQLInputMesh(target)
        targetVerts = pm.ls(pm.polyListComponentConversion(mesh, tv=True),
                            fl=True)

    # build symmetry map for once
    if not symmetryMap:
        symmetryMap = buildSymmetryMap(srcAxis, targetVerts)

    # mirror map
    targetNode = target[0].node() if isinstance(target, list) else target
    targetType = getQLType(targetNode)
    if not attrList: attrList = mapAttrs[targetType]
    qlNode = getQLClothNode(targetNode) if targetType == qlTypes[0] \
                                        else getQLColliderNode(targetNode)
    for attr in attrList:
        mapValue = pm.getAttr(qlNode.name()+"."+attr)
        for srcVert, dstVert in symmetryMap.iteritems():
            mapValue[dstVert.indices()[0]] = mapValue[srcVert.indices()[0]]
        pm.setAttr(qlNode.name()+"."+attr, mapValue)


def copyMap(targetNode, srcAttr, dstAttr):
    """
    copy map values.
    :param targetNode: qualoth node which the maps belong to
    :param srcAttr: source map
    :param dstAttr: destination map
    :return:
    """
    srcAttrValue = pm.getAttr(targetNode.name()+"."+srcAttr)
    pm.setAttr(targetNode.name()+"."+dstAttr, srcAttrValue)


def blendCache():
    pass


def exportMap(target, filePath, attrList=None):
    """
    export painted qualoth map.
    :param target: `PyNode` qualoth object to export map from
    :param filePath: `string` map file path
    :param attrList: `list` list of map attributes to export
    :return:
    """
    targetType = getQLType(target)
    if targetType not in qlTypes:
        pm.warning("Please select a cloth or collider to export map.")
        return

    if not attrList:
        attrList = mapAttrs[targetType]

    target = getQLClothNode(target) if targetType==qlTypes[0] \
                                    else getQLColliderNode(target)

    attrDict = {}
    for attr in attrList:
        attrDict[attr] = pm.getAttr("{0}.{1}".format(target, attr))

    f = open(filePath, 'w')
    f.write(json.dumps(attrDict, indent=2))
    f.close()

    # TODO to support position-based maps in addition to index-based maps





def importMap(target, filePath, attrList=None):
    """
    import quoloth map from file.
    :param target: `PyNode` qualoth object to import map to
    :param filePath: `string` map file path
    :param attrList: `list` list of map attributes for import
    :return:
    """
    targetType = getQLType(target)
    if targetType not in qlTypes:
        pm.warning("Please select a cloth or collider to import map.")
        return

    try:
        with open(filePath, 'r') as f:
            maps = json.load(f)
    except:
        pm.error("Error loading map file.")
        return

    attrList = mapAttrs if not attrList else attrList
    target = getQLClothNode(target) if targetType==qlTypes[0] \
                                    else getQLColliderNode(target)
    for attr, mapValue in maps.iteritems():
        if attr in attrList:
            pm.setAttr("{0}.{1}".format(target.name(), attr), mapValue)

    # TODO to support position-based maps in addition to index-based maps



def getQLColliderNode(target):
    """
    get the Qualoth qlColliderShape node related to the target.
    :param target: `PyNode` node from where to get the related qlColliderShape node.
    :return: `PyNode`
    """
    if target.nodeType() == "transform":
        target = target.getShape()
        if not target: return None

    if target.nodeType() == "qlColliderShape":
        return target
    elif target.nodeType() == "mesh":
        qlColliderNode = target.inMesh.connections(shapes=True,
                                                type="qlColliderShape")
        qlTriangulate = target.worldMesh.connections(type="qlTriangulate")
        if qlTriangulate:
            qlColliderNode = qlTriangulate[0].output.connections(shapes=True,
                                                        type="qlColliderShape")
        return qlColliderNode[0] if qlColliderNode else None
    else:
        return None

def getQLClothNode(target):
    """
    get the Qualoth qlClothShape node related to the target.
    :param target: `PyNode` node from where to get the related qlClothShape node.
                    (inmesh, outmesh, cloth node)
    :return: `PyNode`
    """
    if target.nodeType() == "transform":
        target = target.getShape()
        if not target: return None

    if target.nodeType() == "qlClothShape":
        return target
    elif target.nodeType() == "mesh":
        qlClothNode = target.inMesh.connections(shapes=True,
                                                type="qlClothShape")
        qlConverterNode = target.worldMesh.connections(type="qlConverter")
        if qlConverterNode:
            qlClothNode = qlConverterNode[0].output.connections(shapes=True,
                                                        type="qlClothShape")
        return qlClothNode[0] if qlClothNode else None
    else:
        return None

def getQLClothOutMesh(target):
    """
    Get the output mesh of a Qualoth cloth object.
    :param target: `PyNode` qualoth cloth object (inmesh, qlClothShape, outmesh)
    :return: `PyNode`
    """
    clothNode = getQLClothNode(target)
    if not clothNode: return None

    outMesh = clothNode.outputMesh.connections(shapes=True, type="mesh")
    return outMesh[0] if outMesh else None


def getQLClothInMesh(target):
    """
    Get the input mesh of a Qualoth cloth object.
    :param target: `PyNode` qualoth cloth object (inmesh, qlClothShape, outmesh)
    :return: `PyNode`
    """
    clothNode = getQLClothNode(target)
    if not clothNode: return None

    qlConverter = clothNode.inputGeometry.connections(type="qlConverter")
    if qlConverter:
        inMesh = qlConverter[0].input.connections(shapes=True, type="mesh")
        return inMesh[0] if inMesh else None

def getQLSolver(target):
    """
    Get the qlSolver node of a Qualoth object.
    :param target: `PyNode` qualoth object
    :return: `PyNode`
    """
    type = getQLType(target)
    solverNode = None
    if type == qlTypes[0]:
        solverNode = getQLClothNode(target).clothState.connections(shapes=True,
                                                          type="qlSolverShape")
    elif type == qlTypes[1]:
        solverNode = getQLColliderNode(target).ouput.connections(shapes=True,
                                                          type="qlSolverShape")
    return  solverNode[0] if solverNode else None


def getQLColliderMesh(target):
    """
    Get the collider mesh of a Qualoth collider object.
    :param target: `PyNode` qualoth collider object
                    (colliderMesh, qlColliderShape, collisionOffset)
    :return: `PyNode`
    """
    colliderNode = getQLColliderNode(target)
    if not colliderNode: return None
    qlTriangulate = colliderNode.input.connections(type="qlTriangulate")
    if qlTriangulate:
        colliderMesh = qlTriangulate[0].input.connections(shapes=True, type="mesh")
        return colliderMesh[0] if colliderMesh else None
    else:
        return None


def getQLColliderOffset(target):
    """
    Get the collider offset mesh of a Qualoth collider object.
    :param target: `PyNode` qualoth collider object
                    (colliderMesh, qlColliderShape, collisionOffset)
    :return: `PyNode`
    """
    colliderNode = getQLColliderNode(target)
    if not colliderNode: return None
    colliderOffset = colliderNode.output.connections(shapes=True, type="mesh")
    return colliderOffset[0] if colliderOffset else None

def getQLRestShape(target):
    """
    Get the restshape mesh of a Qualoth cloth object.
    :param target: `PyNode` qualoth cloth object (inmesh, qlClothShape, outmesh)
    :return: `PyNode`
    """
    clothNode = getQLClothNode(target)
    if not clothNode: return None
    restShape = clothNode.restShape.connections(shapes=True, type="mesh")
    return restShape[0] if restShape else None

def exportMaterialProperties(filePath, target):
    """
    export qualoth attributes as json files
    >>> exportMaterialProperties('~/work/coat_attrs.json', qlClothNode)

    :parameter:
        target : `pyNode`
            the qualoth object to export attributes from
        filePath : `string`
            the target file path

    :return:
        status

    :rtype:
        `bool`
    """
    target = getQLClothNode(target)
    if not target:
        pm.warning("Please select a cloth object "
                   "to export material properties from.")
        return None

    outAttrs = {}
    for attrName in materialProperties:
        try:
            targetAttr = "{0}.{1}".format(target.name(), attrName)
            outAttrs[attrName] = (pm.getAttr(targetAttr),
                                  pm.getAttr(targetAttr, type=True))
        except:
            continue

    f = open(filePath, 'w')
    f.write(json.dumps(outAttrs, indent=2))
    f.close()


def importMaterialProperties(filePath, target):
    """
    Import material properties to selected cloth node from file.
    :param target:
    :param filePath:
    :return:
    """
    target = getQLClothNode(target)
    if not target:
        pm.warning("Please select a cloth object "
                   "to import material properties to.")
        return

    try:
        with open(filePath, 'r') as f:
            attrs = json.load(f)
    except:
        pm.error("Error loading material property file.")
        return

    for attr, value in attrs.iteritems():
        if value[1] != "string":
            pm.setAttr("{0}.{1}".format(target.name(), attr), value[0])
        else:
            value[0] = "" if not value[0] else value[0]
            pm.setAttr("{0}.{1}".format(target.name(), attr),
                       value[0], type="string")


def updateInitialStates():
    """
    update initialState meshes.
    The input can be two groups (qlCloth mesh group and initialState mesh group)
    where meshes are matched by vertex count, or two mesh objects.
    :return:
    """
    sel = pm.ls(sl=True, type="transform")
    if len(sel) < 2:
        pm.warning("Please select two groups/objects.")
        return False
    matchDict = {}
    if not sel[0].getShape() and not sel[1].getShape():
        # groups
        # match initial state mesh by vertex count
        # skip the mesh when the match is not uniqe
        initMeshes = sel[0].getChildren()
        outMeshes = sel[1].getChildren()
        vCountDict = {}
        for initMesh in initMeshes:
            vertCount = pm.polyEvaluate(initMesh, vertex=True)
            vCountDict[vertCount] = [initMesh]
        for outMesh in outMeshes:
            vertCount = pm.polyEvaluate(outMesh, vertex=True)
            if vCountDict.has_key(vertCount):
                vCountDict[vertCount].append(outMesh)
            else:
                vCountDict[vertCount] = [outMesh]
        for vCount, match in vCountDict.iteritems():
            if len(match) == 2:
                matchDict[match[0]] = match[1]
            else:
                print "No match or more than one match exists for {0}. " \
                      "Skipped.".format(match[0])
        print matchDict
    elif sel[0].getShape() and sel[1].getShape():
        # meshes
        matchDict[sel[0]] = sel[1]
    else:
        pm.warning("Please select two groups/objects.")
        return False
    for initM, outM in matchDict.iteritems():
        pm.select(initM,r=True)
        pm.select(outM,add=True)
        pm.mel.qlUpdateInitialPose()



