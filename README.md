# Screenshot Graveyard

Your camera roll remembers everything. You remember none of it.

Screenshot Graveyard turns forgotten screenshots into a searchable memory archive. It uses local OCR for literal text and Gemma 3 for semantic understanding and retrieval.

## What it does

1. Drop screenshots into the browser.
2. RapidOCR extracts literal text and preserves names/brands.
3. Gemma 3 turns that into a compact recovered memory.
4. Memories stay in the browser's IndexedDB.
5. Ask fuzzy questions like “what was that private access thing?” and retrieve the original screenshot.

## Stack

- Python HTTP server
- RapidOCR + ONNX Runtime
- Google Gemma 3 4B via Hugging Face Inference Providers
- Vanilla HTML/CSS/JS
- IndexedDB for the screenshot archive
- Render deployment blueprint

## Privacy

The archive is stored in your browser. Screenshot content is sent for AI inference; Screenshot Graveyard does not maintain a cloud screenshot library.

## Run locally

Create a Hugging Face token with Inference Providers access and accept the Gemma model terms.

### Windows

```powershell
$env:HF_TOKEN="hf_..."
.\run.ps1
```

### macOS / Linux

```bash
export HF_TOKEN="hf_..."
./run.sh
```

Then open `http://127.0.0.1:4173`.

## Environment

See `.env.example`.

## Hacktoberfest Weekend Challenge 2026

Built for the “Build for a Friend” weekend challenge.

Target categories:
- Best Use of Gemma
- Best Use of Render

See `JUDGE_NOTES.md` for a concise technical walkthrough and `SUBMISSION_DRAFT.md` for the DEV submission draft.
