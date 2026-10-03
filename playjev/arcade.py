"""Loopback front page: evidence-linked scores, Jev game selection, one launch."""
import argparse
import asyncio
import json
import secrets
import os
import subprocess
import sys
import threading
import httpx
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from dotenv import load_dotenv
from .challenge import ROOT, GAMES, JevPlayer
from .runtime import registry
from .scoreboard import load_groups
from .transports import inference
from .progress import load as load_progress, next_target


def catalog(root=ROOT):
    entries=[]
    profiles=registry()
    for game in GAMES.values():
        candidates=[]
        for file in (root/'runs').rglob('challenge.json'):
            try:
                row=json.loads(file.read_text())
                if row['game']==game.id and (file.parent/'start.state').is_file() and Path(row['rom_path']).is_file() and Path(row['assets_path']).is_dir():
                    candidates.append((row['budget_frames'],file.parent))
            except (OSError,ValueError,KeyError):continue
        challenge=max(candidates,key=lambda item:item[0])[1] if candidates else None
        entries.append({'id':game.id,'title':game.id.replace('-',' ').title(),'goal':game.goal,
                        'available':game.id in profiles and challenge is not None,
                        'challenge':challenge,'terminal_note':profiles[game.id].terminal_note if game.id in profiles else 'continuous adapter pending'})
    return entries


