"""Cancellable typed-judgment transports, independent of gameplay policies."""
import os
import asyncio
import json
import hashlib
import httpx


def local_environment():
    return {k:v for k,v in os.environ.items() if k not in ('TYPESAFE_API_KEY','JEV_API_KEY')}


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
        for key,question in body['questions'].items():
            part={**body,'questions':{key:question}}
            result=await self.run(body['model'],body['state'],part['questions'])
            answers.update(result['answers']);responses.append(result);subrequests.append(part)
        return {'model':responses[0]['model'],'answers':answers,
                'usage':{k:sum(r['usage'][k] for r in responses) for k in ('input_tokens','output_tokens')},
                'transport':'ollaya-cli-sequential-single-question','subrequests':subrequests,'subresponses':responses}


def inference(provider='ollaya',model=None):
    """Explicit selection; never substitute the hosted provider on local failure."""
    if provider=='ollaya':return model or 'kev:0.8b',OllayaTransport()
    if provider=='jev':return model or 'jev-latest',HostedJevTransport()
    raise ValueError('Provider must be ollaya or jev')
