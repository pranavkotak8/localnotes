# Stand-in for Ollama's HTTP API. Deterministic: lets us verify what the app SENDS and handles what it GETS back.
# usage: python3 stub2.py PORT [bad]
import json, os, re, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
PORT=int(sys.argv[1]); BAD=len(sys.argv)>2 and sys.argv[2]=='bad'
def answer(prompt):
    if 'You sort short points' in prompt:
        if BAD: return "Sorry, I would rather not do that. Try writing it yourself."
        import re
        pts=[(int(m.group(1)),m.group(2)) for m in (re.match(r'^(\d+)\. (.*)$',l) for l in prompt.split('POINTS:\n',1)[1].split('\n')) if m]
        KEYS=[('deck','Work','Deck feedback'),('fund','Work','Fundraising'),('milk','Routines','Shopping'),('eggs','Routines','Shopping'),('trip','Journal','Trip'),('gym','Routines','Fitness')]
        out=[]
        for n,t in pts:
            low=t.lower(); topic,space='Other points',''
            for k,sp,tp in KEYS:
                if k in low: topic,space=tp,sp; break
            out.append({'n':n,'topic':topic,'space':space,'due':''})
        return "Here are the topics:\n```json\n"+json.dumps({'points':out})+"\n```"
    if 'Use ONLY the notes below' in prompt:
        if BAD: return "bad mode"
        titles=[l[len('Title: '):] for l in prompt.split('\n') if l.startswith('Title: ')]
        dates=[l[len('Date: '):] for l in prompt.split('\n') if l.startswith('Date: ')]
        return "Notes used: "+" | ".join(titles)+"\nDates: "+" | ".join(dates)
    return "stub answer: " + prompt[:40].replace("\n"," ")
class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Headers','Content-Type'); self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS')
    def _send(self,obj):
        b=json.dumps(obj).encode(); self.send_response(200); self._cors(); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(b)
    def do_OPTIONS(self): self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        if self.path=='/api/tags': self._send({'models':[{'name':'llama3.2:latest'}]})
        else: self.send_response(404); self._cors(); self.end_headers()
    def do_POST(self):
        n=int(self.headers.get('Content-Length',0)); req=json.loads(self.rfile.read(n) or b'{}')
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),f'stub_{PORT}_calls.log'),'a') as f: f.write(req.get('prompt','')[:200].replace('\n',' ')+'\n')
        self._send({'response':answer(req.get('prompt',''))})
    def log_message(self,*a): pass
HTTPServer(('127.0.0.1',PORT),H).serve_forever()
