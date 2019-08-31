from O4_Geo_Utils import *
import O4_ESP_Globals
import os
import O4_File_Names as FNAMES
from PIL import Image
import O4_Config_Utils
import subprocess
from fast_image_mask import *
import glob
from queue import Queue
from threading import Thread

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
    contents += "SamplingMethod    = Point\n"
    contents += "NullValue         = 255,255,255"

    return contents

def get_total_num_sources(seasons_to_create, build_night, build_water_mask):
    total = 0;
    if seasons_to_create:
        created_summer = False
        for season, should_build in seasons_to_create.items():
            if should_build:
                total += 1
                if season == "summer":
                    created_summer = True
        # if at least one season has been built and it is not summer, we always need to create summer
        # to cover the remaining months
        if total > 0 and not created_summer:
            total += 1

    if build_water_mask:
        # if total == 0, no seasons are being built, so we need to account for the generic, non season bmp source entry
        # TODO: when no seasons being built, just use your new logic which sets the season to summer and sets variation to all months not used...
        if total == 0:
            total += 2
        else:
            total += 1

    if build_night:
        # if total == 0, no seasons are being built, so we need to account for the generic, non season bmp source entry
        # TODO: when no seasons being built, just use your new logic which sets the season to summer and sets variation to all months not used...
        if total == 0:
            total += 2
        else:
            total += 1

    # there will at minimum always be 1 source...
    if total == 0:
        total = 1

    return total

def source_num_to_source_num_string(source_num, total_sources):
    if total_sources == 1:
        return ""

    return str(source_num)

# getting None from this function is a good way of seeing if there are no seasons to build...
def get_seasons_inf_string(seasons_to_create, source_num, type, layer, source_dir, source_file, img_mask_folder_abs_path, img_mask_name, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim, total_sources, should_mask):
    string = ""
    source_file_name, ext = os.path.splitext(source_file)
    months_used_dict = { "January": False, "February": False, "March": False, "April": False, "May": False, "June": False, "July": False, "August": False, "September": False, "October": False, "November": False, "December": False }

    if seasons_to_create["spring"]:
        string += create_INF_source_string(source_num_to_source_num_string(source_num, total_sources), "Spring", "March,April,May", type, layer, source_dir, source_file_name + "_spring" + ext, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim) + "\n\n"
        if should_mask:
            string += "; pull the blend mask from Source" + str(total_sources) + ", band 0\nChannel_BlendMask = " + str(total_sources) + ".0\n\n"
        source_num += 1
        months_used_dict["March"] = True
        months_used_dict["April"] = True
        months_used_dict["May"] = True
    if seasons_to_create["fall"]:
        string += create_INF_source_string(source_num_to_source_num_string(source_num, total_sources), "Fall", "September,October", type, layer, source_dir, source_file_name + "_fall" + ext, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim) + "\n\n"
        if should_mask:
            string += "; pull the blend mask from Source" + str(total_sources) + ", band 0\nChannel_BlendMask = " + str(total_sources) + ".0\n\n"
        source_num += 1
        months_used_dict["September"] = True
        months_used_dict["October"] = True
    if seasons_to_create["winter"]:
        string += create_INF_source_string(source_num_to_source_num_string(source_num, total_sources), "Winter", "November", type, layer, source_dir, source_file_name + "_winter" + ext, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim) + "\n\n"
        if should_mask:
            string += "; pull the blend mask from Source" + str(total_sources) + ", band 0\nChannel_BlendMask = " + str(total_sources) + ".0\n\n"
        source_num += 1
        months_used_dict["November"] = True
    if seasons_to_create["hard_winter"]:
        string += create_INF_source_string(source_num_to_source_num_string(source_num, total_sources), "HardWinter", "December,January,February", type, layer, source_dir, source_file_name + "_hard_winter" + ext, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim) + "\n\n"
        if should_mask:
            string += "; pull the blend mask from Source" + str(total_sources) + ", band 0\nChannel_BlendMask = " + str(total_sources) + ".0\n\n"
        source_num += 1
        months_used_dict["December"] = True
        months_used_dict["January"] = True
        months_used_dict["February"] = True
    # create summer with variation which includes all those months that haven't been included yet. do this if either summer is specified in Ortho4XP.cfg OR
    # if at least one other season has been specified (ie string != "") in order that all months are specified if not all seasons are specified...
    if seasons_to_create["summer"] or string != "":
        months_str = ""
        for month, has_been_used in months_used_dict.items():
            if not has_been_used:
                months_str += month + ","

        months_str = months_str[:-1]
        string += create_INF_source_string(source_num_to_source_num_string(source_num, total_sources), "Summer", months_str, type, layer, source_dir, source_file_name + ext, lon, lat, num_cells_line, num_lines, cell_x_dim, cell_y_dim) + "\n\n"
        if should_mask:
            string += "; pull the blend mask from Source" + str(total_sources) + ", band 0\nChannel_BlendMask = " + str(total_sources) + ".0\n\n"
        source_num += 1

    return (string if string != "" else None, source_num - 1)

