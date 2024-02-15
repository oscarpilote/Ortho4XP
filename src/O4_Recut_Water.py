import numpy
import array

def recut_water_tris(node_coords, tri_idx, tri_types):

    assert(len(node_coords) % 5 == 0)
    nbr_nodes = len(node_coords) // 5;
    assert(len(tri_idx) % 3 == 0)
    assert(len(tri_idx) // 3 == len(tri_types))
    nbr_tris  = len(tri_types)

    # Fill node types using a boolean or on a bit field.
    # Coastline nodes are those that will have both a land and water bits set. 
    # Assumes that tri_types[n] is already in the range {0, 1, 2}
    print("compute node types")
    node_types = numpy.zeros(nbr_nodes, dtype = numpy.uint8)
    for i in range(nbr_tris):
        t = 1 << tri_types[i]
        node_types[tri_idx[3 * i + 0]] |= t 
        node_types[tri_idx[3 * i + 1]] |= t 
        node_types[tri_idx[3 * i + 2]] |= t
    node_is_coast = ((node_types & 1) != 0) & ((node_types & 6) != 0)

    # Count the number of coastline tris (i.e. with at least one coastline vtx)
    # The latter are the only ones with a potential recut).
    tri_is_coast = numpy.zeros(nbr_tris, dtype = bool)
    for i in range(nbr_tris):
        tri_is_coast[i] |= node_is_coast[tri_idx[3 * i + 0]]
        tri_is_coast[i] |= node_is_coast[tri_idx[3 * i + 1]]
        tri_is_coast[i] |= node_is_coast[tri_idx[3 * i + 2]]
    coast_tri_count = numpy.sum(tri_is_coast)
    print("coastline tris :", coast_tri_count)

    print("Classigy edges")
    # Classify edges of coastline tris
    edge_type = {}
    for i in range(nbr_tris):
        if not tri_is_coast[i]:
            continue
        t = 1 << tri_types[i]
        (a,b,c) = tri_idx[3 * i: 3 * i + 3]
        for (m,n) in ((a,b), (b,c), (c,a)):
            if (m,n) in edge_type or (n,m) in edge_type:
                edge_type[(m,n)] |= t
                edge_type[(n,m)] |= t
            else:
                edge_type[(m,n)] = t
                edge_type[(n,m)] = t

    # Copy and increase size for node_coords, node_types, node_is_coast
    node_max_count = nbr_nodes + 3 * coast_tri_count
    node_coords = numpy.resize(node_coords, 5 * node_max_count)
    node_types   = numpy.resize(node_types, node_max_count)
    node_is_coast = numpy.resize(node_is_coast, node_max_count)


    print("Cut edges")
    # Cut edges that need to : i.e. have no land bit but their 
    # end-points are coastline.
    edge_cut = {}
    next_n = nbr_nodes
    for ((a, b), t) in edge_type.items():
        if b < a:
            # do not do twice the work we have both pairs anyway
            continue
        if (t & 1 == 0) and node_is_coast[a] and node_is_coast[b]:
            edge_cut[(a,b)] = next_n
            edge_cut[(b,a)] = next_n
            node_coords[5 * next_n: 5 * next_n + 5] = (
                    node_coords[5 * a: 5 * a + 5] +
                    node_coords[5 * b: 5 * b + 5]
                    ) / 2.0
            node_types[next_n] = t
            node_is_coast[next_n] = False
            next_n += 1

    # Copy and increase size for node_coords, node_types, node_is_coast
    tri_max_count = nbr_tris + 3 * coast_tri_count
    tri_idx = numpy.resize(tri_idx, 3 * tri_max_count)
    tri_types = numpy.resize(tri_types, tri_max_count)

    next_t = nbr_tris

    print("Cut tris")
    # Cut the tris that need to.
    # When cutting a tri, its place in tri_idx is taken by one of the 
    # newley created ones, and the others ones are appended at the end.
    for i in range(nbr_tris):
        if not tri_types[i] or not tri_is_coast[i]:
            continue
        (a,b,c) = tri_idx[3 * i: 3 * i + 3]
        C = (a,b) in edge_cut
        A = (b,c) in edge_cut
        B = (c,a) in edge_cut
        cuts = A + B + C
        if (not cuts):
            # If not a singleton tri water patch do nothing 
            # note : this is a water tri so edges surely have water bit(s)
            if ((edge_type[(a,b)] & 1 == 0) or (edge_type[(b,c)] & 1 == 0) or 
               (edge_type[(c,a)] & 1 == 0)):
                   continue
            # Else we cut the tri at its barycenter.
            node_coords[5 * next_n: 5 * next_n + 5] = (
                   node_coords[5 * a: 5 * a + 5] + 
                   node_coords[5 * b: 5 * b + 5] +
                   node_coords[5 * c: 5 * c + 5]
                   ) / 3.0
            node_types[next_n] = tri_types[i]
            node_is_coast[next_n] = False
            tri_idx[3 * i: 3 * i + 3] = (a,b,next_n)
            tri_idx[3 * next_t: 3 * next_t + 6] = (b,c,next_n,c,a,next_n)
            tri_types[next_t] = tri_types[next_t + 1] = tri_types[i]
            next_n += 1
            next_t += 2
        else:
            L = array.array('i')
            L.append(a)
            if C:
                s1 = len(L)
                L.append(edge_cut[(a,b)])
            else:
                s2 = len(L) - 1
            L.append(b)
            if A:
                s1 = len(L)
                L.append(edge_cut[(b,c)])
            else:
                s2 = len(L) - 1
            L.append(c)
            if B:
                s1 = len(L)
                L.append(edge_cut[(c,a)])
            else:
                s2 = len(L) - 1
            L = L + L
            
            if (cuts == 2):
                # By def of s2 (x,y) is the one edge with no cut
                # Make a drawing !
                (x,y,z,t,u) = L[s2:s2+5]
                tri_idx[3 * i: 3 * i + 3] = (x,y,z)
                tri_idx[3 * next_t: 3 * next_t + 6] = (z,t,u,x,z,u)
                tri_types[next_t: next_t + 2] = tri_types[i]
                next_t += 2
            elif (cuts == 1):
                # By def of s1 x is the cut node
                # Make a drawing !
                (x,y,z,t) = L[s1:s1+4]
                tri_idx[3 * i: 3 * i + 3] = (x,y,z)
                tri_idx[3 * next_t: 3 * next_t + 3] = (x,z,t)
                tri_types[next_t] = tri_types[i]
                next_t += 1
            else: # cuts == 3
                # By def of s1 x is some cut node
                # Make a drawing !
                (x,y,z,t,u,v) = L[s1:s1+6]
                tri_idx[3 * i: 3 * i + 3] = (x,y,z)
                tri_idx[3 * next_t: 3 * next_t + 9] = (z,t,u,u,v,x,x,z,u)
                tri_types[next_t: next_t + 3] = tri_types[i]
                next_t += 3

    nbr_nodes = next_n
    assert(node_max_count >= nbr_nodes)
    node_coords = numpy.resize(node_coords, 5 * nbr_nodes)
    node_types  = numpy.resize(node_types, nbr_nodes)
    node_is_coast = numpy.resize(node_is_coast, nbr_nodes)
    
    nbr_tris = next_t
    assert(tri_max_count >= nbr_tris)
    tri_idx = numpy.resize(tri_idx, 3 * nbr_tris)
    tri_types = numpy.resize(tri_types, nbr_tris)

    return (nbr_nodes, node_coords, node_types, node_is_coast, 
            nbr_tris, tri_idx, tri_types)
    



                




















    
