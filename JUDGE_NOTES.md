# Judge Notes

## Fastest way to evaluate Screenshot Graveyard

1. Open the live app.
2. Drop 2–5 screenshots.
3. Wait for recovered memories to appear as each screenshot finishes.
4. Ask a fuzzy question that does **not** repeat the screenshot filename or exact title.
5. Confirm the matching original screenshot is surfaced.

Suggested query:

> what was that private access thing I saved?

## What to look for

- **Open-weight AI is core:** Gemma 3 4B creates semantic memories and ranks fuzzy retrieval matches.
- **Literal text is grounded:** RapidOCR reads exact on-screen text first, reducing model typos in names and acronyms.
- **The archive is browser-first:** originals and recovered memories live in IndexedDB; there is no account or cloud screenshot database.
- **Graceful failure:** one malformed model response or failed screenshot does not strand the entire batch.
- **Multimodal fallback:** text-heavy screenshots use OCR + text reasoning; text-light screenshots can fall back to Gemma vision.

## Privacy note

This hosted submission is not fully on-device. Screenshot content or OCR text is sent to Hugging Face Inference Providers for Gemma analysis. Screenshot Graveyard itself does not maintain a server-side screenshot archive.
