import numpy as np



class MedNodeUtil:

    @staticmethod
    def new_med_node():
        return {'name':None,'ak_type': None, 'input': [], 'output': [], 'ak_attr': {},'type':None,'med_visted':False}

    @staticmethod
    def replace_name_with_list(origin_list, name, replace_list):
        new_list = []
        for index, ori_object in enumerate(origin_list):
            if ori_object['name'] == name:
                new_list = new_list + replace_list + origin_list[index + 1:]
                break
            else:
                new_list.append(ori_object)
        if name in new_list:
            raise Exception('circle error')
        return new_list

    @staticmethod
    def retain_input(node, input_list):
        new_input = []
        for index, node_object in enumerate(node['input']):
            if node_object in input_list:
                input_list.remove(node_object)
                new_input.append(node_object)
        node['input'] = new_input

    @staticmethod
    def redirecto_outputs_input_to_this(node,graph,this_name,this_shape):
        for i in node['output']:
            tar_node=graph[i['name']]
            tar_node['input']=MedNodeUtil.replace_name_with_list(tar_node['input'],node['name'],[{'name':this_name,'shape':this_shape}])



MedGraph_Input_Cnt=0
class MedGraphUtil:
    @staticmethod
    def append_node(father_node, son_node, graph):
        output = father_node['output']
        son_shape = father_node['output'][0]['shape']
        son_node['input'] = [{'name': father_node['name'], 'shape': son_shape}]
        son_node['output'] = output
        father_node['output'] = [{'name': son_node['name'], 'shape': son_shape}]
        for i in output:
            out_node = graph[i['name']]
            out_node['input'] = MedNodeUtil.replace_name_with_list(out_node['input'], father_node['name'],
                                                                   [{'name': son_node['name'], 'shape': son_shape}])
        graph[son_node['name']] = son_node

    @staticmethod
    def check_one_of_input_is_const(node,graph):
        for i in node['input']:
            if graph[i['name']]['type'] == 'Const':
                return True
        return False

    @staticmethod
    def _auto_split(med_node, med_graph):
        output = med_node['output']
        if len(output) > 1:
            split_node = MedNodeUtil.new_med_node()
            split_node['name']=med_node['name']+'_split#'
            split_node['ak_type']='Split'
            split_node['ak_attr']['split_num'] =len(output)
            MedGraphUtil.append_node(med_node,split_node,graph=med_graph)
        pass

    @staticmethod
    def _auto_input_name(med_node, med_graph):
        assert med_node['ak_type']=='Input'
        old_name=med_node['name']
        med_node['name']='input_'+str(MedGraph_Input_Cnt)
        for i in med_node['output']:
            out_node=med_graph[i['name']]
            out_node['input']=MedNodeUtil.replace_name_with_list(out_node['input'],old_name,[{'name':med_node['name'],'shape':i['shape']}])

    @staticmethod
    def _fusionScale(med_node, med_graph):
        if len(med_node['input']) == 1:
            input_node = med_graph[med_node['input'][0]['name']]
            med_ak_attr = med_node['ak_attr']
            if input_node['ak_type'] == 'Convolution':
                input_attr = input_node['ak_attr']
                conv_weights = input_attr['weights']
                scale_weights = med_ak_attr['scale_weights']

                assert conv_weights.shape[0] == scale_weights.shape[-1]
                new_conv_weights = np.zeros(conv_weights.shape)
                for i in range(conv_weights.shape[0]):
                    new_conv_weights[i] = conv_weights[i] * scale_weights[i]
                input_attr['weights'] = new_conv_weights.astype('float32')
                if input_attr.get('bias_weights') is not None:
                    input_attr['bias_weights'] = input_attr['bias_weights'] + med_ak_attr['bias_weights']
                else:
                    input_attr['bias_weights'] = med_ak_attr['bias_weights']
                med_node['ak_type'] = None
                input_node['output'] = MedNodeUtil.replace_name_with_list(input_node['output'], med_node['name'], med_node['output'])
                MedNodeUtil.redirecto_outputs_input_to_this(med_node,med_graph,input_node['name'],med_node['input'][0]['shape'])
                input_node['fusion_out_name']=med_node['name']

        pass

    @staticmethod
    def _all_search_table(graph, table):
        for tf_node in graph.values():
            if tf_node['med_visted']:
                continue
            type_name = tf_node['ak_type']
            if table.get(type_name) is not None:
                table[type_name](tf_node, graph)

    @staticmethod
    def _all_search_fusion(graph, fusion_func):
        for tf_node in graph.values():
            if tf_node['med_visted']:
                continue
            if tf_node['ak_type'] is not None:
                fusion_func(tf_node, graph)

    @staticmethod
    def solve(med_graph):
        for node in med_graph.values():
            node['med_visted'] = False
        MedGraphUtil._all_search_table(med_graph, {'Scale': MedGraphUtil._fusionScale})
        MedGraphUtil._all_search_fusion(med_graph, MedGraphUtil._auto_split)
        MedGraphUtil._all_search_table(med_graph, {'Input':MedGraphUtil._auto_input_name})

    @staticmethod
    def search_output_list(graph):
        output_list = set()
        graph_cp = graph.copy()

        def recursive_search(node):
            if node.get('out_search_flag') is not None:
                return set()
            node['out_search_flag'] = True
            outputs = node['output']
            result = set()
            if len(outputs) == 0:
                result.add(node['name'])
            else:
                for i in outputs:
                    result |= recursive_search(graph[i['name']])
            return result

        for i in graph_cp.values():
            output_list |= recursive_search(i)
        return list(output_list)
