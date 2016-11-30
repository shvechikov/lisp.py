.env:
	virtualenv --python=python3 .env
	./.env/bin/pip install -r requirements.txt

test: .env
	./.env/bin/pytest tests.py
