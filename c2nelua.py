#!/usr/bin/env uv run --script
import sys

reserved_keywords = (
    "end",
)

type_rename_map = {
    "bool": "boolean",
    "int": "cint",
    "constchar": "char",
    # "void*": "pointer",
    "constvoid": "void",
    "size_t": "csize",

    "float": "float32",
    "uintptr_t": "usize",
    "intptr_t": "isize",

    "uint8_t": "uint8",
    "uint16_t": "uint16",
    "uint32_t": "uint32",
    "int8_t": "int8",
    "int16_t": "int16",
    "int32_t": "int32",

    "LCDColor": "ColorOrPattern",
    "LCDPattern": "Pattern",
    "LCDSolidColor": "Color",
    "LCDLineCapStyle": "LineCapStyle",
    "LCDBitmapFlip": "Flip",
    "LCDFontLanguage": "FontLanguage",
    "LCDBitmapDrawMode": "DrawMode",
    "LCDPolygonFillRule": "PolygonFillRule",
    "PDStringEncoding": "StringEncoding",
    "PDTextWrappingMode": "TextWrappingMode",
    "PDTextAlignment": "TextAlignment",

    "LCDBitmap": "Bitmap",
    "LCDBitmapTable": "BitmapTable",
    "LCDFont": "Font",
    "LCDFontData": "FontData",
    "LCDFontPage": "FontPage",
    "LCDFontGlyph": "FontGlyph",
    "LCDTileMap": "TileMap",
    "LCDVideoPlayer": "VideoPlayer",
    "LCDStreamPlayer": "StreamPlayer",
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


for line in sys.stdin:
    line = line.strip()

    if not line:
        print()
        continue

    if line.startswith("//"):
        print("  -- " + line[2:].strip())
        continue

    # this is NOT how you should parse these.
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

            if arg_name in reserved_keywords:
                arg_name = f"{arg_name}_"

            args[index] = (arg_name, arg_type)

    comment = comment.strip()
    if comment and comment.startswith("//"):
        comment = " -- " + comment[2:].strip()

    args_joined = ", ".join(f"{arg_name}: {arg_type}" for arg_name, arg_type in args)
    print(f"  {fn_name}: function({args_joined}){ret_type},{comment}")
