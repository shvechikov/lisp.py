import re


Atom = str
Expression = list


def tokenize(source):
    """Tokenize any lisp-like source string. """
    tokens = re.findall(r"[()']|[^()'\s]+", source)
    return tokens


def parse_expr(tokens):
    """Parse single expression. Return it and remaining tokens."""
    if tokens[0] == "'":
        expr, tokens = parse_expr(tokens[1:])
        return ['quote', expr], tokens
    if tokens[0] == '(':
        expr, tokens = parse_body(tokens[1:])
        assert tokens and tokens[0] == ')', 'Bad trailing tokens: %r' % tokens
        return expr, tokens[1:]
    return tokens[0], tokens[1:]  # Atom


def parse_body(tokens):
    """Parse list of expressions. Return them and remaining tokens."""
    if tokens and tokens[0] != ')':
        first_expr, tokens = parse_expr(tokens)
        rest_list, tokens = parse_body(tokens)
        return [first_expr] + rest_list, tokens
    return [], tokens


def parse(source):
    """Return list of parsed expressions."""
    tokens = tokenize(source)
    expr_list, remaining_tokens = parse_body(tokens)
    assert not remaining_tokens, 'Bad trailing tokens: {}'.format(remaining_tokens)
    return expr_list


def is_atom_or_nil(data):
    return isinstance(data, Atom) or data == []


def is_pair(pair):
    return isinstance(pair, Expression) and len(pair) == 2


class Interpreter:
    BUILTIN_FUNCTIONS = 'quote atom eq car cdr cons cond label defun'.split()

    def __init__(self, env=None):
        self.env = env or {}

    def eval(self, source):
        """Evaluate a sequence of expressions by chaining environments."""
        result = Expression()
        commands = parse(source)
        for command in commands:
            result = self.eval_expr(command)
        return result

    def eval_expr(self, code):
        assert isinstance(code, (Atom, Expression))

        if isinstance(code, Atom):
            return self.env[code]

        if isinstance(code[0], Atom):
            func_name = code[0]
            args = code[1:]
            if func_name in self.BUILTIN_FUNCTIONS:
                builtin_func = getattr(self, func_name)
                return builtin_func(*args)
            else:
                user_func = self.env[func_name]
                return self.child_eval([user_func] + args)

        if isinstance(code[0], Expression):
            assert code[0][0] == 'lambda', 'Bad callable expression: {}'.format(code[0])
            _, arg_names, lambda_body = code[0]
            arg_values = code[1:]
            assert isinstance(arg_names, Expression)
            assert len(arg_names) == len(code) - 1
            func_env = {
                arg: self.child_eval(val)
                for arg, val in zip(arg_names, arg_values)
            }
            return self.child_eval(lambda_body, extra_env=func_env)

        raise RuntimeError('Unknown command: {}'.format(code[0]))

    def child_eval(self, code, extra_env=None):
        child_env = self.env.copy()
        if extra_env:
            child_env.update(extra_env)
        return Interpreter(child_env).eval_expr(code)

    # Builtin functions:

    def quote(self, arg):
        return arg

    def atom(self, arg):
        value = self.child_eval(arg)
        return 't' if is_atom_or_nil(value) else []

    def eq(self, arg1, arg2):
        val1 = self.child_eval(arg1)
        val2 = self.child_eval(arg2)
        return 't' if (is_atom_or_nil(val1) and val1 == val2) else []

    def car(self, arg):
        val = self.child_eval(arg)
        assert isinstance(val, Expression)
        return val[0] if val else []

    def cdr(self, arg):
        value = self.child_eval(arg)
        assert isinstance(value, Expression)
        return value[1:] if value else []

    def cons(self, arg1, arg2):
        val1 = self.child_eval(arg1)
        val2 = self.child_eval(arg2)
        assert isinstance(val2, Expression)
        return [val1] + val2

    def cond(self, *pairs):
        assert all(is_pair(pair) for pair in pairs)
        for arg1, arg2 in pairs:
            val1 = self.child_eval(arg1)
            if val1 == 't':
                return self.child_eval(arg2)
        return []

    def label(self, label_name, label_val):
        assert isinstance(label_name, Atom)
        self.env[label_name] = label_val
        return []

    def defun(self, label_name, lambda_args, lambda_body):
        new_code = ['label', label_name, ['lambda', lambda_args, lambda_body]]
        return self.eval_expr(new_code)
