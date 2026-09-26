"""Controle de navegador do JARVIS usando Playwright.

O navegador é iniciado sob demanda e mantém um perfil persistente em
workspace/.jarvis/browser-profile. Em Windows, por padrão, o navegador é
visível; em servidores sem ambiente gráfico, use JARVIS_BROWSER_HEADLESS=1.
"""
from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except Exception:  # pragma: no cover
    sync_playwright = None
    PlaywrightTimeoutError = Exception


class BrowserController:
    def __init__(self, profile_dir: Path):
        self.profile_dir = Path(profile_dir).resolve()
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._pw = None
        self._context = None
        self._page = None
        self._lock = threading.RLock()

    def _headless(self) -> bool:
        value = os.environ.get("JARVIS_BROWSER_HEADLESS", "auto").strip().lower()
        if value in {"1", "true", "yes", "on", "sim"}:
            return True
        if value in {"0", "false", "no", "off", "nao", "não"}:
            return False
        # Render/Linux sem DISPLAY normalmente precisa de headless.
        return os.name != "nt" and not os.environ.get("DISPLAY")

    def _ensure(self):
        if sync_playwright is None:
            raise RuntimeError("Playwright não está instalado. Execute: pip install playwright e python -m playwright install chromium")
        if self._context is not None:
            return self._context
        self._pw = sync_playwright().start()
        channel = os.environ.get("JARVIS_BROWSER_CHANNEL", "").strip() or None
        # Usa o Google Chrome instalado no Windows.
        # Evita o download do Chromium pelo Playwright.
        chrome_path = os.environ.get(
            "JARVIS_BROWSER_EXECUTABLE",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        )
        kwargs = {
            "headless": self._headless(),
            "viewport": {"width": 1440, "height": 900},
            "accept_downloads": True,
        }
        # Windows: usa o Chrome instalado.
        # Linux/Render: mantém o comportamento original.
        if os.name == "nt" and os.path.isfile(chrome_path):
            kwargs["executable_path"] = chrome_path
        elif channel:
            kwargs["channel"] = channel
        self._context = self._pw.chromium.launch_persistent_context(str(self.profile_dir), **kwargs)
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.set_default_timeout(int(os.environ.get("JARVIS_BROWSER_TIMEOUT", "20000")))
        return self._context

    def _validate_url(self, url: str) -> str:
        url = str(url or "").strip()
        if not re.match(r"^https?://", url, re.I):
            raise ValueError("A URL deve começar com http:// ou https://.")
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError("URL inválida.")
        return url

    def _result(self, success: bool, message: str, **extra):
        data = {"success": success, "message": message}
        data.update(extra)
        return data

    def open_url(self, url: str, new_tab: bool = False):
        with self._lock:
            url = self._validate_url(url)
            try:
                context = self._ensure()
                if new_tab:
                    page = context.new_page()
                else:
                    page = self._page or (context.pages[0] if context.pages else context.new_page())
                self._page = page
                response = page.goto(url, wait_until="domcontentloaded", timeout=int(os.environ.get("JARVIS_BROWSER_NAV_TIMEOUT", "30000")))
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                current = page.url
                title = page.title()
                status = response.status if response else None
                # HTTP 4xx/5xx não é considerado abertura bem-sucedida.
                if status is not None and status >= 400:
                    return self._result(False, f"A página respondeu HTTP {status}.", url=current, title=title, status=status)
                return self._result(True, "Página aberta com sucesso.", url=current, title=title, status=status)
            except PlaywrightTimeoutError:
                return self._result(False, "Tempo esgotado ao abrir a página.", url=url)
            except Exception as exc:
                return self._result(False, f"Não foi possível abrir a página: {exc}", url=url)

    def click_text(self, text: str, exact: bool = False):
        with self._lock:
            text = str(text or "").strip()
            if not text:
                raise ValueError("Informe o texto do link ou botão.")
            try:
                self._ensure()
                locator = self._page.get_by_text(text, exact=exact).first
                locator.click(timeout=int(os.environ.get("JARVIS_BROWSER_TIMEOUT", "20000")))
                self._page.wait_for_load_state("domcontentloaded", timeout=5000)
                return self._result(True, "Elemento clicado com sucesso.", url=self._page.url, title=self._page.title())
            except PlaywrightTimeoutError:
                return self._result(False, f"Não encontrei ou não consegui clicar em: {text}")
            except Exception as exc:
                return self._result(False, f"Não foi possível clicar em '{text}': {exc}")

    def click_selector(self, selector: str):
        with self._lock:
            selector = str(selector or "").strip()
            if not selector:
                raise ValueError("Informe o seletor.")
            try:
                self._ensure()
                self._page.locator(selector).first.click(timeout=int(os.environ.get("JARVIS_BROWSER_TIMEOUT", "20000")))
                try:
                    self._page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                return self._result(True, "Elemento clicado com sucesso.", url=self._page.url, title=self._page.title())
            except Exception as exc:
                return self._result(False, f"Não foi possível clicar no elemento: {exc}")

    def back(self):
        with self._lock:
            self._ensure()
            try:
                self._page.go_back(wait_until="domcontentloaded", timeout=20000)
                return self._result(True, "Voltei para a página anterior.", url=self._page.url, title=self._page.title())
            except Exception as exc:
                return self._result(False, f"Não foi possível voltar: {exc}")

    def forward(self):
        with self._lock:
            self._ensure()
            try:
                self._page.go_forward(wait_until="domcontentloaded", timeout=20000)
                return self._result(True, "Avancei para a próxima página.", url=self._page.url, title=self._page.title())
            except Exception as exc:
                return self._result(False, f"Não foi possível avançar: {exc}")

    def reload(self):
        with self._lock:
            self._ensure()
            try:
                self._page.reload(wait_until="domcontentloaded", timeout=30000)
                return self._result(True, "Página atualizada.", url=self._page.url, title=self._page.title())
            except Exception as exc:
                return self._result(False, f"Não foi possível atualizar: {exc}")

    def scroll(self, direction="down", amount=700):
        with self._lock:
            self._ensure()
            try:
                amount = max(50, min(int(amount), 5000))
                delta = amount if str(direction).lower() != "up" else -amount
                self._page.mouse.wheel(0, delta)
                return self._result(True, "Página rolada.", url=self._page.url, title=self._page.title())
            except Exception as exc:
                return self._result(False, f"Não foi possível rolar a página: {exc}")

    def type_text(self, selector: str, text: str):
        with self._lock:
            try:
                self._ensure()
                self._page.locator(selector).first.fill(str(text))
                return self._result(True, "Texto digitado com sucesso.", url=self._page.url, title=self._page.title())
            except Exception as exc:
                return self._result(False, f"Não foi possível digitar: {exc}")

    def page_info(self):
        with self._lock:
            self._ensure()
            return self._result(True, "Informações da página obtidas.", url=self._page.url, title=self._page.title())

    def close(self):
        with self._lock:
            try:
                if self._context:
                    self._context.close()
            finally:
                self._context = None
                self._page = None
                if self._pw:
                    self._pw.stop()
                    self._pw = None


_browser = None
_browser_lock = threading.Lock()


def get_browser(profile_dir: Path) -> BrowserController:
    global _browser
    with _browser_lock:
        if _browser is None:
            _browser = BrowserController(profile_dir)
        return _browser
