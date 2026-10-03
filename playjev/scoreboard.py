"""Evidence-linked high scores, strictly separated by game and challenge."""
import hashlib
import html
import json
import os
from pathlib import Path
from urllib.parse import quote


def eligible(directory, row):
    if row.get("status") != "complete" or row.get("game_frames") != row.get("budget_frames") or not row.get("score_verified"):
        return False
    score = row.get("score")
    if isinstance(score,bool) or not isinstance(score,int) or score<0:
        return False
    review = row.get("score_review",{})
    file = (directory/review.get("evidence", "final.png")).resolve()
    return file.is_relative_to(directory.resolve()) and file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()==review.get("evidence_sha256")


def build(runs, output):
    output.mkdir(parents=True,exist_ok=True)
    groups = {}
    seen = set()
    for directory in sorted(Path(p).resolve() for p in runs):
        if directory in seen:
            continue
        seen.add(directory)
        row = json.loads((directory/"summary.json").read_text())
        key = (row["game"],row["challenge_id"])
        item = {**row,"run":str(directory),"eligible":eligible(directory,row)}
        groups.setdefault(key,[]).append(item)
    sections, data = [], []
    def link(path,label):
        href = quote(os.path.relpath(path,output.resolve()),safe="/.")
        return f'<a href="{html.escape(href,quote=True)}">{html.escape(label)}</a>'
    for (game, challenge), rows in sorted(groups.items()):
        rows.sort(key=lambda r:(not r["eligible"], -(r["score"] or 0) if r["eligible"] else 0,r["run"]))
        data.append({"game":game,"challenge_id":challenge,"runs":rows})
        text = f'<h2>{html.escape(game)} · challenge {html.escape(challenge[:12])}</h2>'
        text += '<table><tr><th>Rank</th><th>High score</th><th>Player</th><th>Game seconds</th><th>Stage 1</th><th>Evidence</th></tr>'
        rank = 0
        for r in rows:
            path = Path(r["run"])
            if r["eligible"]:
                rank += 1
            score = str(r["score"]) if r["eligible"] else "Pending review"
            stage = "Verified" if r.get("stage_clear_candidate",{}).get("verified") else "—"
            reviewer = r.get("score_review",{}).get("reviewer","human (legacy)") if r["eligible"] else r["status"]
            evidence = r.get("score_review",{}).get("evidence","final.png")
            text += '<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in
                (rank if r["eligible"] else "—",score,r["config"]["player"],r["game_frames"]/60,stage))
            text += f'<td>{link(path/"replay.html",path.name)} · {link(path/evidence,"HUD")} · {html.escape(reviewer)}</td></tr>'
        sections.append(text+'</table>')
    document = '<!doctype html><meta charset="utf-8"><title>Jev Atari high scores</title><style>body{background:#141414;color:#eee;font:16px monospace;margin:32px}a{color:#8ce}td,th{padding:10px;text-align:left;border-bottom:1px solid #444}table{border-collapse:collapse}h2{margin-top:36px}</style><h1>Jev Atari high scores</h1><p>Only complete, full-budget runs with reviewed HUD evidence are ranked. Games and starting-state/time-budget challenges are never mixed. Jev confidence is not a score or proof of success.</p>' + ''.join(sections)
    (output/"index.html").write_text(document)
    (output/"scores.json").write_text(json.dumps(data,indent=2))
    print(f"High-score board: {output/'index.html'}")
