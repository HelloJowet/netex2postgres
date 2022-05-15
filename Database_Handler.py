from sqlalchemy import create_engine
import shapely
from shapely import wkt
import pandas as pd
import geopandas as gpd
import math


class Database_Handler:
    def __init__(self, db_connection_url):
        self.postgresql_db = create_engine(db_connection_url)

    def insert(self, table_name, table_rows):
        if len(table_rows) > 0:
            if 'geom' in table_rows[0].keys():
                table = gpd.GeoDataFrame(table_rows, geometry='geom')
            else:
                table = pd.DataFrame(table_rows)
            
            # ensures that each row has the same column count
            # if a row don't has a specific column value, it automatically sets the value to null
            table = list(table.T.to_dict().values())
            #table_values = [[value for value in row.values()] for row in table]
            
            column_names = table[0].keys()
            query = f'INSERT INTO {table_name} ({{}}) VALUES '.format(','.join(column_names))
            
            # split table in chunks
            table_chunks = [table[i:i + 1000] for i in range(0, len(table), 1000)]
            for table_chunk in table_chunks:
                table_values = []
                
                for row in table_chunk:
                    row_values = []
                    for value in row.values():
                        row_values.append(self.value_to_string(value))

                    table_values.append('(' + ','.join(row_values) + ')')

                table_values = ','.join(table_values)

                self.postgresql_db.engine.execute(query + table_values)

    
    def value_to_string(self, value):
        if isinstance(value, dict):
            return "'" + str(value).replace("'", '"').replace('None', '"NULL"') + "'::jsonb"
        elif isinstance(value, list):
            value_list = []
            for item in value:
                value_list.append(self.value_to_string(item))
            list_string = ','.join(value_list)
            return 'ARRAY[' + list_string + ']'
        elif value == None or (isinstance(value, float) and math.isnan(value)):
            return 'NULL'
        elif isinstance(value, shapely.geometry.base.BaseGeometry):
            return "ST_SetSRID(ST_GeomFromText('" + wkt.dumps(value) + "'), 4326)"
        else:
            return "'" + value + "'"