class Arcade:
    def __init__(self,root=ROOT,provider='ollaya',model=None):
        self.root=Path(root);self.token=secrets.token_urlsafe(32)
        self.lock=threading.Lock();self.process=None;self.active=None;self.last_recommendation=None
        self.recommending=False
        self.provider=provider
        self.model,self.transport=inference(provider,model)
        self.inference_generation=0

    def configure_inference(self,provider,model=None):
        model,transport=inference(provider,model)
        if not isinstance(model,str) or not model or len(model)>200 or model.startswith('-'):
            raise ValueError('Invalid model name')
        with self.lock:
            self.provider,self.model,self.transport=provider,model,transport
            self.inference_generation+=1
            self.last_recommendation=None
        return {'provider':provider,'model':model,'applies_to':'next recommendation/attempt',
                'automatic_hosted_fallback':False,'inference_called':False}

    def scores(self):
        errors=[]
        groups=load_groups((p.parent for p in (self.root/'runs').rglob('summary.json')),errors=errors)
        result=[]
        for (game,challenge,mode),rows in groups.items():
            for r in rows:
                directory=Path(r['run'])
                try:relative=directory.relative_to(self.root/'runs').as_posix()
                except ValueError:continue
                result.append({'game':game,'challenge':challenge,'mode':mode,'run':relative,
                    'score':r['score'] if r['score_supported'] else None,'ranked':r['eligible'],
                    'reviewer':r.get('score_review',{}).get('reviewer','legacy'),'status':r['status'],
                    'seconds':r['game_frames']/60,'player':r['config'].get('player','unknown'),
                    'provider':r['config'].get('provider','jev' if (r['config'].get('model') or '').startswith('jev-') else 'unknown'),
                    'model':r['config'].get('model'),
                    'replay':f'/runs/{relative}/replay.html','hud':f'/runs/{relative}/{r.get("score_review",{}).get("evidence","final.png")}'})
        return result

    def state(self):
        with self.lock:
            active=dict(self.active) if self.active else None
            exit_code=self.process.poll() if self.process else None
            busy=self.process is not None and exit_code is None
            selected={'provider':self.provider,'model':self.model,'automatic_hosted_fallback':False}
            recommendation=self.last_recommendation
        if active:
            active['running']=busy
            active['exit_code']=exit_code
            active['phase']='starting' if busy else 'saved' if exit_code==0 else 'failed'
            phase_path=self.root/'runs'/active['run']/'process.json'
            if phase_path.is_file():
                try:
                    phase=json.loads(phase_path.read_text())
                    active['phase']=phase['phase'] if busy or phase['phase'] in ('saved','failed') else active['phase']
                    active['error']=phase.get('error')
                except (OSError,ValueError,KeyError,TypeError):pass
            path=self.root/'runs'/active['run']/'metrics.json'
            if path.is_file():
                try:active['metrics']=json.loads(path.read_text())
                except (OSError,ValueError):pass
        return {'games':[{k:v for k,v in e.items() if k!='challenge'} for e in catalog(self.root)],
                'scores':self.scores(),'active':active,'recommendation':recommendation,'inference':selected,
                'progress':load_progress(p.parent for p in (self.root/'runs').rglob('summary.json'))}

    def practice_target(self,game_id,increment):
        entry=next((e for e in catalog(self.root) if e['id']==game_id and e['available']),None)
        if not entry:raise ValueError('No available challenge for this game')
        metadata=json.loads((entry['challenge']/'challenge.json').read_text())
        progress=next((p for p in load_progress(r.parent for r in (self.root/'runs').rglob('summary.json'))
                       if p['game']==game_id and p['challenge_id']==metadata['challenge_id']),
                      {'game':game_id,'challenge_id':metadata['challenge_id'],'best_supported_score':None})
        target=next_target(progress,increment)
        directory=self.root/'runs'/'arcade-processes';directory.mkdir(parents=True,exist_ok=True)
        with (directory/'practice-targets.jsonl').open('a') as file:
            file.write(json.dumps({**target,'at':datetime.now(timezone.utc).isoformat()})+'\n')
        return target

    async def recommend(self,intent):
        options={e['id']:e['goal'] for e in catalog(self.root) if e['available']}
        options['wait']='Wait: no appropriate playable game, an attempt is running, or user wants to inspect scores first'
        if len(options)==1:
            return {'choice':'wait','reason':'No continuous game has a usable local challenge','source':'availability-check'}
        with self.lock:
            busy=self.process is not None and self.process.poll() is None
            model,transport,generation=self.model,self.transport,self.inference_generation
        if busy:
            return {'choice':'wait','readiness':'wait_active','confidence':None,'source':'single-attempt-code-guard'}
        state={'user_intent':intent,'session_running':busy,'games':self.state()['games'],
               'recent_results':self.scores()[-12:],'behavior':'Choose one visible attempt; never launch a batch, hide a reset, or claim a completed game from a timer.'}
        body={'model':model,'state':state,'questions':{
            'game':{'type':'choice','instructions':'Which available game should the visitor start next? Follow user_intent and choose only an available game. If session_running is true, or the user only wants score review, choose wait. Prefer Crackpots when continuing the latest new-game work.','criteria':options},
            'readiness':{'type':'choice','instructions':'Classify the current wait/start state from session_running, available games and user_intent. This is a readiness judgment, not a measurement of elapsed time.','criteria':{'ready':'An available game can be started after the visitor clicks Start','wait_active':'An attempt is already running; wait for Stop & save','wait_setup':'No requested game is available yet','review_scores':'The user wants to review evidence before playing'}}}}
        player=JevPlayer(model=model,transport=transport);response=await player.request(body)
        answer=player.validate_choice(response['answers']['game'],options)
        readiness=player.validate_choice(response['answers']['readiness'],body['questions']['readiness']['criteria'])
        record={'request':body,'response':response,'choice':answer['choice'],'confidence':answer['confidence'],
                'readiness':readiness['choice'],'at':datetime.now(timezone.utc).isoformat()}
        directory=self.root/'runs'/'arcade-processes';directory.mkdir(parents=True,exist_ok=True)
        with (directory/'navigation.jsonl').open('a') as file:file.write(json.dumps(record)+'\n')
        with self.lock:
            if generation!=self.inference_generation:
                return {'choice':'wait','readiness':'wait_setup','confidence':None,'source':'provider-changed-during-recommendation'}
            self.last_recommendation=record
        return record

    def start(self,game_id):
        entry=next((e for e in catalog(self.root) if e['id']==game_id and e['available']),None)
        if not entry:raise ValueError('Game is not available for continuous play')
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise ValueError('An attempt is already running; stop and save it first')
            if self.provider=='jev' and not os.environ.get('TYPESAFE_API_KEY'):
                raise ValueError('Hosted Jev requires a server-side TYPESAFE_API_KEY; use Ollaya CLI or configure it locally')
            name=f'arcade-{game_id}-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")}-{secrets.token_hex(3)}'
            out=self.root/'runs'/name
            logs=self.root/'runs'/'arcade-processes';logs.mkdir(parents=True,exist_ok=True)
            with (logs/f'{name}.log').open('w') as log:
                self.process=subprocess.Popen([sys.executable,'-m','playjev.live',str(entry['challenge']),
                    '--out',str(out),'--autostart','--stop-file',str(logs/f'{name}.stop.request'),
                    '--provider',self.provider,'--model',self.model],cwd=self.root,stdout=log,stderr=subprocess.STDOUT)
            self.active={'game':game_id,'run':name,'pid':self.process.pid,'provider':self.provider,'model':self.model,'started_at':datetime.now(timezone.utc).isoformat()}
            return self.active

    def stop(self):
        with self.lock:
            if not self.active or self.process.poll() is not None:raise ValueError('No active attempt')
            file=self.root/'runs'/'arcade-processes'/f'{self.active["run"]}.stop.request'
            file.write_text('User clicked Stop & save on the front page\n')
        return {'status':'stop-requested; waiting for score/video finalization'}


def handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass

        def send(self,value,status=200):
            try:
                data=json.dumps(value).encode();self.send_response(status)
                self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store')
                self.end_headers();self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass  # viewer closed/navigated away

        def safe_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')

        def do_GET(self):
            if not self.safe_host():return self.send({'error':'Host not allowed'},403)
            path=unquote(urlparse(self.path).path)
            try:
                if path=='/api/state':return self.send({**app.state(),'token':app.token})
                if path=='/':file=app.root/'games'/'arcade'/'index.html'
                elif path.startswith('/runs/'):
                    file=(app.root/path.lstrip('/')).resolve()
                    if not file.is_relative_to((app.root/'runs').resolve()) or file.suffix not in ('.html','.webm','.png'):
                        return self.send({'error':'Not found'},404)
                else:return self.send({'error':'Not found'},404)
                if not file.is_file():return self.send({'error':'Not found'},404)
                import mimetypes
                self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(file)[0] or 'application/octet-stream')
                self.send_header('Cache-Control','no-store');self.end_headers()
                with file.open('rb') as stream:
                    while chunk:=stream.read(65536):self.wfile.write(chunk)
            except (BrokenPipeError,ConnectionResetError):pass
            except (OSError,ValueError,KeyError) as exc:self.send({'error':str(exc)},500)

        def do_POST(self):
            if not self.safe_host() or self.headers.get('Origin')!=f'http://{self.headers.get("Host")}' or self.headers.get('X-Arcade-Token')!=app.token:
                return self.send({'error':'Origin or session token not allowed'},403)
            try:
                length=int(self.headers.get('Content-Length',0))
                if not 0<length<=8192:return self.send({'error':'Request size rejected'},413)
                body=json.loads(self.rfile.read(length))
                path=urlparse(self.path).path
                if path=='/api/recommend':
                    with app.lock:
                        if app.recommending:return self.send({'error':'Recommendation already pending'},409)
                        app.recommending=True
                    try:return self.send(asyncio.run(app.recommend(str(body.get('intent','Continue Crackpots'))[:1000])))
                    finally:
                        with app.lock:app.recommending=False
                if path=='/api/start':return self.send(app.start(body.get('game')),202)
                if path=='/api/stop':return self.send(app.stop(),202)
                if path=='/api/inference':return self.send(app.configure_inference(body.get('provider'),body.get('model')))
                if path=='/api/practice-target':return self.send(app.practice_target(body.get('game'),body.get('increment')))
                self.send({'error':'Not found'},404)
            except httpx.HTTPStatusError as exc:
                status=exc.response.status_code
                self.send({'error':f'Inference service returned HTTP {status}; no hidden retry',
                           'retry_after':exc.response.headers.get('Retry-After')},429 if status==429 else 503)
            except httpx.TimeoutException:self.send({'error':'Inference timed out; retry explicitly'},504)
            except (ValueError,KeyError,TypeError) as exc:self.send({'error':str(exc)},400)
            except Exception as exc:self.send({'error':f'{type(exc).__name__}: {exc}'},502)
    return Handler


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--open',action='store_true')
    parser.add_argument('--provider',choices=('ollaya','jev'),default='ollaya');parser.add_argument('--model')
    args=parser.parse_args();load_dotenv(ROOT.parent/'.env',override=False)
    app=Arcade(provider=args.provider,model=args.model);server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(app))
    print(f'Jev Arcade: http://127.0.0.1:{server.server_port}/',flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{server.server_port}/')
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
