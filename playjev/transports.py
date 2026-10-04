"""Cancellable typed-judgment transports, independent of gameplay policies."""
import os
import asyncio
import json
import hashlib
import httpx
from datetime import datetime, timezone


HOSTED_CREDENTIALS=('TYPESAFE_API_KEY','JEV_API_KEY','OPENROUTER_API_KEY','OPENAI_API_KEY',
                    'ANTHROPIC_API_KEY','GH_TOKEN','GITHUB_TOKEN')


def local_environment():
    return {k:v for k,v in os.environ.items() if k not in HOSTED_CREDENTIALS}


def safety_report(exc):
    text=str(exc).lower()
    kind=('allocation-limit' if 'allocate memory' in text or 'gpu allocation' in text else
          'timeout' if isinstance(exc,(asyncio.TimeoutError,httpx.TimeoutException)) else
          'unsupported-feature' if any(p in text for p in ('unsupported question','unsupported type','not supported','unknown question type')) else
          'invalid-response' if isinstance(exc,(ValueError,KeyError,TypeError)) else 'inference-error')
    return {'kind':kind,'action':'release-inputs-stop-save','automatic_hosted_fallback':False,
            'retry':'Explicit retry only; hosted Jev requires an explicit provider selection',
            'error':f'{type(exc).__name__}: {exc}'}


class SafetyHold(RuntimeError):
    def __init__(self,exc):
        self.report=safety_report(exc)
        super().__init__(self.report['error'])


async def ollaya_manifest(model):
    if not isinstance(model,str) or not model or model.startswith('-'):
        raise ValueError('Invalid Ollaya model name')
    process=await asyncio.create_subprocess_exec('ollaya','show',model,'--modelfile',
        stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,env=local_environment())
    try:
        stdout,stderr=await asyncio.wait_for(process.communicate(),10)
    except BaseException:
        if process.returncode is None:process.kill()
        await process.communicate()
        raise
    if process.returncode:raise RuntimeError(f'Ollaya model inspection failed: {stderr.decode(errors="replace")[-2000:]}')
    return {'name':model,'source':'ollaya show --modelfile','modelfile':stdout.decode(),
            'modelfile_sha256':hashlib.sha256(stdout).hexdigest()}


class HostedJevTransport:
    async def request(self,body):
        headers={'Authorization':'Bearer '+os.environ['TYPESAFE_API_KEY']}
        async with httpx.AsyncClient(timeout=45) as client:
            response=await client.post('https://api.typesafe.ai/v1/systemone',json=body,headers=headers)
            response.raise_for_status()
            return response.json()


class RecordedTransport:
    """Keep exact logical requests even when cancellation prevents a decision row."""
    def __init__(self,transport,path,events=None):
        self.transport=transport;self.path=path;self.context=None;self.sequence=0;self.events=events
        if path.is_file():
            with path.open() as file:
                for line in file:
                    row=json.loads(line);self.sequence=max(self.sequence,row['sequence']+1)

    def write(self,sequence,event,**fields):
        with self.path.open('a') as log:
            log.write(json.dumps({'sequence':sequence,'event':event,
                'at':datetime.now(timezone.utc).isoformat(),**fields})+'\n')
        if self.events:
            self.events.write('judgment-'+event,'judgment.'+event,request_sequence=sequence,
                              **{'context':self.context,**fields})

    async def request(self,body):
        sequence=self.sequence;self.sequence+=1
        self.write(sequence,'started',request=body,context=self.context)
        try:
            response=await self.transport.request(body)
        except BaseException as exc:
            self.write(sequence,'cancelled' if isinstance(exc,asyncio.CancelledError) else 'failed',
                       error=f'{type(exc).__name__}: {exc}')
            raise
        self.write(sequence,'completed',response=response)
        return response


class OllayaTransport:
    """Use the supported CLI, never a second local HTTP client or shell command."""
    def __init__(self,timeout=180):
        self.timeout=timeout

    async def run(self,model,state,questions):
        if not isinstance(model,str) or not model or model.startswith('-'):
            raise ValueError('Invalid Ollaya model name')
        env=local_environment()
        structured=isinstance(state,(dict,list))
        args=['ollaya','run',model,'--format','json',*(['--state-json'] if structured else []),'--questions',json.dumps(questions)]
        data=json.dumps(state).encode() if structured else str(state).encode()
        process=await asyncio.create_subprocess_exec(*args,stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,env=env)
        try:
            stdout,stderr=await asyncio.wait_for(process.communicate(data),self.timeout)
        except BaseException:
            if process.returncode is None:
                process.kill()
            await process.communicate()
            raise
        if process.returncode:
            raise RuntimeError(f'Ollaya CLI exited {process.returncode}: {stderr.decode(errors="replace")[-2000:]}')
        result=json.loads(stdout)
        if result.get('state_truncated'):
            raise ValueError('Ollaya truncated the state; cannot compare altered observations')
        if set(result.get('answers',{}))!=set(questions):
            raise ValueError('Ollaya CLI returned a different question set')
        return result

    async def request(self,body):
        answers,responses,subrequests={},[],[]
        # Serial contexts retain exact state/rubrics for limited local GPU memory.
        try:
            if not body.get('questions'):raise ValueError('No typed questions supplied')
            for key,question in body['questions'].items():
                if question.get('type') not in ('choice','noul','score'):
                    raise ValueError('Unsupported question type: '+str(question.get('type')))
                part={**body,'questions':{key:question}}
                result=await self.run(body['model'],body['state'],part['questions'])
                answers.update(result['answers']);responses.append(result);subrequests.append(part)
            return {'model':responses[0]['model'],'answers':answers,
                    'usage':{k:sum(r['usage'][k] for r in responses) for k in ('input_tokens','output_tokens')},
                    'transport':'ollaya-cli-sequential-single-question','subrequests':subrequests,'subresponses':responses}
        except asyncio.CancelledError:raise
        except Exception as exc:raise SafetyHold(exc) from exc


def inference(provider='ollaya',model=None):
    """Explicit selection; never substitute the hosted provider on local failure."""
    if provider=='ollaya':return model or 'kev:0.8b',OllayaTransport()
    if provider=='jev':return model or 'jev-latest',HostedJevTransport()
    raise ValueError('Provider must be ollaya or jev')