# TODO: all this night/season mask code is kind of terrible... need to refactor
def make_ESP_inf_file(file_dir, file_name, til_x_left, til_x_right, til_y_top, til_y_bot, zoomlevel):
    file_name_no_extension, extension = os.path.splitext(file_name)
    img_top_left_tile = gtile_to_wgs84(til_x_left, til_y_top, zoomlevel)
    img_bottom_right_tile = gtile_to_wgs84(til_x_right, til_y_bot, zoomlevel)
    # TODO: add support for images of different sizes (I think different websites make different size images), but for now 4096x4096 support is good enough
    IMG_X_Y_DIM = 4096
    img_cell_x_dimension_deg = (img_bottom_right_tile[1] - img_top_left_tile[1]) / IMG_X_Y_DIM
    img_cell_y_dimension_deg = (img_top_left_tile[0] - img_bottom_right_tile[0]) / IMG_X_Y_DIM

    with open(file_dir + os.sep + file_name_no_extension + ".inf", "w") as inf_file:
        img_mask_name = "_".join(file_name.split(".bmp")[0].split("_")[0:2]) + ".tif"
        img_mask_folder_abs_path = os.path.abspath(O4_ESP_Globals.mask_dir)
        img_mask_abs_path = os.path.abspath(os.path.join(img_mask_folder_abs_path, img_mask_name))

        # make sure we have the mask tile created by Ortho4XP. even if do_build_masks is True, if tile not created
        # we don't tell resample to mask otherwise it will fail
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
        # if seasons_string is not None, there are seasons to build in Ortho4XP.cfg
        if seasons_string:
            current_source_num += num_seasons
            contents += seasons_string

        if O4_Config_Utils.create_ESP_night:
            source_num_str = source_num_to_source_num_string(current_source_num, total_num_sources)
            contents += create_INF_source_string(source_num_str, "LightMap", "LightMap", "BMP", "Imagery", os.path.abspath(file_dir), file_name_no_extension + "_night.bmp", str(img_top_left_tile[1]),
                    str(img_top_left_tile[0]), str(IMG_X_Y_DIM), str(IMG_X_Y_DIM), str(img_cell_x_dimension_deg), str(img_cell_y_dimension_deg)) + "\n\n"
            if should_mask:
                contents += "; pull the blend mask from Source" + str(total_num_sources) + ", band 0\nChannel_BlendMask = " + str(total_num_sources) + ".0\n\n"
            current_source_num += 1

        # TODO: when no seasons being built, just use your new logic which sets the season to summer and sets variation to all months not used...
        if seasons_string is None:
            source_num_str = source_num_to_source_num_string(current_source_num, total_num_sources)
            contents += create_INF_source_string(source_num_str, None, None, "BMP", "Imagery", os.path.abspath(file_dir), file_name, str(img_top_left_tile[1]),
                        str(img_top_left_tile[0]), str(IMG_X_Y_DIM), str(IMG_X_Y_DIM), str(img_cell_x_dimension_deg), str(img_cell_y_dimension_deg)) + "\n\n"
            if should_mask:
                contents += "; pull the blend mask from Source" + str(total_num_sources) + ", band 0\nChannel_BlendMask = " + str(total_num_sources) + ".0\n\n"

            current_source_num += 1

        if should_mask:
            source_num_str = source_num_to_source_num_string(current_source_num, total_num_sources)
            contents += create_INF_source_string(source_num_str, None, None, "TIFF", "None", img_mask_folder_abs_path, img_mask_name, str(img_top_left_tile[1]),
                    str(img_top_left_tile[0]), str(IMG_X_Y_DIM), str(IMG_X_Y_DIM), str(img_cell_x_dimension_deg), str(img_cell_y_dimension_deg)) + "\n\n"

        contents += "[Destination]\n"
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
            contents += "LOD = Auto, 13\n"

        inf_file.write(contents)

