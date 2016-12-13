import re


Atom, Expression = str, list


def tokenize(source):
    """Tokenize any lisp-like source string. """
    tokens = re.findall(r"[()']|[^()'\s]+", source)
    return tokens


def parse_expr(tokens):
    """Parse a single expression. Return it and remaining tokens."""
    if tokens[0] == "'":
        expr, tokens = parse_expr(tokens[1:])
        return ['quote', expr], tokens
    if tokens[0] == '(':
        expr, tokens = parse_body(tokens[1:])
        assert tokens and tokens[0] == ')', 'Bad trailing tokens: %r' % tokens
        return expr, tokens[1:]
    return tokens[0], tokens[1:]  # Atom


def parse_body(tokens):
    """Parse a list of expressions. Return them and remaining tokens."""
    if tokens and tokens[0] != ')':
        first_expr, tokens = parse_expr(tokens)
        rest_list, tokens = parse_body(tokens)
        return [first_expr] + rest_list, tokens
    return [], tokens


def parse(source):
    """Return a list of parsed expressions."""
    tokens = tokenize(source)
    expr_list, remaining_tokens = parse_body(tokens)
    assert not remaining_tokens, 'Bad trailing tokens: %r' % remaining_tokens
    return expr_list


def is_atom_or_nil(data):
    return isinstance(data, Atom) or data == []


def is_pair(data):
    return isinstance(data, Expression) and len(data) == 2


class Lisp:
    """The LISP interpreter bound with environment you pass.

    >>> env = {
    ...     'hey': 'Hello',
    ...     'universe': ['world!'],
    ... }
    >>> Lisp(env).eval("(cons hey universe)")
    ['Hello', 'world!']

    """
    BUILTIN_FUNCTIONS = 'quote atom eq car cdr cons cond label defun add sub lt'.split()

    def __init__(self, env=None):
        self.env = env or {}

    def eval(self, source):
        """Evaluate LISP-code (a sequence of expressions) in shared environment."""
        result = Expression()
        expressions = parse(source)
        for expr in expressions:
            result = self.eval_expr(expr)
        return result

    def eval_expr(self, expr):
        """Evaluate a single expression."""
        assert isinstance(expr, (Atom, Expression))
        if isinstance(expr, Atom):
            if expr.isdigit():
                return expr
            return self.env[expr]
        else:
            func, *args = expr
            return self.eval_func(func, *args)

    def eval_func(self, func, *args):
        """Evaluate a function of any kind.

        It could be:
            - a builtin function,
            - a function defined by user via defun or label,
            - inline lambda expression call.

        """
        if isinstance(func, Atom):
            if func in self.BUILTIN_FUNCTIONS:
                builtin_func = getattr(self, func)
                return builtin_func(*args)
            else:
                # Convert user-defined function to inline lambda call
                user_func = self.env[func]
                return self.eval_func(user_func, *args)
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

    def child_eval(self, expr, extra_env=None):
        """Evaluate a single expression in isolated environment and return the result."""
        child_env = self.env.copy()
        if extra_env:
            child_env.update(extra_env)
        return Lisp(child_env).eval_expr(expr)

    # Builtin LISP functions:

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

    # Trivial arithmetic functions:

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
