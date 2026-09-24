# -*- coding: utf-8 -*-
import os
import re

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_root_dir():
    return os.environ.get("JARVIS_ROOT", ROOT_DIR)


def get_projects_dir():
    root = get_root_dir()
    agente_dir = os.path.join(root, "agente_codigo")
    if os.path.isdir(agente_dir):
        return os.path.join(agente_dir, "projetos")
    return os.path.join(root, "projetos")


def sanitize_project_name(nome):
    if not nome:
        return "novo_projeto"
    nome = str(nome).strip().strip('"\'')
    nome = nome.replace("/", "_").replace("\\", "_")
    nome = re.sub(r"[^A-Za-z0-9_\-\sÀ-ÿ]", " ", nome)
    nome = re.sub(r"\s+", " ", nome).strip()
    nome = nome.replace(" ", "_")
    return nome or "novo_projeto"


def parse_project_name(mensagem):
    if not mensagem:
        return "novo_projeto"

    texto = mensagem.lower()
    texto = re.sub(r"\b(cria|criar|crie)\s+(?:um|uma|o|a|os|as)\s+", r"\1 ", texto)
    texto = texto.replace("projeto chamado", "projeto ")
    texto = texto.replace("projeto chamado ", "projeto ")

    for padrao in [
        r"(?:cria|criar|crie)\s+(?:projeto|app|site|aplicativo|sistema)?\s*(?:chamado\s+)?(.+)",
        r"(?:projeto|app|site|aplicativo|sistema)\s+(?:chamado\s+)?(.+)",
        r"(?:chamado)\s+(.+)",
        r"(?:nome\s+do\s+projeto\s*[:=]?\s*)(.+)",
    ]:
        match = re.search(padrao, texto, flags=re.IGNORECASE)
        if match:
            candidato = match.group(1).strip()
            candidato = re.sub(r"^(?:o|a|um|uma|os|as)\s+", "", candidato)
            candidato = re.sub(r"^(?:projeto|app|site|aplicativo|sistema|chamado|nome)\s+", "", candidato)
            candidato = re.sub(r"\b(?:de|do|da|e)\b", " ", candidato)
            candidato = re.sub(r"\s+", " ", candidato).strip(" \"'\t\n\r")
            if candidato:
                return sanitize_project_name(candidato)

    if "projeto" in texto:
        partes = texto.split("projeto", 1)[1].strip()
        partes = partes.replace("chamado", "").strip()
        if partes:
            return sanitize_project_name(partes)

    return "novo_projeto"


def criar_projeto(nome):
    nome_limpo = sanitize_project_name(nome)
    pasta = os.path.join(get_projects_dir(), nome_limpo)
    os.makedirs(pasta, exist_ok=True)
    return pasta


def gerar_codigo(nome, descricao, extensao="py"):
    projeto = criar_projeto(nome)
    nome_arquivo = "main.py" if extensao.lower() == "py" else f"app.{extensao.lower()}"
    caminho = os.path.join(projeto, nome_arquivo)
    descricao = descricao.strip() or "Projeto gerado pelo Jarvis"
    conteudo = f'''# -*- coding: utf-8 -*-
"""\n{descricao}\n"""

print("Olá! Projeto {nome} foi gerado com sucesso pelo Jarvis.")
print("Descrição: {descricao}")
'''
    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write(conteudo)
    return caminho
