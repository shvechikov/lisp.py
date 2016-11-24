import re
import pytest


meta_lisp = open('meta.lisp').read()


class LispBaseError(Exception):
    pass


class LispParseError(LispBaseError):
    pass


class LispRunTimeError(LispBaseError):
    pass


def tokenize(source):
    """Tokenize any lisp-like source string.

    >>> tokenize('((some atoms) (could be (here)))')
    ['(', '(', 'some', 'atoms', ')', '(', 'could', 'be', '(', 'here', ')', ')', ')']

    """
    tokens = re.findall(r"[()']|[^()'\s]+", source)
    return tokens


Atom = str
Expression = list


def parse_body(tokens):
    """Return expression items"""

    rest = list(tokens)

    result = []

    while True:
        quote = False

        if not rest:
            return result, []

        token, *rest = rest

        if token == "'":
            # TODO: allow multiple quotes in a row (recursion?)
            token, *rest = rest
            assert token != ')'
            quote = True

        if token not in ('(', ')'):
            atom = token
            if quote:
                atom = ['quote', atom]
            result.append(atom)

        if token == ')':
            return result, rest

        if token == '(':
            parsed, rest = parse_body(rest)
            expr = parsed
            if quote:
                expr = ['quote', expr]
            result.append(expr)

    assert False


def parse_tokens(tokens, allow_multi=False):
    """Parse expression or multi-expression."""
    if not tokens:
        raise LispParseError('Empty input')

    parsed, tail = parse_body(tokens)
    assert not tail, 'Some tail: {}'.format(tail)

    if allow_multi:
        return parsed
    else:
        assert len(parsed) == 1
        assert isinstance(parsed[0], (Atom, Expression))
        return parsed[0]


def parse(source, allow_multi=False):
    tokens = tokenize(source)
    return parse_tokens(tokens, allow_multi)


############################ EVAL ################################


def eval_env(code, env=None):
    env = env or {}
    assert isinstance(code, (Atom, Expression))

    if isinstance(code, Atom):
        value = env[code]
        return value, env

    first_arg = code[0]

    if first_arg == 'quote':
        assert len(code) == 2
        return code[1], env

    if first_arg == 'atom':
        assert len(code) == 2
        value, _ = eval_env(code[1], env)
        if isinstance(value, Atom):
            return 't', env
        elif isinstance(value, Expression) and not value:
            return 't', env
        else:
            return [], env

    if first_arg == 'eq':
        assert len(code) == 3
        val1, _ = eval_env(code[1], env)
        val2, _ = eval_env(code[2], env)
        if isinstance(val1, Atom) and val1 == val2:
            return 't', env
        if isinstance(val1, Expression) and not val1 and val1 == val2:
            return 't', env
        return [], env

    if first_arg == 'car':
        assert len(code) == 2
        value, _ = eval_env(code[1], env)
        assert isinstance(value, Expression)
        if value:
            car_value = value[0]
        else:
            car_value = []
        return car_value, env

    if first_arg == 'cdr':
        assert len(code) == 2
        value, _ = eval_env(code[1], env)
        assert isinstance(value, Expression)
        if value:
            return value[1:], env
        else:
            return [], env

    if first_arg == 'cons':
        assert len(code) == 3
        val1, _ = eval_env(code[1], env)
        val2, _ = eval_env(code[2], env)
        # assert isinstance(val1, Atom)
        assert isinstance(val2, Expression)
        return [val1] + val2, env

    if first_arg == 'cond':
        pairs = code[1:]
        for cond_pair in pairs:
            assert isinstance(cond_pair, Expression)
            assert len(cond_pair) == 2
            val1, _ = eval_env(cond_pair[0], env)
            if val1 == 't':
                #!!!
                val2, _ = eval_env(cond_pair[1], env)
                return val2, env
        return [], env

    if first_arg == 'label':
        assert len(code) == 3
        label, value = code[1:]
        assert isinstance(label, Atom)
        new_env = env.copy()
        new_env[label] = value
        return [], new_env

    if first_arg == 'defun':
        assert len(code) == 4
        new_code = ['label', code[1], ['lambda', code[2], code[3]]]
        return eval_env(new_code, env)

    # FIXME: HACK? BETTER WAY? Yes — use recursive call! ;)
    if isinstance(first_arg, Atom):
        value = env[first_arg]
        first_arg = value

    if isinstance(first_arg, Expression):
        if first_arg[0] == 'lambda':
            _, args, body = first_arg
            assert isinstance(args, Expression)
            assert len(args) == len(code) - 1
            arg_env = {
                arg: eval_env(val, env)[0]
                for arg, val in zip(args, code[1:])
            }
            new_env = env.copy()
            new_env.update(arg_env)
            result, _ = eval_env(body, new_env)
            return result, env
        return LispRunTimeError('Bad callable Expression: {}'.format(first_arg))

    raise LispRunTimeError('Unknown command: {}'.format(first_arg))


def multi_eval(code, env=None):
    result = Expression()

    commands = parse(code, allow_multi=True)
    for command in commands:
        result, env = eval_env(command, env)
    return result, env


def meta_eval(meta_code, env=None):
    full_code = meta_lisp + meta_code
    result, env = multi_eval(full_code, env)
    return result


############################ TESTS ################################


def e(source):
    result, new_env = multi_eval(source)
    return result


p = parse


def test_parser():
    assert 'a' == 'a'
    assert p("'a") == ['quote', 'a']
    assert p('b') == 'b'
    assert p('()') == []
    assert p('(c)') == ['c']
    assert p('(c d)') == ['c', 'd']
    assert p('((e) f)') == [['e'], 'f']
    assert p('(g (h))') == ['g', ['h']]
    assert p('(g (h) ())') == ['g', ['h'], []]


base_tests = [
    "(quote a) --> a",
    # FIXME: "'a --> a"
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


def prepare(*test_packs):
    return [pair.split(" --> ") for pair in sum(test_packs, [])]


@pytest.mark.parametrize("code,result", prepare(base_tests, hard_tests))
def test_eval(code, result):
    assert e(code) == p(result)


@pytest.mark.parametrize("code,result", prepare(base_tests))
def test_meta_eval(code, result):
    meta_code = "(eval. '{} '())".format(code)
    assert meta_eval(meta_code) == p(result)


def test_meta_env_lookup():
    meta_code = "(eval. 'x '((x a) (y b)))"
    result = meta_eval(meta_code)
    assert result == p('a')
