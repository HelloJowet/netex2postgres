from sqlalchemy import MetaData, Table, Column, String, create_engine
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
            table_property_elements = []
        
            for edge in self.simplified_schema_graph.edges(node_id):
                target_node_id = edge[1]
                
                if node_id in table_names:
                    self.create_schema(target_node_id, node_id, already_visited_node_ids)
                    
                    target_node_name = self.simplified_schema_graph.nodes[target_node_id]['name']
                    table_property_elements.append(target_node_name)
                else:
                    self.create_schema(target_node_id, parent_node_name, already_visited_node_ids)      
            if node_id in table_names:
                if parent_node_name != None:
                    # Except the 'PublicationDelivery' node every node in NeTEx has a parent node. 
                    # For example 'StopPlace' can have 'GroupOfStopPlaces' as a parent node.
                    # To represent this relation in a relational schema every child node has a parent node property
                    table_property_elements.append(parent_node_name + '_id')
                self.schema[node_id] = list(set(table_property_elements))


    def create_tables_in_database(self, db_connection_url):
        postgresql_db = create_engine(db_connection_url)
        post_meta = MetaData(bind=postgresql_db.engine)
        postgresql_db.engine.connect()

        for table_key, column_names in self.schema.items():
            table_key = camel_to_snake(table_key)
            column_names = [camel_to_snake(column_name) for column_name in column_names]
            
            columns_types = list(itertools.repeat(String, len(column_names)))
            # TODO: Add real primary_key_flags and nullable_flags
            primary_key_flags = list(itertools.repeat(False, len(column_names)))
            nullable_flags = list(itertools.repeat(False, len(column_names)))
            
            table = Table(
                table_key, post_meta,
                *(Column(
                    column_name, column_type, primary_key=primary_key_flag, nullable=nullable_flag)
                    for column_name, column_type, primary_key_flag, nullable_flag 
                    in zip(column_names, columns_types, primary_key_flags, nullable_flags)
                )
            )

            table.create()