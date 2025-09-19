#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import hashlib
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional


class EncryptionManager:
    """加密管理器 - 提供数据加密和解密功能"""

    def __init__(self, password: Optional[str] = None):
        """
        初始化加密管理器

        Args:
            password: 用于生成密钥的密码，如果为None则使用默认密码
        """
        if password is None:
            # 使用默认密码（实际应用中应该使用更安全的方式）
            password = "CineAIStudio_Default_Key_2024"

        self.password = password.encode()
        self._fernet = None

    def _get_fernet(self) -> Fernet:
        """获取Fernet实例"""
        if self._fernet is None:
            # 生成盐值
            salt = b'CineAIStudio_Salt_2024'  # 实际应用中应该使用随机盐值

            # 使用PBKDF2生成密钥
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.password))
            self._fernet = Fernet(key)

        return self._fernet

    def encrypt(self, data: str) -> str:
        """
        加密字符串数据

        Args:
            data: 要加密的字符串

        Returns:
            加密后的base64编码字符串
        """
        try:
            fernet = self._get_fernet()
            encrypted_data = fernet.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            raise EncryptionError(f"加密失败: {e}")

    def decrypt(self, encrypted_data: str) -> str:
        """
        解密字符串数据

        Args:
            encrypted_data: 加密的base64编码字符串

        Returns:
            解密后的原始字符串
        """
        try:
            fernet = self._get_fernet()
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            raise EncryptionError(f"解密失败: {e}")

    def encrypt_file(self, file_path: str, output_path: str):
        """
        加密文件

        Args:
            file_path: 要加密的文件路径
            output_path: 加密后的文件输出路径
        """
        try:
            with open(file_path, 'rb') as file:
                file_data = file.read()

            fernet = self._get_fernet()
            encrypted_data = fernet.encrypt(file_data)

            with open(output_path, 'wb') as file:
                file.write(encrypted_data)

        except Exception as e:
            raise EncryptionError(f"文件加密失败: {e}")

    def decrypt_file(self, encrypted_file_path: str, output_path: str):
        """
        解密文件

        Args:
            encrypted_file_path: 加密的文件路径
            output_path: 解密后的文件输出路径
        """
        try:
            with open(encrypted_file_path, 'rb') as file:
                encrypted_data = file.read()

            fernet = self._get_fernet()
            decrypted_data = fernet.decrypt(encrypted_data)

            with open(output_path, 'wb') as file:
                file.write(decrypted_data)

        except Exception as e:
            raise EncryptionError(f"文件解密失败: {e}")

    def generate_hash(self, data: str) -> str:
        """
        生成数据的SHA256哈希值

        Args:
            data: 要哈希的数据

        Returns:
            十六进制哈希字符串
        """
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def verify_hash(self, data: str, hash_value: str) -> bool:
        """
        验证数据的哈希值

        Args:
            data: 原始数据
            hash_value: 要验证的哈希值

        Returns:
            验证结果
        """
        return self.generate_hash(data) == hash_value


class EncryptionError(Exception):
    """加密相关错误"""
    pass


def mask_sensitive_data(data: str, show_chars: int = 4) -> str:
    """
    掩码敏感数据显示

    Args:
        data: 敏感数据
        show_chars: 显示的字符数（前后各显示的字符数）

    Returns:
        掩码后的字符串
    """
    if not data:
        return ""

    if len(data) <= show_chars * 2:
        return "*" * len(data)

    return data[:show_chars] + "*" * (len(data) - show_chars * 2) + data[-show_chars:]


def generate_secure_token(length: int = 32) -> str:
    """
    生成安全令牌

    Args:
        length: 令牌长度

    Returns:
        随机令牌字符串
    """
    return base64.urlsafe_b64encode(os.urandom(length)).decode('utf-8')[:length]


def validate_api_key_format(provider: str, api_key: str) -> bool:
    """
    验证API密钥格式

    Args:
        provider: 提供商名称
        api_key: API密钥

    Returns:
        验证结果
    """
    if not api_key or not api_key.strip():
        return False

    key = api_key.strip()

    # OpenAI格式验证
    if provider.lower() in ['openai', 'chatgpt']:
        return key.startswith('sk-') and len(key) > 20

    # 通义千问格式验证
    elif provider.lower() in ['qianwen', '通义千问']:
        return len(key) > 10 and key.replace('-', '').replace('_', '').isalnum()

    # 文心一言格式验证
    elif provider.lower() in ['wenxin', '文心一言']:
        return len(key) > 10 and key.replace('-', '').replace('_', '').isalnum()

    # 其他提供商的基础验证
    else:
        return len(key) > 5


# 全局加密管理器实例
_global_encryption_manager = None


def get_encryption_manager(password: Optional[str] = None) -> EncryptionManager:
    """
    获取全局加密管理器实例

    Args:
        password: 密码（仅在首次调用时有效）

    Returns:
        加密管理器实例
    """
    global _global_encryption_manager

    if _global_encryption_manager is None:
        _global_encryption_manager = EncryptionManager(password)

    return _global_encryption_manager


# 便捷函数
def encrypt_string(data: str, password: Optional[str] = None) -> str:
    """加密字符串的便捷函数"""
    manager = get_encryption_manager(password)
    return manager.encrypt(data)


def decrypt_string(encrypted_data: str, password: Optional[str] = None) -> str:
    """解密字符串的便捷函数"""
    manager = get_encryption_manager(password)
    return manager.decrypt(encrypted_data)
