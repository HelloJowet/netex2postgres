from lxml import etree, objectify

class XML_Handler:
    def load(self, filename, huge_tree):
        parser = etree.XMLParser(huge_tree=huge_tree)
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