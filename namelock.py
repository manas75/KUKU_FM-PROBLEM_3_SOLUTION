"""NameLock: finds inconsistent spellings of character/place names and glossary violations across episodes of translated scripts.
Input: folder of .txt scripts ("SPEAKER: dialogue" lines plus scene lines). Usage:
  python namelock.py inputs --glossary glossary.json --planted planted.json --tag run
No model needed. A human (localisation QA) reviews the flagged list; the tool never edits scripts."""
import re, sys, os, json, glob, csv
from difflib import SequenceMatcher
from collections import defaultdict
STOP = {"scene","night","morning","court","garden","study","monday","tuesday","wednesday","thursday","friday","saturday","sunday","mister","then","what","where","because","children","please"}
def skeleton(w): return re.sub(r"[aeiou]", "", w.lower())
def names_in(text, speaker_line):
    found = []; first_ok = False
    m = re.match(r"^([A-Z][A-Za-z.' ]{1,20}):\s*(.*)$", speaker_line)
    body = speaker_line
    if m: found.append(m[1].strip().title()); body = m[2]
    else: body = re.sub(r"^[A-Z]+ \d+ - ", "", speaker_line); first_ok = True
    for sent in re.split(r"(?<=[.!?])\s+", body):
        toks = re.findall(r"[A-Za-z][A-Za-z'-]*", sent)
        for i, t in enumerate(toks):
            if (i > 0 or first_ok) and t[0].isupper() and len(t) >= 4 and t.lower() not in STOP: found.append(t)
    return found
def collect(folder):
    seen = defaultdict(lambda: defaultdict(int)); texts = {}
    for p in sorted(glob.glob(os.path.join(folder, "*.txt"))):
        ep = os.path.basename(p)[:-4]; texts[ep] = open(p, encoding="utf-8").read()
        for line in texts[ep].splitlines():
            for n in names_in(texts[ep], line.strip()): seen[n][ep] += 1
    return seen, texts
def variants(seen, distinct):
    total = {n: sum(e.values()) for n, e in seen.items()}; order = sorted(total, key=lambda n: -total[n]); flags = []; used = set()
    dset = {frozenset(x) for x in distinct}
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            if b in used or frozenset((a, b)) in dset or a[0].lower() != b[0].lower(): continue
            r = SequenceMatcher(None, a.lower(), b.lower()).ratio()
            if (skeleton(a) == skeleton(b) and a != b) or r >= 0.75:
                flags.append({"canonical_guess": a, "variant": b, "ratio": round(r, 2), "same_consonants": skeleton(a) == skeleton(b), "variant_episodes": ",".join(sorted(seen[b])), "variant_count": total[b], "canonical_count": total[a]}); used.add(b)
    return flags
def glossary_hits(texts, gl):
    out = []
    for canon, bad in gl.get("terms", {}).items():
        for ep, t in texts.items():
            for b in bad:
                if re.search(r"(?<![\w-])" + re.escape(b) + r"(?![\w-])", t, re.I): out.append({"canonical": canon, "found": b, "episode": ep})
    return out
if __name__ == "__main__":
    a = sys.argv; folder = a[1]; tag = a[a.index("--tag") + 1] if "--tag" in a else "run"
    gl = json.load(open(a[a.index("--glossary") + 1], encoding="utf-8")) if "--glossary" in a else {}
    pl = json.load(open(a[a.index("--planted") + 1], encoding="utf-8")) if "--planted" in a else None
    seen, texts = collect(folder); fl = variants(seen, gl.get("distinct", [])); gh = glossary_hits(texts, gl)
    with open(f"raw_outputs/{tag}_issues.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["type", "found", "should_be", "episodes", "note"])
        for x in fl: w.writerow(["name_variant", x["variant"], x["canonical_guess"], x["variant_episodes"], f"ratio={x['ratio']} same_consonants={x['same_consonants']} counts {x['variant_count']} vs {x['canonical_count']}"])
        for x in gh: w.writerow(["glossary", x["found"], x["canonical"], x["episode"], "banned variant"])
    md = [f"# NameLock report ({tag})\n", "## Possible name inconsistencies (review each; not auto-fixed)"] + [f"- **{x['variant']}** vs **{x['canonical_guess']}** (ep {x['variant_episodes']}; ratio {x['ratio']})" for x in fl] + ["\n## Glossary violations"] + [f"- '{x['found']}' should be **{x['canonical']}** (ep {x['episode']})" for x in gh]
    if pl:
        fnd = {(x["variant"], x["canonical_guess"]) for x in fl}; got = [p for p in pl["name_variants"] if (p[0], p[1]) in fnd]
        gg = [p for p in pl["glossary_hits"] if any(h["found"].lower() == p[0].lower() and h["episode"] == p[2] for h in gh)]
        fp = [x for x in fl if not any((x["variant"], x["canonical_guess"]) == (p[0], p[1]) for p in pl["name_variants"])]
        md += [f"\n## Check against planted errors (synthetic)\n- Name variants found: **{len(got)}/{len(pl['name_variants'])}**; missed: {[p[0] for p in pl['name_variants'] if p not in got] or 'none'}",
               f"- Glossary hits found: **{len(gg)}/{len(pl['glossary_hits'])}**", f"- False alarms (flagged but not planted): **{len(fp)}** {[(x['variant'], x['canonical_guess']) for x in fp]}"]
    open(f"raw_outputs/{tag}.md", "w", encoding="utf-8").write("\n".join(md)); print("\n".join(md[-4:]))
