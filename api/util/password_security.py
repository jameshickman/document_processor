"""
Securely store passwords in symetric encryption
"""
import base64
import uuid

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from sqlalchemy.orm import Session
from api.models.accounts import Account


class PasswordSecurity:
    def __init__(self, password_secret: str, password_salt: str):
        self.password_secret = password_secret
        self.password_salt = password_salt
        self._fernet = self._create_fernet()

    def _create_fernet(self) -> Fernet:
        """Create a Fernet cipher using the password secret."""
        # Use the password_secret as the base for key derivation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=str.encode(self.password_salt),  # Static salt for consistency
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password_secret.encode()))
        return Fernet(key)

    def encrypt_password(self, plain_password: str) -> str:
        """Encrypt a plain text password."""
        if not plain_password:
            return ""
        encrypted_bytes = self._fernet.encrypt(plain_password.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')

    def decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt an encrypted password."""
        if not encrypted_password:
            return ""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_password.encode('utf-8'))
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception:
            # If decryption fails, assume it's a plain text password
            return encrypted_password

    def is_encrypted(self, password: str) -> bool:
        """Check if a password is encrypted by attempting to decrypt it."""
        if not password:
            return False
        try:
            encrypted_bytes = base64.urlsafe_b64decode(password.encode('utf-8'))
            self._fernet.decrypt(encrypted_bytes)
            return True
        except Exception:
            return False


def get_password(db: Session, user_email: str, password_secret: str) -> (str, None):
    salt = str(uuid.uuid4())
    password_security = PasswordSecurity(password_secret, salt)
    user_info = db.query(Account).filter(Account.email == user_email).first()
    if user_info:
        if not user_info.password_encrypted:
            user_info.password_local = password_security.encrypt_password(user_info.password_local)
            user_info.password_encrypted = True
            user_info.password_salt = salt
            db.add(user_info)
            db.commit()
        return password_security.decrypt_password(user_info.password_local)
    return None
