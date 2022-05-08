import networkx as nx

class Simplified_Schema_Graph_Builder:
    def __init__(self, schema_graph):
        self.graph = nx.DiGraph()
        self.schema_graph = schema_graph

    
    def create_graph(self, node_id, graph_parent_node_id):
        edges = list(self.schema_graph.edges(node_id, data=True))
        
        is_parent_node_abstract = False
        if 'abstract' in self.schema_graph.nodes[node_id]:
            is_parent_node_abstract = self.schema_graph.nodes[node_id]['abstract'] == 'true'
            
        for edge in edges:
            target_edge_node_id = edge[1]
            
            # if target node is already added to simplified_schema_graph, only a connection to the target node should be created
            # this should prevent endless loops
            if target_edge_node_id in self.graph.nodes:
                self.graph.add_edge(
                    graph_parent_node_id,
                    target_edge_node_id
                )
            # if node has the xml tag abstract, this node shouldn't be processed further, because abstract nodes aren't needed for the end schema
            # this doesn't apply to abstract nodes with the tag 'substitutionGroup', because this nodes are highly important for the end schema
            elif (not is_parent_node_abstract or edge[2]['edge_type'] == 'substitution_group'):
                target_edge_node = self.schema_graph.nodes[target_edge_node_id]

                # only proceed if target node is further specified in schema_graph. Otherwise informations are missing how to proceed with target node
                # TODO: check why target node isn't further specified
                if target_edge_node != {}:
                    has_ref_attribute = False
                    is_abstract = False

                    if 'ref' in target_edge_node.keys() and target_edge_node['ref'] != None:
                        self.create_graph(target_edge_node_id, graph_parent_node_id)
                        has_ref_attribute = True

                    if 'abstract' in target_edge_node.keys() and target_edge_node['abstract'] == 'true':
                        is_abstract = True

                    if target_edge_node['node_type'] in ['element', 'attribute', 'ref_element'] and not has_ref_attribute and not is_abstract:
                        name = target_edge_node['name']
                        
                        # a edge should always be unique
                        # because a lot of nodes got assigned random ids in the previous step, the uniqueness of edges in the schema_graph cannot be guaranteed
                        # Example: 
                        # the node 'Operator' and the node 'CustomerServiceContactDetails' are connected with two edges
                        # both edges are describing the same connection but have different node ids for 'CustomerServiceContactDetails'
                        # The following code should ensure that a edges are always unique
                        is_node_already_in_simplified_schema_graph = False
                        if graph_parent_node_id in self.graph.nodes:
                            parent_edges = self.graph.edges(graph_parent_node_id)
                            parent_edge_target_names = [self.graph.nodes[parent_edge[1]]['name'] for parent_edge in parent_edges]
                            
                            if name in parent_edge_target_names:
                                is_node_already_in_simplified_schema_graph = True

                        if not is_node_already_in_simplified_schema_graph:              
                            self.graph.add_node(
                                target_edge_node_id,
                                name = name,
                                node_type = target_edge_node['node_type'],
                                is_list = edge[2]['is_list']
                            )

                            self.graph.add_edge(
                                graph_parent_node_id,
                                target_edge_node_id
                            )

                            self.create_graph(target_edge_node_id, target_edge_node_id)

                    if target_edge_node['node_type'] != 'element' or is_abstract:
                        self.create_graph(target_edge_node_id, graph_parent_node_id)