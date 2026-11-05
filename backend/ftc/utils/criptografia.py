import base64

from cryptography.fernet import Fernet
from django.conf import settings
from django.utils.crypto import salted_hmac


def _fernet():
    chave = salted_hmac(
        'ftc.credenciais',
        'fernet',
        secret=settings.SECRET_KEY,
        algorithm='sha256',
    ).digest()
    return Fernet(base64.urlsafe_b64encode(chave))


def cifrar(valor: str) -> str:
    return _fernet().encrypt(valor.encode('utf-8')).decode('ascii')


def decifrar(valor: str) -> str:
    return _fernet().decrypt(valor.encode('ascii')).decode('utf-8')
