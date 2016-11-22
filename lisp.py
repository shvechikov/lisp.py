import re


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


def is_expression(item):
    return isinstance(item, (Atom, Expression))


class Atom:
    def __init__(self, value):
        assert re.match(r'[^()\s]', value), value
        self.value = value

    def __eq__(self, other):
        if isinstance(other, Atom):
            return self.value == other.value
        return False

    def __repr__(self):
        return self.value


class Expression:
    def __init__(self, items=None):
        items = items or []
        assert all(is_expression(item) for item in items)
        self.items = items
        # print(repr(self))

    def __eq__(self, other):
        if isinstance(other, Expression):
            return self.items == other.items
        return False

    def __repr__(self):
        return '({})'.format(' '.join(repr(item) for item in self.items))


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
            atom = Atom(token)
            if quote:
                atom = Expression([Atom('quote'), atom])
            result.append(atom)

        if token == ')':
            return result, rest

        if token == '(':
            parsed, rest = parse_body(rest)
            expr = Expression(parsed)
            if quote:
                expr = Expression([Atom('quote'), expr])
            result.append(expr)

    assert False


def parse_expression(tokens, allow_multi=False):
    """Parse expression. Return exactly one Atom or Expression"""
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
    return parse_expression(tokens, allow_multi)


############################ EVAL ################################


def eval(code, env=None):
    env = env or Expression()
    result, new_env = eval_env(code, env)
    return result


def lookup(atom, env):
    assert isinstance(atom, Atom)
    for pair in env.items:
        assert len(pair.items) == 2
        if pair.items[0] == atom:
            return pair.items[1]
    raise LispRunTimeError('Could not find unknown atom: {}'.format(atom))


def eval_env(code, env=None):
    env = env or Expression()
    assert is_expression(code)

    if isinstance(code, Atom):
        value = lookup(code, env)
        return value, env

    first_arg = code.items[0]

    if first_arg == Atom('quote'):
        assert len(code.items) == 2
        return code.items[1], env

    if first_arg == Atom('atom'):
        assert len(code.items) == 2
        value = eval(code.items[1], env)
        if isinstance(value, Atom):
            return Atom('t'), env
        elif isinstance(value, Expression) and not value.items:
            return Atom('t'), env
        else:
            return Expression(), env

    if first_arg == Atom('eq'):
        assert len(code.items) == 3
        val1 = eval(code.items[1], env)
        val2 = eval(code.items[2], env)
        if isinstance(val1, Atom) and val1 == val2:
            return Atom('t'), env
        if isinstance(val1, Expression) and not val1.items and val1 == val2:
            return Atom('t'), env
        return Expression(), env

    if first_arg == Atom('car'):
        assert len(code.items) == 2
        value = eval(code.items[1], env)
        assert isinstance(value, Expression)
        return value.items[0], env

    if first_arg == Atom('cdr'):
        assert len(code.items) == 2
        value = eval(code.items[1], env)
        assert isinstance(value, Expression)
        return Expression(value.items[1:]), env

    if first_arg == Atom('cons'):
        assert len(code.items) == 3
        val1 = eval(code.items[1], env)
        val2 = eval(code.items[2], env)
        assert isinstance(val1, Atom)
        assert isinstance(val2, Expression)
        return Expression([val1] + val2.items), env

    if first_arg == Atom('cond'):
        pairs = code.items[1:]
        for cond_pair in pairs:
            assert isinstance(cond_pair, Expression)
            assert len(cond_pair.items) == 2
            val1 = eval(cond_pair.items[0], env)
            val2 = eval(cond_pair.items[1], env)
            if val1 == Atom('t'):
                return val2, env
        return Expression(), env

    if first_arg == Atom('label'):
        assert len(code.items) == 3
        label, value = code.items[1:]
        assert isinstance(label, Atom)
        # value = eval(code.items[2], env)
        extended_env = [Expression(code.items[1:])] + env.items
        return Expression(), Expression(extended_env)

    # HACK? BETTER WAY? Yes — use recursive call! ;)
    if isinstance(first_arg, Atom):
        value = lookup(first_arg, env)
        first_arg = value

    if isinstance(first_arg, Expression):
        if first_arg.items[0] == Atom('lambda'):
            _, args, body = first_arg.items
            assert isinstance(args, Expression)
            assert isinstance(body, Expression)
            assert len(args.items) == len(code.items) - 1
            arg_env = [
                Expression([arg, eval(val, env)])
                for arg, val in zip(args.items, code.items[1:])
            ]
            new_env = Expression(arg_env + env.items)
            result = eval(body, new_env)
            return result, env
        return LispRunTimeError('Bad callable Expression: {}'.format(first_arg))

    raise LispRunTimeError('Unknown command: {}'.format(first_arg))


