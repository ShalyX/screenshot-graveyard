#!/usr/bin/env python3
import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

class H(BaseHTTPRequestHandler):
    calls = 0
    def do_POST(self):
        n = int(self.headers.get('Content-Length', '0'))
        body = json.loads(self.rfile.read(n))
        assert self.headers.get('Authorization') == 'Bearer test-token'
        assert body['model'].startswith('google/gemma-3-4b-it')
        assert body['response_format']['type'] == 'json_schema'
        H.calls += 1
        messages = body['messages']
        content = messages[0]['content']
        prompt = content if isinstance(content, str) else content[0]['text']
        if 'SCREENSHOT CATALOG' in prompt:
            import re
            ids = re.findall(r'"id":\s*"([^"]+)"', prompt)
            result = {
                'matches': ([{'id': ids[0], 'score': 0.96, 'reason': 'The recovered memory matches the query.'}] if ids else []),
                'answer': 'I think this is it.'
            }
        else:
            result = {
                'title': 'VEYRA — Private Access',
                'category': 'ideas',
                'summary': 'A concept explaining VEYRA private access without credential exposure.',
                'whySaved': 'You probably saved this to revisit the private-access design.',
                'entities': ['VEYRA'],
                'searchTerms': ['private access', 'credential exposure', 'VEYRA']
            }
        raw = json.dumps({
            'id':'chatcmpl-test',
            'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(result)},'finish_reason':'stop'}]
        }).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def log_message(self, *args): pass

ThreadingHTTPServer(('127.0.0.1', 11435), H).serve_forever()
