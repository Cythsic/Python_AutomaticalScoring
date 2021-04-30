import ast, json, re, sys
import argparse
import subprocess
import difflib
import itertools
from ast import parse, NodeTransformer, copy_location, Name, FunctionDef, Expr, Str
import astunparse
import editdistance

#标准答案函数Answer()
standard_func="""def Answer(value):
    s=""
    for i in range(value):
        s+= "*" * (value-i)+ '\\n'
    return s
"""

class NormIdentifiers(NodeTransformer):
    def __init__(self):
        self.identifiers = {}
        super().__init__()

    def visit_Name(self, node):
        try:
            id = self.identifiers[node.id]
        except KeyError:
            id = f'id_{len(self.identifiers)}'
            self.identifiers[node.id] = id

        return copy_location(Name(id=id), node)

class NormFunctions(NodeTransformer):
    def __init__(self, func=None):
        self.identifiers = {}
        self.func = func
        super().__init__()

    def visit_FunctionDef(self, node):
        if self.func and self.func != node.name:
            return None

        try:
            name = self.identifiers[node.name]
        except KeyError:
            name = f'function{len(self.identifiers):x}'
            self.identifiers[node.name] = name

        for i, arg in enumerate(node.args.args):
            arg.arg = f'arg{i}'

        new_func = FunctionDef(name=name, args=node.args, body=node.body, decorator_list=node.decorator_list)

        if isinstance(new_func.body[0], Expr) and isinstance(new_func.body[0].value, Str):
            del new_func.body[0]

        return copy_location(new_func, node)

def get_normed_content_tree(filecontent, func=None):
    tree = parse(filecontent)
    tree = NormFunctions(func=func).visit(tree)
    tree = NormIdentifiers().visit(tree)
    return tree

def get_normed_content(filecontent, filename, func=None):
        tree = parse(filecontent)
        tree = NormFunctions(func=func).visit(tree)
        tree = NormIdentifiers().visit(tree)
        return (filename, astunparse.unparse(tree))

def get_pair_stats(pair):
    dstc = editdistance.eval(pair[0][1], pair[1][1])
    avg_len = len(pair[1][1])
    percent = 100.0 * (1 - (dstc / avg_len))
    return((percent, dstc, pair[0], pair[1]))

class viz_walker(ast.NodeVisitor):
    def __init__(self):
        self.stack = []
        self.graph = nx.Graph()

    def generic_visit(self, stmt):
        node_name = str(stmt).split('.')[1].split(' ')[0]
        # print(node_name)
        parent_name = None

        if self.stack:
            parent_name = self.stack[-1]

        self.stack.append(node_name)

        self.graph.add_node(node_name)

        if parent_name:
            self.graph.add_edge(node_name, parent_name)

        super(self.__class__, self).generic_visit(stmt)

        self.stack.pop()

#学生答案以字符串形式存给参数student_func
student_func = """{{ STUDENT_ANSWER | e('py') }}"""

output = ""
expected = ""
mark = 20

#判断是否使用其他库函数
if 'import' in student_func:
    output = '你的代码里有 "import" 语句,该题不得分!'
    result = {'got': output, 'fraction': 0}
    print(json.dumps(result))
    sys.exit(0)
elif 'print' in student_func:
    output = '你的代码里有 "print" 语句，该题不得分!'
    result = {'got': output, 'fraction': 0}
    print(json.dumps(result))
    sys.exit(0)
else:
    try:
        tree = ast.parse(student_func)
    except Exception as e:
        output += '你的代码存在语法错误，扣5分！\n'
        mark -= 5
        output += "%s"%e
        stu_str = ["student_func", student_func]
        std_str = ["standard_func", standard_func]
        submissions = [stu_str, std_str]
        pairs = [get_pair_stats(pair) for pair in itertools.combinations(submissions, 2)]
        for sim, dstc, a, b in pairs:
            if sim > 0:
                mark = mark * sim /100
        result = {'expected': '', 'got': output, 'fraction': mark/20.0}
        print(json.dumps(result))   
        sys.exit(0)
    
    exec(student_func)
    exec(standard_func)
    if re.search(r"\bfor\b", student_func):
        mark = 20
    else:
        mark-=5
        output += '你的代码里没有使用for循环,扣5分！\n'
        expected += '\n'
   

    #测试用例动态测试
    std_answ=Answer(5) 
    stu_ans=pirnt_triangle(5)
    if std_answ!=stu_ans:
        expected += '测试用例未全部通过'
    else:
        expected += str(std_answ) + '\n'
        output += str(stu_ans) + '\n'
        std_answ=Answer(1)
        stu_ans=pirnt_triangle(1)
        if std_answ!=stu_ans:
            expected += '测试用例未全部通过' 
        else:
            expected += str(std_answ) + '\n'
            output += str(stu_ans) + '\n'
            std_answ=Answer(0)
            stu_ans=pirnt_triangle(0)
            if std_answ!=stu_ans:
                expected += '测试用例未全部通过'
            else:
                expected += str(std_answ) + '\n'
                output += str(stu_ans) + '\n'
                result = {'expected': expected, 'got': output, 'fraction': mark/20.0}
                print(json.dumps(result))
                sys.exit(0)
    #图比较
    stu_tree = get_normed_content_tree(student_func)
    std_tree = get_normed_content_tree(standard_func)
    stu = viz_walker()
    std = viz_walker()
    stu.visit(stu_tree)
    std.visit(std_tree)

    #字符串比较
    stu_str = get_normed_content(student_func,"student_func")
    std_str = get_normed_content(standard_func,"standard_func")
    submissions = [stu_str, std_str]
    pairs = [get_pair_stats(pair) for pair in itertools.combinations(submissions, 2)]
    for sim, dstc, a, b in pairs:
        if sim > 0:
            mark = mark * sim /100

    result = {'expected': expected, 'got': output, 'fraction': mark/20.0}
    print(json.dumps(result))   

