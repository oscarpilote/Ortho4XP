#!/usr/bin/env python3

import os
import sys
sys.dont_write_bytecode = True

lin_cfg = { 
        "name":"Linux",
        "dir":"lin",
        "suff" : "",
        "toolchain":""
      }

mac_cfg = { 
        "name":"OSX",
        "dir":"mac",
        "suff":"",
        "toolchain":"./toolchains/osxcross-on-linux.cmake"
      }

win_cfg = { 
        "name":"Windows",
        "dir":"win",
        "suff":".exe",
        "toolchain":"./toolchains/mingw-on-linux.cmake"
      }

all_cfg = [lin_cfg, mac_cfg, win_cfg]

def parse_args(argv):
    build_type = ""
    os_cfg = []
    dest = ""
    data_dest = ""
    for arg in argv[1:]:
        if "debug" in arg.lower():
            build_type = "Debug"
        if "release" in arg.lower():
            build_type = "Release"
        if "lin" in arg.lower():
            os_cfg.append(lin_cfg)
        if "mac" in arg.lower():
            os_cfg.append(mac_cfg)
        if "win" in arg.lower():
            os_cfg.append(win_cfg)
            
    if (not  build_type):
        build_type = "Release"
    if (not os_cfg):
        os_cfg = all_cfg
    return (build_type, os_cfg)

   
if __name__ == "__main__":
    (build_type, os_cfg) = parse_args(sys.argv)
    for cfg in os_cfg:
        print()
        print("--------------------------------------------------------")
        print("Configurating Ortho4XP C executables {:s} mode for {:s}.".format(build_type, cfg["name"]))
        print("--------------------------------------------------------")
        cmd =  "cmake"
        if cfg["toolchain"]: 
            cmd += " -DCMAKE_TOOLCHAIN_FILE=" + cfg["toolchain"]
        cmd += " -DCMAKE_BUILD_TYPE=" + build_type
        cmd += " -B build/" + build_type.lower() + "/" + cfg["dir"]
        print("Executing : " + cmd)
        os.system(cmd)
        print("Configuration done for " + cfg["name"] + ".")
