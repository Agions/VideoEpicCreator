"""
API Key Manager for VideoEpicCreator

This module provides secure management of API keys and sensitive credentials
with encryption support and environment variable integration.
"""

import os
import base64
from pathlib import Path
from typing import Dict, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import json


class APIKeyManager:
    """Secure API key manager with encryption support"""
    
    def __init__(self, keys_file: Optional[Path] = None):
        self.keys_file = keys_file or Path.home() / ".videoepiccreator" / "api_keys.enc"
        self.keys_file.parent.mkdir(parents=True, exist_ok=True)
        self._keys: Dict[str, str] = {}
        self._encryption_key: Optional[bytes] = None
        self._cipher: Optional[Fernet] = None
        
        # Initialize encryption
        self._init_encryption()
        
        # Load existing keys
        self._load_keys()
    
    def _init_encryption(self):
        """Initialize encryption key and cipher"""
        # Try to get encryption key from environment
        key_b64 = os.getenv('VIDEOEPIC_ENCRYPTION_KEY')
        
        if key_b64:
            try:
                self._encryption_key = base64.b64decode(key_b64)
            except Exception:
                # Generate new key if environment key is invalid
                self._generate_encryption_key()
        else:
            # Generate new key
            self._generate_encryption_key()
        
        self._cipher = Fernet(self._encryption_key)
    
    def _generate_encryption_key(self):
        """Generate a new encryption key"""
        # Generate a random key
        self._encryption_key = Fernet.generate_key()
        
        # Store in environment variable for current session
        os.environ['VIDEOEPIC_ENCRYPTION_KEY'] = base64.b64encode(self._encryption_key).decode()
        
        # Note: In production, you might want to store this securely
        # This is just for demonstration purposes
        print(f"Generated new encryption key: {base64.b64encode(self._encryption_key).decode()}")
        print("Please set this as VIDEOEPIC_ENCRYPTION_KEY environment variable for persistence")
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt data"""
        if not self._cipher:
            raise RuntimeError("Encryption not initialized")
        return self._cipher.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data"""
        if not self._cipher:
            raise RuntimeError("Encryption not initialized")
        return self._cipher.decrypt(encrypted_data.encode()).decode()
    
    def _load_keys(self):
        """Load encrypted API keys from file"""
        if self.keys_file.exists():
            try:
                with open(self.keys_file, 'r', encoding='utf-8') as f:
                    encrypted_data = f.read().strip()
                
                if encrypted_data:
                    decrypted_data = self._decrypt_data(encrypted_data)
                    self._keys = json.loads(decrypted_data)
            except Exception as e:
                print(f"Warning: Failed to load API keys: {e}")
                self._keys = {}
        else:
            self._keys = {}
    
    def _save_keys(self):
        """Save encrypted API keys to file"""
        try:
            encrypted_data = self._encrypt_data(json.dumps(self._keys))
            with open(self.keys_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
        except Exception as e:
            print(f"Error saving API keys: {e}")
    
    def set_key(self, service: str, key: str, save: bool = True):
        """Set API key for a service"""
        if not service or not key:
            raise ValueError("Service name and key cannot be empty")
        
        # Check environment variable first
        env_var = f"{service.upper()}_API_KEY"
        env_key = os.getenv(env_var)
        
        if env_key:
            # Use environment variable value
            self._keys[service] = env_key
        else:
            # Store the provided key
            self._keys[service] = key
        
        if save:
            self._save_keys()
    
    def get_key(self, service: str) -> Optional[str]:
        """Get API key for a service"""
        # Check environment variable first
        env_var = f"{service.upper()}_API_KEY"
        env_key = os.getenv(env_var)
        
        if env_key:
            return env_key
        
        # Fall back to stored keys
        return self._keys.get(service)
    
    def remove_key(self, service: str, save: bool = True):
        """Remove API key for a service"""
        if service in self._keys:
            del self._keys[service]
            if save:
                self._save_keys()
    
    def list_services(self) -> List[str]:
        """List all services with stored keys"""
        return list(self._keys.keys())
    
    def has_key(self, service: str) -> bool:
        """Check if a service has an API key"""
        return self.get_key(service) is not None
    
    def validate_key(self, service: str) -> bool:
        """Validate if an API key is properly formatted"""
        key = self.get_key(service)
        if not key:
            return False
        
        # Basic validation based on service
        if service.lower() == 'openai':
            return key.startswith('sk-') and len(key) > 40
        elif service.lower() == 'qianwen':
            return len(key) > 20  # Basic length check
        elif service.lower() == 'anthropic':
            return key.startswith('sk-ant-') and len(key) > 40
        else:
            # Generic validation
            return len(key) > 10
    
    def get_key_info(self, service: str) -> Dict[str, str]:
        """Get information about an API key"""
        key = self.get_key(service)
        if not key:
            return {"exists": False, "valid": False}
        
        # Mask the key for security
        if len(key) > 8:
            masked_key = key[:4] + "*" * (len(key) - 8) + key[-4:]
        else:
            masked_key = "*" * len(key)
        
        return {
            "exists": True,
            "valid": self.validate_key(service),
            "masked_key": masked_key,
            "source": "environment" if os.getenv(f"{service.upper()}_API_KEY") else "stored"
        }
    
    def export_keys(self, export_path: Path, password: Optional[str] = None):
        """Export keys to a file with optional password protection"""
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        if password:
            # Create a new cipher with password-based key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'videoepic_salt',  # In production, use random salt
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            cipher = Fernet(key)
            
            encrypted_data = cipher.encrypt(json.dumps(self._keys).encode()).decode()
        else:
            encrypted_data = json.dumps(self._keys)
        
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(encrypted_data)
    
    def import_keys(self, import_path: Path, password: Optional[str] = None):
        """Import keys from a file with optional password protection"""
        if not import_path.exists():
            raise FileNotFoundError(f"Keys file not found: {import_path}")
        
        with open(import_path, 'r', encoding='utf-8') as f:
            encrypted_data = f.read().strip()
        
        if password:
            # Create cipher with password-based key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'videoepic_salt',  # In production, use random salt
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            cipher = Fernet(key)
            
            try:
                decrypted_data = cipher.decrypt(encrypted_data.encode()).decode()
            except Exception:
                raise ValueError("Invalid password or corrupted file")
        else:
            decrypted_data = encrypted_data
        
        # Merge with existing keys
        imported_keys = json.loads(decrypted_data)
        self._keys.update(imported_keys)
        self._save_keys()
    
    def clear_all_keys(self):
        """Clear all stored API keys"""
        self._keys.clear()
        if self.keys_file.exists():
            self.keys_file.unlink()
    
    def rotate_encryption_key(self, new_key: Optional[bytes] = None):
        """Rotate encryption key and re-encrypt all data"""
        if new_key:
            self._encryption_key = new_key
        else:
            self._generate_encryption_key()
        
        self._cipher = Fernet(self._encryption_key)
        self._save_keys()
    
    def get_security_info(self) -> Dict[str, any]:
        """Get security information about the key manager"""
        return {
            "encryption_enabled": self._cipher is not None,
            "keys_file_exists": self.keys_file.exists(),
            "keys_file_path": str(self.keys_file),
            "stored_services": len(self._keys),
            "environment_keys": self._get_environment_keys()
        }
    
    def _get_environment_keys(self) -> List[str]:
        """Get list of API keys available from environment variables"""
        env_keys = []
        for key, value in os.environ.items():
            if key.endswith('_API_KEY'):
                service = key[:-9]  # Remove '_API_KEY' suffix
                env_keys.append(service.lower())
        return env_keys