.env:
	virtualenv .env
	./.env/bin/pip install -r requirements.txt

test: .env
	./.env/bin/pytest --doctest-modules lisp.py