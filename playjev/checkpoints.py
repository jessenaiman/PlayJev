"""Local, hash-bound canonical practice checkpoints. No reset or launch authority."""
import json
from pathlib import Path
from .challenge import digest
from .native import capture as native_capture


async def capture(env, directory, metadata, origin, base_frames=0):
    # Called only after inputs are released and the attempt is paused. EmulatorJS
    # queues loadState; disclose the canonicalization instead of claiming an exact
    # death-state resume. These callbacks are outside the recorded attempt budget.
    frozen = await env.page.evaluate('EJS_emulator.gameManager.getFrameNum()')
    state = await env.save()
    await env.restore(state)
    await env.frames([], 3, slow=False)
    image,_ = await native_capture(env,paused=True)
    ready = await env.save()
    canonical = await env.page.evaluate('EJS_emulator.gameManager.getFrameNum()')
    # Normalization may load without advancing on its first callback.
    advanced = canonical-frozen
    if not 0 <= advanced <= 4:
        raise ValueError('Checkpoint frame counter changed unexpectedly')
    row = {'schema':'atari-checkpoint-v1', 'game':metadata['game'],
           'challenge_id':metadata['challenge_id'], 'rom_sha256':metadata['rom_sha256'],
           'assets_sha256':metadata['assets_sha256'], 'state_sha256':digest(state),
           'ready_state_sha256':digest(ready), 'image_sha256':digest(image),
           'frozen_frame':frozen, 'canonical_frame':canonical,
           'logical_frames':base_frames+max(0,frozen-origin)+advanced,
           'normalization_callbacks':4, 'normalization_advanced_frames':advanced,
           'inputs_released':True,
           'note':'Canonical released-input checkpoint, not the exact last observation/death frame. Restore setup is verified and disclosed.'}
    directory=Path(directory)
    (directory/'checkpoint.state').write_bytes(state)
    (directory/'checkpoint-ready.state').write_bytes(ready)
    (directory/'checkpoint.png').write_bytes(image)
    (directory/'checkpoint.json').write_text(json.dumps(row,indent=2))
    return row


def verify(directory, metadata):
    directory=Path(directory)
    summary=json.loads((directory/'summary.json').read_text())
    row=json.loads((directory/'checkpoint.json').read_text())
    if (row.get('schema')!='atari-checkpoint-v1' or summary.get('checkpoint')!=row
            or summary.get('status')!='stopped' or summary.get('error')
            or summary.get('game_over_candidate') or summary.get('game_completed')):
        raise ValueError('Checkpoint source is failed, terminal, or not bound to its summary')
    if summary.get('attribution_hold'):raise ValueError('Checkpoint gameplay mode is disputed; do not resume demo evidence')
    for key in ('game','challenge_id','rom_sha256','assets_sha256'):
        if row.get(key)!=metadata[key]:raise ValueError('Checkpoint '+key+' mismatch')
    if summary.get('game')!=row['game'] or summary.get('challenge_id')!=row['challenge_id']:
        raise ValueError('Checkpoint source identity mismatch')
    for file,key in (('checkpoint.state','state_sha256'),('checkpoint-ready.state','ready_state_sha256'),('checkpoint.png','image_sha256')):
        path=directory/file
        if not path.resolve().is_relative_to(directory.resolve()) or digest(path.read_bytes())!=row[key]:
            raise ValueError('Checkpoint evidence changed: '+file)
    if row.get('inputs_released') is not True or type(row.get('logical_frames')) is not int or row['logical_frames']<0:
        raise ValueError('Invalid checkpoint input/frame contract')
    return row
