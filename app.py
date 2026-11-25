import os
import json
import secrets
import threading
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================================
# H4X ALTAF HOSTING PLATFORM
# ==========================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY", secrets.token_hex(32)
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=86400
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(TEMPLATE_DIR, exist_ok=True)

data_lock = threading.RLock()


# ==========================================
# DEFAULT DATA
# ==========================================

DEFAULT_DATA = {
    "users": {},
    "settings": {
        "site_name": "H4X ALTAF",
        "tagline": "PREMIUM HOSTING PLATFORM",
        "maintenance": False,
        "maintenance_message": "We are improving your experience. Please come back soon.",
        "registration_enabled": True,

        "theme": {
            "primary": "#ff2525",
            "secondary": "#850000",
            "background": "#080808",
            "text": "#ffffff",
            "accent": "#ff5555"
        },

        "content": {
            "home_title": "WELCOME TO H4X ALTAF",
            "home_description": "Your premium hosting platform.",
            "dashboard_title": "MY DASHBOARD",
            "login_title": "WELCOME BACK",
            "support_text": "Contact our support team for help.",
            "footer_text": "ALL RIGHTS RESERVED."
        },

        "plans": [
            {
                "id": "basic",
                "name": "Basic Hosting",
                "price": 49,
                "description": "For small projects",
                "enabled": True
            },
            {
                "id": "premium",
                "name": "Premium Hosting",
                "price": 99,
                "description": "For advanced projects",
                "enabled": True
            },
            {
                "id": "pro",
                "name": "Pro Hosting",
                "price": 199,
                "description": "For professional projects",
                "enabled": True
            }
        ]
    },
    "transactions": [],
    "created_at": None
}


# ==========================================
# JSON DATABASE
# ==========================================

def save_data(data):
    temp_file = DATA_FILE + ".tmp"

    with data_lock:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        os.replace(temp_file, DATA_FILE)


def load_data():
    with data_lock:
        if not os.path.exists(DATA_FILE):
            data = DEFAULT_DATA.copy()
            data["created_at"] = datetime.now(timezone.utc).isoformat()
            save_data(data)
            return data

        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Restore missing default settings after updates
            for key, value in DEFAULT_DATA.items():
                if key not in data:
                    data[key] = value

            for key, value in DEFAULT_DATA["settings"].items():
                if key not in data["settings"]:
                    data["settings"][key] = value

            for key, value in DEFAULT_DATA["settings"]["theme"].items():
                data["settings"]["theme"].setdefault(key, value)

            for key, value in DEFAULT_DATA["settings"]["content"].items():
                data["settings"]["content"].setdefault(key, value)

            return data

        except (json.JSONDecodeError, OSError):
            raise RuntimeError(
                "data.json is damaged or unreadable. Restore a valid backup."
            )


def update_data(callback):
    with data_lock:
        data = load_data()
        callback(data)
        save_data(data)
        return data


# ==========================================
# ADMIN BOOTSTRAP
# ==========================================

def get_admin_credentials():
    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")

    if not username or not password:
        return None, None

    return username, password


# ==========================================
# SECURITY / AUTHENTICATION
# ==========================================

def user_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))

        data = load_data()
        user = data["users"].get(session["user"])

        if not user or not user.get("active", True):
            session.clear()
            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))

        return func(*args, **kwargs)

    return wrapper


def current_user():
    username = session.get("user")
    if not username:
        return None

    return load_data()["users"].get(username)


# ==========================================
# TEMPLATE SETTINGS
# ==========================================

@app.context_processor
def inject_site_settings():
    data = load_data()
    return {
        "site": data["settings"],
        "current_user": current_user(),
        "is_admin": bool(session.get("admin"))
    }


# ==========================================
# MAINTENANCE CONTROL
# ==========================================

@app.before_request
def maintenance_check():
    allowed = (
        "admin_login",
        "admin_panel",
        "admin_logout",
        "login",
        "logout",
        "static"
    )

    if request.endpoint in allowed:
        return None

    data = load_data()

    if data["settings"].get("maintenance") and not session.get("admin"):
        return render_template(
            "maintenance.html",
            maintenance_message=data["settings"].get(
                "maintenance_message", "We will be back soon."
            )
        ), 503


