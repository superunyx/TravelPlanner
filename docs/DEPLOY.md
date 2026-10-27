# Deployment & Hosting Guide

Complete step-by-step instructions for deploying the **Personalized Travel Itinerary Planner** to production:
- **Backend API**: Render (Free Tier Web Service, Python runtime)
- **Frontend SPA**: Vercel (Vite preset with client-side SPA rewrites)
- **Database & Auth**: Hosted Supabase (Postgres + Auth + Row Level Security)

---

## 1. Supabase Setup (Database & Authentication)

1. **Create Project**:
   - Go to [Supabase](https://supabase.com) and create a new project.
   - Choose your preferred region.

2. **Execute Database Migration**:
   - Open **SQL Editor** in the Supabase Dashboard.
   - Open [supabase/migrations/001_init.sql](../supabase/migrations/001_init.sql), copy its contents, paste into the editor, and click **Run**.
   - This creates tables (`trips`, `itinerary_days`, `trip_members`), RLS policies, triggers, and helper functions.

3. **Retrieve Project Secrets**:
   - Navigate to **Project Settings -> API**:
     - `Project URL` (e.g. `https://xyzcompany.supabase.co`) -> `SUPABASE_URL`
     - `anon public` key -> `SUPABASE_ANON_KEY` / `VITE_SUPABASE_ANON_KEY`
     - `service_role secret` key -> `SUPABASE_SERVICE_ROLE_KEY` (Backend only, never expose to frontend)
     - `JWT Secret` -> `SUPABASE_JWT_SECRET` (Under JWT Settings)

4. **Configure Authentication URLs**:
   - In Supabase Dashboard, go to **Authentication -> URL Configuration**:
     - **Site URL**: `https://your-frontend-app.vercel.app`
     - **Redirect URLs**: Add both of the following:
       - `https://your-frontend-app.vercel.app/**`
       - `http://localhost:5173/**` (for local development)
   - *(Optional Google OAuth)*: Under **Authentication -> Providers -> Google**:
     - Enable Google and paste your Client ID & Client Secret from Google Cloud Console.
     - Authorized redirect URI in Google Cloud Console must be: `https://<your-project-id>.supabase.co/auth/v1/callback`

---

## 2. Backend Deployment on Render

Render's free tier spins down web services after 15 minutes of inactivity. The application includes a cold-start warmup banner on the frontend and a CLI warmup tool (`scripts/warmup.sh`).

1. **Connect Repo**:
   - In [Render Dashboard](https://dashboard.render.com), click **New + -> Web Service**.
   - Select your GitHub repository.

2. **Configure Service Details**:
   - **Name**: `travel-planner-api`
   - **Runtime**: `Python`
   - **Region**: Choose one close to your Supabase region (e.g., Oregon or Frankfurt)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`

3. **Configure Environment Variables**:
   Add the following variables under **Environment**:

   | Key | Example Value | Description |
   | :--- | :--- | :--- |
   | `ENV` | `production` | Enables startup validation and disables auto-reload |
   | `ALLOWED_ORIGINS` | `https://your-app.vercel.app,http://localhost:5173` | Comma-separated CORS origins |
   | `SUPABASE_URL` | `https://your-project.supabase.co` | Supabase API endpoint |
   | `SUPABASE_ANON_KEY` | `eyJhbG...` | Supabase anon key |
   | `SUPABASE_SERVICE_ROLE_KEY` | `eyJhbG...` | Supabase server-only service role key |
   | `SUPABASE_JWT_SECRET` | `your-supabase-jwt-secret-string` | JWT Secret used to verify HS256 tokens |
   | `AI_PROVIDER` | `gemini` | LLM Provider (`gemini`) |
   | `GEMINI_API_KEY` | `AIzaSy...` | Google Gemini API key |
   | `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
   | `MAX_DAILY_GENERATIONS` | `50` | Total daily generation cap protecting Gemini quota |
   | `DEMO_USER_ID` | `uuid-string` | (Optional) UUID of demo user to protect sample trips |

4. **Deploy**:
   - Click **Deploy Web Service**. Once deployed, copy your Render service URL (e.g., `https://travel-planner-api.onrender.com`).

---

## 3. Frontend Deployment on Vercel

1. **Import Project**:
   - In [Vercel Dashboard](https://vercel.com/new), import your repository.
   - Set **Root Directory** to `frontend`.
   - Framework preset will automatically detect **Vite**.

2. **Configure Environment Variables**:
   Add the following environment variables in the Vercel project settings:

   | Key | Example Value | Description |
   | :--- | :--- | :--- |
   | `VITE_API_URL` | `https://travel-planner-api.onrender.com` | Deployed backend Render URL |
   | `VITE_SUPABASE_URL` | `https://your-project.supabase.co` | Supabase project URL |
   | `VITE_SUPABASE_ANON_KEY` | `eyJhbG...` | Supabase public anon key |
   | `VITE_DEMO_EMAIL` | `demo@travelplanner.local` | Email prefilled by "Try demo account" button |
   | `VITE_DEMO_PASSWORD` | `DemoPlanner123!` | Password for demo account |

   > **Security Check**: Confirm that `SUPABASE_SERVICE_ROLE_KEY` and `GEMINI_API_KEY` are **never** added to Vercel or prefixed with `VITE_`. Only public keys are bundled in client assets.

3. **Deploy**:
   - Click **Deploy**. Vercel will build and assign your production domain (`https://your-app.vercel.app`).
   - The provided `frontend/vercel.json` automatically ensures all client-side paths (`/trips/:id`, `/trips/new`) route to `index.html` on page reload.

4. **Sync CORS on Render**:
   - Return to your Render dashboard for `travel-planner-api` and update `ALLOWED_ORIGINS` to include your new Vercel URL:
     `ALLOWED_ORIGINS=https://your-app.vercel.app`

---

## 4. Post-Deployment Verification

1. **Seed Demo Trips**:
   Run the seed script against your hosted Supabase instance to populate the demo user and sample trips:
   ```bash
   SUPABASE_URL="https://your-project.supabase.co" \
   SUPABASE_SERVICE_ROLE_KEY="eyJ..." \
   DEMO_EMAIL="demo@travelplanner.local" \
   DEMO_PASSWORD="DemoPlanner123!" \
   python scripts/seed_demo.py
   ```

2. **Run Production Smoke Test**:
   ```bash
   python scripts/smoke_test.py \
     --backend-url https://travel-planner-api.onrender.com \
     --frontend-url https://your-app.vercel.app \
     --email demo@travelplanner.local \
     --password DemoPlanner123! \
     --supabase-url https://your-project.supabase.co \
     --supabase-key eyJhbG...
   ```

3. **Pre-warm Cold Start**:
   ```bash
   ./scripts/warmup.sh https://travel-planner-api.onrender.com
   ```
