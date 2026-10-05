import base64, json, os, re, tempfile, threading, urllib.error, urllib.request
from difflib import SequenceMatcher
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
HF_URL = os.getenv("HF_BASE_URL", "https://router.huggingface.co/v1/chat/completions")
HF_MODEL = os.getenv("HF_MODEL", "google/gemma-3-4b-it:deepinfra")
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
OCR = None
OCR_LOCK = threading.Lock()

MEMORY_SCHEMA = {
    "type":"object","additionalProperties":False,
    "required":["title","category","summary","whySaved","entities","searchTerms"],
    "properties":{
        "title":{"type":"string"},
        "category":{"type":"string","enum":["places","things","ideas","read-later","useful","mystery"]},
        "summary":{"type":"string"},
        "whySaved":{"type":"string"},
        "entities":{"type":"array","items":{"type":"string"},"maxItems":8},
        "searchTerms":{"type":"array","items":{"type":"string"},"maxItems":10}
    }
}
SEARCH_SCHEMA = {
    "type":"object","additionalProperties":False,"required":["matches","answer"],
    "properties":{
        "matches":{"type":"array","maxItems":5,"items":{
            "type":"object","additionalProperties":False,"required":["id","score","reason"],
            "properties":{"id":{"type":"string"},"score":{"type":"number"},"reason":{"type":"string"}}
        }},
        "answer":{"type":"string"}
    }
}

def parse_json(text):
    text = str(text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I|re.S).strip()
    start, end = text.find("{"), text.rfind("}")
    candidate = text[start:end+1] if start >= 0 and end > start else text
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    for raw in (candidate, _balance(candidate)):
        try:
            out = json.loads(raw)
            if isinstance(out, dict): return out
        except Exception:
            pass
    raise RuntimeError("Gemma returned invalid structured output.")

def _balance(s):
    stack=[]; ins=False; esc=False
    for ch in s:
        if ins:
            if esc: esc=False
            elif ch=="\\": esc=True
            elif ch=='"': ins=False
            continue
        if ch=='"': ins=True
        elif ch in "[{": stack.append(ch)
        elif ch=="}" and stack and stack[-1]=="{": stack.pop()
        elif ch=="]" and stack and stack[-1]=="[": stack.pop()
    if ins: s += '"'
    while stack:
        s += "}" if stack.pop()=="{" else "]"
    return re.sub(r",\s*([}\]])", r"\1", s)

def hf_chat(messages, schema, name, max_tokens=320):
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN is not configured.")
    payload = json.dumps({
        "model": HF_MODEL,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        "response_format":{"type":"json_schema","json_schema":{"name":name,"schema":schema,"strict":True}}
    }).encode()
    req = urllib.request.Request(HF_URL, data=payload, headers={
        "Content-Type":"application/json","Authorization":f"Bearer {HF_TOKEN}"
    }, method="POST")
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                body = json.loads(res.read().decode())
            content = (body.get("choices") or [{}])[0].get("message",{}).get("content","")
            return parse_json(content)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            if e.code in (401,403):
                raise RuntimeError("Hugging Face rejected HF_TOKEN or Gemma access.")
            if e.code in (429,502,503,504) and attempt == 0:
                continue
            raise RuntimeError(f"Hugging Face inference failed ({e.code}).")
        except Exception as e:
            if attempt == 0 and "invalid structured" in str(e).lower():
                continue
            if isinstance(e, RuntimeError): raise
            raise RuntimeError(f"Inference failed: {e}")
    raise RuntimeError("Inference failed.")

def ocr_text(image_bytes):
    global OCR
    try:
        if OCR is None:
            from rapidocr import RapidOCR
            OCR = RapidOCR()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(image_bytes); path=f.name
        try:
            with OCR_LOCK:
                result = OCR(path)
        finally:
            try: os.unlink(path)
            except OSError: pass
        txts = list(getattr(result,"txts",None) or [])
        scores = list(getattr(result,"scores",None) or [])
        lines=[]
        for i,t in enumerate(txts[:140]):
            t=str(t or "").strip()
            score=float(scores[i]) if i < len(scores) else 0
            if t and score >= .58: lines.append(t)
        return "\n".join(lines)[:9000]
    except Exception as e:
        print("[OCR fallback]", e)
        return ""