def spawn_resample_process(filename):
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 7 # subprocess.SW_SHOWMINNOACTIVE is 7
    process = subprocess.Popen([O4_Config_Utils.ESP_resample_loc, filename], creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=startupinfo)
    # wait until done
    process.communicate()

def remove_file_if_exists(filename):
    try:
        os.remove(filename)
    except OSError:
        pass

# TODO: cleanup processes when main program quits
def worker(queue):
    # """Process files from the queue."""
    for args in iter(queue.get, None):
        try:
            file_name = args[0]
            inf_abs_path = args[1]
            img_mask_abs_path = args[2]

            # we create the night and seasonal textures at resample time, and delete them right after...
            # why? to not require a ridiculously large amount of storage space...
            if O4_Config_Utils.create_ESP_night:
                create_night(file_name + ".bmp", file_name + "_night.bmp", img_mask_abs_path)
            if O4_Config_Utils.create_ESP_spring:
                create_spring(file_name + ".bmp", file_name + "_spring.bmp", img_mask_abs_path)
            if O4_Config_Utils.create_ESP_fall:
                create_autumn(file_name + ".bmp", file_name + "_fall.bmp", img_mask_abs_path)
            if O4_Config_Utils.create_ESP_winter:
                create_winter(file_name + ".bmp", file_name + "_winter.bmp", img_mask_abs_path)
            if O4_Config_Utils.create_ESP_hard_winter:
                create_hard_winter(file_name + ".bmp", file_name + "_hard_winter.bmp", img_mask_abs_path)

            spawn_resample_process(inf_abs_path)
            # now remove the extra night/season bmps
            # could check if we created night, season, etc but let's be lazy and use remove_file_if_exists
            remove_file_if_exists(file_name + "_night.bmp")
            remove_file_if_exists(file_name + "_spring.bmp")
            remove_file_if_exists(file_name + "_fall.bmp")
            remove_file_if_exists(file_name + "_winter.bmp")
            remove_file_if_exists(file_name + "_hard_winter.bmp")
        except Exception as e: # catch exceptions to avoid exiting the
                               # thread prematurely
            print('%r failed: %s' % (args, e,))

def spawn_scenproc_process(scenproc_script_file, scenproc_osm_file, texture_folder):
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 7 # subprocess.SW_SHOWMINNOACTIVE is 7
    process = subprocess.Popen([O4_Config_Utils.ESP_scenproc_loc, scenproc_script_file, "/run", scenproc_osm_file, texture_folder],
                                creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=startupinfo)
    # wait until done
    process.communicate()

def run_scenproc_threaded(queue):
    # """Process files from the queue."""
    for args in iter(queue.get, None):
        try:
            scenproc_script_file = args[0]
            scenproc_osm_file = args[1]
            texture_folder = args[2]
            spawn_scenproc_process(scenproc_script_file, scenproc_osm_file, texture_folder)
        except Exception as e: # catch exceptions to avoid exiting the
                               # thread prematurely
            print('%r failed: %s' % (args, e,))


