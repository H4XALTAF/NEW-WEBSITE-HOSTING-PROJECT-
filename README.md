# 🔴 H4X ALTAF HOSTING PLATFORM

**Premium Hosting Management Platform**

A modern hosting management website built with Python Flask, featuring user accounts, an admin panel, customizable themes, hosting plans, and website controls.

---

## 🚀 Features

- User Login & Registration
- Admin Panel
- Admin-Controlled User Accounts
- User Dashboard
- Hosting Management Interface
- Hosting Plans Management
- Balance & Transaction System
- Upload Management
- Website Theme Customization
- Maintenance Mode
- Registration Controls
- Website Content Management
- Red, Blue, Green & White Themes

---

## 📁 Project Structure

```text
H4X-ALTAF/
│
├── app.py
├── data.json
├── Procfile
├── README.md
├── requirements.txt
├── runtime.txt
│
└── templates/
    ├── index.html
    ├── landing.html
    ├── login.html
    ├── dashboard.html
    ├── maintenance.html
    └── server.html
```

---

## 🛠️ Requirements

- Python 3
- Flask
- Gunicorn

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ▶️ Run Locally

```bash
python app.py
```

---

## 🌐 Render Deployment

1. Upload the project to GitHub.
2. Connect your GitHub repository to Render.
3. Create a new Web Service.
4. Select Python as the environment.
5. Set the Start Command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
```

---

## 🔐 Environment Variables

Configure these in Render:

| Variable | Purpose |
|---|---|
| ADMIN_USERNAME | Admin login username |
| ADMIN_PASSWORD | Strong admin password |
| SECRET_KEY | Flask session security key |

Never publish these credentials.

---

## ⚙️ Data Storage

The initial version uses `data.json` for storing website data.

For persistent storage on Render, configure a persistent disk and use a suitable storage path.

---

## ⚠️ Important Notes

- Payment processing is not implemented yet.
- Actual hosting and server provisioning require additional backend development.
- Uploaded files must be validated and safely handled.
- JSON storage is intended for the initial version, not a multi-instance production setup.

---

## 👑 Project

**H4X ALTAF**

© 2026 H4X ALTAF. All Rights Reserved.
