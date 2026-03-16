"""
Utilitários de criptografia para campos sensíveis no banco.

Usa Fernet (AES-128-CBC + HMAC-SHA256) com chave derivada do SECRET_KEY do Django.
Se a chave mudar, os valores criptografados ficam ilegíveis — o usuário deve
reconfigurar as credenciais afetadas (ex: senha do Bimer).

Para valores já em texto puro (ex: migração inicial), decrypt() retorna o valor
original sem falhar, permitindo transição suave.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    """Deriva chave Fernet de 32 bytes a partir do SECRET_KEY do Django."""
    from django.conf import settings
    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt(value: str) -> str:
    """Criptografa uma string. Retorna string vazia se value for vazio."""
    if not value:
        return value
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """
    Descriptografa uma string criptografada por encrypt().
    Se o valor não for um token Fernet válido (ex: texto puro legado),
    retorna o valor original — permite migração sem quebrar.
    """
    if not value:
        return value
    try:
        return _fernet().decrypt(value.encode()).decode()
    except (InvalidToken, Exception):
        return value  # valor legado em texto puro
