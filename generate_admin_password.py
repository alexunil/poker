#!/usr/bin/env python3
"""
Admin-Passwort Hash Generator
Erzeugt einen bcrypt Hash für das Admin-Passwort
"""

from werkzeug.security import generate_password_hash
import getpass


def main():
    print("=" * 60)
    print("Admin-Passwort Hash Generator")
    print("=" * 60)
    print("\nDieser Hash wird in der .env Datei als ADMIN_PASSWORD_HASH gespeichert.\n")

    # Passwort eingeben (versteckt)
    password = getpass.getpass("Admin-Passwort eingeben: ")

    if not password:
        print("❌ Fehler: Passwort darf nicht leer sein")
        return

    # Bestätigung
    password_confirm = getpass.getpass("Passwort bestätigen: ")

    if password != password_confirm:
        print("❌ Fehler: Passwörter stimmen nicht überein")
        return

    # Hash generieren
    password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    print("\n" + "=" * 60)
    print("✅ Passwort-Hash erfolgreich generiert!")
    print("=" * 60)
    print("\nFüge folgende Zeile in deine .env Datei ein:\n")
    print(f"ADMIN_PASSWORD_HASH={password_hash}")
    print("\n" + "=" * 60)
    print("\nWichtig:")
    print("  1. Kopiere den Hash in die .env Datei")
    print("  2. Stelle sicher, dass .env NICHT in Git eingecheckt wird")
    print("  3. Bewahre das Passwort sicher auf")
    print("=" * 60)


if __name__ == "__main__":
    main()
