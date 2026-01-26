#!/usr/bin/env python3
from pathlib import Path
import os
from shutil import which
import subprocess

BLACK = "\033[37m"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"
YELLOW = "\033[33m"


def run(args):
    print(f"{GREEN}$", f"{YELLOW}{args[0]}{BLACK}", *args[1:], RESET)
    subprocess.run(args)


def get_sdk_path() -> str:
    if (from_env := os.getenv("PLAYDATE_SDK_PATH")) is not None:
        return from_env

    with open(Path.home() / ".Playdate" / "config") as fp:
        for line in fp:
            if line.startswith("SDKRoot"):
                return line.split()[1]


pdx = "HelloWorld.pdx"

cwd = Path.cwd()
assets_dir = cwd / "assets"
src_dir = cwd / "src"
build_dir = cwd / "build"
dep_dir = build_dir / "dep"
bundle_dir = build_dir / "bundle"

sdk_dir = Path(get_sdk_path())
c_api_dir = sdk_dir / "C_API"
support_dir = c_api_dir / "buildsupport"

dev_main_c = build_dir / "dev_main.c"
sim_main_c = build_dir / "sim_main.c"
setup_c = support_dir / "setup.c"

sim_defs = [
    "TARGET_SIMULATOR",
    "TARGET_EXTENSION",
]

dev_defs = [
    "TARGET_PLAYDATE",
    "TARGET_EXTENSION",
]

include_dirs = [
    cwd,
    c_api_dir,
]

lib_dirs = []

nelua = which("nelua")

sim_cc = which("clang")  # FIXME gcc if linux
sim_cc_flags = [
    "-g",  # "Generate source-level debug information"
    "-lm",  # I think this links with the math lib?
]

dylib_flags = [
    "-dynamiclib",  # undocumented
    "-rdynamic",  # undocumented
]
dylib_ext = "dylib"
dylib = build_dir / ("pdex." + dylib_ext)

pdc = which("pdc")

dev_prefix = "arm-none-eabi-"
dev_cc_flags = [
    "-g3",  # not sure, possibly related to -g
]

dev_cc = which(dev_prefix + "gcc")
dev_objcopy = which(dev_prefix + "objcopy")
dev_strip = which(dev_prefix + "strip")

dev_as = [dev_cc, "-x", "assembler-with-cpp"]
dev_bin = [dev_objcopy, "-O", "binary"]
dev_hex = [dev_objcopy, "-O", "hex"]

build_dir.mkdir(exist_ok=True)
bundle_dir.mkdir(exist_ok=True)
dep_dir.mkdir(exist_ok=True)

dev_flags = [
    "-mthumb",
    "-mcpu=cortex-m7",
    "-mfloat-abi=hard",
    "-mfpu=fpv5-sp-d16",
    "-D__FPU_USED=1",
]

cp_flags = [
    "-O2",
    "-falign-functions=16",
    "-fomit-frame-pointer",
    "-gdwarf-2",
    "-Wall",
    "-Wno-unused",
    "-Wstrict-prototypes",
    "-Wno-unknown-pragmas",
    "-Wdouble-promotion",
    "-mword-relocations",
    "-fverbose-asm",
    "-fno-common",
    "-ffunction-sections",
    "-fdata-sections",
]

ld_flags = [
    "--specs=nosys.specs",
    "-nostartfiles",
    "-T/Users/jweachock/Developer/PlaydateSDK/C_API/buildsupport/link_map.ld",
    "-Wl,-Map=build/pdex.map,--cref,--gc-sections,--no-warn-mismatch,--emit-relocs",
]

print(set(cp_flags) & set(ld_flags))

sim_def_flags = [f"-D{flag}=1" for flag in sim_defs]
dev_def_flags = [f"-D{flag}=1" for flag in dev_defs]
include_flags = [flag for path in include_dirs for flag in ("-I", path)]

# transpile main.c for device
run(
    [nelua] + ["--cc", dev_cc] + ["--code", "src/main.nelua"] + ["--output", dev_main_c]
)

# transpile main.c for simulator
run(
    [nelua] + ["--cc", sim_cc] + ["--code", "src/main.nelua"] + ["--output", sim_main_c]
)

# compile main.o for device
run(
    [dev_cc]
    + dev_cc_flags
    + [
        "-c",
    ]
    + dev_flags
    + cp_flags
    + [
        "-Wa,-ahlms=build/main.lst",
    ]
    + dev_def_flags
    + [
        "-MD",
        "-MP",
        "-MF",
        "build/dep/main.o.d",
    ]
    + include_flags
    + [dev_main_c, "-o", "build/main.o"]
)

# compile setup.o for device
run(
    [dev_cc]
    + dev_cc_flags
    + [
        "-c",
    ]
    + dev_flags
    + cp_flags
    + [
        "-Wa,-ahlms=build/setup.lst",
    ]
    + dev_def_flags
    + [
        "-MD",
        "-MP",
        "-MF",
        "build/dep/setup.o.d",
    ]
    + include_flags
    + [setup_c, "-o", "build/setup.o"]
)

# link for device
run(
    [dev_cc]
    + ["build/main.o", "build/setup.o"]
    + dev_flags
    + ld_flags
    + ["-o", "build/pdex.elf"]
)

# compile for simulator
run(
    [sim_cc]
    + sim_cc_flags
    + dylib_flags
    + sim_def_flags
    + include_flags
    + ["-o", dylib]
    + [sim_main_c, setup_c]
)

run(["cp", "-rf", "build/pdex.elf", dylib, bundle_dir])
run(["cp", "-rf"] + list(assets_dir.iterdir()) + [bundle_dir])

run([pdc, bundle_dir, pdx])
