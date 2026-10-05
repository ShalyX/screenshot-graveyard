---
title: "Screenshot Graveyard: I built my friend a memory for the screenshots they never revisit"
published: false
description: "A searchable memory layer for forgotten screenshots, built with RapidOCR and Gemma 3."
tags: devchallenge, weekendchallenge, hf26challenge, gemma
---

# Screenshot Graveyard: I built my friend a memory for the screenshots they never revisit

Hacktoberfest Weekend Challenge: Build for a Friend Submission 🤝

This is a submission for the Hacktoberfest Weekend Challenge: Build for a Friend.

## What I Built

My friend saves everything as a screenshot.

A restaurant they want to try. A product they might buy. A tweet worth rereading. A design idea. A technical explanation. A recommendation somebody sent them.

At the moment they save it, the screenshot feels useful.

A week later, it is just one more image buried in the camera roll.

That was the problem I wanted to solve this weekend.

I built **Screenshot Graveyard**, a tiny memory layer for screenshots.

You drop in screenshots. It reads what is actually visible, turns each image into a compact memory of what it is and why you probably saved it, and stores that memory alongside the original screenshot in the browser.

Later you can ask something vague like:

> what was that private access thing I saved?

You do not need the filename. You do not need the exact title. You do not even need to remember the proper noun.

Screenshot Graveyard searches the recovered memories, finds the likely match, and brings the original screenshot back up.

That is the whole product.

I deliberately kept it narrow because the useful moment is not “AI organized my photos.”

It is:

> I remembered the idea, but not enough of it to find the screenshot — and the app found it anyway.

The friend I built it for is real, but I am keeping them anonymous. Their screenshot habit is the product brief.

## Demo

Live app:

https://screenshot-graveyard.vercel.app

Try this flow:

1. Drop in a few screenshots.
2. Let Screenshot Graveyard recover a memory for each one.
3. Search with a fuzzy description instead of the exact words in the screenshot.
4. Open the result and confirm it surfaced the original image.

The archive itself lives in the browser using IndexedDB.

There is no account and no server-side screenshot library.

## Code

https://github.com/ShalyX/screenshot-graveyard

The repository includes the Flask backend, browser UI, RapidOCR pipeline, Gemma integration, structured-output recovery logic, IndexedDB archive, and smoke tests.

## How I Built It

The final architecture looks simple:

```text
Screenshot
   ↓
RapidOCR
   ↓
literal text
   ↓
Gemma 3 4B
   ↓
title / summary / why saved / entities / search terms
   ↓
IndexedDB
   ↓
fuzzy natural-language retrieval
   ↓
original screenshot
```

It did not start that way.

### Version one: let Gemma do everything

My first version ran **Gemma 3 4B locally through Ollama**.

I sent the screenshot to Gemma and asked it to both read the image and understand it.

Architecturally, that was beautifully simple.

In practice, it exposed two problems immediately.

The first was speed. Vision inference on my machine took long enough that a small batch felt broken even when it was technically still processing.

The second problem was worse because it attacked trust.

A screenshot contained the name:

> VEYRA

Gemma read it as:

> VETRA

Then the retrieval layer repeated the same wrong spelling back to me.

The app had successfully remembered the screenshot — incorrectly.

For this product, that is not a cosmetic bug.

If Screenshot Graveyard quietly changes the names inside the things you saved, it is manufacturing memories instead of recovering them.

### The architecture changed because of one typo

That VEYRA → VETRA failure made the separation of responsibilities obvious.

An LLM is useful for questions like:

- What is this screenshot about?
- Why might somebody have saved it?
- Which future query should retrieve it?
- Does this fuzzy question refer to this memory?

It should not be the only authority for:

- exact product names
- usernames
- acronyms
- project names
- visible quoted text

So I split the pipeline.

**RapidOCR owns literal text. Gemma owns meaning.**

For text-heavy screenshots, RapidOCR first extracts the on-screen text. That transcript is then sent to Gemma with an explicit rule: distinctive names and proper nouns are evidence, not material to “improve.”

I also added a small grounding pass. If Gemma produces a suspicious near-match to a distinctive OCR token, the stored title is corrected back toward the literal evidence.

If OCR finds very little useful text, the system falls back to Gemma's multimodal image understanding.

That gave me a much better division of labor:

