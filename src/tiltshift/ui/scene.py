"""Procedural solid geometry. Panda coordinates: X right, Y depth, Z up."""
from panda3d.core import GeomVertexData, GeomVertexFormat, GeomVertexWriter, GeomTriangles, Geom, GeomNode


def cube(parent, name, position, scale, color):
    data = GeomVertexData(name, GeomVertexFormat.getV3n3(), Geom.UHStatic)
    v, n = GeomVertexWriter(data, 'vertex'), GeomVertexWriter(data, 'normal')
    triangles = GeomTriangles(Geom.UHStatic)
    faces = [((1,0,0),[(1,-1,-1),(1,1,-1),(1,1,1),(1,-1,1)]),
             ((-1,0,0),[(-1,1,-1),(-1,-1,-1),(-1,-1,1),(-1,1,1)]),
             ((0,1,0),[(1,1,-1),(-1,1,-1),(-1,1,1),(1,1,1)]),
             ((0,-1,0),[(-1,-1,-1),(1,-1,-1),(1,-1,1),(-1,-1,1)]),
             ((0,0,1),[(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]),
             ((0,0,-1),[(-1,1,-1),(1,1,-1),(1,-1,-1),(-1,-1,-1)])]
    for normal, vertices in faces:
        start = v.getWriteRow()
        for xyz in vertices:
            v.addData3(*[q / 2 for q in xyz]); n.addData3(*normal)
        triangles.addVertices(start, start+1, start+2)
        triangles.addVertices(start, start+2, start+3)
    geom = Geom(data); geom.addPrimitive(triangles)
    node = GeomNode(name); node.addGeom(geom)
    result = parent.attachNewNode(node)
    result.setPos(*position); result.setScale(*scale); result.setColor(*color)
    return result


def wall(parent, vertical):
    root = parent.attachNewNode('vertical gate' if vertical else 'horizontal gate')
    w, h = (0.9, 3.6) if vertical else (3.6, 0.9)
    color = (0.18, 0.08, 0.35, 1) if vertical else (0.035, 0.22, 0.29, 1)
    for x in (-1, 1):
        cube(root, 'side', (x*(4+w/2)/2, 0, 0), (4-w/2, .55, 7), color)
    for z in (-1, 1):
        cube(root, 'cap', (0, 0, z*(3.5+h/2)/2), (w, .55, 3.5-h/2), color)
    accent = (.65,.28,1,1) if vertical else (.1,1,1,1)
    for x in (-w/2,w/2): cube(root,'edge',(x,-.29,0),(.045,.035,h),accent)
    for z in (-h/2,h/2): cube(root,'edge',(0,-.29,z),(w,.035,.045),accent)
    return root
