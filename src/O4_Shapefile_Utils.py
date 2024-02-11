import fiona

def shapefile_to_dico(shapefilename, filter, bbox = None, existing_dico = None, file_encoding = 'utf-8'):
    dico = existing_dico if existing_dico else {}    
    with fiona.open(shapefilename, encoding = file_encoding) as data: 
        iterator = data.items() if not bbox else data.items(bbox = bbox)
        for elem in iterator:
            filter(dico, elem[1])
    return dico






