import os
import pickle
import shutil
import io
from math import floor, ceil
import array
import numpy
from PIL import Image, ImageDraw
from collections import defaultdict
import struct
import hashlib
import O4_File_Names as FNAMES
import O4_Geo_Utils as GEO
import O4_Mask_Utils as MASK
import O4_UI_Utils as UI
import O4_Overlay_Utils as OVL
import O4_Mesh_Utils as MESH
import O4_Bathymetry as BATHY

quad_init_level = 3
quad_capacity_high = 50000
quad_capacity_low = 35000

# For Laminar test suite
use_test_texture = False

################################################################################
def float2qquad(x):
    if x >= 1:
        return "111111111111111111111111"
    return numpy.binary_repr(int(16777216 * x)).zfill(24)  # 2**24 == 16777216


################################################################################

################################################################################
class QuadTree(dict):
    class Bucket(dict):
        def __init__(self):
            self["size"] = 0
            self["idx_nodes"] = set()

    def __init__(self, level, bucket_size):
        self.bucket_size = bucket_size
        if level == 0:
            self[("", "")] = self.Bucket()
        else:
            for i in range(2 ** level):
                for j in range(2 ** level):
                    key = (
                        numpy.binary_repr(i).zfill(level),
                        numpy.binary_repr(j).zfill(level),
                    )
                    self[key] = self.Bucket()
        self.nodes = {}
        self.levels = {}
        self.last_node = 0

    def split_bucket(self, key):
        level = len(key[0]) + 1
        self[(key[0] + "0", key[1] + "0")] = self.Bucket()
        self[(key[0] + "0", key[1] + "1")] = self.Bucket()
        self[(key[0] + "1", key[1] + "0")] = self.Bucket()
        self[(key[0] + "1", key[1] + "1")] = self.Bucket()
        for idx in self[key]["idx_nodes"]:
            new_key = (self.nodes[idx][0][:level], self.nodes[idx][1][:level])
            self[new_key]["idx_nodes"].add(idx)
            self[new_key]["size"] += 1
            self.levels[idx] += 1
        del self[key]

    def insert(self, bx, by, level):
        while True:
            key = (bx[:level], by[:level])
            if key in self:
                break
            level += 1
        if self[key]["size"] < self.bucket_size:
            self[key]["idx_nodes"].add(self.last_node)
            self[key]["size"] += 1
            self.nodes[self.last_node] = (bx, by)
            self.levels[self.last_node] = level
            self.last_node += 1
        else:
            self.split_bucket(key)
            self.insert(bx, by, level + 1)

    def clean(self):
        for key in list(self.keys()):
            if not self[key]["size"]:
                del self[key]

    def statistics(self):
        lengths = numpy.array([self[key]["size"] for key in self])
        depths = numpy.array([len(key[0]) for key in self])
        UI.vprint(2, "     Number of buckets:", len(lengths))
        UI.vprint(
            2,
            "     Average depth:",
            depths.mean(),
            ", Average bucket size:",
            lengths.mean(),
        )
        UI.vprint(2, "     Largest depth:", numpy.max(depths))


################################################################################

################################################################################
def zone_list_to_ortho_dico(tile):
    # tile.zone_list is a list of 3-uples of the form
    # ([(lat0,lat0), ... ,(latN,lonN)], zoomlevel, provider_code)
    # where higher lines have priority over lower ones.
    masks_im = Image.new("L", (4096, 4096), "black")
    masks_draw = ImageDraw.Draw(masks_im)
    airport_array = numpy.zeros((4096, 4096), dtype=numpy.bool_)
    if tile.cover_airports_with_highres in ("True", "ICAO"):
        UI.vprint(1, "-> Checking airport locations for upgraded zoomlevel.")
        try:
            f = open(FNAMES.apt_file(tile), "rb")
            dico_airports = pickle.load(f)
            f.close()
        except:
            UI.vprint(
                1,
                "   WARNING: File",
                FNAMES.apt_file(tile),
                "is missing (erased after Step 1?), cannot check airport info ",
                "for upgraded zoomlevel.",
            )
            dico_airports = {}
        if tile.cover_airports_with_highres == "ICAO":
            airports_list = [
                airport
                for airport in dico_airports
                if dico_airports[airport]["key_type"] == "icao"
            ]
        else:
            airports_list = dico_airports.keys()
        for airport in airports_list:
            (xmin, ymin, xmax, ymax) = dico_airports[airport]["boundary"].bounds
            # extension
            xmin -= 1000 * tile.cover_extent * GEO.m_to_lon(tile.lat)
            xmax += 1000 * tile.cover_extent * GEO.m_to_lon(tile.lat)
            ymax += 1000 * tile.cover_extent * GEO.m_to_lat
            ymin -= 1000 * tile.cover_extent * GEO.m_to_lat
            # round off to texture boundaries at tile.cover_zl zoomlevel
            (til_x_left, til_y_top) = GEO.wgs84_to_orthogrid(
                ymax + tile.lat, xmin + tile.lon, tile.cover_zl
            )
            (ymax, xmin) = GEO.gtile_to_wgs84(
                til_x_left, til_y_top, tile.cover_zl
            )
            ymax -= tile.lat
            xmin -= tile.lon
            (til_x_left2, til_y_top2) = GEO.wgs84_to_orthogrid(
                ymin + tile.lat, xmax + tile.lon, tile.cover_zl
            )
            (ymin, xmax) = GEO.gtile_to_wgs84(
                til_x_left2 + 16, til_y_top2 + 16, tile.cover_zl
            )
            ymin -= tile.lat
            xmax -= tile.lon
            xmin = max(0, xmin)
            xmax = min(1, xmax)
            ymin = max(0, ymin)
            ymax = min(1, ymax)
            # mark to airport_array
            colmin = round(xmin * 4095)
            colmax = round(xmax * 4095)
            rowmax = round((1 - ymin) * 4095)
            rowmin = round((1 - ymax) * 4095)
            airport_array[rowmin : rowmax + 1, colmin : colmax + 1] = 1
    dico_customzl = {}
    dico_tmp = {}
    til_x_min, til_y_min = GEO.wgs84_to_orthogrid(
        tile.lat + 1, tile.lon, tile.mesh_zl
    )
    til_x_max, til_y_max = GEO.wgs84_to_orthogrid(
        tile.lat, tile.lon + 1, tile.mesh_zl
    )
    i = 1
    base_zone = (
        [
            tile.lat,
            tile.lon,
            tile.lat,
            tile.lon + 1,
            tile.lat + 1,
            tile.lon + 1,
            tile.lat + 1,
            tile.lon,
            tile.lat,
            tile.lon,
        ],
        tile.default_zl,
        tile.default_website,
    )
    for region in [base_zone] + tile.zone_list[::-1]:
        dico_tmp[i] = (region[1], region[2])
        pol = [
            (round((x - tile.lon) * 4095), round((tile.lat + 1 - y) * 4095))
            for (x, y) in zip(region[0][1::2], region[0][::2])
        ]
        masks_draw.polygon(pol, fill=i)
        i += 1
    for til_x in range(til_x_min, til_x_max + 1, 16):
        for til_y in range(til_y_min, til_y_max + 1, 16):
            (latp, lonp) = GEO.gtile_to_wgs84(
                til_x + 8, til_y + 8, tile.mesh_zl
            )
            lonp = max(min(lonp, tile.lon + 1), tile.lon)
            latp = max(min(latp, tile.lat + 1), tile.lat)
            x = round((lonp - tile.lon) * 4095)
            y = round((tile.lat + 1 - latp) * 4095)
            (zoomlevel, provider_code) = dico_tmp[masks_im.getpixel((x, y))]
            if airport_array[y, x]:
                zoomlevel = max(zoomlevel, tile.cover_zl)
            til_x_text = 16 * (
                int(til_x / 2 ** (tile.mesh_zl - zoomlevel)) // 16
            )
            til_y_text = 16 * (
                int(til_y / 2 ** (tile.mesh_zl - zoomlevel)) // 16
            )
            dico_customzl[(til_x, til_y)] = (
                til_x_text,
                til_y_text,
                zoomlevel,
                provider_code,
            )
    if tile.cover_airports_with_highres == "Existing":
        # what we find in the texture folder of the existing tile
        for f in os.listdir(os.path.join(tile.build_dir, "textures")):
            if f[-4:] != ".dds":
                continue
            items = f.split("_")
            (til_y_text, til_x_text) = [int(x) for x in items[:2]]
            zoomlevel = int(items[-1][-6:-4])
            provider_code = "_".join(items[2:])[:-6]
            for til_x in range(
                til_x_text * 2 ** (tile.mesh_zl - zoomlevel),
                (til_x_text + 16) * 2 ** (tile.mesh_zl - zoomlevel),
            ):
                for til_y in range(
                    til_y_text * 2 ** (tile.mesh_zl - zoomlevel),
                    (til_y_text + 16) * 2 ** (tile.mesh_zl - zoomlevel),
                ):
                    if ((til_x, til_y) not in dico_customzl) or dico_customzl[
                        (til_x, til_y)
                    ][2] <= zoomlevel:
                        dico_customzl[(til_x, til_y)] = (
                            til_x_text,
                            til_y_text,
                            zoomlevel,
                            provider_code,
                        )
    return dico_customzl
