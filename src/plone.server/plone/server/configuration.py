from xml.dom import minidom

import hjson
import io
import json
import xml.etree.cElementTree as ET


def mod_data(data):
    for key, value in data.items():
        if isinstance(value, list):
            data[key] = ' '.join(value)


_defaults = {
    "xmlns": "http://namespaces.zope.org/zope",
    "xmlns:plone": "http://namespaces.plone.org/plone",
    "i18n_domain": "plone.server",
    "xmlns:zcml": "http://namespaces.zope.org/zcml"
}


def convert_json_to_zcml(input_file):
    txt = input_file.read()
    filename = getattr(input_file, 'name', '')
    if filename.lower().endswith('.hjson'):
        data = hjson.loads(txt)
    else:
        # regular json...
        data = json.loads(txt)

    configurations = data.pop('configuration')
    root = ET.Element("configure")

    for key, value in data.items():
        root.attrib[key] = value
    for key, value in _defaults.items():
        if key not in root.attrib:
            root.attrib[key] = value

    for config in configurations:
        for directive, data in config.items():
            if isinstance(data, list):
                # auto expand lists...
                for sub_data in data:
                    mod_data(sub_data)
                    ET.SubElement(root, directive, **sub_data)
            else:
                mod_data(data)
                ET.SubElement(root, directive, **data)

    fi = io.BytesIO()
    tree = ET.ElementTree(root)
    tree.write(fi)
    fi.seek(0)
    fi.name = filename
    return fi


def convert_zcml_to_hjson(input_file):
    tree = minidom.parse(input_file)
    root = tree.documentElement
    data = dict(root.attributes.items())
    configuration = []
    for node in root.childNodes:
        if not hasattr(node, 'tagName'):
            continue
        configuration.append({
            node.tagName: dict(node.attributes.items())
        })
    data['configuration'] = configuration
    return hjson.dumps(data)
