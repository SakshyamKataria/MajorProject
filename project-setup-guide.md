# Environment Setup Guide — Meeting \& Lecture Intelligence Platform

Tailored for: Dell G15, RTX 3050 6GB, Windows. Follow in order — steps 5–9 (GPU stack) are the ones most likely to break, so do them in isolation before touching the project code.

\---

## 1\. Git

1. Download from https://git-scm.com/download/win and install with defaults.
2. Verify: `git --version`
3. Set your identity:

```
   git config --global user.name "Your Name"
   git config --global user.email "your@email.com"
   ```

4. Set up SSH or a personal access token for GitHub if you haven't already (needed to push to the team repo).

\---

## 2\. VS Code

1. Install from https://code.visualstudio.com/
2. Extensions to add: **Python**, **Pylance**, **ESLint**, **Prettier**, **Tailwind CSS IntelliSense**, **Docker** (if using Docker), **Thunder Client** (for testing API endpoints without leaving the editor).

\---

## 3\. Python 3.11 (installed alongside your existing 3.14 — do not remove 3.14)

1. Download the Python 3.11 installer from https://www.python.org/downloads/release/python-3119/ (or latest 3.11.x).
2. During install, check **"Add python.exe to PATH"** — but since you already have 3.14, you'll manage versions explicitly rather than relying on PATH order (step below handles this).
3. Verify both versions are accessible:

```
   py -3.11 --version
   py -3.14 --version
   ```

   `py` is the Windows launcher — it lets you pick the version per-command instead of fighting PATH order.

4. From now on, always create this project's virtual environment with `py -3.11`, never bare `python`.

\---

## 4\. Node.js LTS

1. Download the **LTS** version (not "Current") from https://nodejs.org/
2. Verify: `node --version` and `npm --version`
3. Optional but recommended for speed: `npm install -g pnpm`

\---

## 5\. NVIDIA driver check

1. Open **NVIDIA GeForce Experience** (or NVIDIA app) and check for driver updates — update if not current.
2. Verify your GPU is visible: open a terminal and run `nvidia-smi`. You should see your RTX 3050 listed along with a CUDA version in the top right — note that version number, it tells you the *maximum* CUDA version your driver supports.

\---

## 6\. CUDA Toolkit

