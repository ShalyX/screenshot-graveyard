#!/usr/bin/env python3
"""Smoke-test Screenshot Graveyard against the fake Hugging Face router."""
import base64, json, urllib.request
BASE='http://127.0.0.1:4173'
PNG_1X1='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl+XHkAAAAASUVORK5CYII='

def post(path, payload):
    req=urllib.request.Request(BASE+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    return json.loads(urllib.request.urlopen(req).read())

health=json.loads(urllib.request.urlopen(BASE+'/api/health').read())
assert health['ok'] and health['provider']=='huggingface' and health['modelReady'], health
memory=post('/api/analyze', {'image':'data:image/png;base64,'+PNG_1X1,'filename':'veyra.png'})['memory']
assert memory['title'].startswith('VEYRA'), memory
searched=post('/api/search', {'query':'what was that private access thing?', 'memories':[{'id':'m1', **memory}]})
assert searched['matches'][0]['id']=='m1', searched
print('PASS: health → HF analyze → search')
