from string import ascii_letters, digits
import secrets

def safe_random_string(characters: str = ascii_letters + digits, length: int = 16) -> str:
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string