import pytest

from paketscope.backup import decrypt_backup, encrypt_backup


def test_encrypted_backup_round_trip():
    rows = [{"name": "Browser", "version": "1.0", "source": "APT / dpkg"}]
    encrypted = encrypt_backup(rows, "a-unique-long-passphrase")
    assert b"Browser" not in encrypted
    assert decrypt_backup(encrypted, "a-unique-long-passphrase") == rows


def test_wrong_password_and_tampering_are_rejected():
    encrypted = encrypt_backup([{"name": "Editor"}], "a-unique-long-passphrase")
    with pytest.raises(ValueError, match="Kata sandi salah"):
        decrypt_backup(encrypted, "another-long-passphrase")
    changed = encrypted[:-1] + bytes([encrypted[-1] ^ 1])
    with pytest.raises(ValueError, match="Kata sandi salah"):
        decrypt_backup(changed, "a-unique-long-passphrase")


def test_short_passphrase_is_rejected():
    with pytest.raises(ValueError, match="minimal 12"):
        encrypt_backup([], "too-short")
