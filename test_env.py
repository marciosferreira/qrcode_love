from dotenv import load_dotenv
import os
load_dotenv()
key = os.getenv('AWS_ACCESS_KEY_ID')
secret = os.getenv('AWS_SECRET_ACCESS_KEY')
print(f"Key found: {bool(key)}")
print(f"Secret found: {bool(secret)}")
if key:
    print(f"Key length: {len(key)}")
    print(f"Key first char: {key[0]}")
if secret:
    print(f"Secret length: {len(secret)}")
