#!/usr/bin/env python3
"""
encrypt_env.py - تشفير ملف .env إلى .env.enc باستخدام AES-GCM
استخدام:
    python encrypt_env.py          # ينشئ مفتاحًا جديدًا ويشفر .env
    python encrypt_env.py --key KEY  # يستخدم مفتاحًا موجودًا
"""

import os
import sys
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

ENV_FILE = ".env"
ENCRYPTED_FILE = ".env.enc"
KEY_FILE = ".env.key"  # تخزين المفتاح (يمكن وضعه في مكان آمن)

def generate_key() -> bytes:
    """توليد مفتاح عشوائي 32 بايت (256 بت)"""
    return get_random_bytes(32)

def encrypt_file(key: bytes):
    """تشفير ملف .env إلى .env.enc باستخدام AES-GCM"""
    if not os.path.exists(ENV_FILE):
        print(f"❌ الملف {ENV_FILE} غير موجود!")
        sys.exit(1)

    with open(ENV_FILE, 'rb') as f:
        data = f.read()

    # توليد nonce عشوائي (12 بايت)
    nonce = get_random_bytes(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(data)

    # تخزين nonce + tag + ciphertext
    encrypted_data = nonce + tag + ciphertext

    with open(ENCRYPTED_FILE, 'wb') as f:
        f.write(encrypted_data)

    print(f"✅ تم تشفير {ENV_FILE} إلى {ENCRYPTED_FILE}")
    print(f"🔑 المفتاح (احتفظ به بأمان): {base64.b64encode(key).decode()}")

def main():
    # قراءة المفتاح من وسيط أو توليد مفتاح جديد
    key = None
    if len(sys.argv) > 1 and sys.argv[1] == '--key' and len(sys.argv) > 2:
        key = base64.b64decode(sys.argv[2].encode())
    elif os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'r') as f:
            key = base64.b64decode(f.read().strip())
    else:
        key = generate_key()
        with open(KEY_FILE, 'w') as f:
            f.write(base64.b64encode(key).decode())

    encrypt_file(key)

if __name__ == "__main__":
    main()
