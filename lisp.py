import re


Atom, Expression = str, list


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
    assert not remaining_tokens, 'Bad trailing tokens: %r' % remaining_tokens
    return expr_list


def is_atom_or_nil(data):
    return isinstance(data, Atom) or data == []


def is_pair(data):
    return isinstance(data, Expression) and len(data) == 2


class Lisp:
    BUILTIN_FUNCTIONS = 'quote atom eq car cdr cons cond label defun add sub lt'.split()

    def __init__(self, env=None):
        self.env = env or {}

    def eval(self, source):
        """Evaluate a sequence of expressions in shared environment."""
        result = Expression()
        commands = parse(source)
        for command in commands:
            result = self.eval_expr(command)
        return result

    def child_eval(self, expr, extra_env=None):
        child_env = self.env.copy()
        if extra_env:
            child_env.update(extra_env)
        return Lisp(child_env).eval_expr(expr)

    def eval_expr(self, expr):
        assert isinstance(expr, (Atom, Expression))

        if isinstance(expr, Atom):
            if expr.isdigit():
                return expr
            return self.env[expr]
        else:
            func, *args = expr
            if isinstance(func, Atom):
                if func in self.BUILTIN_FUNCTIONS:
                    builtin_func = getattr(self, func)
                    return builtin_func(*args)
                else:
                    user_func = self.env[func]
                    return self.child_eval([user_func, *args])
            else:
                assert func[0] == 'lambda', 'Bad callable expression: %r' % func
                _, arg_names, lambda_body = func
                assert isinstance(arg_names, Expression)
                assert len(arg_names) == len(args)
                func_env = {
                    arg_name: self.child_eval(arg)
                    for arg_name, arg in zip(arg_names, args)
                }
                return self.child_eval(lambda_body, extra_env=func_env)

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
        val = self.child_eval(arg)
        assert isinstance(val, Expression)
        return val[1:] if val else []

    def cons(self, arg1, arg2):
        val1 = self.child_eval(arg1)
        val2 = self.child_eval(arg2)
        assert isinstance(val2, Expression)
        return [val1, *val2]

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

    def add(self, *args):
        vals = [int(self.child_eval(arg)) for arg in args]
        return Atom(sum(vals))

    def sub(self, arg1, arg2):
        val1 = self.child_eval(arg1)
        val2 = self.child_eval(arg2)
        return Atom(int(val1) - int(val2))

    def lt(self, arg1, arg2):
        val1 = self.child_eval(arg1)
        val2 = self.child_eval(arg2)
        if int(val1) < int(val2):
            return 't'
        return []
