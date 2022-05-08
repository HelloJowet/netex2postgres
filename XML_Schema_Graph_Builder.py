import networkx as nx
from lxml import etree
import uuid
import os

from XML_Handler import XML_Handler

class XML_Schema_Graph_Builder:
    def __init__(self):
        self.graph = nx.DiGraph()
    
    def create_graph(self, xsd_netex_path):
        folders = ['netex_framework', 'netex_part_1', 'netex_part_2', 'netex_part_3', 'netex_part_5']

        # add NeTEx XML schema files to schema graph
        root = XML_Handler().load(f'{xsd_netex_path}/NeTEx_publication-NoConstraint.xsd', False)
        self.process_file(root)

        for folder in folders:
            for route, _, files in os.walk(f'{xsd_netex_path}/{folder}'):
                for file in files:
                    if file.endswith('.xsd'):
                        filename = f'{route}/{file}'
                        root = XML_Handler().load(filename, False)
                        self.process_file(root)


    def process_file(self, node):
        for child in node:
            if child.tag in ['import', 'annotation', 'include', 'attribute'] or isinstance(child, etree._Comment):
                continue
            elif child.tag == 'element':
                type = child.get('type')
                name = child.get('name')
                abstract = child.get('abstract')
                substitution_group = child.get('substitutionGroup')
                
                self.graph.add_node(
                    name, 
                    name = name,
                    node_type = child.tag, 
                    content_type = type,
                    abstract = abstract
                )
                
                if abstract != 'true':
                    if type != None and not type.startswith('xsd'):
                        self.graph.add_edge(name, type, edge_type = 'type', is_list = False)

                    self.process_node(child, name, False)
                    
                if substitution_group != None:
                    self.graph.add_edge(substitution_group, name, edge_type = 'substitution_group', is_list = False)
            elif child.tag in ['complexType', 'group', 'simpleType', 'attributeGroup']:
                name = child.get('name')
                
                self.graph.add_node(name, node_type = child.tag)
                self.process_node(child, name, False)


    def process_node(self, node, graph_parent_node_id, is_list):
        for child in node:
            # Assign each child nodes a random id, because they aren't unique
            # Explanation: For example multiple nodes have the same child node 'placeEquipments'. If we assign 'placeEquipments' (tag of the child node) as
            # the node identifier in the graph, every 'placeEquipments' node would need to have the same attributes. But this isn't the case in NeTeX:
            # <xsd:element name="placeEquipments" type="placeEquipments_RelStructure" minOccurs="0"> in xsd/netex_part_1/part1_ifopt/netex_ifopt_equipmentAll.xsd
            # <xsd:element name="placeEquipments" type="equipments_RelStructure" minOccurs="0"> in xsd/netex_framework/netex_reusableComponents/netex_equipmentPlace_version.xsd
            # For this reason every child node gets an random id assigned to be unique
            random_id = str(uuid.uuid4())
            
            if child.tag in ['annotation', 'pattern', 'minLength', 'maxLength', 'unique', 'key'] or isinstance(child, etree._Comment):
                continue
            elif child.tag in ['complexType', 'choice', 'complexContent', 'simpleContent', 'restriction']:
                self.process_node(child, graph_parent_node_id, False)
            elif child.tag == 'sequence':
                self.process_node(child, graph_parent_node_id, True)
            elif child.tag in ['element', 'group', 'attribute']:
                type = child.get('type')
                ref = child.get('ref')
                abstract = child.get('abstract')
                substitution_group = child.get('substitutionGroup')
                
                self.graph.add_node(
                    random_id,
                    name = child.get('name'),
                    ref = ref,
                    node_type = child.tag,
                    content_type = type,
                    abstract = abstract
                )

                self.graph.add_edge(graph_parent_node_id, random_id, edge_type = None, is_list = is_list)

                if abstract != 'true':
                    if type != None and not type.startswith('xsd'):
                        self.graph.add_edge(random_id, type, edge_type = 'type', is_list = False)

                    # TODO: Check if this if statement is needed
                    if ref != None:
                        self.graph.add_edge(random_id, ref, edge_type = 'ref', is_list = False)

                    if substitution_group != None:
                        self.graph.add_edge(random_id, substitution_group, edge_type = 'ref', is_list = False)

                    self.process_node(child, random_id, False)
                
                if substitution_group != None:
                    self.graph.add_edge(substitution_group, random_id, edge_type = 'substitution_group', is_list = is_list)
            elif child.tag in ['extension']:
                self.graph.add_node(random_id, node_type = child.tag)
                self.graph.add_edge(graph_parent_node_id, random_id, edge_type = None, is_list = is_list)
                
                base = child.get('base')
                if not base.startswith('xsd'):
                    self.graph.add_edge(random_id, base, edge_type = 'base', is_list = False)
                
                self.process_node(child, random_id, False)
            elif child.tag in ['enumeration', 'minInclusive', 'maxInclusive']:
                self.graph.add_node(random_id, node_type = child.tag, value = child.get('value'))
                self.graph.add_edge(graph_parent_node_id, random_id, edge_type = None, is_list = is_list)
            elif child.tag == 'attributeGroup':
                self.graph.add_node(random_id, node_type = child.tag, ref = child.get('ref'))
                self.graph.add_edge(graph_parent_node_id, random_id, edge_type = None, is_list = is_list)
                self.graph.add_edge(random_id, child.get('ref'), edge_type = 'ref', is_list = False)
            elif child.tag in ['simpleType', 'any']:
                self.graph.add_node(random_id, node_type = child.tag)
                self.graph.add_edge(graph_parent_node_id, random_id, edge_type = None, is_list = is_list)
                
                self.process_node(child, random_id, False)
            elif child.tag == 'list':
                item_type = child.get('itemType')
                
                self.graph.add_node(random_id, node_type = child.tag, item_type = item_type)
                self.graph.add_edge(graph_parent_node_id, random_id, edge_type = None, is_list = is_list)
                
                if not item_type.startswith('xsd'):
                    self.graph.add_edge(random_id, item_type, edge_type = None, is_list = is_list)
            elif child.tag == 'unique':
                self.graph.add_node(random_id, node_type = child.tag)
                self.process_node(child, self.graph, random_id, False)