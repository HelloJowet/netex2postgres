import re
from lxml import etree, objectify

def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

def load_xml(filename):
    parser = etree.XMLParser(huge_tree=True)
    tree = etree.parse(filename, parser)
    root = tree.getroot()

    # remove namespaces from xml
    for elem in root.getiterator():
        if not hasattr(elem.tag, 'find'): continue  # guard for Comment tags
        i = elem.tag.find('}')

        if i >= 0:
            elem.tag = elem.tag[i+1:]

    objectify.deannotate(root, cleanup_namespaces=True)
    
    return root