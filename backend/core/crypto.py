import os
from cryptography.fernet import Fernet, InvalidToken

_fernet = Fernet(os.environ["ENCRYPTION_KEY"].encode())

def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    return _fernet.decrypt(value.encode()).decode()

def decrypt_or_plain(value: str) -> str:
    """暗号化済みなら復号、暗号化前の旧データ（平文）はそのまま返す"""
    try:
        return decrypt(value)
    except InvalidToken:
        return value
