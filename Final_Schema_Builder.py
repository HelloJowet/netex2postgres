from sqlalchemy import MetaData, Table, Column, String, ARRAY, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2.types import Geometry
import itertools

from shared import camel_to_snake

table_names = [
    'PublicationDelivery', 'CompositeFrame', 'ResourceFrame', 'ServiceFrame', 'ServiceCalendarFrame', 'TimetableFrame', 'SiteFrame', 
    'FareFrame', 'Operator', 'Authority', 'Network', 'RoutePoint', 'DestinationDisplay', 'ScheduledStopPoint', 'ServiceLink', 
    'PassengerStopAssignment', 'Notice', 'DayType', 'OperatingPeriod', 'DayTypeAssignment', 'Route', 'PointOnRoute', 'Line', 'JourneyPattern',
    'StopPointInJourneyPattern', 'ServiceLinkInJourneyPattern', 'ServiceJourney', 'TimetabledPassingTime', 'NoticeAssignment',
    'TopographicPlace', 'GroupOfStopPlaces', 'StopPlace', 'Quay', 'Parking', 'ParkingCapacity', 'TariffZone', 'GroupOfTariffZones', 'FareZone'
]

class Final_Schema_Builder:
    def __init__(self, simplified_schema_graph):
        self.schema = {}
        self.simplified_schema_graph = simplified_schema_graph

    def create_schema(self, node_id, parent_node_name, already_visited_node_ids):
        # prevent endless loop
        if not node_id in already_visited_node_ids:
            already_visited_node_ids.append(node_id)
            table_property_elements = {}
        
            for edge in self.simplified_schema_graph.edges(node_id):
                target_node_id = edge[1]
                
                if node_id in table_names:
                    self.create_schema(target_node_id, node_id, already_visited_node_ids)
                    
                    target_node = self.simplified_schema_graph.nodes[target_node_id]
                    edges = self.simplified_schema_graph.edges([target_node_id])

                    # if node has element children, the column should be the type dict
                    is_dict = False
                    is_list = False
                    for edge in edges:
                        if self.simplified_schema_graph.nodes[edge[1]]['node_type'] == 'element':
                            is_dict = True
                            # sometimes it's not 100% clear if a column should be a list or not
                            # example: 
                                # the xsd sequence tag specifies that the child elements must appear in a sequence
                                # each child element can occur from 0 to any number of times
                                # a sequence tag can indicate a list, but don't have to
                                # but if a element don't have child nodes, it can't be a list, because it can only have a single text or ref attribute value
                            # the following line takes care of this specific case
                            is_list = target_node['is_list']
                            
                    if is_list:
                        if is_dict:
                            column_type = ARRAY(JSONB)
                        else:
                            column_type = ARRAY(String)
                    elif is_dict:
                        column_type = JSONB
                    else:
                        column_type = String
                        
                    table_property_elements[target_node['name']] = {'column_type': column_type, 'is_list': is_list}
                else:
                    self.create_schema(target_node_id, parent_node_name, already_visited_node_ids)  
                    
            if node_id in table_names:
                table_property_elements['id'] = {'column_type': String, 'is_list': False}
                table_property_elements['attributes'] = {'column_type': JSONB, 'is_list': False}
                table_property_elements['geom'] = {'column_type': Geometry, 'is_list': False}
                
                if parent_node_name != None:
                    # Except the 'PublicationDelivery' node every node in NeTEx has a parent node. 
                    # For example 'StopPlace' can have 'GroupOfStopPlaces' as a parent node.
                    # To represent this relation in a relational schema every child node has a parent node property
                    table_property_elements['parent_id'] = {'column_type': String, 'is_list': False}
                    
                
                self.schema[node_id] = table_property_elements


    def create_tables_in_database(self, db_connection_url):
        postgresql_db = create_engine(db_connection_url)
        post_meta = MetaData(bind=postgresql_db.engine)

        for table_key, columns in self.schema.items():
            table_key = camel_to_snake(table_key)
            
            column_names = [camel_to_snake(column_name) for column_name in columns.keys()]
            columns_types = [column_value['column_type'] for column_value in columns.values()]
            # TODO: Add real primary_key_flags and nullable_flags
            primary_key_flags = list(itertools.repeat(False, len(columns)))
            nullable_flags = list(itertools.repeat(True, len(columns)))
            
            table = Table(
                table_key, post_meta,
                *(Column(
                    column_name, column_type, primary_key=primary_key_flag, nullable=nullable_flag)
                    for column_name, column_type, primary_key_flag, nullable_flag 
                    in zip(column_names, columns_types, primary_key_flags, nullable_flags)
                )
            )

            table.create()