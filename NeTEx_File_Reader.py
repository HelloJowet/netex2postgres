import uuid
from lxml import etree
import re
import pygml
from shapely.geometry import shape, Point
from shapely.ops import transform
import pyproj

from shared import camel_to_snake


class NeTEx_File_Reader:
    def __init__(self, schema, simplified_schema_graph):
        self.schema = schema
        self.simplified_schema_graph = simplified_schema_graph
        self.results = {camel_to_snake(key): [] for key in schema.keys()}


    def query_node(self, node, simplified_schema_node_id, parent_node_tag, parent_node_id):
        result = {}
    
        child_ids_from_xml = [child.tag for child in node]
        
        node_id = node.get('id')
        if node_id == None:
            node_id = str(uuid.uuid4())
        
        for edge in self.simplified_schema_graph.edges(simplified_schema_node_id):
            child_node_id_from_schema_graph = edge[1]
            child_node_from_schema_graph = self.simplified_schema_graph.nodes[child_node_id_from_schema_graph]
            child_node_name = child_node_from_schema_graph['name']
            
            if child_node_name in child_ids_from_xml:
                child_xml = [child for child in node if child.tag == child_node_name][0]
                # every database column should be snake case
                child_node_name = camel_to_snake(child_node_name)
                
                # check if element belongs to a separate table
                # Example:
                # 'Operator' belongs to a seperate table, because it's part of the specified schema.
                # 'ContactDetails' doesn't belongs to a seperate table and for this reason it's part of the parent node table
                belongs_to_a_seperate_table = False

                # sometimes the child of the child of the node belongs to a separate table
                # example: node: 'StopPlace', child: 'quays', child of child: 'Quay' (belongs to a seperate table)
                for child_of_child in child_xml:
                    if child_of_child.tag in self.schema.keys():
                        belongs_to_a_seperate_table = True

                        # get the node id specified in the simplified_schema_graph from the child_of_child xml element
                        child_of_child_node_id_from_schema_graph = [
                            edge[1] for edge in self.simplified_schema_graph.edges(child_node_id_from_schema_graph) if edge[1] == child_of_child.tag
                        ][0]

                        self.query_node(child_of_child, child_of_child_node_id_from_schema_graph, node.tag, node_id)

                if not belongs_to_a_seperate_table:
                    # 'Centroid' should be transformed first to shapely geometry and then added to results
                    if child_xml.tag == 'Centroid':
                        result['geom'] = self.centroid_to_shapely(child_xml)
                    # if child xml element has children, transform the children to dict and save it in the result dict
                    elif len(child_xml) > 0:
                        if child_node_from_schema_graph['is_list']:
                            result_list, geom = self.xml_to_list(child_xml, child_node_id_from_schema_graph)
                            
                            # only if list has values add it to result dict
                            if len(result_list) > 0:
                                result[child_node_name] = result_list
                            else:
                                result[child_node_name] = None
                        else:
                            result_dict, geom = self.xml_to_dict(child_xml, child_node_id_from_schema_graph)

                            # if dict has no value, the value added to result dict should be just None
                            # example for dict with no values: {'PointProjection': {'ProjectedPointRef': None}}
                            if self.check_if_dict_has_values(result_dict):
                                result[child_node_name] = result_dict
                            else:
                                result[child_node_name] = None
                        
                        if geom != None:
                            result['geom'] = geom
                    # check if element is ref element (= elements that link to other elements)
                    # if that's the case save the ref attribute as value in column
                    # example: <QuayRef ref="NSR:Quay:39450" version="1"/> in element 'PassengerStopAssignment'
                    elif child_xml.tag[-3:] == 'Ref' and child_xml.get('ref') != None:
                        result[child_node_name] = child_xml.get('ref')
                    else:
                        result[child_node_name] = child_xml.text
                        
        # add parent node id to result so that the nested xml structure get represented in a relational structure without data loss
        if parent_node_tag != None and parent_node_tag != None:
            result['parent_id'] = parent_node_id
                        
        # add attributes to result
        attributes = {}
        for attribute in node.attrib:
            if attribute != 'id':
                attributes[attribute] = node.get(attribute)
        
        result['id'] = node_id
        result['attributes'] = attributes
        
        # in some NeTEx files gml geometries get added to xml elements although this is not defined in the NeTEx xsd schema files
        # example (07.05.2022, NeTEx Norway): the elements 'TopographicPlace' and 'TariffZone' have gml geometries as child
        # because the geometries aren't part of the simplified_schema_graph, the following code should take care of this case
        geometry_child = [child for child in node if child.tag in ['LineString', 'Polygon']]
        
        if len(geometry_child) > 0:
            result['geom'] = self.gml_geometry_to_shapely(geometry_child[0])
        
        self.results[camel_to_snake(node.tag)].append(result)


    def check_if_dict_has_values(self, input_dict):
        has_value = False
        
        for value in input_dict.values():
            if isinstance(value, dict):
                has_value = self.check_if_dict_has_values(value) or has_value
            elif value != None:
                return True
        return has_value

    
    def xml_to_dict(self, xml_element, simplified_schema_node_id):
        result = {}
        child_ids_from_xml = [child.tag for child in xml_element]
        
        geom = self.handle_geometry(xml_element)
        
        # if xml element isn't geometry, transform xml to dictionary
        if geom == None:
            for edge in self.simplified_schema_graph.edges(simplified_schema_node_id):
                child_node_id_from_schema_graph = edge[1]
                child_node_from_schema_graph = self.simplified_schema_graph.nodes[child_node_id_from_schema_graph]

                if child_node_from_schema_graph['name'] in child_ids_from_xml:
                    child_node_name = child_node_from_schema_graph['name']
                    child_xml = [child for child in xml_element if child.tag == child_node_name][0]
                    # every key in the dict should be snake case
                    child_node_name = camel_to_snake(child_node_name)

                    # example: 'FromDate' in 'AvailabilityCondition' is flagged as list, but don't have children. 'FromDate' just has a text value
                    # for this reason the value added to the result dict should just be the text value, not a list from the xml_to_list function
                    if len(child_xml) > 0 and child_node_from_schema_graph['is_list']:
                        result[child_node_name], geom = self.xml_to_list(child_xml, child_node_id_from_schema_graph)
                    elif len(child_xml) > 0:
                        result[child_node_name], geom = self.xml_to_dict(child_xml, child_node_id_from_schema_graph)
                    elif child_xml.tag[-3:] == 'Ref' and child_xml.get('ref') != None:
                        result[child_node_name] = child_xml.get('ref')
                    else:
                        result[child_node_name] = child_xml.text
        
        return result, geom


    def xml_to_list(self, xml_element, simplified_schema_node_id):
        result = []
        geom = None

        simplified_schema_target_edge_ids = [edge[1] for edge in self.simplified_schema_graph.edges(simplified_schema_node_id)]
        simplified_schema_target_nodes = [self.simplified_schema_graph.nodes[simplified_schema_target_edge_id] for simplified_schema_target_edge_id in simplified_schema_target_edge_ids]
        
        for child_xml in xml_element:
            # get node id from child_xml in simplified schema graph
            simplified_schema_target_node_id = [
                target_edge_id for target_edge_id, target_node in zip(simplified_schema_target_edge_ids, simplified_schema_target_nodes) if target_node['name'] == child_xml.tag
            ]
            
            if len(simplified_schema_target_node_id) > 0:
                simplified_schema_target_node_id = simplified_schema_target_node_id[0]
                if len(child_xml) > 0:
                    dict_value, geom = self.xml_to_dict(child_xml, simplified_schema_target_node_id)
                    if dict_value != None:
                        result.append({
                            camel_to_snake(child_xml.tag): dict_value
                        })
                    if geom != None:
                        return [], geom
                elif child_xml.tag[-3:] == 'Ref' and child_xml.get('ref') != None:
                    result.append(child_xml.get('ref'))
                else:
                    result.append({
                            camel_to_snake(child_xml.tag): child_xml.text
                    })
            else:
                # missing element in simplified schema 
                # TODO: Add error handeling
                print(f'missing element in simplified schema: {child_xml.tag}')
                
        return result, geom

    
    def handle_geometry(self, xml_element):
        child_geometry_element = [child for child in xml_element if child.tag in ['LineString', 'Polygon', 'Centroid']]
        
        if len(child_geometry_element) == 0:
            # xml element isn't geometry
            return None
        # if the xml_element is a gml geometry, the gml geometry will be transformed into a shapely geometry
        elif child_geometry_element[0].tag in ['LineString', 'Polygon']:
            return self.gml_geometry_to_shapely(child_geometry_element[0])
        else:
            return None

    
    def gml_geometry_to_shapely(self, gml_geometry):
        # xml elements to string, because the library pygml can only read strings
        gml_string = etree.tostring(gml_geometry, encoding=str)

        # TODO: add huge_tree feature to pygml package
        if len(gml_string) > 5000000:
            return None

        # get gml namespace
        # example input: <gml:Polygon xmlns:ns2="http://www.opengis.net/gml/3.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ns2:id="GEN-PolygonType-1162673">
        # example result: ns2
        gml_namespace = re.search('(xmlns:)(.*)(="http:\/\/www.opengis.net\/gml\/3.2")', gml_string).groups()[1]

        # edit gml string so that the library pygml can read it
        # (I'm not sure if the following code covers all cases)
        if gml_namespace != 'gml:':
            gml_string = gml_string.replace(f':{gml_namespace}', ':gml')
            gml_string = gml_string.replace(f'{gml_namespace}:', 'gml:')
            gml_string = gml_string.replace('<', '<gml:')
            gml_string = gml_string.replace('<gml:/', '</gml:')

        # if spatial reference system isn't specified in gml geometry, add it
        if 'srsName' not in gml_string:
            gml_string = gml_string.replace('"http://www.opengis.net/gml/3.2"', '"http://www.opengis.net/gml/3.2" srsName="EPSG:4326"')
        elif 'EPSG' not in gml_string:
            gml_string = gml_string.replace('srsName="', 'srsName="EPSG:')

        # transform gml string to shapely geometry
        geom = pygml.parse(gml_string)

        # if spatial reference identifier of geometry isn't EPSG:4326, transform the geometry to this identifier, because all geometries should be in the same spatial reference system
        if 'crs' in geom.__geo_interface__.keys():
            crs = geom.__geo_interface__['crs']['properties']['name']
            geom = shape(geom)

            if crs != 'EPSG:4326':
                target_crs = pyproj.CRS('EPSG:4326')
                current_crs = pyproj.CRS(crs)

                project = pyproj.Transformer.from_crs(current_crs, target_crs, always_xy=True).transform
                geom = transform(project, geom)
        else:
            geom = shape(geom)

        return geom


    def centroid_to_shapely(self, xml_element):
        latitude = float(xml_element.find('.//Latitude').text)
        longitude = float(xml_element.find('.//Longitude').text)
        return Point(longitude, latitude)