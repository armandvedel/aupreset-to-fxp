from construct import Array, Float32b, Bytes, Const, Container, Enum, LazyBound, PaddedString, Struct, Switch, Int32ub, Int32ul
from os import path
import sys
import base64
from xml.dom import minidom

# fxp/fxb file format. (VST/Cubase's preset or "bank" files from before VST3 era)
# based on VST SDK's vst2.x/vstfxstore.h
# names as in the source
vst2preset = Struct(
     'chunkMagic' / Const(b"CcnK"),
     "byteSize" / Int32ub,
     "fxMagic" / Enum(Bytes(4),
        FXP_PARAMS = b'FxCk', FXP_OPAQUE_CHUNK = b'FPCh',
        FXB_REGULAR = b'FxBk', FXB_OPAQUE_CHUNK = b'FBCh',
     ),
     "version" / Int32ub,
     "fxID" / Int32ub,
     "fxVersion" / Int32ub,
     "count" / Int32ub,
     # Switch('data', lambda ctx: ctx['fxMagic'], {
     #     'FXP_PARAMS': Struct('data',
     #         String('prgName', 28, padchar = '\0'),
     #         Array(lambda ctx: ctx['_']['count'], Float32b('params')),
     #         ),
     #     'FXP_OPAQUE_CHUNK': Struct('data',
     #         String('prgName', 28, padchar = '\0'),
     #         Int32ub('size'),
     #         Bytes('chunk', lambda ctx: ctx['size']),
     #         ),
     #     'FXB_REGULAR': Struct('data',
     #         Bytes('future', 128), # zeros
     #         # Array of FXP_PARAMS vst2preset
     #         Array(lambda ctx: ctx['_']['count'], LazyBound('presets', lambda: vst2preset)),
     #         ),
     #     'FXB_OPAQUE_CHUNK': Struct('data',
     #         Bytes('future', 128), # zeros
     #         Int32ub('size'),
     #         # Unknown format of internal chunk
     #         Bytes('chunk', lambda ctx: ctx['size']),
     #         ),
     #     }),
     )

def get_aupreset_value_node_for_key(dom, key, value_tag):
    for key_node in dom.getElementsByTagName('key'):
        [key_data] = key_node.childNodes
        if key_data.data == key:
            break
    else:
        raise KeyError
    # Advance to the value node.
    node = key_node
    while True:
        node = node.nextSibling
        if node.hasChildNodes():
            value_node = node
            break
    assert value_node.tagName == value_tag
    return value_node

def get_xml_node_data(node):
    [data_node] = node.childNodes
    return data_node.data

def get_aupreset_subtype_node(dom):
    return get_aupreset_value_node_for_key(dom, 'subtype', 'integer')

def parse_aupreset(dom):
    return {
        'data': base64.b64decode(get_xml_node_data(get_aupreset_value_node_for_key(dom, 'jucePluginState', 'data'))),
        'plugin_id_int': int(get_xml_node_data(get_aupreset_subtype_node(dom))),
        }

[src_filename, dst_filename] = sys.argv[1:]

preset_name = path.split(src_filename)[1].rsplit('.', 1)[0]
au_preset = parse_aupreset(minidom.parseString(open(src_filename, 'rb').read()))

# Save to vst format
fxp_data = Container(
    chunkMagic = b'CcnK',
    byteSize = 0, # will fill later
    fxMagic = 'FXP_OPAQUE_CHUNK',
    version = 1,
    fxID = au_preset['plugin_id_int'],
    fxVersion = 1,
    count = 0,
    data = Container(
        prgName = preset_name,
        size = len(au_preset['data']),
        chunk = au_preset['data'],
        ),
    )
fxp_data.byteSize = len(vst2preset.build(fxp_data)) - 8
open(dst_filename, 'wb').write(vst2preset.build(fxp_data))
