# NewsHub — Local Setup with pgAdmin 4 (PostgreSQL) on Windows

## Tech used (short)
Backend: Python + Django 5.2 + Django REST Framework · Database: PostgreSQL (pgAdmin 4) · Frontend: HTML5 + Bootstrap 5 + CSS + JavaScript (Fetch API) · Background: Celery + Redis (local par eager mode chalega) · Server: Gunicorn (production) / Django dev server (local)

## Step 1 — PostgreSQL + pgAdmin 4 install karo
1. https://www.postgresql.org/download/windows/ se PostgreSQL 16/17 install karo. Install ke time superuser (postgres) ka password yaad rakhna — wahi pgAdmin login hai.
2. pgAdmin 4 kholo → password dalo → Servers → PostgreSQL → right-click Databases → Create → Database:
   - Database name: `newshub`
   - Owner: `postgres`
   - Save.
3. (Optional, recommended) Ek alag user banao: pgAdmin me Login/Group Roles → Create:
   - Name: `newshub_user`, Password tab me ek password set karo, Privileges me "Can login" ON.
   - Phir `newshub` database → Properties → Privileges me is user ko ALL do. (Ya seedha postgres user use kar sakte ho.)

## Step 2 — Project setup (PowerShell)
```powershell
cd C:\path\to\newsverify-ai
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```
## Step 3 — .env file me apna database lagao
`.env` kholo aur ye line apne pgAdmin wale database se set karo:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/newshub
```
(agar alag user banaya hai: `postgresql://newshub_user:YOUR_PASSWORD@localhost:5432/newshub`)
DEBUG=True local ke liye rakho.

## Step 4 — Database tables + data (ek hi baar)
```powershell
python manage.py migrate
python manage.py seed_sources
python manage.py fetch_news
python manage.py createsuperuser
```
`createsuperuser` se apna admin account banao — yahi /admin/ login hai.

## Step 5 — Site chalao
```powershell
python manage.py runserver
```
Browser: http://127.0.0.1:8000/ (site) · http://127.0.0.1:8000/admin/ (admin)

## pgAdmin 4 me data kaise dekhe
pgAdmin → Servers → PostgreSQL → Databases → newshub → Schemas → public → Tables.
`news_newsarticle` par right-click → View/Edit Data → All Rows. Yahi se articles, sources (`sources_newssource`), verification reports sab dikhenge.

## Daily use
- Nayi news: `python manage.py fetch_news` (ya Celery beat schedule hourly)
- Verify: fetch ke saath auto-verify hota hai; manual: `python manage.py verify_news --limit 20`
- Tests: `python manage.py test`

## Optional API keys (.env me, chat me kabhi mat bhejna)
- `GEMINI_API_KEY` — Google AI Studio ki free key: brief aur achha LLM likhega.
- `GOOGLE_FACTCHECK_API_KEY` — Google Cloud ki key: Google Fact Check se verification strong hoga.
Dono na ho to bhi site chalti hai (local brief + cross-source verification).