```text
OCR: what does the screenshot literally say?
Gemma: what does it mean to this person?
```

### Gemma creates a memory, not just a caption

Each screenshot becomes a small structured record:

```json
{
  "title": "...",
  "category": "ideas",
  "summary": "...",
  "whySaved": "...",
  "entities": ["..."],
  "searchTerms": ["..."]
}
```

The field I care about most is `whySaved`.

Generic image classification can tell me there is a restaurant menu in a screenshot.

Screenshot Graveyard is trying to reconstruct something closer to intent:

> You probably saved this because you wanted to compare this ramen place later.

That makes the archive searchable by the future thought, not only by the pixels.

### Retrieval is deliberately small

I did not add a vector database.

When you search, the browser sends Gemma a compact catalog of recovered metadata — not every original image again.

Gemma ranks plausible matches and returns screenshot IDs with short reasons.

The browser then resolves those IDs back to the original screenshot already stored in IndexedDB.

That means the retrieval loop is:

```text
vague memory → semantic match → original evidence
```

not:

```text
vague memory → generated answer that replaces the screenshot
```

The screenshot remains the source of truth.

### I had to make structured output fail gracefully too

Dense screenshots exposed another model failure mode: Gemma occasionally returned useful content wrapped in slightly malformed JSON.

The first implementation treated that as a total failure.

That was silly.

The server now handles common structured-output mistakes such as code fences, trailing commas, and truncated closing brackets. If a response is still unusable, it retries once with a stricter instruction.

Batch processing is also incremental. If screenshot 4 of 5 fails, the first three recovered memories remain visible instead of the whole interface looking stuck.

For a weekend app, those boring failure states mattered more than adding another feature.

### From Ollama to hosted Gemma

The original build was fully local: Gemma ran through Ollama.

That made the privacy story strong, but it created a judging problem. A live demo should not depend on my laptop staying online, and local vision inference was too slow on my hardware anyway.

So for the submitted version, I moved the same Gemma family to **Hugging Face Inference Providers**, currently serving `google/gemma-3-4b-it`, and deployed the app on Vercel.

The browser archive is still local.

The hosted backend does not maintain a screenshot database. It receives screenshot content or OCR-derived text for inference and returns the recovered memory.

I want to be explicit about that distinction: the submitted version is **not fully on-device** anymore.

## Why Does Open Innovation Matter?

The most useful thing about building this around Gemma was not a slogan about open models.

It was **portability**.

I started with Gemma 3 4B on my own machine through Ollama.

When local inference turned out to be the wrong deployment choice for judging, I did not have to redesign the product around a completely different intelligence layer.

I could keep the same model family and move inference to a hosted provider.

That mattered because the product's behavior had already been shaped around Gemma:

- structured screenshot memories
- semantic “why saved” reconstruction
- fuzzy retrieval
- multimodal fallback
- strict proper-noun handling

Open-weight AI let the model be part of the architecture instead of a dependency on one closed endpoint.

It also made the local version real, not hypothetical. I was able to run the same core intelligence on my own hardware while iterating on the product.

And the biggest lesson from the build was that “use AI for everything” was the wrong approach anyway.

Open tools gave me the freedom to compose the system:

**RapidOCR for literal evidence. Gemma for interpretation. Browser storage for memory.**

Each part does the job it is actually good at.

## What I Would Improve Next

I am intentionally not turning the weekend build into a giant photo-management platform.

The core loop I care about is still:

**save screenshot → recover meaning → forget the exact details → find it again**

The next improvements would stay inside that loop:

- stronger OCR grounding for unusual names
- faster batch ingestion
- duplicate screenshot detection
- an optional fully local mode for people who prefer on-device inference
- better confidence signals when the model is uncertain

No accounts. No social layer. No giant dashboard.

The graveyard only needs to remember.

## Prize Categories

### Best Use of Gemma

I am entering **Best Use of Gemma**.

Gemma is not an optional assistant attached to Screenshot Graveyard. It performs the semantic work that makes the product useful: turning screenshots into personal memories, reconstructing likely intent, handling multimodal fallback, and matching fuzzy future queries back to saved evidence.

The build also exercised one of the reasons an open-weight model matters in practice: I moved the same core model from local Ollama inference to hosted Hugging Face inference without changing the product into something else.

---

**Screenshot Graveyard**

Your camera roll remembers everything.

You remember none of it.
