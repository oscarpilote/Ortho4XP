
from math import cos, sin, tan, pi
import numpy

# 

def translate(geom ,vector):
    if isinstance(vector,tuple):
        vector = numpy.array(vector, dtype=numpy.float)
    if isinstance(geom,list):
        return [translate(subgeom,vector) for subgeom in geom]
    else:
        vertex = numpy.array(geom) # copy 
        vertex[:3] += vector
        return vertex

def rotate(geom, axis, angle):
    if isinstance(geom,list):
        return [rotate(subgeom, axis, angle) for subgeom in geom]
    else:
        vertex = numpy.array(geom) # copy 
        A = rotation_matrix(axis, angle)
        vertex[:3] = A.dot(vertex[:3])
        vertex[3:6] = A.dot(vertex[3:6])
        return vertex

def rotation_matrix(axis, angle):
    a = angle*pi/180
    if axis == 'z':
        return numpy.array([[cos(a), -sin(a), 0],[sin(a),cos(a), 0],[0,0,1]],dtype=numpy.float)
    elif axis == 'x':
        return numpy.array([[1, 0, 0],[0, cos(a), -sin(a)],[0, sin(a), cos(a)]],dtype = numpy.float)
    else:
        return numpy.array([[cos(a), 0, sin(a)],[0, 1, 0],[-sin(a), 0, cos(a)]],dtype = numpy.float)


def face_a_plat(vertex_list):
    face = [] 
    for (x,y) in vertex_list:
        face.append(numpy.array([x,y,0,0,0,1,0,0],dtype = numpy.float))
    return face
    
def texture_face_a_plat(face, st_orig, scale):
    vertex_orig = face[0]
    for vertex in face:
        vertex[6] = st_orig[0]+(vertex[0]-vertex_orig[0])*scale
        vertex[7] = st_orig[1]+(vertex[1]-vertex_orig[1])*scale

def build_simple_house(L,l,h,angle,dtL=0,dtl=0,id_toit=1):
    # L = longueur
    # l = largeur
    # h = hauteur de l'avant toit
    # angle = pente du toit
    # dtL = debord toit dans la longueur
    # dtl = idem largeur
    a = angle*pi/180
    ht = h + l/2*tan(a) # hauteur totale
    lt = l/(2*cos(a))   # largeur du toit (sans debord) 
    st_orig_toit = (((id_toit-1)//3)*1/8, (2-(id_toit-1)%3)*1/16)
    scale = 1/(0.035*4096)
    front = face_a_plat([(0,0),(L,0),(L,h),(0,h)])
    texture_face_a_plat(front, (0,0.5), scale)
    front = rotate(front,'x',90)
    back = face_a_plat([(0,0),(L,0),(L,h),(0,h)])
    texture_face_a_plat(back, (0,0.5), scale)
    back = rotate(back,'x',90)
    back = rotate(back,'z',180)
    back = translate(back, (L,l,0))
    left = face_a_plat([(0,0),(l,0),(l,h),(l/2,ht),(0,h)])
    texture_face_a_plat(left, (0,0.5), scale)
    left = rotate(left, 'x', 90)
    left = rotate(left, 'z', -90)
    left = translate(left, (0,l,0))
    right = face_a_plat([(0,0),(l,0),(l,h),(l/2,ht),(0,h)])
    texture_face_a_plat(right, (0,0.5), scale)
    right = rotate(right,'x', 90)
    right = rotate(right,'z', 90)
    right = translate(right, (L,0,0))
    tfront = face_a_plat([(-dtL,-dtl),(L+dtL,-dtl),(L+dtL,lt),(-dtL,lt)])
    texture_face_a_plat(tfront, st_orig_toit, scale)
    tfront = rotate(tfront,'x',angle)
    tfront = translate(tfront,(0,0,h))
    tback = face_a_plat([(-dtL,-dtl),(L+dtL,-dtl),(L+dtL,lt),(-dtL,lt)])
    texture_face_a_plat(tback, st_orig_toit, scale)
    tback = rotate(tback,'x',angle)
    tback = rotate(tback,'z',180)
    tback = translate(tback,(L,l,h))
    return translate([front, right, back, left, tfront, tback],(-L/2,-l/2,0))

def faces_to_obj(faces, objfilename):
    rounding = 3
    f = open(objfilename,'w')
    vtot = 1
    f.write("mtllib house_1.mtl\n")
    f.write("usemtl house_1\n")
    for i in range(len(faces)):
        face = faces[i]
        for v in face:
            f.write("v "+str(numpy.round(v[0],rounding))+" "+str(numpy.round(v[1],rounding))+" "+str(numpy.round(v[2],rounding))+"\n")
            f.write("vn "+str(numpy.round(v[3],rounding))+" "+str(numpy.round(v[4],rounding))+" "+str(numpy.round(v[5],rounding))+"\n")
            f.write("vt "+str(numpy.round(v[6],rounding))+" "+str(numpy.round(v[7],rounding))+"\n")
        f.write("f")
        for j in range(len(face)):
            f.write(" "+str(j+vtot)+"/"+str(j+vtot)+"/"+str(j+vtot))
        f.write("\n")
        vtot += len(face)
    f.close()
    f = open("house_1.mtl",'w')
    f.write("newmtl house_1\n")
    f.write("map_Ka house_1.png\n")
    f.close()


def faces_to_obj8(faces, objfilename, texturefilename):
    rounding = 3
    f = open(objfilename,'w')
    vttot = numpy.sum([len(face) for face in faces])
    idxtot = 3 * numpy.sum([len(face)-2 for face in faces])
    f.write('I\n800\nOBJ\n\nTEXTURE '+texturefilename+'\n')
    f.write('POINT_COUNTS    ')
    f.write(str(vttot))
    f.write(' 0 0 ')
    f.write(str(idxtot))
    f.write('\n\n') 
    for i in range(len(faces)):
        face = faces[i]
        for v in face:
            f.write("VT "+str(numpy.round(v[0],rounding))+" "+str(numpy.round(v[2],rounding))+" "+str(-numpy.round(v[1],rounding))+ " "
               #+ "0 1 0 "
               + str(numpy.round(v[3],rounding))+" "+str(numpy.round(v[5],rounding))+" "+str(-numpy.round(v[4],rounding))+ " "
               + str(numpy.round(v[6],rounding))+" "+str(numpy.round(v[7],rounding))+"\n")
    idxtmp = 0           
    idxlist = []
    for face in faces:
        for j in range(1, len(face)-1):
            idxlist.append(idxtmp)
            idxlist.append(idxtmp + j + 1)
            idxlist.append(idxtmp + j )
        idxtmp += len(face)
    idx10 = len(idxlist)//10    
    for i in range(0,idx10):
            f.write('IDX10 ')
            for j in range(0,10):
                f.write(str(idxlist[10*i+j])+" ")
            f.write("\n")
    for j in range(0,(len(idxlist)%10)):
        f.write('IDX ')
        f.write(str(idxlist[idx10*10+j]))
        f.write("\n")
    f.write("\n")
    f.write("TRIS 0 "+str(len(idxlist)))
    f.close()
        
        
   
