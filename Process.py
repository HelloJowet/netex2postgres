import json
import pandas as pd

from Query import Query
from Missing_Attribute_Check import Missing_Attribute_Check

class Process:
    def __init__(self):
        with open('query_instructions.json') as file:
            self.query_instructions = json.load(file)
        
        self.results = dict()
        for key in self.query_instructions.keys():
                self.results[key] = []
        
        self.current_frame_id = None
        self.netex_publication = dict()
        self.query_object = Query(self)
        
        # divide part of the possible NeTEx XML nodes in different categories, so that the query knows what to do when the nodes occur
        self.frames = [
            'ResourceFrame', 'ServiceFrame', 'ServiceCalendarFrame', 'TimetableFrame', 'SiteFrame', 'FareFrame'
        ]
        self.ignored_nodes = [
            'PublicationTimestamp', 'ParticipantRef', 'Description', 'codespaces'
        ]
        self.passing_nodes = [
            'PublicationDelivery', 'dataObjects', 'CompositeFrame', 'validityConditions', 'FrameDefaults', 'DefaultLocale', 'DefaultLanguage', 'frames', 'organisations', 'routePoints', 
            'destinationDisplays', 'scheduledStopPoints', 'serviceLinks', 'stopAssignments', 'notices', 'dayTypes', 'operatingPeriods', 'dayTypeAssignments', 'routes', 'lines','journeyPatterns',
            'vehicleJourneys', 'noticeAssignments', 'topographicPlaces', 'groupsOfStopPlaces', 'stopPlaces', 'parkings', 'tariffZones', 'groupsOfTariffZones', 'fareZones'
        ]
        
    
    def main(self, root):
        composite_frame = root.find('.//CompositeFrame')
        if composite_frame == None:
            self.composite_frame_id = None
        else:
            self.composite_frame_id = root.find('.//CompositeFrame').get('id')
        
        self.run(root)

        # results to dataframes 
        for key, result in self.results.items():
            self.netex_publication[key] = pd.DataFrame(result)
    
        return self.netex_publication
    
    
    def run(self, node):
        for child in node:
            if child.tag in self.frames:
                self.current_frame_id = child.get('id')
                self.run(child)
            elif child.tag in self.ignored_nodes: 
                pass
            elif child.tag in self.passing_nodes:
                self.run(child)
            elif child.tag in self.query_instructions.keys():
                Missing_Attribute_Check().main(self.query_instructions[child.tag], child)
                result = self.query_object.main(self.query_instructions[child.tag], child)

                # add frame information to result
                frame_data = {
                    'composite_frame_id': self.composite_frame_id,
                    'current_frame_id': self.current_frame_id
                }
                result = dict(list(result.items()) + list(frame_data.items()))

                self.results[child.tag].append(result)
            else:
                print('missing node: ' + child.tag)