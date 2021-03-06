import ast

from fields import Field, Fields


class Resolver(object):
    """
    Wrapper class for static methods to resolve various ast nodes and more
    complex datatypes to their respective data.
    """

    @staticmethod
    def resolve(node):
        node_type = type(node).__name__.split('.')[-1]
        method = getattr(Resolver, node_type)
        return method(node)

    @staticmethod
    def Call(field_node):
        try:
            func = field_node.func
        except AttributeError:
            print field_node

        # e.g. serializers.CharField
        if isinstance(func, ast.Attribute):
            # Attribute has value: Name
            #               attr : str
            return Resolver.Attribute(func)
        else:
            return func.id

    @staticmethod
    def Attribute(node):
        rhs = node.attr
        lhs = Resolver.resolve(node.value)

        return '.'.join([lhs, rhs])

    @staticmethod
    def Assign(node):
        # TODO: We don't usually do multi assignments
        target = node.targets[0]
        lhs = target.id
        rhs = node.value

        return (lhs, rhs)

    @staticmethod
    def Name(node):
        return node.id

    @staticmethod
    def Str(node):
        return node.s

    @staticmethod
    def Num(node):
        return node.n

    @staticmethod
    def List(node):
        return [Resolver.resolve(x) for x in node.elts]

    @staticmethod
    def Tuple(node):
        return tuple(Resolver.resolve(x) for x in node.elts)

    @staticmethod
    def keywords(keywords):
        # each keyword is a `keyword` with arg: str and value: node
        return {
            keyword.arg: Resolver.resolve(keyword.value)
            for keyword in keywords
        }

    @staticmethod
    def func_params(field_node):
        field = Field()

        if field_node.args:
            field['args'] = Resolver.resolve(field_node.args)

        field.update(**Resolver.keywords(field_node.keywords))

        return field

    @staticmethod
    def class_var_drf_field(node):
        field_name, rhs = Resolver.resolve(node)

        # TODO: we don't care about other class variables.
        if not isinstance(rhs, ast.Call):
            return None

        return Resolver.parse_drf_field_node(field_name, rhs)

    @staticmethod
    def drf_meta_fields(meta_node):
        def resolve_fields(fields_node, read_only=False):
            fields = []
            known_types = [ast.Tuple, ast.List, ast.Set]

            if isinstance(fields_node, ast.BinOp):
                assert isinstance(fields_node.op, ast.Add)
                # if either is Attribute, resolve_fields returns [] which is fine
                # since it will be handled by the logic in bases
                return resolve_fields(fields_node.left) + resolve_fields(fields_node.right)

            if any(isinstance(fields_node, t) for t in known_types):
                for field_node in fields_node.elts:
                    field = Field(field_name=Resolver.resolve(field_node),
                                  read_only=read_only)

                    fields.append(field)

            return fields

        fields = Fields()

        for node in meta_node.body:
            if not isinstance(node, ast.Assign):
                continue

            lhs, rhs = Resolver.resolve(node)

            if lhs == 'fields':
                fields.extend(resolve_fields(rhs))
            elif lhs == 'read_only_fields':
                fields.extend(resolve_fields(rhs, read_only=True))

        return fields

    @staticmethod
    def parse_drf_field_node(field_name, field_node):
        return Field(field_name=field_name,
                     func_name=Resolver.resolve(field_node),
                     **Resolver.func_params(field_node))

    @staticmethod
    def init_method(init_node):
        fields = Fields()
        # TODO: ???
        return fields
