from XML_Schema_Graph_Builder import XML_Schema_Graph_Builder
from Simplified_Schema_Graph_Builder import Simplified_Schema_Graph_Builder
from Final_Schema_Builder import Final_Schema_Builder 
from XML_Handler import XML_Handler
from NeTEx_File_Reader import NeTEx_File_Reader
from Database_Handler import Database_Handler
import config
import os

xml_schema_graph_builder = XML_Schema_Graph_Builder()
xml_schema_graph_builder.create_graph('xsd_netex')

simplified_schema_graph_builder = Simplified_Schema_Graph_Builder(xml_schema_graph_builder.graph)
simplified_schema_graph_builder.create_graph('PublicationDelivery', 'PublicationDelivery')

final_schema_builder = Final_Schema_Builder(simplified_schema_graph_builder.graph)
final_schema_builder.create_schema('PublicationDelivery', None, [])

for file in os.listdir('../norway_netex'):
    print(file)
    root = XML_Handler().load(f'../norway_netex/{file}', True)
    netex_file_reader = NeTEx_File_Reader(final_schema_builder.schema, simplified_schema_graph_builder.graph)
    netex_file_reader.query_node(root, 'PublicationDelivery', None, None)

    database_handler = Database_Handler(config.db_connection_url)
    for table_name, table_rows in netex_file_reader.results.items():
        database_handler.insert(table_name, table_rows)
