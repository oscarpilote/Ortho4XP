from O4_Geo_Utils import *
import O4_ESP_Globals
import os
import O4_File_Names as FNAMES
from PIL import Image
from O4_Config_Utils import ESP_resample_loc
import subprocess

#TODO: use os.path.join instead of os.sep and concatenation

def create_INF_source_string(source_num, type, layer, source_dir, source_file, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim):
    contents = "[Source" + source_num + "]\n"
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

def make_ESP_inf_file(file_dir, file_name, til_x_left, til_x_right, til_y_top, til_y_bot, zoomlevel):
    file_name_no_extension, extension = os.path.splitext(file_name)
    img_top_left_tile = gtile_to_wgs84(til_x_left, til_y_top, zoomlevel)
    img_bottom_right_tile = gtile_to_wgs84(til_x_right, til_y_bot, zoomlevel)
    # TODO: add support for images of different sizes (I think different websites make different size images), but for now 4096x4096 support is good enough
    IMG_X_Y_DIM = 4096
    img_cell_x_dimension_deg = (img_bottom_right_tile[1] - img_top_left_tile[1]) / IMG_X_Y_DIM
    img_cell_y_dimension_deg = (img_top_left_tile[0] - img_bottom_right_tile[0]) / IMG_X_Y_DIM

    with open(file_dir + os.sep + file_name_no_extension + ".inf", "w") as inf_file:
        if True or O4_ESP_Globals.do_build_masks:
            contents = create_INF_source_string("1", "BMP", "Imagery", os.path.abspath(file_dir), file_name, str(img_top_left_tile[1]),
                    str(img_top_left_tile[0]), str(IMG_X_Y_DIM), str(IMG_X_Y_DIM), str(img_cell_x_dimension_deg), str(img_cell_y_dimension_deg))
            build_dir_path_parts = os.path.abspath(file_dir).split(os.sep)
            str_lat_lon_folder_name = build_dir_path_parts[build_dir_path_parts.index("Orthophotos") + 1] + os.sep + build_dir_path_parts[build_dir_path_parts.index("Orthophotos") + 2]
            img_mask_folder_abs_path = os.path.abspath(FNAMES.Ortho4XP_dir + os.sep + "Masks" + os.sep + str_lat_lon_folder_name)
            img_mask_name = "_".join(file_name.split(".bmp")[0].split("_")[0:2]) + ".tif"
            img_mask_abs_path = os.path.abspath(img_mask_folder_abs_path + os.sep + img_mask_name)

            contents = "[Source]\nType = MultiSource\nNumberOfSources = 2\n\n" + contents + "\n"
            contents += "; pull the blend mask from Source2, band 0\nChannel_BlendMask = 2.0\n\n"
            contents += create_INF_source_string("2", "TIFF", "None", img_mask_folder_abs_path, img_mask_name, str(img_top_left_tile[1]),
                    str(img_top_left_tile[0]), str(IMG_X_Y_DIM), str(IMG_X_Y_DIM), str(img_cell_x_dimension_deg), str(img_cell_y_dimension_deg))
        else:
            contents = create_INF_source_string("", "BMP", "Imagery", os.path.abspath(file_dir), file_name, str(img_top_left_tile[1]),
                    str(img_top_left_tile[0]), str(IMG_X_Y_DIM), str(IMG_X_Y_DIM), str(img_cell_x_dimension_deg), str(img_cell_y_dimension_deg))


        contents += "\n\n[Destination]\n"
        contents += "DestDir             = " + os.path.abspath(file_dir) + os.sep + "ADDON_SCENERY" + os.sep + "scenery\n"
        contents += "DestBaseFileName     = " + file_name_no_extension + "\n"
        contents += "BuildSeasons        = 0\n"
        contents += "UseSourceDimensions  = 1\n"
        contents += "CompressionQuality   = 100\n"
        contents += "LOD = Auto,13\n"

        inf_file.write(contents)


def run_ESP_resample(build_dir):
    if ESP_resample_loc is '':
        print("No resample.exe is specified in Ortho4XP.cfg, quitting")
        return
    if not os.path.isfile(ESP_resample_loc):
        print("resample.exe doesn't exist at " + ESP_resample_loc + ", quitting")
        return


    # call resample on each individual file, to avoid file name too long errors with subprocess
    # https://stackoverflow.com/questions/2381241/what-is-the-subprocess-popen-max-length-of-the-args-parameter
    # passing shell=True to subprocess didn't help with this error when there are a large amount of inf files to process
    # another solution would be to create inf files with multiple sources, but the below is simpler to code...
    for (dirpath, dir_names, file_names) in os.walk(build_dir):
        for full_file_name in file_names:
            file_name, file_extension = os.path.splitext(full_file_name)
            if file_extension == ".inf":
                inf_abs_path = os.path.abspath(FNAMES.Ortho4XP_dir + os.sep + build_dir + os.sep + full_file_name)
                print(inf_abs_path)
                subprocess.call([ESP_resample_loc, inf_abs_path])

def convert_BMP_to_8_bit_grayscale_tif(img_name, saveNewName=False):
    img = Image.open(img_name).convert("RGB")
    img.save(img_name)