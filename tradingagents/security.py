import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

load_dotenv()

class DataProtection:
    def __init__(self, key_env_var="ENCRYPTION_KEY"):
        """
        Initialize the DataProtection module.
        It tries to load an encryption key from the environment variable.
        If not found, it generates one (for temporary session use) or warns.
        """
        self.key = None
        key_str = os.getenv(key_env_var)
        
        if key_str:
            try:
                # If the key is already base64 encoded Fernet key
                self.key = key_str.encode()
            except Exception:
                pass
        
        if not self.key:
            # Fallback: Generate a key based on OPENAI_API_KEY if available (deterministic for the user)
            # OR generate a random one (which means data is lost if script restarts)
            # Here we derive a key from a secret if available to be persistent across runs
            secret = os.getenv("OPENAI_API_KEY", "default_secret_salt")
            salt = b'trading_agents_salt' # In production, use a random salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            self.key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))

        self.cipher_suite = Fernet(self.key)

    def encrypt_string(self, text: str) -> str:
        """Encrypts a string and returns the url-safe base64 encoded token."""
        if not text:
            return ""
        return self.cipher_suite.encrypt(text.encode()).decode()

    def decrypt_string(self, token: str) -> str:
        """Decrypts a token and returns the original string."""
        if not token:
            return ""
        try:
            return self.cipher_suite.decrypt(token.encode()).decode()
        except Exception as e:
            return f"[Decryption Failed: {str(e)}]"

    def encrypt_file(self, file_path: str):
        """Encrypts the content of a file in place."""
        if not os.path.exists(file_path):
            return
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        encrypted_data = self.cipher_suite.encrypt(data)
        
        with open(file_path, 'wb') as f:
            f.write(encrypted_data)

    def decrypt_file(self, file_path: str) -> bytes:
        """Reads and decrypts a file's content."""
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'rb') as f:
            encrypted_data = f.read()
            
        return self.cipher_suite.decrypt(encrypted_data)
