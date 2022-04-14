from Missing_Attribute_Check import Missing_Attribute_Check
from shared import camel_to_snake

class Query:
    def __init__(self, process_object):
        self.process_object = process_object
    
    def main(self, instructions, node):
        # the id and version from every data object should be queried. To save efford this doesn't have to be specified in the data object instruction
        id_and_version_instruction = {
            'id': {
                'type': 'attribute'
            },
            'version': {
                'type': 'attribute'
            }
        }
        combined_instructions = dict(list(id_and_version_instruction.items()) + list(instructions.items()))
        
        results = self.instructions_to_results(combined_instructions, node)

        return results
    
    
    def instructions_to_results(self, instructions, node):
        results = {}

        for key, value in instructions.items():
            if value['type'] == 'parent_node':
                output_child_node_ids = False
                
                if 'output_child_node_ids' in value.keys():
                    if value['output_child_node_ids'] == True:
                        output_child_node_ids = True
                        
                        child_nodes = node.findall(value['title'] + '/' + value['child_node_title'])
                        results[key] = [child_node.get('ref') for child_node in child_nodes]
                
                if not output_child_node_ids:
                    if 'route' in value.keys():
                        child_node = node.find(value['route'])
                    else:
                        child_node = node.find(value['title'])
                    
                    if child_node != None:
                        self.query_child_nodes(child_node, node, value['child_node_title'])
            elif 'route' in value.keys():
                target_node = node.find(value['route'])

                if target_node == None:
                    results[key] = None
                elif value['type'] == 'attribute':
                    results[key] = target_node.get(value['attribute_title'])
                elif value['type'] == 'value':
                    results[key] = target_node.text
            elif value['type'] == 'attribute':
                if 'attribute_title' in value.keys():
                    results[key] = node.get(value['attribute_title'])
                else:
                    results[key] = node.get(key)
            elif value['type'] == 'value':
                target_node = node.find(value['title'])

                if target_node == None:
                    results[key] = None
                elif not 'kind' in value.keys():
                    results[key] = target_node.text
                elif value['kind'] == 'attribute':
                    results[key] = target_node.get(value['attribute_title'])
                else:
                    print(f'Unknown kind property in node {node.text}')
            elif value['type'] == 'node':
                child_node = node.find(value['title'])
                
                if child_node != None:
                    results[key] = self.instructions_to_results(value['values'], child_node)
            elif value['type'] == 'text':
                results[key] = node.text

        return results
    
    
    # if a data object is inside another data object (example: multiple PointOnRoute objects in Route object), the child data object (in the example the PointOnRoute object) gets handled by 
    # this function
    def query_child_nodes(self, node, parent_node, child_node_title):
        parent_id = parent_node.get('id')
        parent_title = camel_to_snake(parent_node.tag)
        
        for child in node:
            instructions = self.process_object.query_instructions[child_node_title]
            result = self.main(instructions, child)
            
            # run missing attribute check for child nodes
            Missing_Attribute_Check().main(instructions, child)
            
            # add parent id to result
            result[parent_title + '_id'] = parent_id
            
            # add child node result to all results from the process object
            self.process_object.results[child_node_title].append(result)