################################################################################

################################################################################
def create_terrain_file(
    tile,
    texture_file_name,
    til_x_left,
    til_y_top,
    zoomlevel,
    provider_code,
    tri_type,
    is_overlay,
):

    if not os.path.exists(os.path.join(tile.build_dir, "terrain")):
        os.makedirs(os.path.join(tile.build_dir, "terrain"))

    suffix = "_water" if tri_type == 1 else "_sea" if tri_type == 2 else ""
    if is_overlay:
        suffix += "_overlay"
    ter_file_name = texture_file_name[:-4] + suffix + ".ter"

    if use_test_texture:
        texture_file_name = "test_texture.dds"

    with open(os.path.join(tile.build_dir, "terrain", ter_file_name), "w") as f:

        f.write("A\n800\nTERRAIN\n\n")

        [lat_med, lon_med] = GEO.gtile_to_wgs84(
            til_x_left + 8, til_y_top + 8, zoomlevel
        )
        texture_approx_size = int(
            GEO.webmercator_pixel_size(lat_med, zoomlevel) * 4096
        )
        f.write(
            "LOAD_CENTER "
            + "{:.5f}".format(lat_med)
            + " "
            + "{:.5f}".format(lon_med)
            + " "
            + str(texture_approx_size)
            + " 4096\n"
        )

        f.write("BASE_TEX_NOWRAP ../textures/" + texture_file_name + "\n")

        if tri_type in (1, 2) and (not is_overlay):  # XP12 water
            #pass
            f.write("WATER_COLOR_MASK\n")
        elif (tri_type == 1) or (
            (tri_type == 2) and (is_overlay == "ratio_water")
        ):  # constant transparency level
            f.write("BORDER_TEX ../textures/water_transition.png\n")
            if not os.path.exists(
                os.path.join(tile.build_dir, "textures", "water_transition.png")
            ):
                shutil.copy(
                    os.path.join(FNAMES.Utils_dir, "water_transition.png"),
                    os.path.join(tile.build_dir, "textures"),
                )
        elif (tri_type == 2) and (not tile.imprint_masks_to_dds):  
            # border_tex mask
            f.write(
                "LOAD_CENTER_BORDER "
                + "{:.5f}".format(lat_med)
                + " "
                + "{:.5f}".format(lon_med)
                + " "
                + str(texture_approx_size)
                + " "
                + str(4096 // 2 ** (zoomlevel - tile.mask_zl))
                + "\n"
            )
            f.write(
                "BORDER_TEX ../textures/"
                + FNAMES.mask_file(
                    til_x_left, til_y_top, zoomlevel, provider_code
                )
                + "\n"
            )

        # Hack/TODO
        # Should we use decals on ocean floor ? 
        #if (not tri_type) and (tile.use_decal_on_terrain):
        if (tri_type != 1) and (tile.use_decal_on_terrain):
            f.write("DECAL_LIB lib/g10/decals/maquify_2_green_key.dcl\n")

        if tri_type in (1, 2):
            f.write("WET\n")
        else:
            f.write("NO_ALPHA\n")

        if (tri_type in (1, 2)) or (not tile.terrain_casts_shadows):
            f.write("NO_SHADOW\n")

        return ter_file_name


################################################################################

################################################################################
def extract_elevation_and_bathymetry_data(lat, lon):
    UI.vprint(1, "     Extracting some rasters from X-Plane's Global Scenery")
    global_scenery_dsf = os.path.join(
        OVL.custom_overlay_src,
        "Earth nav data",
        FNAMES.long_latlon(lat, lon) + ".dsf",
    )
    if not os.path.exists(global_scenery_dsf):
        UI.exit_message_and_bottom_line(
            "   ERROR: file ",
            global_scenery_dsf,
            "absent. Global Scenery directory needs to be set in the config ",
            "window first.",
        )
        return (b"", b"")
    tmp_file = os.path.join(
        FNAMES.Tmp_dir, FNAMES.short_latlon(lat, lon) + ".dsf"
    )
    UI.vprint(2, "     Making a copy of the Global Scenery DSF in tmp dir")
    try:
        shutil.copy(global_scenery_dsf, tmp_file)
    except:
        UI.exit_message_and_bottom_line(
            "     ERROR: could not copy it. Disk full, write permissions,",
            " erased tmp dir ?",
        )
        return (b"", b"")

    f = open(tmp_file, "rb")
    dsfid = f.read(2).decode("ascii")
    f.close()
    if dsfid == "7z":
        UI.vprint(2, "     The original DSF is a 7z archive, uncompressing...")
        os.replace(tmp_file, tmp_file + ".7z")
        os.system(
            OVL.unzip_cmd + " e -o" + FNAMES.Tmp_dir + ' "' + tmp_file + '.7z"'
        )
        os.remove(tmp_file + '.7z')
    file_len = os.path.getsize(tmp_file)
    f = open(tmp_file, "rb")
    # read filetype cookie
    dsfid = f.read(8).decode("ascii")
    if dsfid != "XPLNEDSF":
        UI.exit_message_and_bottom_line("     ERROR: Corrupted DSF file.")
        os.remove(tmp_file)
        return (b"", b"")
    # skip format number
    f.read(4)
    # read atoms
    atoms_len = file_len - 12 - 16  # 12 for HDR and 16 for MD5
    atoms_consumed = 0
    while atoms_consumed < atoms_len:
        atom_hdr = f.read(4).decode("ascii")
        atom_len = struct.unpack("<I", f.read(4))[0]
        if atom_hdr == "SMED":
            bDEMS_orig = f.read(atom_len - 8)
            bDEMS = b""
            bELEV = b""
            g = io.BytesIO(bDEMS_orig)
            consumed = 8
            i = 0
            while consumed < atom_len:
                bH = g.read(4)
                sub_atom_hdr = bH.decode("ascii")
                bL = g.read(4)
                sub_atom_len = struct.unpack("<I", bL)[0]
                bDATA = g.read(sub_atom_len - 8)
                if (sub_atom_len > 100):
                    i += 1
                    if (i == 1):
                        bELEV = bDATA
                    elif (i == 2):
                        # XP bathy data for inland water is only partial,
                        # we use a safe margin = DEM_elev - 2 to cope with it
                        bathy = numpy.frombuffer(bDATA, dtype=numpy.int16)
                        safe  = numpy.frombuffer(bELEV, dtype=numpy.int16) - 2 
                        bathy = numpy.minimum(bathy, safe)
                        bDATA = bytes(bathy)
                bDEMS += bH + bL + bDATA
                consumed += sub_atom_len
            g.close()
        elif atom_hdr == "NFED":
            consumed = 8
            while consumed < atom_len:
                sub_atom_hdr = f.read(4).decode("ascii")
                sub_atom_len = struct.unpack("<I", f.read(4))[0]
                data = f.read(sub_atom_len - 8)
                if sub_atom_hdr == "NMED":
                    bDEMN = data
                consumed += sub_atom_len
        else:
            f.read(atom_len - 8)

        atoms_consumed += atom_len

    f.close()
    os.remove(tmp_file)

    return (bDEMN, bDEMS)


################################################################################

################################################################################
def build_dsf(tile, download_queue):

    
    dico_customzl = zone_list_to_ortho_dico(tile)

    # 1 Read mesh file
    UI.vprint(1, "-> Reading mesh file")
    mesh_filename = FNAMES.mesh_file(tile.build_dir, tile.lat, tile.lon)
    (mesh_version, nbr_nodes, node_coords, nbr_tris, tri_idx, tri_types) \
            = MESH.read_mesh_file(mesh_filename)

    # 2 Remap tri_types in (0,1,2)
    has_water = 7 if (mesh_version >= 1.3) else 3
    for i in range(nbr_tris):
        t = tri_types[i] & has_water
        t = t and (2 * (t > 1 or tile.use_masks_for_inland) or 1)
        tri_types[i] = t

    # 3 Recut water tris for XP12
    UI.vprint(1, "-> Adapting water triangles to XP12 requirements")
    (nbr_nodes, node_coords, node_types, node_is_coast, nbr_tris, tri_idx, 
        tri_types) = BATHY.recut_water_tris(node_coords, tri_idx, tri_types)

    # 4 Compute bathymetry depth ratio bounds based on masks
    UI.vprint(1, "-> Computing bathymetry depth ratio bounds based on distance masks")
    node_bathy = BATHY.compute_depth_ratio_bounds_from_masks(
                            nbr_nodes, node_coords, node_types, tile)
    
    UI.vprint(1, "-> Computing point pools and texture requirements")
    
    # 5 Compute quadtree
    if (tile.use_masks_for_inland):
        quad_capacity = quad_capacity_low
    else:
        quad_capacity = quad_capacity_high
    pool_quadtree = QuadTree(quad_init_level, quad_capacity)
    for i in range(nbr_nodes):
        pool_quadtree.insert(
                float2qquad(node_coords[5 * i + 0] - tile.lon),
                float2qquad(node_coords[5 * i + 1] - tile.lat),
                quad_init_level)
    pool_quadtree.clean()
    pool_quadtree.statistics()
    
    # 6 Compute pool params
    pool_nbr = len(pool_quadtree)
    idx_node_to_idx_pool = {}
    idx_pool = 0
    key_to_idx_pool = {}
    for key in pool_quadtree:
        key_to_idx_pool[key] = idx_pool
        for idx_node in pool_quadtree[key]["idx_nodes"]:
            idx_node_to_idx_pool[idx_node] = idx_pool
        idx_pool += 1
    pool_param = {}
    node_icoords = numpy.zeros(5 * nbr_nodes, dtype = numpy.uint16)
    for key in pool_quadtree:
        level = len(key[0])
        plist = sorted(list(pool_quadtree[key]["idx_nodes"]))
        node_icoords[[5 * idx_node for idx_node in plist]] = [
            int(pool_quadtree.nodes[idx_node][0][level : level + 16], 2)
            for idx_node in plist
        ]
        node_icoords[[5 * idx_node + 1 for idx_node in plist]] = [
            int(pool_quadtree.nodes[idx_node][1][level : level + 16], 2)
            for idx_node in plist
        ]
        altitudes = numpy.array(
            [node_coords[5 * idx_node + 2] for idx_node in plist]
        )
        altmin = floor(altitudes.min())
        altmax = ceil(altitudes.max())
        if altmax - altmin < 770:
            scale_z = 771  # 65535=771*85
            inv_stp = 85
        elif altmax - altmin < 1284:
            scale_z = 1285  # 65535=1285*51
            inv_stp = 51
        elif altmax - altmin < 4368:
            scale_z = 4369  # 65535=4369*15
            inv_stp = 15
        else:
            scale_z = 13107  # 65535=13107*5
            inv_stp = 5
        scal_x = scal_y = 2 ** (-level)
        node_icoords[[5 * idx_node + 2 for idx_node in plist]] = numpy.round(
            (altitudes - altmin) * inv_stp
        )
        pool_param[key_to_idx_pool[key]] = (
            scal_x,
            tile.lon + int(key[0], 2) * scal_x,
            scal_y,
            tile.lat + int(key[1], 2) * scal_y,
            scale_z,
            altmin,
            2,
            -1,
            2,
            -1,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
        )
    node_icoords[3::5] = numpy.round(
        (1 + tile.normal_map_strength * node_coords[3::5]) / 2 * 65535
    )
    node_icoords[4::5] = numpy.round(
        (1 - tile.normal_map_strength * node_coords[4::5]) / 2 * 65535
    )
    node_icoords = array.array("H", node_icoords)

    
    
    ##########################
    dico_terrains = {}
    overlay_terrains = set()
    treated_textures = set()
    skipped_terrains_for_masking = set()
    dsf_pools = {}
    # we need more pools for textured nodes than for nodes : land, UV masked
    # water, and XP water
    dsf_pool_nbr = 3 * pool_nbr
    for idx_dsfpool in range(dsf_pool_nbr):
        dsf_pools[idx_dsfpool] = array.array("H")
    dsf_pool_length = numpy.zeros(dsf_pool_nbr, "int")
    if (tile.water_tech == "XP11 + bathy"):
        # Land with ortho
        dsf_pool_plane = 7 * numpy.ones(dsf_pool_nbr, "int")
        # Masked ortho (UV1 = ortho, UV2 = border_tex (if aplicable))
        dsf_pool_plane[pool_nbr : 2 * pool_nbr] = 9
        # Regular XP water
        dsf_pool_plane[2 * pool_nbr : 3 * pool_nbr] = 7
    elif (tile.water_tech == "XP12"):
        # Land with ortho
        dsf_pool_plane = 7 * numpy.ones(dsf_pool_nbr, "int")
        # Masked ortho : UV1 = fetch/depth UV2 = ortho)
        #           or : UV1 = ortho, V2 = border_tex
        #                for inland water with constant alpha
        dsf_pool_plane[pool_nbr : 2 * pool_nbr] = 9
        # Regular XP water
        dsf_pool_plane[2 * pool_nbr : 3 * pool_nbr] = 7
    textured_nodes = {}
    len_textured_nodes = 0
    textured_tris = {}
    total_cross_pool = 0
    ##########################

    bPROP = b""
    bTERT = b""
    bOBJT = b""
    bPOLY = b""
    bNETW = b""
    bDEMN = b""
    bGEOD = b""
    bDEMS = b""
    bCMDS = b""

    nbr_dsfpools_yet_in = 0
    dico_terrains = {"terrain_Water": 0}
    bTERT = bytes("terrain_Water\0", "ascii")
    textured_tris[0] = defaultdict(lambda: array.array("H"))

    # Next, we build DSF mesh points (these take into accound texture 
    # as well), point pools, etc.

    step = nbr_tris // 100 + 1
    
    # Tri counter for progress_bars
    done = 0
    

    # First potentially masked water tris
    for tri in range(nbr_tris):
        tri_type = tri_types[tri]
        if (tri_type != 2):
            continue
        (n1, n2, n3) = tri_idx[3 * tri: 3 * tri + 3]
        if done % step == 0:
            UI.progress_bar(1, int(done / step * 0.9))
            if UI.red_flag:
                UI.vprint(1, "DSF construction interrupted.")
                return 0
        done += 1
        bary_lon = (
            node_coords[5 * n1 + 0]
            + node_coords[5 * n2 + 0]
            + node_coords[5 * n3 + 0]
        ) / 3
        bary_lat = (
            node_coords[5 * n1 + 1]
            + node_coords[5 * n2 + 1]
            + node_coords[5 * n3 + 1]
        ) / 3
        texture_attributes = dico_customzl[
            GEO.wgs84_to_orthogrid(bary_lat, bary_lon, tile.mesh_zl)
        ]
        # The entries for the terrain and texture main dictionnaries
        terrain_attributes = (texture_attributes, tri_type)
        is_overlay = False
        

        # Do we need to build new terrain file(s) ?
        if terrain_attributes in dico_terrains:
            terrain_idx = dico_terrains[terrain_attributes]
            is_overlay = terrain_idx in overlay_terrains
        else:
            needs_new_terrain = False
            # if not we need to check with masks values
            if terrain_attributes not in skipped_terrains_for_masking:
                mask_im = MASK.needs_mask(tile, *texture_attributes)
                if mask_im:
                    UI.vprint(2, "      Use of an alpha mask.")
                    needs_new_terrain = True
                else:
                    skipped_terrains_for_masking.add(terrain_attributes)
                    # clean up potential old masks in the tile dir
                    try:
                        os.remove(
                            os.path.join(
                                tile.build_dir,
                                "textures",
                                FNAMES.mask_file(*texture_attributes),
                            )
                        )
                    except:
                        pass
            if needs_new_terrain:
                terrain_idx = len(dico_terrains)
                textured_tris[terrain_idx] = defaultdict(
                    lambda: array.array("H")
                )
                dico_terrains[terrain_attributes] = terrain_idx
                
                # Is it an overlay terrain or the new XP 12 phys water type ?
                # XP11 style => overlay
                is_overlay = (tile.water_tech == "XP11 + bathy") 
                # No alpha channel in DDS => overlay
                is_overlay |= not tile.imprint_masks_to_dds
                
                if is_overlay:
                    overlay_terrains.add(terrain_idx)
                
                texture_file_name = FNAMES.dds_file_name_from_attributes(
                    *texture_attributes
                )
                # do we need to (re)build a texture ?
                if texture_attributes not in treated_textures:
                    target_tex = os.path.join(
                            tile.build_dir, "textures", texture_file_name
                            )
                    rebuild = False
                    if (not os.path.isfile(target_tex)):
                        rebuild = True
                    elif (tile.imprint_masks_to_dds):
                        # Maybe target_tex was a DXT1, we need DXT5
                        if (os.path.getsize(target_tex) < 20000000):
                            rebuild = True
                        # Maybe masks were updated after target_tex was created
                        target_mask = MASK.mask_name_for_texture(tile, 
                                          *texture_attributes)
                        if (os.path.isfile(target_mask)):
                            mask_last_modified = os.path.getmtime(target_mask)
                            tex_last_modified = os.path.getmtime(target_tex)
                            if (tex_last_modified < mask_last_modified):
                                rebuild = True
                    else: 
                        # maybe target_tex was a DXT5, it should ne a DXT1
                        if (os.path.getsize(target_tex) > 20000000):
                            rebuild = True
                        else:
                            print(os.path.getsize(target_tex))
                    
                    if (rebuild or not tile.imprint_masks_to_dds):
                        mask_im.save(os.path.join(
                            tile.build_dir,
                            "textures",
                            FNAMES.mask_file(*texture_attributes),
                        )
                    )

                    if (rebuild):
                            download_queue.put(texture_attributes)
                    else:
                        UI.vprint(
                            2,
                            "   Texture file "
                            + texture_file_name
                            + " already present.",
                        )
                    treated_textures.add(texture_attributes)
                terrain_file_name = create_terrain_file(
                    tile,
                    texture_file_name,
                    *texture_attributes,
                    tri_type,
                    is_overlay
                )
                bTERT += bytes("terrain/" + terrain_file_name + "\0", "ascii")
            else:
                terrain_idx = 0
        
        # We put the tri in the right terrain
        # First the ones associated to the dico_customzl
        if terrain_idx:
            tri_p = array.array("H")
            for n in (n1, n3, n2):  # beware of ordering for orientation !
                idx_pool = idx_node_to_idx_pool[n]
                node_hash = (
                    idx_pool,
                    *node_icoords[5 * n : 5 * n + 2],
                    terrain_idx,
                )
                if node_hash in textured_nodes:
                    (idx_dsfpool, pos_in_pool) = textured_nodes[node_hash]
                else:
                    (s, t) = GEO.st_coord(
                        node_coords[5 * n + 1],
                        node_coords[5 * n],
                        *texture_attributes
                    )
                    # BEWARE : normal coordinates are pointing (EAST,SOUTH)
                    # in X-Plane, not (EAST,NORTH) ! (cfr DSF specs), so v -> -v
                    if is_overlay: 
                        idx_dsfpool = idx_pool + pool_nbr
                        # border_tex masks with original normal
                        dsf_pools[idx_dsfpool].extend(
                            node_icoords[5 * n : 5 * n + 5]
                        )
                        dsf_pools[idx_dsfpool].extend(
                            (
                                int(round(s * 65535)),
                                int(round(t * 65535)),
                                int(round(s * 65535)),
                                int(round(t * 65535)),
                            )
                        )
                    else:  # dtx5 dds with mask included
                        idx_dsfpool = idx_pool + pool_nbr
                        dsf_pools[idx_dsfpool].extend(
                            node_icoords[5 * n : 5 * n + 5]
                        )
                        # TODO (improve fetch values)
                        ratio_bathy = BATHY.set_depth_ratio(n, node_is_coast,
                                                            node_bathy, tile)
                        ratio_fetch = 1
                        dsf_pools[idx_dsfpool].extend(
                            (int(65535 * ratio_fetch), int(65535 * ratio_bathy), 
                             int(round(s * 65535)), int(round(t * 65535)))
                        )
                    len_textured_nodes += 1
                    pos_in_pool = dsf_pool_length[idx_dsfpool]
                    textured_nodes[node_hash] = (idx_dsfpool, pos_in_pool)
                    dsf_pool_length[idx_dsfpool] += 1
                tri_p.extend((idx_dsfpool, pos_in_pool))
            # some triangles could be reduced to nothing by the pool snapping,
            # we skip thme (possible killer to X-Plane's drapping of roads ?)
            if (
                tri_p[:2] == tri_p[2:4]
                or tri_p[2:4] == tri_p[4:]
                or tri_p[4:] == tri_p[:2]
            ):
                continue
            if tri_p[0] == tri_p[2] == tri_p[4]:
                textured_tris[terrain_idx][tri_p[0]].extend(
                    (tri_p[1], tri_p[3], tri_p[5])
                )
            else:
                total_cross_pool += 1
                textured_tris[terrain_idx]["cross-pool"].extend(tri_p)
        # X-Plane water
        if (not terrain_idx) or is_overlay: 
            tri_p = array.array("H")
            for n in (n1, n3, n2):  # beware of ordering for orientation !
                node_hash = (n, 0)
                if node_hash in textured_nodes:
                    (idx_dsfpool, pos_in_pool) = textured_nodes[node_hash]
                else:
                    idx_dsfpool = idx_node_to_idx_pool[n] + 2 * pool_nbr
                    len_textured_nodes += 1
                    pos_in_pool = dsf_pool_length[idx_dsfpool]
                    textured_nodes[node_hash] = [idx_dsfpool, pos_in_pool]
                    # in some cases we might prefer to use normal shading for
                    # some sea triangles too (albedo continuity with elevation
                    # derived masks)
                    # dsf_pools[idx_dsfpool].extend(node_icoords[5*n:5*n+5])
                    dsf_pools[idx_dsfpool].extend(
                        node_icoords[5 * n : 5 * n + 3]
                    )
                    dsf_pools[idx_dsfpool].extend((32768, 32768))
                    ratio_bathy = BATHY.set_depth_ratio(n, node_is_coast,
                                                        node_bathy, tile)
                    # TODO improve bathy and fetch ratio variety
                    ratio_fetch = 1
                    dsf_pools[idx_dsfpool].extend((int(65535 * ratio_fetch),
                                                   int(65535 * ratio_bathy))) 
                    dsf_pool_length[idx_dsfpool] += 1
                tri_p.extend((idx_dsfpool, pos_in_pool))
            if tri_p[0] == tri_p[2] == tri_p[4]:
                textured_tris[0][tri_p[0]].extend(
                    (tri_p[1], tri_p[3], tri_p[5])
                )
            else:
                total_cross_pool += 1
                textured_tris[0]["cross-pool"].extend(tri_p)

    # Second land and inland water tris with no mask
    for tri in range(nbr_tris):
        tri_type = tri_types[tri]
        if (tri_type == 2):
            continue
        (n1, n2, n3) = tri_idx[3 * tri: 3 * tri + 3]
        
        if done % step == 0:
            UI.progress_bar(1, int(done / step * 0.9))
            if UI.red_flag:
                UI.vprint(1, "DSF construction interrupted.")
                return 0
        done += 1
        bary_lon = (
            node_coords[5 * n1] + node_coords[5 * n2] + node_coords[5 * n3]
        ) / 3
        bary_lat = (
            node_coords[5 * n1 + 1]
            + node_coords[5 * n2 + 1]
            + node_coords[5 * n3 + 1]
        ) / 3
        texture_attributes = dico_customzl[
            GEO.wgs84_to_orthogrid(bary_lat, bary_lon, tile.mesh_zl)
        ]
        # The entries for the terrain and texture main dictionnaries
        terrain_attributes = (texture_attributes, tri_type)
        is_overlay = False

        # Do we need to build new terrain file(s) ?
        if terrain_attributes in dico_terrains:
            terrain_idx = dico_terrains[terrain_attributes]
            is_overlay = terrain_idx in overlay_terrains
        else:
            terrain_idx = len(dico_terrains)
            textured_tris[terrain_idx] = defaultdict(lambda: array.array("H"))
            dico_terrains[terrain_attributes] = terrain_idx
            is_overlay = tri_type == 1
            if is_overlay:
                overlay_terrains.add(terrain_idx)
            texture_file_name = FNAMES.dds_file_name_from_attributes(
                *texture_attributes
            )
            # do we need to download a new texture ?
            if texture_attributes not in treated_textures:
                target_tex = os.path.join(
                            tile.build_dir, "textures", texture_file_name
                            )
                rebuild = False
                if (not os.path.isfile(target_tex)):
                    rebuild = True
                if (rebuild):
                    download_queue.put(texture_attributes)
                else:
                    UI.vprint(
                        2,
                        "   Texture file "
                        + texture_file_name
                        + " already present.",
                    )
                treated_textures.add(texture_attributes)
            terrain_file_name = create_terrain_file(
                tile,
                texture_file_name,
                *texture_attributes,
                tri_type,
                is_overlay
            )
            bTERT += bytes("terrain/" + terrain_file_name + "\0", "ascii")
        # We put the tri in the right terrain
        # First the ones associated to the dico_customzl
        tri_p = array.array("H")
        for n in (n1, n3, n2):  # beware of ordering for orientation !
            idx_pool = idx_node_to_idx_pool[n]
            node_hash = (
                idx_pool,
                *node_icoords[5 * n : 5 * n + 2],
                terrain_idx,
            )
            if node_hash in textured_nodes:
                (idx_dsfpool, pos_in_pool) = textured_nodes[node_hash]
            else:
                (s, t) = GEO.st_coord(
                    node_coords[5 * n + 1],
                    node_coords[5 * n],
                    *texture_attributes
                )
                # BEWARE : normal coordinates are pointing (EAST,SOUTH) in 
                # X-Plane, not (EAST,NORTH) ! (cfr DSF specs), so v -> -v
                if not tri_type:  # land
                    idx_dsfpool = idx_pool
                    dsf_pools[idx_dsfpool].extend(
                        node_icoords[5 * n : 5 * n + 5]
                    )
                    dsf_pools[idx_dsfpool].extend(
                        (int(round(s * 65535)), int(round(t * 65535)))
                    )
                else:  # inland water
                    idx_dsfpool = idx_pool + pool_nbr
                    # constant alpha overlay with flat shading
                    dsf_pools[idx_dsfpool].extend(
                        node_icoords[5 * n : 5 * n + 3]
                    )
                    dsf_pools[idx_dsfpool].extend(
                        (
                            32768,
                            32768,
                            int(round(s * 65535)),
                            int(round(t * 65535)),
                            0,
                            int(round(tile.ratio_water * 65535)),
                        )
                    )
                len_textured_nodes += 1
                pos_in_pool = dsf_pool_length[idx_dsfpool]
                textured_nodes[node_hash] = (idx_dsfpool, pos_in_pool)
                dsf_pool_length[idx_dsfpool] += 1
            tri_p.extend((idx_dsfpool, pos_in_pool))
        # some triangles could be reduced to nothing by the pool snapping,
        # we skip them (possible killer to X-Plane's drapping of roads ?)
        if (
            tri_p[:2] == tri_p[2:4]
            or tri_p[2:4] == tri_p[4:]
            or tri_p[4:] == tri_p[:2]
        ):
            continue
        if tri_p[0] == tri_p[2] == tri_p[4]:
            textured_tris[terrain_idx][tri_p[0]].extend(
                (tri_p[1], tri_p[3], tri_p[5])
            )
        else:
            total_cross_pool += 1
            textured_tris[terrain_idx]["cross-pool"].extend(tri_p)
        
        # XP water
        if is_overlay: 
            tri_p = array.array("H")
            for n in (n1, n3, n2):  # beware of ordering for orientation !
                node_hash = (n, 0)
                if node_hash in textured_nodes:
                    (idx_dsfpool, pos_in_pool) = textured_nodes[node_hash]
                else:
                    idx_dsfpool = idx_node_to_idx_pool[n] + 2 * pool_nbr
                    len_textured_nodes += 1
                    pos_in_pool = dsf_pool_length[idx_dsfpool]
                    textured_nodes[node_hash] = [idx_dsfpool, pos_in_pool]
                    # in some cases we might prefer to use normal shading for
                    # some sea triangles too (albedo continuity with elevation
                    # derived masks)
                    # dsf_pools[idx_dsfpool].extend(node_icoords[5*n:5*n+5])
                    dsf_pools[idx_dsfpool].extend(
                        node_icoords[5 * n : 5 * n + 3]
                    )
                    dsf_pools[idx_dsfpool].extend((32768, 32768))
                    ratio_bathy = BATHY.set_depth_ratio(n, node_is_coast,
                                                        node_bathy, tile)
                    ratio_fetch = 1
                    dsf_pools[idx_dsfpool].extend((int(65535 * ratio_fetch),
                                                   int(65535 * ratio_bathy))) 
                    dsf_pool_length[idx_dsfpool] += 1
                tri_p.extend((idx_dsfpool, pos_in_pool))
            if tri_p[0] == tri_p[2] == tri_p[4]:
                textured_tris[0][tri_p[0]].extend(
                    (tri_p[1], tri_p[3], tri_p[5])
                )
            else:
                total_cross_pool += 1
                textured_tris[0]["cross-pool"].extend(tri_p)
    
    download_queue.put("quit")

    UI.vprint(1, "-> Encoding of the DSF file")
    UI.vprint(1, "     Final nbr of nodes: " + str(len_textured_nodes))
    UI.vprint(2, "     Final nbr of cross pool tris: " + str(total_cross_pool))

    # Now is time to write our DSF to disk, the exact binary format is 
    # described on the wiki
    dsf_file_name = os.path.join(
        tile.build_dir,
        "Earth nav data",
        FNAMES.long_latlon(tile.lat, tile.lon) + ".dsf",
    )
    
    if os.path.exists(dsf_file_name):
        os.replace(dsf_file_name, dsf_file_name + ".bak")

    # Note: present code should always choose the first branch.
    if bPROP == b"":
        bPROP = bytes(
            "sim/west\0"
            + str(tile.lon)
            + "\0"
            + "sim/east\0"
            + str(tile.lon + 1)
            + "\0"
            + "sim/south\0"
            + str(tile.lat)
            + "\0"
            + "sim/north\0"
            + str(tile.lat + 1)
            + "\0"
            + "sim/creation_agent\0"
            + "Ortho4XP\0",
            "ascii",
        )
    else:
        bPROP += b"sim/creation_agent\0Patched by Ortho4XP\0"

    # Transfer DEM and bathymetry raster from Global Scenery tiles
    (bDEMN, bDEMS) = extract_elevation_and_bathymetry_data(tile.lat, tile.lon)

    # Computation of intermediate and of total length
    size_of_head_atom = 16 + len(bPROP)
    size_of_prop_atom = 8 + len(bPROP)
    size_of_defn_atom = (
        48 + len(bTERT) + len(bOBJT) + len(bPOLY) + len(bNETW) + len(bDEMN)
    )
    size_of_geod_atom = 8 + len(bGEOD)
    size_of_dems_atom = 8 + len(bDEMS)
    for k in range(dsf_pool_nbr):
        if dsf_pool_length[k] > 0:
            size_of_geod_atom += 21 + dsf_pool_plane[k] * (
                9 + 2 * dsf_pool_length[k]
            )
    UI.vprint(
        2, "     Size of DEFN atom : " + str(size_of_defn_atom) + " bytes."
    )
    UI.vprint(
        2, "     Size of GEOD atom : " + str(size_of_geod_atom) + " bytes."
    )
    f = open(dsf_file_name + ".tmp", "wb")
    f.write(b"XPLNEDSF")
    f.write(struct.pack("<I", 1))

    # Head super-atom
    f.write(b"DAEH")
    f.write(struct.pack("<I", size_of_head_atom))
    f.write(b"PORP")
    f.write(struct.pack("<I", size_of_prop_atom))
    f.write(bPROP)

    # Definitions super-atom
    f.write(b"NFED")
    f.write(struct.pack("<I", size_of_defn_atom))
    f.write(b"TRET")
    f.write(struct.pack("<I", 8 + len(bTERT)))
    f.write(bTERT)
    f.write(b"TJBO")
    f.write(struct.pack("<I", 8 + len(bOBJT)))
    f.write(bOBJT)
    f.write(b"YLOP")
    f.write(struct.pack("<I", 8 + len(bPOLY)))
    f.write(bPOLY)
    f.write(b"WTEN")
    f.write(struct.pack("<I", 8 + len(bNETW)))
    f.write(bNETW)
    f.write(b"NMED")
    f.write(struct.pack("<I", 8 + len(bDEMN)))
    f.write(bDEMN)

    # Geodata super-atom
    f.write(b"DOEG")
    f.write(struct.pack("<I", size_of_geod_atom))
    f.write(bGEOD)
    for k in range(dsf_pool_nbr):
        if dsf_pool_length[k] == 0:
            continue
        f.write(b"LOOP")
        f.write(
            struct.pack(
                "<I",
                13
                + dsf_pool_plane[k]
                + 2 * dsf_pool_plane[k] * dsf_pool_length[k],
            )
        )
        f.write(struct.pack("<I", dsf_pool_length[k]))
        f.write(struct.pack("<B", dsf_pool_plane[k]))
        for l in range(dsf_pool_plane[k]):
            f.write(struct.pack("<B", 0))
            for m in range(dsf_pool_length[k]):
                f.write(
                    struct.pack("<H", dsf_pools[k][dsf_pool_plane[k] * m + l])
                )
    for k in range(dsf_pool_nbr):
        if dsf_pool_length[k] == 0:
            continue
        f.write(b"LACS")
        f.write(struct.pack("<I", 8 + 8 * dsf_pool_plane[k]))
        for l in range(2 * dsf_pool_plane[k]):
            f.write(struct.pack("<f", pool_param[k % pool_nbr][l]))

    UI.progress_bar(1, 95)
    if UI.red_flag:
        UI.vprint(1, "DSF construction interrupted.")
        return 0

    # Since we possibly skipped some pools, and since we possibly
    # get pools from elsewhere, we rebuild a dico
    # which tells the pool position in the dsf of a pool prior
    # to the stripping :

    dico_new_dsf_pool = {}
    new_idx_dsfpool = nbr_dsfpools_yet_in
    for k in range(dsf_pool_nbr):
        if dsf_pool_length[k] != 0:
            dico_new_dsf_pool[k] = new_idx_dsfpool
            new_idx_dsfpool += 1

    # Commands atom
    # we first compute its size :
    size_of_cmds_atom = 8 + len(bCMDS)
    for terrain_idx in textured_tris:
        if len(textured_tris[terrain_idx]) == 0:
            continue
        size_of_cmds_atom += 3
        for idx_dsfpool in textured_tris[terrain_idx]:
            if idx_dsfpool != "cross-pool":
                size_of_cmds_atom += 13 + 2 * (
                    len(textured_tris[terrain_idx][idx_dsfpool])
                    + ceil(len(textured_tris[terrain_idx][idx_dsfpool]) / 255)
                )
            else:
                size_of_cmds_atom += 13 + 2 * (
                    len(textured_tris[terrain_idx][idx_dsfpool])
                    + ceil(len(textured_tris[terrain_idx][idx_dsfpool]) / 510)
                )
    UI.vprint(
        2, "     Size of CMDS atom : " + str(size_of_cmds_atom) + " bytes."
    )
    f.write(b"SDMC")  # CMDS header
    f.write(struct.pack("<I", size_of_cmds_atom))  # CMDS length
    f.write(bCMDS)
    for terrain_idx in textured_tris:
        if len(textured_tris[terrain_idx]) == 0:
            continue
        # print("terrain_idx = "+str(terrain_idx))
        f.write(struct.pack("<B", 4))  # SET DEFINITION 16
        f.write(struct.pack("<H", terrain_idx))  # TERRAIN INDEX
        flag = (
            1 if terrain_idx not in overlay_terrains else 2
        )  # physical or overlay
        lod = -1 if flag == 1 else tile.overlay_lod
        for idx_dsfpool in textured_tris[terrain_idx]:
            if idx_dsfpool != "cross-pool":
                f.write(struct.pack("<B", 1))  # POOL SELECT
                f.write(
                    struct.pack("<H", dico_new_dsf_pool[idx_dsfpool])
                )  # POOL INDEX

                f.write(struct.pack("<B", 18))  # TERRAIN PATCH FLAGS AND LOD
                f.write(struct.pack("<B", flag))  # FLAG
                f.write(struct.pack("<f", 0))  # NEAR LOD
                f.write(struct.pack("<f", lod))  # FAR LOD

                blocks = floor(
                    len(textured_tris[terrain_idx][idx_dsfpool]) / 255
                )
                for j in range(blocks):
                    f.write(struct.pack("<B", 23))  # PATCH TRIANGLE
                    f.write(struct.pack("<B", 255))  # COORDINATE COUNT

                    for k in range(255):
                        f.write(
                            struct.pack(
                                "<H",
                                textured_tris[terrain_idx][idx_dsfpool][
                                    255 * j + k
                                ],
                            )
                        )  # COORDINATE IDX
                remaining_tri_p = (
                    len(textured_tris[terrain_idx][idx_dsfpool]) % 255
                )
                if remaining_tri_p != 0:
                    f.write(struct.pack("<B", 23))  # PATCH TRIANGLE
                    f.write(
                        struct.pack("<B", remaining_tri_p)
                    )  # COORDINATE COUNT
                    for k in range(remaining_tri_p):
                        f.write(
                            struct.pack(
                                "<H",
                                textured_tris[terrain_idx][idx_dsfpool][
                                    255 * blocks + k
                                ],
                            )
                        )  # COORDINATE IDX
            else:  # idx_dsfpool == 'cross-pool'
                pool_idx_init = textured_tris[terrain_idx][idx_dsfpool][0]
                f.write(struct.pack("<B", 1))  # POOL SELECT
                f.write(
                    struct.pack("<H", dico_new_dsf_pool[pool_idx_init])
                )  # POOL INDEX
                f.write(struct.pack("<B", 18))  # TERRAIN PATCH FLAGS AND LOD
                f.write(struct.pack("<B", flag))  # FLAG
                f.write(struct.pack("<f", 0))  # NEAR LOD
                f.write(struct.pack("<f", lod))  # FAR LOD

                blocks = floor(
                    len(textured_tris[terrain_idx][idx_dsfpool]) / 510
                )
                for j in range(blocks):
                    f.write(struct.pack("<B", 24))  # PATCH TRIANGLE CROSS-POOL
                    f.write(struct.pack("<B", 255))  # COORDINATE COUNT
                    for k in range(255):
                        f.write(
                            struct.pack(
                                "<H",
                                dico_new_dsf_pool[
                                    textured_tris[terrain_idx][idx_dsfpool][
                                        510 * j + 2 * k
                                    ]
                                ],
                            )
                        )  # POOL IDX
                        f.write(
                            struct.pack(
                                "<H",
                                textured_tris[terrain_idx][idx_dsfpool][
                                    510 * j + 2 * k + 1
                                ],
                            )
                        )  # POS_IN_POOL IDX
                remaining_tri_p = int(
                    (len(textured_tris[terrain_idx][idx_dsfpool]) % 510) / 2
                )
                if remaining_tri_p != 0:
                    f.write(struct.pack("<B", 24))  # PATCH TRIANGLE CROSS-POOL
                    f.write(
                        struct.pack("<B", remaining_tri_p)
                    )  # COORDINATE COUNT
                    for k in range(remaining_tri_p):
                        f.write(
                            struct.pack(
                                "<H",
                                dico_new_dsf_pool[
                                    textured_tris[terrain_idx][idx_dsfpool][
                                        510 * blocks + 2 * k
                                    ]
                                ],
                            )
                        )  # POOL IDX
                        f.write(
                            struct.pack(
                                "<H",
                                textured_tris[terrain_idx][idx_dsfpool][
                                    510 * blocks + 2 * k + 1
                                ],
                            )
                        )  # POS_IN_PO0L IDX

    # DEMS atom
    if bDEMS != b"":
        f.write(b"SMED")
        f.write(struct.pack("<I", 8 + len(bDEMS)))
        f.write(bDEMS)

    UI.progress_bar(1, 98)
    if UI.red_flag:
        UI.vprint(1, "DSF construction interrupted.")
        return 0

    f.close()

    f = open(dsf_file_name + ".tmp", "rb")
    data = f.read()
    m = hashlib.md5()
    m.update(data)
    md5sum = m.digest()
    f.close()
    f = open(dsf_file_name + ".tmp", "ab")
    f.write(md5sum)
    f.close()
    
    UI.progress_bar(1, 100)
    
    size_of_dsf = (
        28
        + size_of_head_atom
        + size_of_defn_atom
        + size_of_geod_atom
        + size_of_cmds_atom
        + size_of_dems_atom
    )
    UI.vprint(
        1,
        "     DSF file encoded, total size is :",
        size_of_dsf,
        "bytes",
        "(" + UI.human_print(size_of_dsf) + ")",
    )
    return 1


##############################################################################