1. faster-whisper (via CTranslate2) currently works best with **CUDA 12.x**. Confirm your driver (from step 5's `nvidia-smi` output) supports CUDA 12 — RTX 3050 laptops with a reasonably current driver will.
2. Download CUDA Toolkit 12.x from https://developer.nvidia.com/cuda-downloads — select Windows → your version → exe (local).
3. Install with default options.
4. Verify: `nvcc --version`

\---

## 7\. cuDNN (the step most people miss)

1. cuDNN requires a free NVIDIA Developer account — sign up at https://developer.nvidia.com/cudnn if you don't have one.
2. Download the **cuDNN version matching your CUDA 12.x install**.
3. Windows cuDNN ships as a zip of files you copy into your CUDA install directory (`bin`, `include`, `lib` folders) — follow NVIDIA's installation guide exactly; this isn't a normal installer.
4. There's no simple one-line verification for cuDNN alone — you'll confirm it works in step 9 when faster-whisper successfully loads on `cuda`.

\---

## 8\. ffmpeg

1. Download a Windows build from https://www.gyan.dev/ffmpeg/builds/ (the "essentials" build is enough).
2. Extract it somewhere permanent (e.g. `C:\\ffmpeg`), then add `C:\\ffmpeg\\bin` to your system PATH (System Properties → Environment Variables → Path → New).
3. Verify: open a **new** terminal window and run `ffmpeg -version`.

\---

## 9\. Verify the GPU stack end-to-end (do this before writing any app code)

1. Create a throwaway test folder and venv:

```
   py -3.11 -m venv test-env
   test-env\\Scripts\\activate
   pip install faster-whisper
   ```

2. Run a quick Python test:

```python
   from faster\_whisper import WhisperModel
   model = WhisperModel("small", device="cuda", compute\_type="int8")
   print("Loaded on GPU successfully")
   ```

3. If this prints without error, your CUDA/cuDNN setup is correct. If you get a CUDA/cuDNN-related error, it's almost always a version mismatch between CUDA, cuDNN, and the CTranslate2 build faster-whisper installed — check the faster-whisper GitHub README's "GPU" section for the exact compatible version pairing at the time you install, since these shift between releases.
4. Once confirmed, delete this test-env — you'll set up the real one in step 11.

\---

## 10\. Docker Desktop + WSL2 (optional — for local Postgres during dev)

1. Enable WSL2: open PowerShell as Administrator and run `wsl --install`. Reboot if prompted.
2. Check BIOS virtualization (Intel VT-x / AMD-V) is enabled if `wsl --install` complains — this is a BIOS setting, not a Windows one, so you may need to reboot into BIOS to check.
3. Install Docker Desktop from https://www.docker.com/products/docker-desktop/, select the WSL2 backend during setup.
4. Verify: `docker --version` and `docker run hello-world`.

You can skip this entirely and just use your Supabase project directly for dev if you'd rather not deal with WSL2 — Docker is for convenience, not a hard requirement for this project's architecture.

\---

## 11\. Backend project setup

1. In your project repo:

```
   py -3.11 -m venv venv
   venv\\Scripts\\activate
   ```

2. Install packages:

```
   pip install fastapi uvicorn\[standard] faster-whisper scikit-learn google-generativeai supabase python-dotenv pydantic
   ```

3. Create a `.env` file (and add it to `.gitignore` immediately, before it has real keys in it) for your Supabase URL/keys, Gemini API key, and R2 credentials.
4. Confirm the app boots: a minimal `main.py` with a FastAPI instance and `uvicorn main:app --reload`.

\---

## 12\. Frontend project setup

1. Scaffold:

```
   npm create vite@latest frontend -- --template react-ts
   cd frontend
   npm install
   ```

2. Add Tailwind: follow the official Vite+Tailwind guide (`npm install -D tailwindcss postcss autoprefixer` etc. — exact steps change occasionally, check https://tailwindcss.com/docs/guides/vite for the current install command).
3. Add shadcn/ui: `npx shadcn@latest init`, then add components as needed with `npx shadcn@latest add button` etc.
4. Add Framer Motion: `npm install framer-motion`
5. Confirm it runs: `npm run dev`

\---

## 13\. Cloud accounts (set up early so no team member is blocked waiting on credentials)

1. **Supabase** — https://supabase.com → new project → save the project URL and both the `anon` and `service\_role` keys → in the SQL editor, run `create extension if not exists vector;` to enable pgvector.
2. **Google AI Studio** — https://aistudio.google.com → get an API key for Gemini (free tier).
3. **Cloudflare R2** — https://dash.cloudflare.com → R2 → create a bucket → generate an S3-compatible API token (Access Key ID + Secret Access Key).
4. **GitHub** — create the team repo, add all 4 members as collaborators, set up a basic branch protection rule on `main` if you want one.
5. **Vercel** — https://vercel.com → connect your GitHub repo (can wait until the frontend has something worth deploying).
6. **Render** — https://render.com → connect your GitHub repo, create a **web service** (not a worker — remember, free tier doesn't support those) pointing at your backend (can also wait).

\---

## Suggested order to actually execute this

**Day 1:** Steps 1–4 (Git, VS Code, Python 3.11, Node) — quick, no surprises.
**Day 1–2:** Steps 5–9 (GPU stack) — do this in isolation, as its own task, before anyone touches app code. This is the one place things commonly go sideways, so budget real time for it and don't schedule it the night before a deadline.
**Day 2:** Steps 11–12 (backend + frontend scaffolds) — can happen in parallel across team members once GPU setup is confirmed working on at least one machine.
**Day 2 (parallel):** Step 13 (cloud accounts) — whoever owns backend/database should do this while others are scaffolding, so keys are ready when needed.
**Optional, anytime:** Step 10 (Docker/WSL2) — only if you decide you want local Postgres instead of hitting Supabase directly during dev.

