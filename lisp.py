import re
import pytest


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


META_LISP = open('meta.lisp').read()


def meta_eval(meta_code, env=None):
    """Evaluate expression using MetaLISP."""
    source = META_LISP + meta_code
    interpreter = Interpreter(env)
    return interpreter.eval(source)


def e(source):
    """Shortcut for evaluating expressions in tests."""
    interpreter = Interpreter()
    return interpreter.eval(source)


def p(source):
    """Shortcut for parsing single expression."""
    return parse(source)[0]


def test_tokenizer():
    source = '((some atoms) (could be (here)))'
    tokens = ['(', '(', 'some', 'atoms', ')', '(', 'could', 'be', '(', 'here', ')', ')', ')']
    assert tokenize(source) == tokens


def test_parser():
    assert p("'a") == ['quote', 'a']
    assert p('b') == 'b'
    assert p('()') == []
    assert p('(c)') == ['c']
    assert p('(c d)') == ['c', 'd']
    assert p('((e) f)') == [['e'], 'f']
    assert p('(g (h))') == ['g', ['h']]
    assert p('(g (h) ())') == ['g', ['h'], []]
    assert parse('(g) (h)') == [['g'], ['h']]
    assert parse("(label a 'b) (wrap a)") == [['label', 'a', ['quote', 'b']], ['wrap', 'a']]
    with pytest.raises(AssertionError):
        parse('(g(')


base_tests = [
    "(quote a) --> a",
    "'a --> a",
    "''a --> (quote a)",
    "''() --> (quote ())",
    "(atom (quote a)) --> t",
    "(atom (quote (a b c))) --> ()",
    "(atom (quote ())) --> t",
    "(atom (atom (quote a))) --> t",
    "(atom (quote (atom (quote a)))) --> ()",
    "(eq 'a 'a) --> t",
    "(eq 'a 'b) --> ()",
    "(eq '() '()) --> t",
    "(eq '(a) '(a)) --> ()",
    "(car '(a b c)) --> a",
    "(cdr '(a b c)) --> (b c)",
    "(cons 'a '(b c)) --> (a b c)",
    "(cons 'a (cons 'b (cons 'c '()))) --> (a b c)",

    """
        (cond ((eq 'a 'b) 'first)
              ((atom 'a) 'second))
         --> second
    """,

    """
        ((lambda (x) x) 'z)
        --> z
    """,

    """
        ((lambda (x) (cons x '(b c))) 'z)
        --> (z b c)
    """,
]

hard_tests = [
    """
        (label l (a b c))
        (cdr l)
        --> (b c)
    """,
    """
        (label l (a b c))
        (label REST cdr)
        (REST l)
        --> (b c)
    """,
    """
        (label wrap (lambda (x) (cons x '())))
        (wrap 'wrap_me)
        --> (wrap_me)
    """,

    """
        (defun separate (lst)
            (cond
                ((eq (cdr lst) '()) lst)
                ('t (cons (car lst) (cons '| (separate (cdr lst)))))))

        (separate '(a b c))

        --> (a | b | c)
    """
]

meta_tests = [
    """
        ((label wrap (lambda (x) (cons x '()))) 'wrap_me)
        --> (wrap_me)
    """,
    """
        ((label separate (lambda (lst)
            (cond
                ((eq (cdr lst) '()) lst)
                ('t (cons (car lst) (cons '| (separate (cdr lst))))))))

            '(a b c))
        --> (a | b | c)
    """
]


def make_params(*test_packs):
    return [pair.split("-->") for pair in sum(test_packs, [])]


@pytest.mark.parametrize("code,result", make_params(base_tests, hard_tests))
def test_eval(code, result):
    assert e(code) == p(result)


@pytest.mark.parametrize("code,result", make_params(base_tests, meta_tests))
def test_meta_eval(code, result):
    meta_code = "(eval. '{} '())".format(code)
    assert meta_eval(meta_code) == p(result)


def test_meta_env_lookup():
    meta_code = "(eval. 'x '((x a) (y b)))"
    result = meta_eval(meta_code)
    assert result == p('a')
