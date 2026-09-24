# AI-Powered Meeting & Lecture Intelligence Platform

A platform that processes recorded meetings/lectures, generates structured summaries, extracts action items and decisions, provides a searchable meeting memory, and runs a custom ML sentence classifier.

## Repository Structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # API route definitions
│   │   ├── core/         # Configuration & app settings (Pydantic BaseSettings)
│   │   ├── models/       # Pydantic & database schema models
│   │   ├── services/     # Whisper STT, Gemini LLM, Supabase integration
│   │   └── ml/           # Custom TF-IDF + Logistic Regression classifier
│   ├── main.py           # FastAPI application entrypoint & health check
│   ├── requirements.txt  # Python backend dependencies
│   └── .env.example      # Environment variable template
├── frontend/
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── hooks/        # Custom React hooks
│   │   ├── lib/          # Utilities and helpers (cn helper, etc.)
│   │   ├── pages/        # Main view pages
│   │   ├── services/     # API & client services
│   │   ├── types/        # TypeScript interfaces & types
│   │   ├── App.tsx       # Root App component
│   │   └── index.css     # Tailwind styling
│   ├── package.json      # Frontend npm dependencies
│   ├── vite.config.ts    # Vite configuration with Tailwind CSS
│   └── .env.example      # Frontend environment template
├── .gitignore            # Git ignore configuration
└── README.md             # Project documentation
```

## ML Classifier Performance State

- **Architecture:** TF-IDF (unigram + bigrams, sublinear TF) + Logistic Regression (`class_weight='balanced'`).
- **Classes:** `['Action Item', 'Decision', 'Deadline', 'Discussion', 'Question']`.
- **Current Metrics (Held-Out 20% Split):**
  - **Deadline:** F1 = 0.93 (Precision = 1.00, Recall = 0.88)
  - **Decision:** F1 = 0.82 (Precision = 0.88, Recall = 0.78)
  - **Discussion:** F1 = 0.89 (Precision = 0.84, Recall = 0.95)
  - **Action Item:** F1 = 0.44 (Precision = 0.67, Recall = 0.33)
  - **Question:** F1 = 0.20 (Precision = 0.25, Recall = 0.17)
  - **Overall Accuracy:** 81.2%, **Macro-F1:** 0.66
- **Known Filter Considerations for Inference:**
  - *Action Item recall (0.33):* Since the ML classifier acts as a pre-filter before Gemini refinement, monitor whether action item candidates get inadvertently filtered out. Consider a lower confidence threshold or including high-probability secondary predictions when passing candidates to Gemini.

## Getting Started

### 1. Backend Setup

```bash
cd backend
py -3.11 -m venv venv
# Windows:
venv\Scripts\activate

# Install dependencies:
pip install -r requirements.txt

# Create .env from template:
cp .env.example .env

# Run FastAPI server:
uvicorn main:app --reload --port 8000
```
Backend health endpoint will be available at: [http://localhost:8000/health](http://localhost:8000/health) and interactive Swagger docs at [http://localhost:8000/docs](http://localhost:8000/docs).

### 2. Frontend Setup

```bash
cd frontend
npm install

# Create .env from template:
cp .env.example .env

# Run development server:
npm run dev
```
Frontend development server will run at: [http://localhost:5173](http://localhost:5173).
