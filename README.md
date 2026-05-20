# Recipe App (MVP)

React (Vite) frontend + **FastAPI** (Python) API + **SQLite** database. **Video import:** paste a URL; the backend uses **yt-dlp** for metadata/captions, then either **Google Gemini** (optional AI, [Google AI Studio](https://aistudio.google.com/app/apikey) free tier) or **heuristic** text splitting to fill a draft you edit before saving.

## Authentication (design note)

| Approach | Verdict |
|----------|---------|
| **Client-only “auth”** (e.g. hiding UI with `localStorage` flags) | **Not** sufficient for a real API. Anyone can call your endpoints directly. |
| **Server-side auth** (sessions or signed JWTs validated on every request) | **Correct** when you have multiple users, saved data that must be private, or paid AI usage. |

**This MVP has no login** so you can ship UI + CRUD quickly. When you add accounts, store a **`user_id` on each recipe** (and optionally a `users` table) and require a **session cookie or `Authorization: Bearer` JWT** validated on every mutating route—never trust the client alone to decide who owns a row.

## Run locally

**Backend** (terminal 1):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then set GEMINI_API_KEY (required when using AI video extract)
uvicorn app.main:app --reload --port 8000
```

**Video import:** set **`GEMINI_API_KEY`** (or **`GOOGLE_API_KEY`**) in `backend/.env` when **`use_ai: true`** (default in the UI). Get a key at [Google AI Studio](https://aistudio.google.com/app/apikey). Optional: **`GEMINI_MODEL`** (default `gemini-2.0-flash`). Send **`use_ai: false`** on `POST /recipes/extract-from-video` to skip Gemini and use heuristics only (no API usage). See [Troubleshooting](#troubleshooting). Caption/description availability depends on the site and video; without text the endpoint returns `422`.

**YouTube “Sign in to confirm you’re not a bot”:** see [YouTube cookies (step by step)](#youtube-cookies-step-by-step) and [Troubleshooting](#troubleshooting).

**Frontend** (terminal 2):

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually `http://127.0.0.1:5173`). API docs: `http://127.0.0.1:8000/docs`.

## YouTube cookies (step by step)

YouTube often requires cookies so **yt-dlp** can read the page as a signed-in user. The backend reads **`backend/.env`** (restart **uvicorn** after every change).

**Pick one method.** If you set both `YTDLP_COOKIES_FILE` and `YTDLP_COOKIES_FROM_BROWSER`, the **cookie file wins**.

### Method A — Cookie file (good for sharing a path or running on a server)

1. In your normal browser, **log in to YouTube** (same Google account you use to watch videos).
2. Export a **Netscape / cookies.txt** file that includes **`youtube.com`** cookies. Official guidance: [How do I pass cookies to yt-dlp?](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp) and [Exporting YouTube cookies](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies). Many people use a browser add-on that exports **only** the sites you choose (export **youtube.com** only; avoid exporting your whole browser).
3. Create a folder **`backend/cookies/`** (this repo’s `.gitignore` ignores it so you do not commit secrets).
4. Save the file there, for example **`backend/cookies/youtube.txt`**.
5. Open **`backend/.env`** and add a line (no quotes needed unless the path has spaces):

   ```env
   YTDLP_COOKIES_FILE=cookies/youtube.txt
   ```

   Paths are relative to the **`backend/`** directory. You can instead use an **absolute** path to a file anywhere on disk.
6. **Stop** the backend (Ctrl+C) and start it again: `uvicorn app.main:app --reload --port 8000`.
7. In the app, try **Import from video** with a YouTube URL again.

**Security:** That file is a **session** for your Google/YouTube account. Do not commit it, do not paste it into chat, and restrict who can read the server disk.

### Method B — Read cookies from your browser (fastest on a dev laptop)

1. **Quit** the browser you will use (so the cookie database is not locked), **or** use a browser you are okay closing briefly.
2. Stay **logged in to YouTube** in that browser (e.g. Chrome).
3. Open **`backend/.env`** and add **one** line:

   - **Chrome (default profile):**

     ```env
     YTDLP_COOKIES_FROM_BROWSER=chrome
     ```

   - **Edge:**

     ```env
     YTDLP_COOKIES_FROM_BROWSER=edge
     ```

   - **Firefox** (replace with your profile folder name if yt-dlp cannot find the default):

     ```env
     YTDLP_COOKIES_FROM_BROWSER=firefox
     ```

     If you need a specific profile: `firefox:ProfileName` (see [yt-dlp `--cookies-from-browser`](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)).

4. **Restart uvicorn** (same as step 6 in Method A).
5. Try **Import from video** again.

If Method B fails (permissions, locked DB, wrong profile), use **Method A** instead.

### Troubleshooting

**Environment file location:** The backend loads **`RecipeAI/.env`** (next to this README) first, then **`backend/.env`**, so **values in `backend/.env` override the root file** for the same variable. Put secrets in **`backend/.env`** for predictable behavior.

**Gemini API key / invalid key:** Put **`GEMINI_API_KEY=...`** on one line in `backend/.env` ([Google AI Studio](https://aistudio.google.com/app/apikey)). **`GOOGLE_API_KEY`** is accepted as an alias. Restart uvicorn after edits.

**Gemini `429` / quotas:** The free tier has rate and usage caps. If `gemini-2.0-flash` shows `limit: 0`, set **`GEMINI_MODEL=gemini-2.0-flash-lite`** in `backend/.env`. By default the app **retries other models**, then **falls back to heuristic parsing** (`GEMINI_FALLBACK_ON_QUOTA=true`) instead of crashing. See [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

**YouTube still “Sign in to confirm you’re not a bot” with a cookie file:** (1) Run **`pip install -U yt-dlp`** in the same venv as the app. (2) Export a **new** `cookies.txt` while logged into YouTube in that browser (cookies expire). (3) Try **`YTDLP_COOKIES_FROM_BROWSER=chrome`** instead of a file. (4) Some accounts need extra steps (see [Exporting YouTube cookies](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies), including **PO token** guidance for hard cases). The app also rotates **player clients** (`android`, `web`, …) automatically for YouTube URLs; override with **`YTDLP_YOUTUBE_PLAYER_CLIENTS`** in `.env` or set it to **`off`** to disable that behavior.

## Stack

- **Frontend:** React 19 + TypeScript + Vite (responsive layout; works in mobile browsers).
- **Backend:** FastAPI + SQLAlchemy 2 + SQLite (`backend/recipes.db`).
- **Video → draft:** yt-dlp, then **optional** Gemini (`app/gemini_extract.py`; `use_ai` in `POST /recipes/extract-from-video`) or **heuristic** parsing (`app/heuristic_recipe.py`) when `use_ai` is false. Saving still uses `POST /recipes` after you edit the form.
