# LISP in LISP in Python

This little project was created to understand how LISP works. I started to work on it after reading
[The Roots of LISP][1] — an excellent article by Paul Graham.

The challenge was to create from scratch a basic LISP interpreter in Python
and then — as a proof of the completeness — test it by running the canonical
McCarthy's LISP in LISP on my own LISP in Python implementation.

The hardest part (and the funniest one!) was the debugging LISP in LISP!

If you want to follow my steps just open `tests.py`. All the tests are in chronological
order there. Thanks to [pytest][2] for making the process of testing such a pleasure!

You can run the tests by calling:

    $ make test

The only requirement is Python 3.5 or higher.

[1]: http://www.paulgraham.com/rootsoflisp.html
[2]: http://pytest.org/
