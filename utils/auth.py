import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")


def ensure_users_file():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(USERS_FILE):
        default_users = [
            {
                "username": "hoangton",
                "password": "123",
                "role": "Admin",
                "department": "Management",
                "team": "General",
            }
        ]
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_users, f, indent=4, ensure_ascii=False)


def load_users():
    ensure_users_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)


def authenticate(username, password):
    users = load_users()
    for user in users:
        if user.get("username") == username and user.get("password") == password:
            fixed_user = dict(user)

            if "department" not in fixed_user:
                fixed_user["department"] = "Technical Support"

            if "team" not in fixed_user:
                fixed_user["team"] = "General"

            role_map = {
                "tech": "TS Junior",
                "techas": "TS Senior",
                "admin": "Admin",
                "sale": "Sale Staff",
                "saleadmin": "Sale Admin",
            }

            raw_role = str(fixed_user.get("role", "")).strip().lower()
            fixed_user["role"] = role_map.get(raw_role, fixed_user.get("role", ""))

            return fixed_user
    return None


def username_exists(username):
    users = load_users()
    return any(user.get("username", "").lower() == username.lower() for user in users)


def register_user(
    username, password, role="TS Junior", department="Technical Support", team="General"
):
    username = username.strip()
    password = password.strip()

    if not username or not password:
        return False, "Username và password không được để trống."

    if len(username) < 3:
        return False, "Username phải từ 3 ký tự trở lên."

    if len(password) < 3:
        return False, "Password phải từ 3 ký tự trở lên."

    if username_exists(username):
        return False, "Username đã tồn tại."

    users = load_users()

    users.append(
        {
            "username": username,
            "password": password,
            "role": role,
            "department": department,
            "team": team,
        }
    )

    save_users(users)

    return True, "Đăng ký thành công."


def change_user_password(username, old_password, new_password):
    users = load_users()

    for user in users:
        if user.get("username") == username:
            if user.get("password") != old_password:
                return False, "Mật khẩu cũ không đúng."

            if not new_password.strip():
                return False, "Mật khẩu mới không được để trống."

            user["password"] = new_password.strip()
            save_users(users)
            return True, "Đổi mật khẩu thành công."

    return False, "Không tìm thấy tài khoản."
