import pytest

from lisp import tokenize, parse, Lisp


META_LISP = open('meta.lisp').read()


def meta_eval(meta_code, env=None):
    """Evaluate an expression using MetaLISP - LISP in LISP."""
    source = META_LISP + meta_code
    return Lisp(env).eval(source)


def e(source):
    """Shortcut for evaluating expressions in tests."""
    return Lisp().eval(source)


def p(source):
    """Shortcut for parsing a single expression in tests."""
    expressions = parse(source)
    assert len(expressions) == 1
    return expressions[0]


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


# These tests work in both "LISP in Python" implementation and "LISP in "LISP in Python"" :)
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

# Next tests are multi-line and more tricky (with arithmetic inside!)
# so they works only in the first level of Matrix :)
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
    """,

    "(add 1 2 3 4 5) --> 15",
    "(sub 10 3) --> 7",
    "(lt 3 5) --> t",
    "(lt 7 5) --> ()",

    """
        (label + add)
        (label - sub)
        (label < lt)

        (defun fib (n)
            (cond ((< n 2) n)
                  ('t (+ (fib (- n 1))
                         (fib (- n 2))))))

        (fib 10)

        --> 55
    """,
]


# This couple of tests was made to check the special form of (label f (lambda ...))
# expression which was implemented in the canonical McCarthy's LISP in LISP.
# It allows us to create recursive functions.
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
