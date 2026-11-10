# USIU CSE Library

A library management system for our class project, built with Django and plain HTML/CSS.

- **Students** create an account, wait for a librarian to approve it, then search books and request to borrow them.
- **Library admins** approve student accounts and borrow requests, manage book stock, mark books returned, and record fine payments.

---

## 1. First-time setup

You need **Python 3.12 or newer** (`python3 --version`) and **Git**.

```bash
git clone https://github.com/gachikinoti2026-dev/Lib_m_s.git
cd Lib_m_s
```

Create a virtual environment and install Django:

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Your terminal prompt should now start with `(.venv)`. Activate the virtual environment like this every time you open a new terminal for this project.

Create the database and your own librarian account:

```bash
python manage.py migrate
python manage.py createsuperuser
```

The database (`db.sqlite3`) is on your machine only and is never committed, so every teammate makes their own accounts and test books.

## 2. Run the app

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000 and stop the server with `Ctrl+C`.

## 3. Try the whole flow

1. **Add books.** Log in, choose **Library admin**, enter your superuser details, then go to **Stock** and click **+ Add book**.
2. **Register a student.** Open a private/incognito window, click **Create a student account** and fill in the form. Logging in now fails with "waiting for approval", as it should.
3. **Approve the student.** In the admin window, open **Dashboard**, find **Student account requests** and click **Approve**.
4. **Borrow a book.** Log in as the student (choose **Student**), go to **Find books** and click **Borrow**. The request shows as *Pending* under **My loans**.
5. **Approve the loan.** As admin, go to **Dashboard**, find **Borrow requests** and click **Approve**. The book is due in 14 days.
6. **Return the book.** Under **Books on loan**, click **Mark returned**. If it was late, the fine appears under **Unpaid fines**, where you click **Mark paid** once the student pays. A student with an unpaid fine can't borrow.

**Forgot password** links don't send real email. The email, including the reset link, is printed in the terminal running `runserver`.

To make another account a library admin: go to **Site admin** (top bar, superusers only), open **Members**, open the account, tick **Staff status** and save.

## 4. Working on the code together

Never work directly on `main`. For each piece of work:

```bash
git checkout main
git pull                                # get everyone's latest work
git checkout -b your-name/short-topic   # e.g. lee/home-page-layout
# ...make your changes, run the app, run the tests...
git add -A
git commit -m "Describe what you changed"
git push -u origin your-name/short-topic
```

Then open a **Pull Request** into `main` on GitHub and ask a teammate to review it before merging.

**Rules that keep the project working for everyone:**

- **Run the tests before you push:** `python manage.py test`. They should say `OK`.
- **If you change `library/models.py`**, run `python manage.py makemigrations` and commit the new file in `library/migrations/` together with your model change.
- **After pulling**, run `python manage.py migrate` in case someone added a migration.
- **Don't commit** `.venv/`, `db.sqlite3` or `__pycache__/`. `.gitignore` already skips them.
- **If you install a new package**, add it to `requirements.txt`.

## 5. Where things live

| What you want to change | File(s) |
|---|---|
| Page HTML (templates) | `library/templates/library/*.html`, login and password pages in `library/templates/registration/` |
| Shared layout: top bar, footer, logo | `library/templates/base.html`, `library/templates/_logo.html` |
| Colours, fonts, spacing | `library/static/library/style.css`. Colours are variables at the top (`--primary`, `--accent`, …) |
| Database tables (models) | `library/models.py`: `Member`, `Book`, `Loan`, `Announcement` |
| Form fields and validation | `library/forms.py` |
| Page logic and permissions | `library/views.py` |
| URLs | `library/urls.py` (app pages), `lib_m_s/urls.py` (login, admin) |
| Site admin screens | `library/admin.py` |
| Settings | `lib_m_s/settings.py` |
| Tests | `library/tests.py` |

Loan period and fine amount are `LOAN_DAYS` and `FINE_PER_DAY` at the top of `library/models.py`.

### Pages

| URL | Page | Who |
|---|---|---|
| `/accounts/login/` | Login with Student / Library admin choice | everyone |
| `/register/` | Student sign-up (needs admin approval) | everyone |
| `/` | Home: my loans, fines, announcements, new arrivals | students |
| `/books/` | Search and borrow | students |
| `/loans/` | My loans, due dates, fines | students |
| `/librarian/` | Dashboard: account requests, borrow requests, books on loan, unpaid fines | library admin |
| `/librarian/stock/` | Stock: in stock / not available, add, edit, delete books | library admin |
| `/admin/` | Site admin: members, announcements | superusers |

## 6. Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'django'` | Activate the virtual environment (step 1), then `pip install -r requirements.txt` |
| `no such table` or `no such column` | `python manage.py migrate` |
| Django won't install or says Python is too old | Install Python 3.12+ and recreate `.venv` |
| `Error: That port is already in use` | Another `runserver` is running. Stop it, or use `python manage.py runserver 8001` |
| PowerShell won't run `Activate.ps1` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once |
| Forgot your local admin password | `python manage.py changepassword <username>` |
| Want a fresh, empty database | Delete `db.sqlite3`, then `python manage.py migrate` and `createsuperuser` again |