def ground_title(title, transcript):
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", transcript)
    if not words: return title
    out=title
    for token in re.findall(r"\b[A-Z][A-Z0-9_-]{2,}\b", title):
        if token in words: continue
        best=max(words, key=lambda w: SequenceMatcher(None,token.lower(),w.lower()).ratio())
        if SequenceMatcher(None,token.lower(),best.lower()).ratio() >= .78:
            out=re.sub(rf"\b{re.escape(token)}\b", best, out)
    return out

def normalize_memory(m, transcript):
    cat=m.get("category","mystery")
    if cat not in {"places","things","ideas","read-later","useful","mystery"}: cat="mystery"
    title=str(m.get("title") or "Recovered screenshot").strip()[:120]
    title=ground_title(title, transcript)
    return {
        "title":title,
        "category":cat,
        "summary":str(m.get("summary") or "Recovered from this screenshot.").strip()[:360],
        "whySaved":str(m.get("whySaved") or "You probably saved this to revisit later.").strip()[:360],
        "entities":[str(x)[:100] for x in (m.get("entities") or [])[:8]],
        "searchTerms":[str(x)[:100] for x in (m.get("searchTerms") or [])[:10]],
        "visibleText":[x for x in transcript.splitlines()[:24]]
    }

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify(ok=True, provider="huggingface", model=HF_MODEL, modelReady=bool(HF_TOKEN))

@app.get("/api/_selftest")
def selftest():
    try:
        schema={"type":"object","additionalProperties":False,"required":["ok","word"],"properties":{"ok":{"type":"boolean"},"word":{"type":"string"}}}
        probe=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl+XHkAAAAASUVORK5CYII=")
        ocr_text(probe)
        result=hf_chat([{"role":"user","content":"Return JSON with ok=true and word=graveyard."}],schema,"deployment_selftest",40)
        return jsonify(result, ocrInitialized=(OCR is not None))
    except Exception as e:
        return jsonify(error=str(e)),503

@app.post("/api/analyze")
def analyze():
    try:
        data=request.get_json(force=True)
        image=str(data.get("image",""))
        filename=str(data.get("filename","screenshot"))[:160]
        if "," in image: image=image.split(",",1)[1]
        raw=base64.b64decode(image, validate=True)
        transcript=ocr_text(raw)
        categories="places for venues/travel; things for products; ideas for creative/technical ideas; read-later for articles/posts; useful for practical reference; mystery if unclear."
        if len(transcript) >= 35:
            prompt=f"""You turn saved screenshots into useful personal memories.
Literal OCR below is authoritative. Preserve names, brands, handles, acronyms and quoted phrases EXACTLY; never autocorrect unfamiliar names.
Filename: {filename}
Categories: {categories}
OCR:
---
{transcript}
---
Return a semantic title (not filename), one-sentence summary, one-sentence whySaved, sparse entities and searchTerms. Do not invent unsupported facts."""
            messages=[{"role":"user","content":prompt}]
            mode="ocr+text"
        else:
            prompt=f"""Analyze this intentionally saved screenshot as a future memory.
Categories: {categories}
Preserve visible names exactly. If unsure about a proper noun, omit it instead of guessing.
Return a semantic title, one-sentence summary, one-sentence whySaved, sparse entities and searchTerms."""
            messages=[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+image}}]}]
            mode="vision-fallback"
        result=hf_chat(messages,MEMORY_SCHEMA,"screenshot_memory",360)
        memory=normalize_memory(result,transcript)
        memory["analysisMode"]=mode
        return jsonify(memory=memory, analysisMode=mode)
    except Exception as e:
        return jsonify(error=str(e)), 503

@app.post("/api/search")
def search():
    try:
        data=request.get_json(force=True)
        query=str(data.get("query","")).strip()[:500]
        memories=data.get("memories") or []
        if not query or not memories: return jsonify(error="Add memories and ask a question first."),400
        compact=[{k:m.get(k) for k in ("id","title","category","summary","whySaved","visibleText","entities","searchTerms")} for m in memories[:200]]
        prompt=f"""Retrieve screenshots from a personal archive.
Rank only plausible matches. Never invent IDs. Reproduce stored proper nouns exactly.
If nothing matches, return an empty matches list.

USER QUERY:
{query}

SCREENSHOT CATALOG:
{json.dumps(compact,ensure_ascii=False)}"""
        result=hf_chat([{"role":"user","content":prompt}],SEARCH_SCHEMA,"graveyard_search",320)
        valid={str(m.get("id")) for m in compact}
        result["matches"]=[m for m in result.get("matches",[]) if str(m.get("id")) in valid]
        return jsonify(result)
    except Exception as e:
        return jsonify(error=str(e)), 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","4173")))