# ==========================================
# PUBLIC PAGES
# ==========================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/landing")
def landing():
    return render_template("landing.html")


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if session.get("user"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        # Form only sends email + password
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        username_input = request.form.get("username", "").strip()

        data = load_data()
        user = None
        username = None

        # Prefer email lookup (main path from form)
        if email:
            for uname, u in data["users"].items():
                if u.get("email", "").lower() == email:
                    user = u
                    username = uname
                    break

        # Fallback to username if provided
        if not user and username_input:
            user = data["users"].get(username_input)
            if user:
                username = username_input

        if user and user.get("active", True):
            if check_password_hash(user["password"], password):
                session.clear()
                session["user"] = username
                session.permanent = True
                return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


# ==========================================
# REGISTER
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    data = load_data()

    if not data["settings"].get("registration_enabled", True):
        abort(403)

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or len(name) < 2:
            flash("Please enter your full name.", "error")
            return render_template("login.html")

        if not email or "@" not in email:
            flash("Please enter a valid email address.", "error")
            return render_template("login.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return render_template("login.html")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("login.html")

        # Auto-generate username from email local-part
        base = email.split("@")[0].lower()
        base = "".join(c if c.isalnum() or c == "_" else "_" for c in base)
        base = base.strip("_") or "user"
        if len(base) < 3:
            base = (base + "user")[:8]
        if len(base) > 30:
            base = base[:30]

        def create_user(db):
            if any(u.get("email") == email for u in db["users"].values()):
                raise ValueError("Email already registered.")

            username = base
            counter = 1
            while username in db["users"]:
                suffix = str(counter)
                username = (base[:30 - len(suffix)] + suffix)
                counter += 1

            db["users"][username] = {
                "username": username,
                "name": name,
                "email": email,
                "password": generate_password_hash(password),
                "active": True,
                "balance": 0,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

        try:
            update_data(create_user)
            flash("Account created successfully. Please login with your email.", "success")
            return redirect(url_for("login"))

        except ValueError as e:
            flash(str(e), "error")

    return render_template("login.html")


# ==========================================
# USER DASHBOARD
# ==========================================

@app.route("/dashboard")
@user_required
def dashboard():
    return render_template("dashboard.html")


# ==========================================
# SERVER PAGE
# ==========================================

@app.route("/server")
@user_required
def server():
    return render_template("server.html")


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==========================================
# ADMIN LOGIN
# ==========================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if session.get("admin"):
        return redirect(url_for("admin_panel"))

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        admin_username, admin_password = get_admin_credentials()

        if (
            admin_username
            and secrets.compare_digest(username, admin_username)
            and secrets.compare_digest(password, admin_password)
        ):
            session.clear()
            session["admin"] = True
            session.permanent = True
            return redirect(url_for("admin_panel"))

        flash("Invalid admin credentials.", "error")

    return """
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>H4X ALTAF Admin Login</title>
    <style>
    *{box-sizing:border-box}
    body{background:#080808;color:white;font-family:Arial;
    display:grid;place-items:center;min-height:100vh;padding:20px}
    form{width:100%;max-width:380px;background:#141010;
    border:1px solid #632020;border-radius:15px;padding:30px}
    h2{color:#ff2929;text-align:center}
    input,button{width:100%;padding:14px;margin-top:15px;
    border-radius:7px;border:1px solid #522020;background:#080808;color:white}
    button{background:#b50000;font-weight:bold;cursor:pointer}
    </style></head>
    <body><form method="POST">
    <h2>H4X ALTAF ADMIN</h2>
    <input name="username" placeholder="Admin Username" required>
    <input name="password" type="password" placeholder="Admin Password" required>
    <button>ADMIN LOGIN</button>
    </form></body></html>
    """


# ==========================================
# ADMIN PANEL
# ==========================================

@app.route("/admin")
@admin_required
def admin_panel():

    data = load_data()
    settings = data["settings"]

    users_html = ""

    for username, user in data["users"].items():
        status = "Active" if user.get("active", True) else "Disabled"

        users_html += f"""
        <tr>
        <td>{username}</td>
        <td>{user.get('email', '')}</td>
        <td>{status}</td>
        <td>
        <form method="POST" action="/admin/user/status">
        <input type="hidden" name="username" value="{username}">
        <button name="action" value="toggle">Toggle</button>
        </form>
        <form method="POST" action="/admin/user/delete">
        <input type="hidden" name="username" value="{username}">
        <button class="danger">Delete</button>
        </form>
        </td></tr>
        """

    plans_json = json.dumps(settings.get("plans", []), indent=2)
    content_json = json.dumps(settings.get("content", {}), indent=2)

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>H4X ALTAF | Admin Panel</title>
    <style>
    *{{box-sizing:border-box}}
    body{{margin:0;background:#080808;color:white;font-family:Arial,sans-serif}}
    header{{padding:22px;background:#120909;border-bottom:1px solid #551b1b}}
    header h2{{color:#ff2929;margin:0}}
    main{{max-width:1100px;margin:auto;padding:20px}}
    .card{{background:#121010;border:1px solid #382020;
    border-radius:12px;padding:20px;margin:20px 0;overflow-x:auto}}
    h3{{color:#ff4545;margin-top:0}}
    input,textarea,select{{width:100%;padding:12px;margin:8px 0 15px;
    background:#080808;border:1px solid #462020;color:white;border-radius:7px}}
    button,.btn{{display:inline-block;padding:11px 16px;
    background:#bd1111;color:white;border:0;border-radius:7px;
    cursor:pointer;font-weight:bold;text-decoration:none;margin:3px}}
    .danger{{background:#570d0d}}
    table{{width:100%;border-collapse:collapse;min-width:550px}}
    td,th{{padding:12px;border-bottom:1px solid #332020;text-align:left;font-size:12px}}
    label{{font-size:12px;color:#bbb}}
    .grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:15px}}
    .check{{width:auto}}
    @media(max-width:600px){{.grid{{grid-template-columns:1fr}}main{{padding:12px}}}}
    </style></head>
    <body>
    <header><h2>H4X ALTAF | ADMIN PANEL</h2>
    <p>Complete Website Control Center</p>
    <a class="btn" href="/admin/logout">Logout</a></header>
    <main>

    <div class="card">
    <h3>Website Settings</h3>
    <form method="POST" action="/admin/settings">
    <label>Website Name</label>
    <input name="site_name" value="{settings.get('site_name','')}">
    <label>Tagline</label>
    <input name="tagline" value="{settings.get('tagline','')}">
    <label>Primary Color</label>
    <input type="color" name="primary" value="{settings['theme']['primary']}">
    <label>Secondary Color</label>
    <input type="color" name="secondary" value="{settings['theme']['secondary']}">
    <label>Background Color</label>
    <input type="color" name="background" value="{settings['theme']['background']}">
    <label>Text Color</label>
    <input type="color" name="text" value="{settings['theme']['text']}">
    <label>Accent Color</label>
    <input type="color" name="accent" value="{settings['theme']['accent']}">
    <button>Save Website Settings</button>
    </form>
    </div>

    <div class="card">
    <h3>Website Content Editor</h3>
    <form method="POST" action="/admin/content">
    <label>Edit website text (JSON)</label>
    <textarea name="content" rows="12">{content_json}</textarea>
    <button>Save All Text</button>
    </form>
    </div>

    <div class="card">
    <h3>Hosting Plans & Prices</h3>
    <form method="POST" action="/admin/plans">
    <label>Edit plans and prices (JSON)</label>
    <textarea name="plans" rows="15">{plans_json}</textarea>
    <button>Save Plans</button>
    </form>
    </div>

    <div class="card">
    <h3>Create User Account</h3>
    <form method="POST" action="/admin/user/create">
    <div class="grid">
    <div><label>Username</label><input name="username" required></div>
    <div><label>Full Name</label><input name="name"></div>
    <div><label>Email</label><input type="email" name="email" required></div>
    <div><label>Password</label><input type="password" name="password" minlength="8" required></div>
    </div>
    <button>Create User</button>
    </form>
    </div>

    <div class="card">
    <h3>User Management ({len(data['users'])} users)</h3>
    <table><tr><th>Username</th><th>Email</th><th>Status</th><th>Actions</th></tr>
    {users_html}
    </table>
    </div>

    <div class="card">
    <h3>Website Controls</h3>
    <form method="POST" action="/admin/controls">
    <label><input class="check" type="checkbox" name="maintenance"
    {'checked' if settings.get('maintenance') else ''}> Maintenance Mode</label>
    <br>
    <label>Maintenance Message</label>
    <textarea name="maintenance_message" rows="3">{settings.get('maintenance_message','')}</textarea>
    <label><input class="check" type="checkbox" name="registration_enabled"
    {'checked' if settings.get('registration_enabled') else ''}> Allow Registration</label>
    <br><button>Save Controls</button>
    </form>
    </div>

    </main></body></html>
    """


# ==========================================
# ADMIN ACTIONS
# ==========================================

@app.route("/admin/settings", methods=["POST"])
@admin_required
def admin_settings():

    def change(db):
        s = db["settings"]
        s["site_name"] = request.form.get("site_name", "")[:100]
        s["tagline"] = request.form.get("tagline", "")[:200]

        for key in ("primary", "secondary", "background", "text", "accent"):
            value = request.form.get(key, "")
            if len(value) == 7 and value.startswith("#"):
                try:
                    int(value[1:], 16)
                    s["theme"][key] = value
                except ValueError:
                    pass

    update_data(change)
    flash("Website settings saved.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/content", methods=["POST"])
@admin_required
def admin_content():

    try:
        content = json.loads(request.form.get("content", "{}"))

        if not isinstance(content, dict):
            raise ValueError()

        if len(content) > 100:
            raise ValueError()

        clean = {
            str(k)[:80]: str(v)[:2000]
            for k, v in content.items()
        }

        update_data(lambda db: db["settings"].update({"content": clean}))

    except (ValueError, json.JSONDecodeError):
        flash("Invalid content JSON.", "error")

    return redirect(url_for("admin_panel"))


@app.route("/admin/plans", methods=["POST"])
@admin_required
def admin_plans():

    try:
        plans = json.loads(request.form.get("plans", "[]"))

        if not isinstance(plans, list) or len(plans) > 100:
            raise ValueError()

        clean = []

        for p in plans:
            if not isinstance(p, dict):
                raise ValueError()

            price = float(p.get("price", 0))

            if price < 0 or price > 10000000:
                raise ValueError()

            clean.append({
                "id": str(p.get("id", secrets.token_hex(4)))[:40],
                "name": str(p.get("name", "Hosting"))[:100],
                "price": price,
                "description": str(p.get("description", ""))[:500],
                "enabled": bool(p.get("enabled", True))
            })

        update_data(lambda db: db["settings"].update({"plans": clean}))
        flash("Hosting plans updated.", "success")

    except (ValueError, TypeError, json.JSONDecodeError):
        flash("Invalid plans JSON or price.", "error")

    return redirect(url_for("admin_panel"))


@app.route("/admin/controls", methods=["POST"])
@admin_required
def admin_controls():

    def change(db):
        db["settings"]["maintenance"] = "maintenance" in request.form
        db["settings"]["registration_enabled"] = (
            "registration_enabled" in request.form
        )
        db["settings"]["maintenance_message"] = (
            request.form.get("maintenance_message", "")[:1000]
        )

    update_data(change)
    flash("Website controls updated.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/user/create", methods=["POST"])
@admin_required
def admin_create_user():

    username = request.form.get("username", "").strip()
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if (
        len(username) < 3 or len(username) > 30
        or not username.replace("_", "").isalnum()
        or len(password) < 8 or not email
    ):
        flash("Invalid username, email or password.", "error")
        return redirect(url_for("admin_panel"))

    def create(db):
        if username in db["users"]:
            raise ValueError("Username already exists.")

        if any(u.get("email") == email for u in db["users"].values()):
            raise ValueError("Email already exists.")

        db["users"][username] = {
            "username": username,
            "name": name,
            "email": email,
            "password": generate_password_hash(password),
            "active": True,
            "balance": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    try:
        update_data(create)
        flash("User account created.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("admin_panel"))


@app.route("/admin/user/status", methods=["POST"])
@admin_required
def admin_user_status():

    username = request.form.get("username", "")

    def change(db):
        user = db["users"].get(username)
        if user:
            user["active"] = not user.get("active", True)

    update_data(change)
    return redirect(url_for("admin_panel"))


@app.route("/admin/user/delete", methods=["POST"])
@admin_required
def admin_user_delete():

    username = request.form.get("username", "")

    update_data(lambda db: db["users"].pop(username, None))

    if session.get("user") == username:
        session.clear()

    return redirect(url_for("admin_panel"))


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# ==========================================
# ERROR PAGES
# ==========================================

@app.errorhandler(403)
def forbidden(error):
    return "403 - Access Denied", 403


@app.errorhandler(404)
def not_found(error):
    return "404 - Page Not Found", 404


@app.errorhandler(500)
def server_error(error):
    return "500 - Internal Server Error", 500


# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":
    load_data()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
