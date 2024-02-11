
########################################################################
def add_to_index(iterable, bounds_of_items, rtree_idx, dico_idx):
    id_pol = len(dico_idx)
    for elem in iterable:
        rtree_idx.insert(id_pol, bounds_of_items(elem))
        dico_idx[id_pol] = elem
        id_pol +=1
    return
########################################################################
    
########################################################################
def aggregate_elems(rtree_idx, dico_idx):
    dico_groups = {}
    dico_tmp = {}
    for id_pol in range(len(dico_idx)):
        if id_pol%100 == 0: print(id_pol)
        pol = dico_idx[id_pol]['geometry']
        touching_list = []
        for polid in rtree_idx.intersection(pol.bounds):
            if polid >= id_pol: continue
            if pol.intersection(dico_idx[polid]['geometry']):
                touching_list.append(polid)
        if touching_list:
            min_id = min(touching_list)
            tmp = set()
            for id in touching_list:
                tmp=tmp.union(dico_groups[dico_tmp[id]])
            tmp.add(id_pol)
            for id in touching_list:
                dico_groups.pop(dico_tmp[id],None)
            for id in tmp:
                dico_tmp[id] = min_id
            dico_groups[min_id] = tmp
        else:
            dico_tmp[id_pol]=id_pol
            dico_groups[id_pol]=set([id_pol])
    return dico_groups
########################################################################
