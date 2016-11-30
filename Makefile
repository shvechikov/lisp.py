.env:
	python3 -m venv .env
	./.env/bin/pip install -r requirements.txt

test: .env
	./.env/bin/pytest tests.py
