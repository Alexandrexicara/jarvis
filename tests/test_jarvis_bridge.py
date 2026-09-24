import os
import shutil
import sys
import tempfile
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from jarvis_core import criar_projeto, gerar_codigo, parse_project_name


class TestJarvisBridge(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="jarvis_test_")
        self.original_root = os.environ.get("JARVIS_ROOT")
        os.environ["JARVIS_ROOT"] = self.temp_dir

    def tearDown(self):
        if self.original_root is None:
            os.environ.pop("JARVIS_ROOT", None)
        else:
            os.environ["JARVIS_ROOT"] = self.original_root
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_project_name(self):
        self.assertEqual(parse_project_name("Cria um projeto chamado cassino"), "cassino")
        self.assertEqual(parse_project_name("Cria o projeto loja"), "loja")
        self.assertEqual(parse_project_name("criar projeto de agenda"), "agenda")

    def test_criar_projeto_e_gerar_codigo(self):
        nome = "site_teste"
        pasta = criar_projeto(nome)
        self.assertTrue(os.path.isdir(pasta))

        caminho_arquivo = gerar_codigo(nome, "aplicativo de teste")
        self.assertTrue(os.path.isfile(caminho_arquivo))
        with open(caminho_arquivo, "r", encoding="utf-8") as fh:
            conteudo = fh.read()
        self.assertIn("aplicativo de teste", conteudo.lower())


if __name__ == "__main__":
    unittest.main()
