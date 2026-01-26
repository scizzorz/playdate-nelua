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

main_nelua = src_dir / "main.nelua"

dev_main_c = build_dir / "dev_main.c"
sim_main_c = build_dir / "sim_main.c"
setup_c = support_dir / "setup.c"

dylib = build_dir / "pdex.dylib"
elf = build_dir / "pdex.elf"

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

pdc = which("pdc")

dev_prefix = "arm-none-eabi-"
dev_cc_flags = [
    "-g3",  # not sure, possibly related to -g
    "-mthumb",
    "-mcpu=cortex-m7",
    "-mfloat-abi=hard",
    "-mfpu=fpv5-sp-d16",
    "-D__FPU_USED=1",
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

sim_def_flags = [f"-D{flag}=1" for flag in sim_defs]
dev_def_flags = [f"-D{flag}=1" for flag in dev_defs]
include_flags = [flag for path in include_dirs for flag in ("-I", path)]


def transpile_nelua(cc, output):
    run([nelua, "--cc", cc, "--code", main_nelua, "--output", output])


def compile_for_device(source_files):
    obj_files = []
    for source_file in source_files:
        assembly_list = build_dir / source_file.with_suffix(".lst").name
        dep_file = dep_dir / source_file.with_suffix(".d").name
        obj_file = build_dir / source_file.with_suffix(".o").name
        run(
            [dev_cc]
            + dev_cc_flags
            + cp_flags
            + dev_def_flags
            + include_flags
            + [
                f"-Wa,-ahlms={assembly_list}",
                "-MD",
                "-MP",
                "-MF",
                dep_file,
                "-c",
                source_file,
                "-o",
                obj_file,
            ]
        )
        obj_files.append(obj_file)

    return obj_files


def link_for_device(obj_files):
    run([dev_cc] + dev_cc_flags + ld_flags + obj_files + ["-o", elf])


def compile_for_simulator(source_files):
    run(
        [sim_cc]
        + sim_cc_flags
        + dylib_flags
        + sim_def_flags
        + include_flags
        + source_files
        + ["-o", dylib]
    )


# transpile main.c for device
transpile_nelua(dev_cc, dev_main_c)

# transpile main.c for simulator
transpile_nelua(sim_cc, sim_main_c)

# compile main.o for device
obj_files = compile_for_device([dev_main_c, setup_c])

# link for device
link_for_device(obj_files)

# compile for simulator
compile_for_simulator([sim_main_c, setup_c])

# populate bundle
run(["cp", "-rf", elf, dylib, bundle_dir])
run(["cp", "-rf"] + list(assets_dir.iterdir()) + [bundle_dir])

# build PDX
run([pdc, bundle_dir, pdx])
