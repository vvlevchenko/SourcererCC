import re
import javalang
import itertools

global found_parent

re_string = re.escape("\"") + '.*?' + re.escape("\"")


def getFunctions(filestring, file_path, separators, comment_inline_pattern):
    method_string = []
    method_pos = []
    method_name = []

    global found_parent
    found_parent = []

    tree = None

    try:
        tree = javalang.parse.parse(filestring)
        package = tree.package
        if package is None:
            package = 'JHawkDefaultPackage'
        else:
            package = package.name
    except:
        print(f"[WARNING] File {file_path} contains syntax error")
        return None, None, []

    file_string_split = filestring.split('\n')
    nodes = itertools.chain(tree.filter(javalang.tree.ConstructorDeclaration), \
        tree.filter(javalang.tree.MethodDeclaration))

    try:
        for path, node in nodes:
            node_name = '.' + node.name
            for i, var in enumerate(reversed(path)):
                if isinstance(var, javalang.tree.ClassDeclaration):
                    if len(path) - 3 == i:  # Top most
                        name = '.'
                    else:
                        name = '$'
                    name += var.name + check_repetition(var, var.name)
                elif isinstance(var, javalang.tree.InterfaceDeclaration):
                    name = '$' + var.name + check_repetition(var, var.name)
                elif isinstance(var, javalang.tree.ClassCreator):
                    var_type = var.type.name
                    name = '$' + var_type + check_repetition(var, var_type)
                name += node_name
            args = []
            for t in node.parameters:
                dims = []
                if len(t.type.dimensions) > 0:
                    for _ in t.type.dimensions:
                        dims.append("[]")
                dims = "".join(dims)
                args.append(t.type.name + dims)
            args = ",".join(args)

            fqn = "%s%s(%s)" % (package, name, args)

            init_line = node.position[0]
            method_body = []
            closed = 0
            openned = 0

            for line in file_string_split[init_line - 1:]:
                if len(line) == 0:
                    continue
                line_re = re.sub(comment_inline_pattern, '', line, flags=re.MULTILINE)
                line_re = re.sub(re_string, '', line_re, flags=re.DOTALL)

                closed += line_re.count('}')
                openned += line_re.count('{')
                if (closed - openned) == 0:
                    method_body.append(line)
                    break
                else:
                    method_body.append(line)

            end_line = init_line + len(method_body) - 1
            method_body = '\n'.join(method_body)

            method_pos.append((init_line, end_line))
            method_string.append(method_body)

            method_name.append(fqn)
    except RecursionError:
        print(f"[WARNING] Stack recursion limit exceeded on {method_name}")
        return None, None, method_name

    if len(method_pos) != len(method_string):
        print(f"[WARNING] File {file_path} contains syntax error")
        return None, None, method_name
    else:
        return method_pos, method_string, method_name


def check_repetition(node, name):
    before = -1
    i = 0
    for (obj, n, value) in found_parent:
        if obj is node:
            if value == -1:
                return ''
            else:
                return '_' + str(value)
        else:
            i += 1
        if n == name:
            before += 1
    found_parent.append((node, name, before))
    if before == -1:
        return ''
    else:
        return '_' + str(before)
