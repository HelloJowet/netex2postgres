# check if attributes are missing in the query_instructions.json file
class Missing_Attribute_Check:
    def main(self, instructions, node):
        routes = self.get_every_route_object_from_instructions(instructions, [])
        routes_attribute_tree = self.routes_to_attribute_tree(routes)
        instructions_attribute_tree = self.instructions_to_attribute_tree(instructions, {})

        attribute_tree = self.combine_attribute_trees(routes_attribute_tree, instructions_attribute_tree, {})    
        self.compare_attribute_tree_with_real_attributes(attribute_tree, node)
    
    
    def get_every_route_object_from_instructions(self, instructions, previous_route):
        routes = [previous_route + value['route'].split('/') for _, value in instructions.items() if 'route' in value.keys()]
        
        for key, instruction in instructions.items():
            if instruction['type'] == 'node':
                previous_route01 = previous_route + [instruction['title']]
                routes = routes + self.get_every_route_object_from_instructions(instruction['values'], previous_route01)
                
        return routes
    
    
    # function builds a nested attribute tree
    # example:
        # input = [['a1', 'b1', 'c1'], ['a1', 'b2'], ['a2', 'b1'], ['a1', 'b1', 'c2']]
        # output = {'a2': {'b1': None}, 'a1': {'b1': {'c2': None, 'c1': None}, 'b2': None}}
    def routes_to_attribute_tree(self, routes):
        first_elements = list(set([route[0] for route in routes]))

        attribute_tree = {}

        for first_element in first_elements:
            routes_without_first_element = [route[1:] for route in routes if route[0] == first_element and len(route) > 1]

            if len(routes_without_first_element) > 0:
                attribute_tree[first_element] = self.routes_to_attribute_tree(routes_without_first_element)
            else:
                attribute_tree[first_element] = None

        return attribute_tree


    def instructions_to_attribute_tree(self, instructions, attributes):
        for key, instruction in instructions.items():
            if 'title' in instruction.keys():
                attributes[instruction['title']] = None

            if 'values' in instruction.keys():
                attributes[instruction['title']] = self.instructions_to_attribute_tree(instruction['values'], {})

        return attributes


    # example:
        # attribute_tree_01 = {'a1': {'b1': {'c2': None, 'c1': None}, 'b2': None}, 'a2': {'b1': None}}
        # attribute_tree_02 = {'a1': {'b3': {'c2': None}, 'b1': {'c2': None, 'c1': {'d3': None}}}}
        # temp_result = {}
        # output = {'a2': {'b1': None}, 'a1': {'b2': None, 'b3': {'c2': None},'b1': {'c1': {'d3': None}, 'c2': None}}}
    def combine_attribute_trees(self, attribute_tree_01, attribute_tree_02, temp_result):
        keys_01 = set([key for key in attribute_tree_01.keys()])
        keys_02 = set([key for key in attribute_tree_02.keys()])

        keys_01_difference = keys_01.difference(keys_02)
        keys_02_difference = keys_02.difference(keys_01)
        key_matches = keys_01 & keys_02

        for key in keys_01_difference:
            temp_result[key] = attribute_tree_01[key]

        for key in keys_02_difference:
            temp_result[key] = attribute_tree_02[key]

        for key in key_matches:
            value_01 = attribute_tree_01[key]
            value_02 = attribute_tree_02[key]

            if value_01 == None:
                temp_result[key] = value_02
            elif value_02 == None:
                temp_result[key] = value_01
            else:
                temp_result[key] = self.combine_attribute_trees(value_01, value_02, {})

        return temp_result


    def compare_attribute_tree_with_real_attributes(self, attribute_tree, node):
        attribute_tree_elements = [key for key, value in attribute_tree.items()]           
        real_attributes = [child.tag for child in node]
        
        ignored_attributes = ['keyList', 'SanitaryFacilityList', 'PaymentMethods', 'ParkingUserTypes']

        missing_attributes = list(set(real_attributes) - set(attribute_tree_elements) - set(ignored_attributes))
        if len(missing_attributes) > 0:
            print(f'missing attributes for node {node.tag}:{missing_attributes}')

        for key, value in attribute_tree.items():
            target_node = node.find(key)
            if value != None and target_node != None:
                self.compare_attribute_tree_with_real_attributes(value, node.find(key))  