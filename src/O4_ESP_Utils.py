from O4_Geo_Utils import *
import O4_ESP_Globals
import os
import O4_File_Names as FNAMES
from PIL import Image
import O4_Config_Utils
import subprocess
from fast_image_mask import *
import glob

#TODO: use os.path.join instead of os.sep and concatenation

def create_INF_source_string(source_num, season, variation, type, layer, source_dir, source_file, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim):
    contents = "[Source" + source_num + "]\n"
    if season:
        contents += "Season          = " + season + "\n"
    if variation:
        contents += "Variation          = " + variation + "\n"

    contents += "Type          = " + type + "\n"
    contents += "Layer          = " + layer + "\n"
    contents += "SourceDir  = " + source_dir + "\n"
    contents += "SourceFile = " + source_file + "\n"
    contents += "Lon               = " + lon + "\n"
    contents += "Lat               = " + lat + "\n"
    contents += "NumOfCellsPerLine = " + num_cells_line + "       ;Pixel isn't FSX/P3D\n"
    contents += "NumOfLines        = " + num_lines + "       ;Pixel isn't used in FSX/P3D\n"
    contents += "CellXdimensionDeg = """ + cell_x_dim + "\n"
    contents += "CellYdimensionDeg = """ + cell_y_dim + "\n"
    contents += "PixelIsPoint      = 0\n"
    contents += "SamplingMethod    = Point"

    return contents

def get_total_num_sources(seasons_to_create, build_night, build_water_mask):
    # there will at minimum always be 1 source...
    total = 1;
    if seasons_to_create:
        for season, should_build in seasons_to_create.items():
            if should_build:
                total += 1

    if build_night:
        total += 1
    if build_water_mask:
        total += 1

    return total

def source_num_to_source_num_string(source_num, total_sources):
    if total_sources == 1:
        return ""

    return str(source_num)

# getting None from this function is a good way of seeing if there are no seasons to build...
def get_seasons_inf_string(seasons_to_create, source_num, type, layer, source_dir, source_file, img_mask_folder_abs_path, img_mask_name, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim, total_sources, should_mask):
    string = ""
    source_file_name, ext = os.path.splitext(source_file)
    if seasons_to_create["summer"]:
        string = create_INF_source_string(str(source_num), "Summer", "June,July,August", type, layer, source_dir, source_file_name + ext, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim) + "\n\n"
        if should_mask:
            string += "; pull the blend mask from Source" + str(total_sources) + ", band 0\nChannel_BlendMask = " + str(total_sources) + ".0\n\n"
        source_num += 1
    if seasons_to_create["spring"]:
        string += create_INF_source_string(str(source_num), "Spring", "March,April,May", type, layer, source_dir, source_file_name + "_spring" + ext, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim) + "\n\n"
        if should_mask:
            string += "; pull the blend mask from Source" + str(total_sources) + ", band 0\nChannel_BlendMask = " + str(total_sources) + ".0\n\n"
        source_num += 1
    if seasons_to_create["fall"]:
        string += create_INF_source_string(str(source_num), "Fall", "September,October", type, layer, source_dir, source_file_name + "_fall" + ext, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim) + "\n\n"
        if should_mask:
            string += "; pull the blend mask from Source" + str(total_sources) + ", band 0\nChannel_BlendMask = " + str(total_sources) + ".0\n\n"
        source_num += 1
    if seasons_to_create["winter"]:
        string += create_INF_source_string(str(source_num), "Winter", "November", type, layer, source_dir, source_file_name + "_winter" + ext, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim) + "\n\n"
        if should_mask:
            string += "; pull the blend mask from Source" + str(total_sources) + ", band 0\nChannel_BlendMask = " + str(total_sources) + ".0\n\n"
        source_num += 1
    if seasons_to_create["hard_winter"]:
        string += create_INF_source_string(str(source_num), "HardWinter", "December,January,February", type, layer, source_dir, source_file_name + "_hard_winter" + ext, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim) + "\n\n"
        if should_mask:
            string += "; pull the blend mask from Source" + str(total_sources) + ", band 0\nChannel_BlendMask = " + str(total_sources) + ".0\n\n"
        source_num += 1

    return (string if string != "" else None, source_num - 1)

