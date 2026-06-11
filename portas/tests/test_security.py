"""
Testes de segurança: autenticação, permissões, API REST e validações.
"""
from unittest.mock import Mock

from django.contrib.auth.models import User
from django.test import Client, TestCase

from portas.forms.configuracoes import _validate_logo_size


# ── Autenticação ─────────────────────────────────────────────────────────────

class AutenticacaoTests(TestCase):
    """Requisições sem login devem ser redirecionadas para /login/."""

    URLS_PROTEGIDAS = [
        "/pedidos/",
        "/perfis/",
        "/acabamentos/",
        "/clientes/",
        "/configuracoes/",
    ]

    def test_anonimo_redirecionado_para_login(self):
        client = Client()
        for url in self.URLS_PROTEGIDAS:
            with self.subTest(url=url):
                resp = client.get(url)
                self.assertIn(resp.status_code, [301, 302], f"{url} não redirecionou")
                self.assertIn("/login/", resp["Location"], f"{url} não aponta para /login/")


# ── Permissões staff-only ─────────────────────────────────────────────────────

class PermissoesStaffTests(TestCase):
    """Views restritas a staff bloqueiam usuários comuns e liberam staff."""

    URLS_STAFF = [
        "/configuracoes/",
        "/integracoes/bimer/",
        "/integracoes/assistente-ia/",
    ]

    def setUp(self):
        self.usuario_comum = User.objects.create_user("comum", password="pass")
        self.usuario_staff = User.objects.create_user("staff", password="pass", is_staff=True)

    def test_usuario_comum_bloqueado(self):
        self.client.login(username="comum", password="pass")
        for url in self.URLS_STAFF:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertNotEqual(resp.status_code, 200,
                                    f"{url} acessível por usuário comum (status {resp.status_code})")

    def test_staff_acessa_normalmente(self):
        self.client.login(username="staff", password="pass")
        for url in self.URLS_STAFF:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200,
                                 f"{url} bloqueada para staff (status {resp.status_code})")


# ── API REST ─────────────────────────────────────────────────────────────────

class DRFApiTests(TestCase):
    """Endpoints da API exigem autenticação (SessionAuthentication → 403 para anônimos)."""

    URLS_API = [
        "/api/v1/clientes/",
        "/api/v1/perfis/",
        "/api/v1/acabamentos/",
        "/api/v1/vidros/",
    ]

    def test_anonimo_recebe_403(self):
        client = Client()
        for url in self.URLS_API:
            with self.subTest(url=url):
                resp = client.get(url)
                self.assertEqual(resp.status_code, 403,
                                 f"{url} acessível sem autenticação (status {resp.status_code})")

    def test_autenticado_recebe_200(self):
        User.objects.create_user("apiuser", password="pass")
        self.client.login(username="apiuser", password="pass")
        for url in self.URLS_API:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200,
                                 f"{url} bloqueada para usuário autenticado (status {resp.status_code})")


# ── Validação do logo ─────────────────────────────────────────────────────────

class LogoValidacaoTests(TestCase):
    """Testa o validador de tamanho do logo (5 MB máx)."""

    def test_arquivo_grande_rejeitado(self):
        from django.core.exceptions import ValidationError
        arquivo = Mock()
        arquivo.size = 6 * 1024 * 1024  # 6 MB
        with self.assertRaises(ValidationError):
            _validate_logo_size(arquivo)

    def test_arquivo_no_limite_passa(self):
        arquivo = Mock()
        arquivo.size = 5 * 1024 * 1024  # exatamente 5 MB — deve passar
        _validate_logo_size(arquivo)

    def test_arquivo_pequeno_passa(self):
        arquivo = Mock()
        arquivo.size = 1 * 1024 * 1024  # 1 MB
        _validate_logo_size(arquivo)
