#!/usr/bin/env python3

import os
import sys
sys.dont_write_bytecode = True
import shutil

import configure

def parse_args():
    build_type = "release"
    for arg in sys.argv[1:]:
        if arg.lower() == "debug":
            build_type = "debug"
    return build_type

build_type = parse_args()

for cfg in configure.all_cfg:
    dst = os.path.join(cfg["dir"])
    os.makedirs(dst, exist_ok = True)
    src = os.path.join("build", build_type, cfg["dir"], "Triangle4XP" + cfg["suff"])
    shutil.copy2(src, dst)



