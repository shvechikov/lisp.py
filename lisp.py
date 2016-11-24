import re
import pytest


Atom = str
Expression = list
meta_lisp = open('meta.lisp').read()


def tokenize(source):
    """Tokenize any lisp-like source string.

    >>> tokenize('((some atoms) (could be (here)))')
    ['(', '(', 'some', 'atoms', ')', '(', 'could', 'be', '(', 'here', ')', ')', ')']

    """
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
    """Return list of parsed expressions.

    >>> parse("(label a 'b) (wrap a)")
    [['label', 'a', ['quote', 'b']], ['wrap', 'a']]

    """
    tokens = tokenize(source)
    expr_list, remaining_tokens = parse_body(tokens)
    assert not remaining_tokens, 'Bad trailing tokens: {}'.format(remaining_tokens)
    return expr_list


def p(source):
    """Shortcut for parsing single expression."""
    return parse(source)[0]


def eval_expr(code, env=None):
    """Evaluate single expression."""
    env = env or {}
    assert isinstance(code, (Atom, Expression))

    if isinstance(code, Atom):
        value = env[code]
        return value, env

    if code[0] == 'quote':
        assert len(code) == 2
        return code[1], env

    if code[0] == 'atom':
        assert len(code) == 2
        value, _ = eval_expr(code[1], env)
        if isinstance(value, Atom) or value == []:
            return 't', env
        return [], env

    if code[0] == 'eq':
        assert len(code) == 3
        val1, _ = eval_expr(code[1], env)
        val2, _ = eval_expr(code[2], env)
        if (isinstance(val1, Atom) or val1 == []) and val1 == val2:
            return 't', env
        return [], env

    if code[0] == 'car':
        assert len(code) == 2
        value, _ = eval_expr(code[1], env)
        assert isinstance(value, Expression)
        if value:
            return value[0], env
        return [], env

    if code[0] == 'cdr':
        assert len(code) == 2
        value, _ = eval_expr(code[1], env)
        assert isinstance(value, Expression)
        if value:
            return value[1:], env
        return [], env

    if code[0] == 'cons':
        assert len(code) == 3
        val1, _ = eval_expr(code[1], env)
        val2, _ = eval_expr(code[2], env)
        assert isinstance(val2, Expression)
        return [val1] + val2, env

    if code[0] == 'cond':
        pairs = code[1:]
        for cond_pair in pairs:
            assert isinstance(cond_pair, Expression)
            assert len(cond_pair) == 2
            val1, _ = eval_expr(cond_pair[0], env)
            if val1 == 't':
                val2, _ = eval_expr(cond_pair[1], env)
                return val2, env
        return [], env

    if code[0] == 'label':
        assert len(code) == 3
        label, value = code[1:]
        assert isinstance(label, Atom)
        new_env = env.copy()
        new_env[label] = value
        return [], new_env

    if code[0] == 'defun':
        assert len(code) == 4
        new_code = ['label', code[1], ['lambda', code[2], code[3]]]
        return eval_expr(new_code, env)

    if isinstance(code[0], Atom):
        value = env[code[0]]
        return eval_expr([value] + code[1:], env)

    if isinstance(code[0], Expression):
        if code[0][0] == 'lambda':
            _, args, body = code[0]
            assert isinstance(args, Expression)
            assert len(args) == len(code) - 1
            arg_env = {
                arg: eval_expr(val, env)[0]
                for arg, val in zip(args, code[1:])
            }
            new_env = env.copy()
            new_env.update(arg_env)
            result, _ = eval_expr(body, new_env)
            return result, env
        assert False, 'Bad callable Expression: {}'.format(code[0])

    assert False, 'Unknown command: {}'.format(code[0])


def eval_code(code, env=None):
    """Evaluate a sequence of expressions by chaining environments."""
    result = Expression()
    commands = parse(code)
    for command in commands:
        result, env = eval_expr(command, env)
    return result, env


def meta_eval(meta_code, env=None):
    """Evaluate expression using MetaLISP."""
    full_code = meta_lisp + meta_code
    result, env = eval_code(full_code, env)
    return result


def e(source):
    """Shortcut for evaluating expressions in tests."""
    result, new_env = eval_code(source)
    return result


############################ TESTS ################################


def test_parser():
    assert p("'a") == ['quote', 'a']
    assert p('b') == 'b'
    assert p('()') == []
    assert p('(c)') == ['c']
    assert p('(c d)') == ['c', 'd']
    assert p('((e) f)') == [['e'], 'f']
    assert p('(g (h))') == ['g', ['h']]
    assert p('(g (h) ())') == ['g', ['h'], []]
    assert parse('(g) (h)') ==[['g'], ['h']]
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


def make_params(*test_packs):
    return [pair.split("-->") for pair in sum(test_packs, [])]


@pytest.mark.parametrize("code,result", make_params(base_tests, hard_tests))
def test_eval(code, result):
    assert e(code) == p(result)


@pytest.mark.parametrize("code,result", make_params(base_tests))
def test_meta_eval(code, result):
    meta_code = "(eval. '{} '())".format(code)
    assert meta_eval(meta_code) == p(result)


def test_meta_env_lookup():
    meta_code = "(eval. 'x '((x a) (y b)))"
    result = meta_eval(meta_code)
    assert result == p('a')
