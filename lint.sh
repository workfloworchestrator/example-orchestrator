echo ========== isort ==========
isort main.py migrations products services utils workflows
echo ========== black ==========
black main.py migrations products services utils workflows
echo ========== ruff ==========
ruff main.py migrations products services utils workflows
echo ========== flake8 ==========
flake8 main.py migrations products services utils workflows
echo ========== mypy ==========
mypy main.py migrations products services utils workflows