def make_ESP_inf_file(file_dir, file_name, til_x_left, til_x_right, til_y_top, til_y_bot, zoomlevel):
    file_name_no_extension, extension = os.path.splitext(file_name)
    img_top_left_tile = gtile_to_wgs84(til_x_left, til_y_top, zoomlevel)
    img_bottom_right_tile = gtile_to_wgs84(til_x_right, til_y_bot, zoomlevel)
    # TODO: add support for images of different sizes (I think different websites make different size images), but for now 4096x4096 support is good enough
    IMG_X_Y_DIM = 4096
    img_cell_x_dimension_deg = (img_bottom_right_tile[1] - img_top_left_tile[1]) / IMG_X_Y_DIM
    img_cell_y_dimension_deg = (img_top_left_tile[0] - img_bottom_right_tile[0]) / IMG_X_Y_DIM

    with open(file_dir + os.sep + file_name_no_extension + ".inf", "w") as inf_file:
        build_dir_path_parts = os.path.abspath(file_dir).split(os.sep)
        str_lat_lon_folder_name = build_dir_path_parts[build_dir_path_parts.index("Orthophotos") + 1] + os.sep + build_dir_path_parts[build_dir_path_parts.index("Orthophotos") + 2]
        img_mask_folder_abs_path = os.path.abspath(FNAMES.Ortho4XP_dir + os.sep + "Masks" + os.sep + str_lat_lon_folder_name)
        img_mask_name = "_".join(file_name.split(".bmp")[0].split("_")[0:2]) + ".tif"
        img_mask_abs_path = os.path.abspath(img_mask_folder_abs_path + os.sep + img_mask_name)

        # make sure we have the mask tile created by Ortho4XP. even if do_build_masks is True, if tile not created
        # we don't tell resample to mask otherwise it will fail
        print(str(O4_ESP_Globals.do_build_masks))
        print(str(os.path.isfile(img_mask_abs_path)))
        print(img_mask_abs_path)
        should_mask = (O4_ESP_Globals.do_build_masks and os.path.isfile(img_mask_abs_path))
        seasons_to_create = {
            "summer": O4_Config_Utils.create_ESP_summer,
            "spring": O4_Config_Utils.create_ESP_spring,
            "fall": O4_Config_Utils.create_ESP_fall,
            "winter": O4_Config_Utils.create_ESP_winter,
            "hard_winter": O4_Config_Utils.create_ESP_hard_winter
        }
        contents = ""
        total_num_sources = get_total_num_sources(seasons_to_create, O4_Config_Utils.create_ESP_night, should_mask)
        if total_num_sources > 1:
            contents = "[Source]\nType = MultiSource\nNumberOfSources = " + str(total_num_sources) + "\n\n"

        current_source_num = 1
        seasons_string, num_seasons = get_seasons_inf_string(seasons_to_create, current_source_num, "BMP", "Imagery", os.path.abspath(file_dir), file_name, img_mask_folder_abs_path, img_mask_abs_path,
        str(img_top_left_tile[1]), str(img_top_left_tile[0]), str(IMG_X_Y_DIM), str(IMG_X_Y_DIM), str(img_cell_x_dimension_deg), str(img_cell_y_dimension_deg), total_num_sources, should_mask)
        # if seasons_strong is not None, there are seasons to build in Ortho4XP.cfg
        if seasons_string:
            current_source_num += num_seasons
            contents += seasons_string

        if O4_Config_Utils.create_ESP_night:
            source_num_str = source_num_to_source_num_string(current_source_num, total_num_sources)
            contents += create_INF_source_string(source_num_str, "LightMap", "LightMap", "BMP", "Imagery", os.path.abspath(file_dir), file_name, str(img_top_left_tile[1]),
                    str(img_top_left_tile[0]), str(IMG_X_Y_DIM), str(IMG_X_Y_DIM), str(img_cell_x_dimension_deg), str(img_cell_y_dimension_deg)) + "\n\n"
            if should_mask:
                contents += "; pull the blend mask from Source" + str(total_num_sources) + ", band 0\nChannel_BlendMask = " + str(total_num_sources) + ".0\n\n"
            current_source_num += 1

        source_num_str = source_num_to_source_num_string(current_source_num, total_num_sources)
        contents += create_INF_source_string(source_num_str, None, None, "BMP", "Imagery", os.path.abspath(file_dir), file_name, str(img_top_left_tile[1]),
                    str(img_top_left_tile[0]), str(IMG_X_Y_DIM), str(IMG_X_Y_DIM), str(img_cell_x_dimension_deg), str(img_cell_y_dimension_deg))
        current_source_num += 1
        print(str(should_mask))
        if should_mask:
            source_num_str = source_num_to_source_num_string(current_source_num, total_num_sources)
            contents += "\n\n; pull the blend mask from Source" + source_num_str + ", band 0\nChannel_BlendMask = " + source_num_str + ".0\n\n"
            contents += create_INF_source_string(source_num_str, None, None, "TIFF", "None", img_mask_folder_abs_path, img_mask_name, str(img_top_left_tile[1]),
                    str(img_top_left_tile[0]), str(IMG_X_Y_DIM), str(IMG_X_Y_DIM), str(img_cell_x_dimension_deg), str(img_cell_y_dimension_deg))

        contents += "\n\n[Destination]\n"
        contents += "DestDir             = " + os.path.abspath(file_dir) + os.sep + "ADDON_SCENERY" + os.sep + "scenery\n"
        contents += "DestBaseFileName     = " + file_name_no_extension + "\n"
        contents += "BuildSeasons        = 0\n"
        contents += "UseSourceDimensions  = 1\n"
        contents += "CompressionQuality   = 100\n"

        # Default land class textures will be used if the terrain system cannot find photo-imagery at LOD13 (5 meters per pixel) or greater detail.
        # source: https://docs.microsoft.com/en-us/previous-versions/microsoft-esp/cc707102(v=msdn.10)
        # otherwise, nothing will be added, so the default of LOD = Auto will be used
        LOD_13_DEG_PER_PIX = 4.27484e-05
        if img_cell_x_dimension_deg > LOD_13_DEG_PER_PIX or img_cell_y_dimension_deg > LOD_13_DEG_PER_PIX:
            pass
            #contents += "LOD = Auto, 13\n"

        inf_file.write(contents)


