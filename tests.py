import pytest

from lisp import tokenize, parse, Interpreter


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
