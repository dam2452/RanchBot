

def get_no_username_provided_message() -> str:
    return "✏️ Podaj ID użytkownika.✏️"


def get_user_added_message(username: str) -> str:
    return f"✅ Dodano {username} do whitelisty.✅"


def get_log_user_added_message(username: str, executor: str) -> str:
    return f"User {username} added to whitelist by {executor}."

def get_no_user_id_provided_message() -> str:
    return "⚠️ Nie podano ID użytkownika.⚠️"

def get_user_not_found_message() -> str:
    return "❌ Nie można znaleźć użytkownika. Upewnij się, że użytkownik rozpoczął rozmowę z botem. ❌"
