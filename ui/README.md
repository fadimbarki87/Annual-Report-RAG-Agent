# UI

This folder contains the React frontend for the annual-report RAG agent.

## What It Includes

- luxury dark landing/chat layout
- centered title and subtitle
- top-right portrait placeholder asset
- scrollable example-question explorer fed by the real 30-category benchmark bank
- chat composer that autofills from example questions and sends on `Enter`
- API-ready chat panel that renders answer text, resources, and evidence once the local API service is running

## Main Files

| File | Responsibility |
| --- | --- |
| `src/App.jsx` | Main page layout, question bank loading, chat state, and API calls. |
| `src/styles.css` | Black-and-silver visual system and responsive layout. |
| `public/category_question_bank.json` | Frontend copy of the benchmark question bank used for the example explorer. |
| `public/portrait-placeholder.svg` | Fallback portrait placeholder used if no real profile photo is present. |

## Run Locally

From the project root:

```powershell
cd C:\Users\hp\Downloads\rag_annual_reports\ui
npm install
npm run dev
```

Then open the local Vite URL shown in the terminal.

## Connect To The API

Start the backend API from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.app:app --reload
```

During local development Vite proxies `/api/*` requests to `http://127.0.0.1:8000`.

## Personal Photo

If you want to show your own photo in the hero, place one of these files in `ui/public`:

- `profile-photo.png`
- `profile-photo.jpg`
- `profile-photo.jpeg`

The UI will try those first and fall back to `portrait-placeholder.svg` if none exists.

## Notes

- The UI already works as a frontend shell even if the API is temporarily offline.
- Until the backend API is connected, the chat panel shows a graceful fallback message.
- I recommend using your own portrait plus text names for the five companies rather than a collage of official company logos.