def run_ESP_resample(build_dir):
    if O4_Config_Utils.ESP_resample_loc is '':
        print("No resample.exe is specified in Ortho4XP.cfg, quitting")
        return
    if not os.path.isfile(O4_Config_Utils.ESP_resample_loc):
        print("resample.exe doesn't exist at " + O4_Config_Utils.ESP_resample_loc + ", quitting")
        return


    # call resample on each individual file, to avoid file name too long errors with subprocess
    # https://stackoverflow.com/questions/2381241/what-is-the-subprocess-popen-max-length-of-the-args-parameter
    # passing shell=True to subprocess didn't help with this error when there are a large amount of inf files to process
    # another solution would be to create inf files with multiple sources, but the below is simpler to code...
    for (dirpath, dir_names, file_names) in os.walk(build_dir):
        for full_file_name in file_names:
            file_name, file_extension = os.path.splitext(os.path.abspath(build_dir + os.sep + full_file_name))
            if file_extension == ".inf":
                inf_abs_path = file_name + file_extension
                # we create the night and seasonal textures at resample time, and delete them right after...
                # why? to not require a ridiculously large amount of storage space...
                if O4_Config_Utils.create_ESP_night:
                    create_night(file_name + ".bmp", file_name + "_night.bmp")
                if O4_Config_Utils.create_ESP_spring:
                    create_spring(file_name + ".bmp", file_name + "_spring.bmp")
                if O4_Config_Utils.create_ESP_fall:
                    create_autumn(file_name + ".bmp", file_name + "_fall.bmp")
                if O4_Config_Utils.create_ESP_winter:
                    create_winter(file_name + ".bmp", file_name + "_winter.bmp")
                if O4_Config_Utils.create_ESP_hard_winter:
                    create_hard_winter(file_name + ".bmp", file_name + "_hard_winter.bmp")

                subprocess.call([O4_Config_Utils.ESP_resample_loc, inf_abs_path])
                # now remove the extra night/season bmps
                for file in glob.glob(file_name + "_*.bmp"):
                    os.remove(file)

def convert_BMP_to_8_bit_grayscale_tif(img_name, saveNewName=False):
    img = Image.open(img_name).convert("RGB")
    img.save(img_name)