def multi_eval(code, env=None):
    env = env or Expression()
    result = Expression()

    commands = parse(code, allow_multi=True)
    for command in commands:
        result, env = eval_env(command, env)
    return result, env


############################ TESTS ################################

p = parse


def e(source):
    return eval(parse(source))


def test_parser():
    assert Atom('a') == Atom('a')
    assert p("'a") == p('(quote a)')
    assert p('b') == Atom('b')
    assert p('()') == Expression()
    assert p('(c)') == Expression([Atom('c')])
    assert p('(c d)') == Expression([Atom('c'), Atom('d')])
    assert p('((e) f)') == Expression([Expression([Atom('e')]), Atom('f')])
    assert p('(g (h))') == Expression([Atom('g'), Expression([Atom('h')])])
    assert p('(g (h) ())') == Expression([Atom('g'), Expression([Atom('h')]), Expression()])

    source = '(g (h) ((some ((crazy) nested)) code))'
    assert repr(p(source)) == source


def test_eval_quote():
    assert e('(quote a)') == p('a')


def test_eval_atom():
    assert e('(atom (quote a))') == p('t')
    assert e('(atom (quote (a b c)))') == p('()')
    assert e('(atom (quote ()))') == p('t')
    assert e('(atom (atom (quote a)))') == p('t')
    assert e('(atom (quote (atom (quote a))))') == p('()')


def test_eval_eq():
    assert e("(eq 'a 'a)") == p('t')
    assert e("(eq 'a 'b)") == p('()')
    assert e("(eq '() '())") == p('t')
    assert e("(eq '(a) '(a))") == p('()')


def test_eval_car():
    assert e("(car '(a b c))") == p('a')


def test_eval_cdr():
    assert e("(cdr '(a b c))") == p('(b c)')


def test_eval_cons():
    assert e("(cons 'a '(b c))") == p('(a b c)')
    assert e("(cons 'a (cons 'b (cons 'c '())))") == p('(a b c)')


def test_eval_cond():
    assert e("""
    (cond ((eq 'a 'b) 'first)
          ((atom 'a) 'second))
    """) == p('second')


def test_multi_eval_env_persistence():
    start_env = p('((nil ()))')
    result, env = multi_eval("'a", start_env)
    assert result == p('a')
    assert env == p('((nil ()))')


def test_multi_eval_label():
    result, env = multi_eval("(label nil ())")
    assert result == p('()')
    assert env == p('((nil ()))')


def test_multi_eval_env_work():
    result, env = multi_eval("""
        (label l (a b c))
        (cdr l)
    """)
    assert result == p('(b c)')


def test_lambda():
    code = "((lambda (x) (cons x '(b c))) 'z)"
    expected_result = '(z b c)'
    result, env = multi_eval(code)
    assert result == p(expected_result)


def test_labeled_lambda():
    code = """
        (label wrap (lambda (x) (cons x '())))
        (wrap 'wrap_me)
    """
    result, env = multi_eval(code)
    assert result == p('(wrap_me)')


def test_recursion():
    code = """
        (label separate
          (lambda (lst)
                  (cond
                    ((eq lst '()) '())
                    ((eq (cdr lst) '()) lst)
                    ('t (cons (car lst) (cons '| (separate (cdr lst))))))))

        (separate '(a b c))

    """
    result, env = multi_eval(code)
    assert result == p('(a | b | c)')