def build_for_ESP(build_dir, tile):
    if not build_dir:
        print("ESP_build_dir is None inside of resample... something went wrong, so can't run resample")
        return

    if O4_Config_Utils.ESP_resample_loc is '':
        print("No resample.exe is specified in Ortho4XP.cfg, quitting")
        return
    if not os.path.isfile(O4_Config_Utils.ESP_resample_loc):
        print("resample.exe doesn't exist at " + O4_Config_Utils.ESP_resample_loc + ", quitting")
        return

    # run ScenProc if user has specified path to the scenProc.exe and OSM file was successfully downloaded previously
    scenproc_osm_directory = os.path.abspath(os.path.join(FNAMES.osm_dir(tile.lat, tile.lon), "scenproc_osm_data"))
    scenproc_thread = None
    q2 = None
    if os.path.isfile(O4_Config_Utils.ESP_scenproc_loc) and os.path.exists(scenproc_osm_directory):
        scenproc_script_file = os.path.abspath(FNAMES.scenproc_script_file(O4_Config_Utils.ESP_scenproc_script))
        addon_scenery_folder = os.path.abspath(os.path.join(build_dir, "ADDON_SCENERY"))
        texture_folder = os.path.abspath(os.path.join(addon_scenery_folder, "texture"))
        # in case resample threads haven't created ADDON_SCENERY folder yet
        # TODO: maybe race condition??
        if not os.path.exists(addon_scenery_folder):
            os.mkdir(addon_scenery_folder)
        if not os.path.exists(texture_folder):
            os.mkdir(texture_folder)

        q2 = Queue()
        scenproc_thread = Thread(target=run_scenproc_threaded, args=(q2, ))
        scenproc_thread.daemon = True
        scenproc_thread.start()
        for (dirpath, dir_names, file_names) in os.walk(scenproc_osm_directory):
            print("Running ScenProc... Run the below command on each file in this directory if you want to run scenProc manually:")
            first_scenproc_file = os.path.abspath(os.path.join(scenproc_osm_directory, file_names[0]))
            print(O4_Config_Utils.ESP_scenproc_loc + " " + scenproc_script_file + " /run " + first_scenproc_file + " " + texture_folder)
            for full_file_name in file_names:
                scenproc_osm_file_name = os.path.abspath(os.path.join(scenproc_osm_directory, full_file_name))
                q2.put_nowait([scenproc_script_file, scenproc_osm_file_name, texture_folder])
        
    # call resample on each individual file, to avoid file name too long errors with subprocess
    # https://stackoverflow.com/questions/2381241/what-is-the-subprocess-popen-max-length-of-the-args-parameter
    # passing shell=True to subprocess didn't help with this error when there are a large amount of inf files to process
    # another solution would be to create inf files with multiple sources, but the below is simpler to code...
	# start threads
    print("Starting ESP queue with a max of " + str(O4_Config_Utils.max_resample_processes) + " processes. *Resample windows will open minimized to the task bar. This process will take a while... you will be notified when finished")
    q = Queue()
    threads = [Thread(target=worker, args=(q,)) for _ in range(O4_Config_Utils.max_resample_processes)]
    for t in threads:
        t.daemon = True # threads die if the program dies
        t.start()

    for (dirpath, dir_names, file_names) in os.walk(build_dir):
        for full_file_name in file_names:
            file_name, file_extension = os.path.splitext(os.path.abspath(build_dir + os.sep + full_file_name))
            if file_extension == ".inf":
                inf_abs_path = file_name + file_extension

                # TODO: refactor below code into function as you've repeated it above...
                img_mask_name = "_".join(full_file_name.split(".inf")[0].split("_")[0:2]) + ".tif"
                img_mask_folder_abs_path = os.path.abspath(O4_ESP_Globals.mask_dir)
                img_mask_abs_path = os.path.abspath(os.path.join(img_mask_folder_abs_path, img_mask_name))
                should_mask = (O4_ESP_Globals.do_build_masks and os.path.isfile(img_mask_abs_path))
                if not should_mask:
                    img_mask_abs_path = None

                # subprocess.call([O4_Config_Utils.ESP_resample_loc, inf_abs_path])
                q.put_nowait([file_name, inf_abs_path, img_mask_abs_path])
    
    for _ in threads: q.put_nowait(None) # signal no more files
    if scenproc_thread is not None:
        q2.put_nowait(None)

    for t in threads: t.join() # wait for completion
    if scenproc_thread is not None:
        scenproc_thread.join()
