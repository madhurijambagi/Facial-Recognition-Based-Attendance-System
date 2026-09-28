from werkzeug.security import generate_password_hash, check_password_hash


def test_password_hash_roundtrip():
    hashed = generate_password_hash("Sup3rSecret!")
    assert hashed != "Sup3rSecret!"
    assert hashed.startswith(("pbkdf2:", "scrypt:"))
    assert check_password_hash(hashed, "Sup3rSecret!")


def test_password_hash_rejects_wrong_password():
    hashed = generate_password_hash("Sup3rSecret!")
    assert not check_password_hash(hashed, "wrong-password")
