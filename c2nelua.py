#!/usr/bin/env uv run --script
import sys

reserved_names = ("end",)

type_rename_map = {
    "bool": "boolean",
    "constchar": "char",
    "constvoid": "void",
    "int": "cint",
    "size_t": "csize",
    "unsignedint": "cuint",
    "float": "float32",
    "intptr_t": "isize",
    "uintptr_t": "usize",
    "int16_t": "int16",
    "int32_t": "int32",
    "int8_t": "int8",
    "uint16_t": "uint16",
    "uint32_t": "uint32",
    "uint8_t": "uint8",
    "LCDBitmapDrawMode": "DrawMode",
    "LCDBitmapFlip": "Flip",
    "LCDColor": "ColorOrPattern",
    "LCDFontLanguage": "FontLanguage",
    "LCDLineCapStyle": "LineCapStyle",
    "LCDPattern": "Pattern",
    "LCDPolygonFillRule": "PolygonFillRule",
    "LCDSolidColor": "Color",
    "PDStringEncoding": "StringEncoding",
    "PDTextAlignment": "TextAlignment",
    "PDTextWrappingMode": "TextWrappingMode",
    "LCDBitmap": "Bitmap",
    "LCDBitmapTable": "BitmapTable",
    "LCDFont": "Font",
    "LCDFontData": "FontData",
    "LCDFontGlyph": "FontGlyph",
    "LCDFontPage": "FontPage",
    "LCDStreamPlayer": "StreamPlayer",
    "LCDTileMap": "TileMap",
    "LCDVideoPlayer": "VideoPlayer",
    "SDFile": "File",
}

const_rename_map = {
    "kFileRead": "Read",
    "kFileReadData": "ReadData",
    "kFileWrite": "Write",
    "kFileAppend": "Append",
}


def fix_type(typ):
    typ = "".join(typ.split())
    refs = 0
    while typ[-1] == "*":
        refs += 1
        typ = typ[:-1]
    typ = type_rename_map.get(typ, typ)

    if typ == "char" and refs >= 1:
        typ = "cstring"
        refs -= 1

    if typ == "void" and refs >= 1:
        typ = "pointer"
        refs -= 1

    typ = ("*" * refs) + typ
    return typ


def fix_const(name):
    return const_rename_map.get(name, name)


lines = list(sys.stdin)
first_line = lines[0].strip()

if first_line == "typedef enum":
    # this is defnitely hacky
    names = [line.strip().split()[0] for line in lines[2:-2]]
    enum_name = lines[-1].strip()[2:-1]
    enum_type = fix_type(enum_name)
    if enum_type == enum_name:
        enum_name = ""
    else:
        enum_name = f' "{enum_name}"'

    print(
        f'global {enum_type}: type <cimport{enum_name}, nodecl, cinclude "pd_api.h"> = @enum {{'
    )
    print(
        "  UNUSED = 0, -- Nelua doesn't allow an empty enum, but we inject the values below."
    )
    print("}")
    for name in names:
        const_name = fix_const(name)
        print(f'global {enum_type}.{const_name}: {enum_type} <cimport "{name}", nodecl, cinclude "pd_api.h">')


elif first_line == "typedef struct":
    struct_name = lines[-1].strip()[2:-1]
    struct_type = fix_type(struct_name)
    if struct_type == struct_name:
        struct_name = ""
    else:
        struct_name = f' "{struct_name}"'

    members = lines[2:-1]
    for index, member in enumerate(members):
        typ, _, name = member.rpartition(" ")
        name = "".join(name.split())[:-1]
        while name[0] == "*":
            typ += "*"
            name = name[1:]

        typ = fix_type(typ)
        members[index] = (name, typ)

    print(f'global {struct_type}: type <cimport{struct_name}, nodecl, cinclude "pd_api.h"> = @record {{')
    for name, typ in members:
        print(f"  {name}: {typ},")
    print("}")

else:
    for line_num, line in enumerate(lines):
        line = line.strip()

        if not line:
            print()
            continue

        if line.startswith("//"):
            print("  -- " + line[2:].strip())
            continue

        # this is NOT how you should parse these.
        line = line.replace("\t", " ")
        ret_type, _, rest = line.partition(" (*")
        fn_name, _, args = rest.partition(")(")
        args, _, comment = args.partition(");")

        ret_type = fix_type(ret_type)
        if ret_type == "void":
            ret_type = ""
        else:
            ret_type = f": {ret_type}"

        if args == "void":
            args = []
        else:
            args = args.split(", ")
            for index, arg in enumerate(args):
                arg_type, _, arg_name = arg.rpartition(" ")
                if not arg_type:
                    arg_type, arg_name = arg_name, f"unnamed{index}"
                arg_name = "".join(arg_name.split())

                while arg_name[0] == "*":
                    arg_type += "*"
                    arg_name = arg_name[1:]

                arg_type = fix_type(arg_type)

                if arg_name in reserved_names:
                    arg_name = f"{arg_name}_"

                args[index] = (arg_name, arg_type)

        comment = comment.strip()
        if comment and comment.startswith("//"):
            comment = " -- " + comment[2:].strip()

        args_joined = ", ".join(
            f"{arg_name}: {arg_type}" for arg_name, arg_type in args
        )
        print(f"  {fn_name}: function({args_joined}){ret_type},{comment}")
