"""Evidence-linked high scores, strictly separated by game and challenge."""
import hashlib
import html
import json
import os
from pathlib import Path
from urllib.parse import quote
from .usage import token_usage, player_identity
from .participation import score_attributable


def score_supported(directory, row):
    """Evidence validity is independent of whether an attempt can be ranked."""
    if not row.get("score_verified"):
        return False
    if not score_attributable(directory,row):return False
    score = row.get("score")
    if isinstance(score,bool) or not isinstance(score,int) or score<0:
        return False
    review = row.get("score_review",{})
    if not isinstance(review,dict):return False
    try:
        file = (directory/review.get("evidence", "final.png")).resolve()
        return file.is_relative_to(directory.resolve()) and file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()==review.get("evidence_sha256")
    except (OSError,TypeError,ValueError):return False


def eligible(directory, row):
    return (not row.get('practice') and row.get('playback_mode') not in ('continuous-practice-fresh','continuous-practice-resumed')
            and row.get("status") == "complete" and row.get("budget_frames") is not None
            and row.get("game_frames") == row.get("budget_frames") and score_supported(directory,row))


def load_groups(runs,errors=None):
    """One grouping/evidence contract for the static board and live front page."""
    groups = {}
    seen = set()
    for directory in sorted(Path(p).resolve() for p in runs):
        if directory in seen:
            continue
        seen.add(directory)
        try:
            row = json.loads((directory/"summary.json").read_text())
            key = (row["game"],row["challenge_id"],row.get("playback_mode","paused-inference-benchmark"))
            if not all(isinstance(k,str) for k in key) or not isinstance(row.get('config'),dict) or not isinstance(row.get('game_frames'),(int,float)) or 'status' not in row:
                raise ValueError('Invalid score summary fields')
        except (OSError,ValueError,KeyError,TypeError) as exc:
            if errors is not None:errors.append({'run':directory.name,'error':type(exc).__name__})
            continue
        item = {**row,"run":str(directory),"eligible":eligible(directory,row),"score_supported":score_supported(directory,row)}
        groups.setdefault(key,[]).append(item)
    for rows in groups.values():
        rows.sort(key=lambda r:(not r['eligible'],-(r['score'] or 0) if r['score_supported'] else 0,r['run']))
    return groups


def build(runs, output):
    output.mkdir(parents=True,exist_ok=True)
    groups = load_groups(runs)
    sections, data = [], []
    def link(path,label):
        href = quote(os.path.relpath(path,output.resolve()),safe="/.")
        return f'<a href="{html.escape(href,quote=True)}">{html.escape(label)}</a>'
    for (game, challenge, mode), rows in sorted(groups.items()):
        rows.sort(key=lambda r:(not r["eligible"], -(r["score"] or 0) if r["eligible"] else 0,r["run"]))
        data.append({"game":game,"challenge_id":challenge,"playback_mode":mode,"runs":rows})
        text = f'<h2>{html.escape(game)} · challenge {html.escape(challenge[:12])} · {html.escape(mode)}</h2>'
        text += '<table><tr><th>Rank</th><th>High score</th><th>Player handle</th><th>Game seconds</th><th>Stage 1</th><th>Input tokens</th><th>Output tokens</th><th>Total tokens</th><th>Evidence</th></tr>'
        rank = 0
        for r in rows:
            path = Path(r["run"])
            usage=token_usage(path,r);participant=player_identity(r['config'])
            r['token_usage']=usage;r['participant']=participant
            def tokens(key):
                value=usage[key]
                return 'Unknown' if value is None else ('' if usage['complete'] else '≥ ')+f'{value:,}'
            if r["eligible"]:
                rank += 1
            score = str(r["score"]) if r["eligible"] else f'{r["score"]} (unranked)' if r['score_supported'] else "Pending review"
            stage = "Verified" if r.get("stage_clear_candidate",{}).get("verified") else "—"
            reviewer = r.get("score_review",{}).get("reviewer","human (legacy)") if r.get('score_verified') else r["status"]
            evidence = r.get("score_review",{}).get("evidence","final.png")
            text += '<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in
                (rank if r["eligible"] else "—",score,participant['name'],r["game_frames"]/60,stage,tokens('input_tokens'),tokens('output_tokens'),tokens('total_tokens')))
            text += f'<td>{link(path/"replay.html",path.name)} · {link(path/evidence,"HUD")} · {html.escape(reviewer)}</td></tr>'
        sections.append(text+'</table>')
    document = '<!doctype html><meta charset="utf-8"><title>Jev Atari high scores</title><style>body{background:#141414;color:#eee;font:16px monospace;margin:32px}a{color:#8ce}td,th{padding:10px;text-align:left;border-bottom:1px solid #444}table{border-collapse:collapse}h2{margin-top:36px}</style><h1>Jev Atari high scores</h1><p>Only complete, full-budget runs with reviewed HUD evidence are ranked. Games and starting-state/time-budget challenges are never mixed. Jev confidence is not a score or proof of success.</p><p>Tokens include recorded attempt replies and HUD inference, including rejected actions. ≥ denotes incomplete/legacy usage, not a free run. Development/discovery/navigation and machine resources are outside this scope; tokens are not dollars or an all-cost winner.</p>' + ''.join(sections)
    (output/"index.html").write_text(document)
    (output/"scores.json").write_text(json.dumps(data,indent=2))
    print(f"High-score board: {output/'index.html'}")
