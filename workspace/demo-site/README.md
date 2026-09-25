# Website demo gerado pelo JARVIS

Projeto Flask com cadastro, login, logout, dashboard protegido e SQLite.

## Executar

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000`.

## Testar

```bash
pytest -q
```

A base de dados é criada em `instance/app.sqlite3`. Para Render, use `gunicorn --bind 0.0.0.0:$PORT app:app` e defina `SECRET_KEY` forte. Este é um projeto de demonstração; ainda não inclui recuperação de senha, confirmação de e-mail, CSRF ou gestão de perfis.
