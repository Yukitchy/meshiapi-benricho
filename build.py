#!/usr/bin/env python3
"""data/ から index.html を生成する。rewrite1..3.md が置かれたら再実行で差し込まれる。"""
import json, html, re, pathlib, os, sys
try:
    import budoux
except ImportError:  # BudouX は python3.11 側に入っている
    os.execv("/Library/Frameworks/Python.framework/Versions/3.11/bin/python3", ["python3", *sys.argv])
from urllib.parse import urlparse, quote

D = pathlib.Path(__file__).parent / "data"
E = html.escape
audit = json.loads((D / "audit.json").read_text())
menu = json.loads((D / "menu.json").read_text())
sauna = json.loads((D / "sauna.json").read_text())
meta, terms, arts = audit["meta"], audit["terms"], audit["articles"]

# ---- 最小Markdown ----
def inline(s):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", E(s))

def md(text, h="h4"):
    out, ul = [], False
    for ln in text.splitlines():
        s = ln.strip()
        m = re.match(r"^[-*]\s+(.*)", s)
        if m:
            if not ul: out.append("<ul>"); ul = True
            out.append(f"<li>{inline(m.group(1))}</li>"); continue
        if ul: out.append("</ul>"); ul = False
        if not s: continue
        m = re.match(r"^#{1,6}\s+(.*)", s)
        out.append(f"<{h}>{inline(m.group(1))}</{h}>" if m else f"<p>{inline(s)}</p>")
    if ul: out.append("</ul>")
    return "\n".join(out)

def summary_lines(text, n=2):
    lines, on = [], False
    for ln in text.splitlines():
        s = ln.strip()
        if on and re.match(r"^-{3,}$", s): break
        if s.startswith("#"):
            if on: break
            on = "変更点サマリー" in s; continue
        if on and s:
            lines.append(re.sub(r"\*\*(.+?)\*\*", r"\1", re.sub(r"^[-*]\s+", "", s)))
            if len(lines) == n: break
    return lines

# ---- 出口の部品 ----
def line_url(t): return "https://line.me/R/share?text=" + quote(t, safe="")
def line_btns(t, label, kind, main=True):
    c = "btn" if main else "btn sec sm"
    return (f'<a class="{c}" href="{line_url(t)}" data-x="{kind}">{E(label)}</a>'
            '<button type="button" class="btn sec sm">コピー</button>')
HINT = '<p class="hint">LINEが開いたらユウキを選んで送信。開かなければコピーして貼る</p>'
TXT = {"terms": "\n".join(f'{t["old"]}\t{t["new"]}' for t in terms)}
assert len(terms) == 10

def plain(lines):
    o = []
    for ln in lines:
        x = re.sub(r"^\s*#{1,6}\s+", "", ln.rstrip())
        x = re.sub(r"^\s*[-*]\s+", "・", x)
        o.append(re.sub(r"\*\*(.+?)\*\*", r"\1", x))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(o)).strip()

def rw_parts(text):
    ls = text.splitlines()
    a = next(i for i, l in enumerate(ls) if re.match(r"^#\s", l))
    b = next((i for i, l in enumerate(ls) if re.match(r"^##\s*迷った点", l)), len(ls))
    body = plain(ls[a:b])
    if not re.search(r"[。」）!！?？]$", body):  # 末尾が文で終わらない＝書き直し案が途中で切れている
        print("WARN: 書き直し案の末尾が途中で切れている:", body.splitlines()[-1][:30])
    return body, "\n".join("・" + x for x in summary_lines(text, None))

# ---- 旧用語表 ----
cnt = {t["old"]: 0 for t in terms}
for a in arts:
    for h in a["hits"]: cnt[h["old"]] += h["count"]
assert sum(cnt.values()) == meta["total_hits"], (sum(cnt.values()), meta["total_hits"])

term_rows = "".join(
    f'<tr><td class="main"><b class="old">{E(t["old"])}</b></td>'
    f'<td data-l="現行" class="new">{E(t["new"])}</td>'
    f'<td data-l="メモ">{E(t["note"])}</td>'
    f'<td data-l="件数" class="num">{cnt[t["old"]]}</td>'
    f'<td data-l="根拠"><a href="{E(t["ref"])}" target="_blank" rel="noopener">{E(urlparse(t["ref"]).netloc)}</a></td></tr>'
    for t in terms)

# ---- 記事表 ----
rows = sorted(arts, key=lambda a: (a["total"], a["date"]), reverse=True)
def chips(a):
    if not a["hits"]: return '<span class="none">なし</span>'
    return "".join(f'<span class="chip">{E(h["old"])} <b>{h["count"]}</b></span>' for h in a["hits"])
art_rows = "".join(
    f'<tr><td class="main"><a href="{E(a["url"])}" target="_blank" rel="noopener">{E(a["title"])}</a></td>'
    f'<td data-l="日付">{a["date"].replace("-", ".")}</td>'
    f'<td data-l="文字数" class="num">{a["chars"]:,}</td>'
    f'<td data-l="旧用語の内訳"><div class="chips">{chips(a)}</div></td>'
    f'<td data-l="件数" class="num">{a["total"]}</td></tr>'
    for a in rows)

# ---- 浄書の試み 上位3本 ----
slugs = ["ads-introduction3", "3c-analysis", "ads-introduction2"]
rw = []
for i, slug in enumerate(slugs, 1):
    a = next(x for x in arts if slug in x["url"])
    f = D / f"rewrite{i}.md"
    orig = D / f"orig{i}.txt"
    head = f'<span class="dn">{i}</span><span class="ds"><b>{E(a["title"])}</b>'
    meta_line = f'<span class="dm"><span>旧用語 {a["total"]}箇所</span></span>'
    if f.exists():
        t = f.read_text()
        TXT[f"b{i}"], TXT[f"s{i}"] = rw_parts(t)
        meta_line = f'<span class="dm"><span>旧用語 {a["total"]}箇所</span><span>要再確認 {TXT[f"b{i}"].count("【要再確認】")}箇所</span></span>'
        acts = (f'<div class="act"><button type="button" class="btn" data-t="b{i}">本文をコピー</button>'
                f'<button type="button" class="btn sec" data-t="s{i}">変更点だけコピー</button></div>')
        sl = summary_lines(t)
        sub = "".join(f'<span class="dl">{E(x)}</span>' for x in sl) or '<span class="dl">変更点サマリーは本文の冒頭にあります</span>'
        o = ""
        if orig.exists():
            paras = [p.strip() for p in re.split(r"\n\s*\n", orig.read_text().split("\n", 1)[-1]) if p.strip()]
            o = '<details class="orig"><summary>原文を見る</summary>' + "".join(f"<p>{E(re.sub(chr(10), ' ', p))}</p>" for p in paras) + "</details>"
        rw.append(f'<details class="rw"><summary>{head}{sub}</span>{meta_line}</summary><div class="rwbody">{acts}{md(t)}{o}</div></details>')
    else:
        rw.append(f'<div class="rw pend">{head}<span class="dl">書き直し案は準備中</span></span>{meta_line}</div>')

# ---- 10案 ----
KAN = "零一二三四五六七八九"
def kanji(n):
    if n < 10: return KAN[n]
    h, r = divmod(n, 100); t, o = divmod(r, 10)
    s = (("" if h == 1 else KAN[h]) + "百") if h else ""
    if t: s += ("" if t == 1 else KAN[t]) + "十"
    return s + (KAN[o] if o else "")
def card(it):
    msg = f'救世主の魔導書／術式{it["n"]}（{it["name"]}）を頼む'
    return (f'<li class="card"><span class="no">{it["n"]}</span><div><span class="sn">第{kanji(it["n"])}の術式</span><h3>{E(it["name"])}</h3>'
            f'<p class="io"><span class="lab">入力</span><span>{E(it["in"])}</span></p>'
            f'<p class="io"><span class="lab">出力</span><span>{E(it["out"])}</span></p>'
            f'<div class="act">{line_btns(msg, "この術式を頼む", "jutsu")}</div></div></li>')
cards = "".join(card(it) for it in menu["items"])

# ---- サウナ ----
def opt(o):
    msg = f'救世主の魔導書／巡礼は{o["k"]}（{o["dates"]}）で'
    return (f'<div class="opt"><span class="k">{E(o["k"])}</span><div><span class="sn">巡礼の候補 {E(o["k"])}</span><h3>{E(o["dates"])}</h3><p>{E(o["note"])}</p>'
            f'<div class="act">{line_btns(msg, o["k"] + "で行く", "ab")}</div></div></div>')
opts = "".join(opt(o) for o in sauna["options"])
ALT = line_btns("救世主の魔導書／巡礼は別の週で。候補: ", "別の週がいい", "alt", main=False)

TITLE = "救世主の魔導書"
DESC = "古き言葉を清め、十の術式を授ける書。"
FACT = "運用型広告研究所の鮮度チェックと、AIでできること10案"
URL = "https://yukitchy.github.io/meshiapi-benricho/"
NA, NH, NT = meta["articles"], meta["with_hits"], meta["total_hits"]
JO = (f"運用型広告研究所を久しぶりに読み返した。名を変えられた言葉が、{kanji(NA)}の章に{kanji(NT)}。"
      "放っておくには惜しいので、清めの手順と、ひとりで回せる十の術式をここに記す。")

CSS = r'''
*{box-sizing:border-box;min-width:0}
html,body{max-width:100%;overflow-x:hidden}
h1,h2,h3,h4,p{margin:0}
:root{color-scheme:dark;--bg:#0b0b0d;--card:#141317;--ink:#e8e4da;--mute:#9a948a;--acc:#c4182f;--gold:#c9a84c;--line:rgba(201,168,76,.28);--font:"Noto Sans JP","Hiragino Sans",-apple-system,sans-serif;--num:Inter,"Noto Sans JP",sans-serif}
body{margin:0;padding:28px 20px 48px;font:400 16px/1.85 var(--font);color:var(--ink);background:var(--bg);word-break:keep-all;overflow-wrap:break-word}
a{color:var(--ink);text-decoration-line:underline;text-decoration-color:var(--acc);text-decoration-thickness:2px;text-underline-offset:4px}
ruby{ruby-position:over;ruby-align:center}
rt{font-size:max(12px,.24em);font-weight:700;letter-spacing:.04em;color:var(--mute);font-family:var(--font)}
.book{position:relative;max-width:1120px;margin:0 auto;padding:64px 48px 40px;border:1px solid var(--gold);outline:1px solid var(--line);outline-offset:-8px;overflow:hidden}
.corner{position:absolute;width:80px;height:80px;color:var(--gold)}
.corner.tl{left:14px;top:14px}
.corner.tr{right:14px;top:14px;transform:scaleX(-1)}
.corner.bl{left:14px;bottom:14px;transform:scaleY(-1)}
.corner.br{right:14px;bottom:14px;transform:scale(-1,-1)}
.ring{display:block;width:44px;height:44px;margin:0;color:var(--gold)}
header{text-align:center;padding:0 0 30px}
.stage{position:relative;min-height:460px;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:20px 0}
.sigil{position:absolute;left:50%;top:50%;width:460px;height:460px;transform:translate(-50%,-50%);color:var(--gold);opacity:.28;pointer-events:none;-webkit-mask-image:radial-gradient(circle,transparent 12%,#000 46%);mask-image:radial-gradient(circle,transparent 12%,#000 46%)}
.stage>*:not(.sigil){position:relative}
.eyebrow{display:flex;align-items:center;gap:14px;font:700 12px/1 var(--num);letter-spacing:.5em;color:var(--mute);margin:0 0 14px}
.eyebrow::before,.eyebrow::after{content:"";width:44px;height:1px;background:var(--gold);opacity:.7}
h1{font-weight:900;font-size:clamp(30px,6.2vw,60px);line-height:1.5;letter-spacing:.04em;white-space:nowrap}
.seal{display:inline-block;vertical-align:top;margin:.1em 0 0 .2em;width:26px;height:26px;border:2px solid var(--acc);color:var(--ink);font:900 15px/22px var(--font);letter-spacing:0;text-align:center;transform:rotate(4deg)}
.lead{font-size:min(17px,4.6vw);color:var(--ink);margin:12px auto 0;font-weight:700;letter-spacing:.06em;line-height:2.1}
.nb{display:inline-block;white-space:nowrap}
.fact{font-size:14px;color:var(--mute);margin:8px auto 0;max-width:30em;text-wrap:balance;line-height:1.7}
.facts{display:flex;justify-content:center;flex-wrap:wrap;gap:2px 28px;margin:6px 0 0;padding:0;list-style:none;font-size:13px;color:var(--mute)}
.facts b{color:var(--ink);font-weight:700}
.toc{max-width:560px;margin:0 auto;border-top:3px double var(--gold);border-bottom:3px double var(--gold);padding:14px 4px 12px}
.toc>b{display:block;text-align:center;font-weight:900;font-size:13px;letter-spacing:.5em;text-indent:.5em;margin-bottom:8px;color:var(--mute)}
.toc ol{list-style:none;margin:0;padding:0}
.toc a{display:flex;align-items:baseline;gap:8px;text-decoration:none;padding:5px 0;font-weight:700;font-size:16px}
.toc a::after{content:"";order:2;flex:1;border-bottom:2px dotted var(--gold);transform:translateY(-3px)}
.toc a em{order:3;font:700 13px/1 var(--num);font-style:normal;color:var(--mute)}
.toc a span{order:1}
.sep{display:flex;align-items:center;gap:18px;margin:46px 0 6px}
.sep::before,.sep::after{content:"";flex:1;height:1px;background:var(--line)}
section{padding:6px 0 0}
.sh{display:flex;flex-direction:column;align-items:center;text-align:center;margin:10px 0 30px}
.sh .ch{font-weight:700;font-size:13px;letter-spacing:.4em;text-indent:.4em;color:var(--mute)}
.sh .n{font:700 72px/1.05 var(--font);color:var(--acc);margin:2px 0 4px}
h2{font-weight:900;font-size:clamp(24px,4.6vw,38px);line-height:1.6;letter-spacing:.06em;white-space:nowrap}
.sh::after{content:"";display:block;width:9px;height:9px;margin-top:16px;border:1px solid var(--gold);transform:rotate(45deg);background:var(--bg)}
section.jo .sh{margin-bottom:18px}
.jo .addr{text-align:center;font-weight:900;font-size:18px;letter-spacing:.1em;margin-bottom:10px}
.jo p.body{max-width:34em;margin:0 auto;font-size:16.5px;line-height:2.05;font-weight:500}
.sn{display:block;font-size:12px;font-weight:700;letter-spacing:.2em;color:var(--mute);line-height:1.2;margin:3px 0 4px}
h3.sub{font-weight:900;font-size:20px;margin:40px 0 6px;letter-spacing:.04em;padding-bottom:6px;border-bottom:1px solid var(--line)}
.note{color:var(--mute);font-size:15px;margin:6px 0 14px}
td,.dl,.note{text-wrap:pretty}
td.main{text-wrap:balance}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.tile{padding:16px 16px 14px;background:var(--card);border:1px solid var(--line);text-align:center}
.tile .l{display:block;font-size:13px;color:var(--mute);font-weight:700}
.tile .v{display:block;margin-top:6px;font:900 clamp(38px,5vw,52px)/1 var(--num);letter-spacing:-.04em;white-space:nowrap}
.tile .v small{font:700 15px/1 var(--font);letter-spacing:0;margin-left:3px;color:var(--mute)}
table.terms{table-layout:fixed}
.terms th:nth-child(1){width:26%}.terms th:nth-child(2){width:20%}.terms th:nth-child(3){width:28%}.terms th:nth-child(4){width:6%}.terms th:nth-child(5){width:20%}
table{width:100%;border-collapse:collapse;font-size:15px;background:var(--card);border:1px solid var(--line)}
th{text-align:left;font-size:12.5px;font-weight:900;letter-spacing:.06em;padding:9px 12px;border-bottom:1px solid var(--gold);white-space:nowrap;color:var(--mute)}
td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top;line-height:1.6}
tr:last-child td{border-bottom:0}
.num{text-align:right;font-family:var(--num);font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
th.num{font-family:inherit}
.old{font-weight:900}
.new{font-weight:700}
.chips{display:flex;flex-wrap:wrap;gap:4px 6px}
.chip{font-size:12.5px;border:1px solid var(--line);padding:0 8px;white-space:nowrap}
.chip b{font-family:var(--num);font-weight:900}
.none{color:var(--mute);font-size:13px}
.rws{display:grid;gap:10px}
.rw{background:var(--card);border:1px solid var(--line)}
.rw>summary::-webkit-details-marker{display:none}
.rw>summary{list-style:none;cursor:pointer}
.rw>summary,.rw.pend{display:flex;align-items:flex-start;gap:14px;padding:16px 20px}
.rw>summary::after{content:"開く";margin-left:auto;flex:none;font-size:13px;font-weight:900;background:var(--acc);color:var(--ink);padding:1px 14px;letter-spacing:.1em}
.rw[open]>summary::after{content:"閉じる"}
.dn{flex:none;font:900 26px/1.1 var(--num);width:1.1em;color:var(--acc)}
.ds{display:flex;flex-direction:column;gap:3px;flex:1}
.ds b{font-weight:900;line-height:1.5}
.dl{font-size:14px;color:var(--mute);line-height:1.65}
.dm{flex:none;font-size:12.5px;color:var(--mute);white-space:nowrap}
.rwbody{border-top:1px solid var(--line);padding:22px 26px 26px;max-width:46em}
.rwbody h4{font-size:17px;font-weight:900;margin:26px 0 8px}
.rwbody h4:first-child{margin-top:0}
.rwbody p{line-height:2;margin:0 0 12px}
.rwbody ul{margin:0 0 14px;padding-left:1.3em;line-height:1.95}
.orig{margin-top:22px;border-top:1px dashed var(--line);padding-top:12px}
.orig summary{cursor:pointer;font-size:14px;font-weight:900}
.orig p{font-size:15px;color:var(--mute);line-height:1.9;margin-top:10px}
.cards{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.card{display:flex;gap:16px;padding:20px 22px 22px;background:var(--card);border:1px solid var(--line)}
.no{flex:none;width:1.2em;font:900 44px/1 var(--num);letter-spacing:-.05em;color:var(--acc)}
.card h3{font-size:18px;font-weight:900;line-height:1.45;margin:0 0 10px;letter-spacing:.02em}
.io{display:grid;grid-template-columns:2.8em 1fr;gap:10px;font-size:15.5px;line-height:1.7;margin-top:6px}
.lab{font-size:12px;font-weight:900;border:1px solid var(--mute);color:var(--mute);text-align:center;height:1.7em;line-height:1.6em;margin-top:.1em}
.opts{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.opt{display:flex;gap:18px;padding:20px 22px;background:var(--card);border:1px solid var(--line)}
.opt .k{flex:none;font:900 48px/1 var(--num);width:.8em;color:var(--acc)}
.opt h3{font-size:18px;font-weight:900;line-height:1.5;margin:0 0 6px}
.opt p{color:var(--mute);font-size:15px}
.ask{margin-top:18px;font-weight:700;text-align:center}
footer{margin-top:20px;text-align:center}
footer .sh{margin-bottom:20px}
footer b{display:block;font-size:min(24px,5vw);font-weight:900;margin:0 0 10px;letter-spacing:.02em;white-space:nowrap}
footer .vo{display:block;font-size:14px;color:var(--ink);letter-spacing:.16em;margin-bottom:22px;font-weight:700}
footer p{color:var(--mute);font-size:12.5px}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 18px;font:900 15px/1.3 var(--font);letter-spacing:.06em;white-space:nowrap;text-decoration:none;cursor:pointer;color:var(--ink);background:var(--acc);border:1px solid var(--acc);border-radius:0;-webkit-appearance:none;appearance:none}
.btn.sec{background:transparent;border-color:var(--ink)}
.btn.sm{padding:0 14px;font-size:14px}
.btn:focus-visible,.exit:focus-visible{outline:2px solid var(--gold);outline-offset:3px}
.act{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.act .btn:not(.sm){flex:1 1 9em}
.act.alt{justify-content:center;margin-top:12px}
.hint{font-size:13px;color:var(--mute);line-height:1.7;margin-top:10px}
.act.alt+.hint{text-align:center}
.rwbody>.act{margin:0 0 20px}
.dm{display:flex;flex-direction:column;align-items:flex-end}
.fix{margin:26px 0 0;padding:20px 22px 22px;background:var(--card);border:1px solid var(--gold)}
.fix h3{font-size:20px;font-weight:900;letter-spacing:.04em}
.fix ol{list-style:none;counter-reset:s;margin:12px 0 0;padding:0;display:grid;gap:14px}
.fix li{display:grid;grid-template-columns:1.5em 1fr;gap:10px;line-height:1.85;font-size:15.5px}
.fix li::before{counter-increment:s;content:counter(s);font:900 32px/1.1 var(--num);color:var(--acc)}
.subrow{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:8px 12px;margin:40px 0 6px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.subrow h3.sub{margin:0;padding:0;border:0}
.exits{display:grid;gap:12px;margin:0 0 30px;text-align:left}
.exit{display:grid;grid-template-columns:auto 1fr auto;gap:12px 16px;align-items:center;padding:20px 22px;background:var(--card);border:1px solid var(--ink);color:var(--ink);text-decoration:none}
.exit .no{font-size:44px;text-align:center}
.exit h3{font-size:20px;font-weight:900;line-height:1.45}
.exit p{color:var(--mute);font-size:14px;line-height:1.7;margin-top:2px}
.exit::after{content:"→";font:900 22px/1 var(--num);color:var(--acc)}
@media(max-width:1180px){
 thead{display:none}
 table,tbody{display:block;border:0;background:none}
 tr{display:block;background:var(--card);border:1px solid var(--line);padding:10px 12px;margin-bottom:10px}
 td{display:block;position:relative;border:0;padding:3px 0 3px calc(5.2em + 10px)}
 td::before{content:attr(data-l);position:absolute;left:0;top:5px;font-size:12px;font-weight:900;color:var(--mute)}
 td.main{padding:0 0 6px}
 td.main::before{content:none}
 td.num{text-align:left}
}
@media(max-width:860px){
 .tiles{grid-template-columns:repeat(2,1fr)}
 .cards,.opts{grid-template-columns:1fr}
}
@media(max-width:720px){
 body{padding:10px 8px 28px}
 .book{padding:52px 16px 28px}
 .corner{width:40px;height:40px;left:auto}
 .corner.tl,.corner.bl{left:8px}.corner.tr,.corner.br{right:8px}
 .corner.tl,.corner.tr{top:8px}.corner.bl,.corner.br{bottom:8px}
 .stage{min-height:300px}
 .sigil{width:min(300px,100%);height:auto;aspect-ratio:1}
 .seal{width:22px;height:22px;font-size:13px;line-height:18px}
 .eyebrow{letter-spacing:.3em;gap:8px}.eyebrow::before,.eyebrow::after{width:20px}
 .sh .n{font-size:56px}
 h2 ruby.ov{margin-right:-14px}
 .rw>summary,.rw.pend{flex-wrap:wrap;padding:14px}
 .rw>summary::after{margin-left:calc(1.1em + 14px)}
 .dm{margin-left:calc(1.1em + 14px);flex-basis:100%}
 .rwbody{padding:18px 14px 22px}
 .card,.opt{gap:6px;flex-direction:column;padding:16px 14px 18px}
 .tile{padding:12px 8px}
 .chip{white-space:normal;max-width:100%}
 .opt h3{font-size:16px}
 .dm{flex-direction:row;gap:12px;align-items:flex-start}
 .fix{padding:16px 14px 18px}
 .exit{padding:16px 14px;gap:10px 12px}
 .exit .no{font-size:36px}
 .tile-date .v small{display:block;margin:6px 0 0}
 .rw>summary{display:grid;grid-template-columns:30px minmax(0,1fr) auto;gap:10px}
 .rw>summary .dn{grid-column:1;grid-row:1}
 .rw>summary .ds{grid-column:2 / 4;grid-row:1}
 .rw>summary .dm{grid-column:2;grid-row:2;margin:0;flex-wrap:wrap;white-space:normal}
 .rw>summary::after{grid-column:3;grid-row:2;margin:0;align-self:start;padding:4px 10px}
 h1,h2,footer b{white-space:normal}
 .btn{max-width:100%;white-space:normal;padding-block:10px}
}
.card{display:grid;grid-template-columns:2.2rem minmax(0,1fr);gap:12px}
.card>.no{width:auto;font-size:28px;color:var(--gold)}
.card>div{display:flex;flex-direction:column}
.card .act{margin-top:auto;padding-top:16px}
a:focus-visible,summary:focus-visible{outline:2px solid var(--gold);outline-offset:4px}
@media(hover:hover){
 .btn:hover{filter:brightness(1.15)}
 .toc a:hover,.rw>summary:hover{background:#1c191d}
}
'''

JS = r'''(()=>{
const fb=s=>{const t=document.createElement("textarea");t.value=s;t.style.cssText="position:fixed;top:0;opacity:0";document.body.appendChild(t);t.select();t.setSelectionRange(0,1e6);let ok=false;try{ok=document.execCommand("copy")}catch(e){}t.remove();return ok};
const copy=async s=>{try{await navigator.clipboard.writeText(s);return true}catch(e){return fb(s)}};
document.addEventListener("click",async e=>{
 const b=e.target.closest("button.btn");if(!b)return;
 const s=b.dataset.t?T[b.dataset.t]:new URL(b.previousElementSibling.href).searchParams.get("text");
 const ok=await copy(s);
 if(!b.dataset.o)b.dataset.o=b.textContent;
 b.textContent=ok?"写した":"写せず";
 clearTimeout(b._t);b._t=setTimeout(()=>{b.textContent=b.dataset.o},1500);
});
})();
'''

SIGIL = '''<symbol id="sigil" viewBox="0 0 200 200"><g fill="none" stroke="currentColor" stroke-linejoin="round" stroke-linecap="round"><circle cx="100" cy="100" r="96" stroke-width="1.4"/><circle cx="100" cy="100" r="91" stroke-width="3" stroke-dasharray="1 5.1" stroke-linecap="butt"/><circle cx="100" cy="100" r="84" stroke-width="1"/><path stroke-width="1.1" d="M100 34V20M100 29l6-6" transform="rotate(0.0 100 100)"/><path stroke-width="1.1" d="M100 34V22M94 18l6 6 6-6" transform="rotate(22.5 100 100)"/><path stroke-width="1.1" d="M100 34V20M96 30l8-4" transform="rotate(45.0 100 100)"/><path stroke-width="1.1" d="M100 34l4-5-8-4 4-5" transform="rotate(67.5 100 100)"/><path stroke-width="1.1" d="M100 34V20M100 29l6-6" transform="rotate(90.0 100 100)"/><path stroke-width="1.1" d="M100 34V22M94 18l6 6 6-6" transform="rotate(112.5 100 100)"/><path stroke-width="1.1" d="M100 34V20M96 30l8-4" transform="rotate(135.0 100 100)"/><path stroke-width="1.1" d="M100 34l4-5-8-4 4-5" transform="rotate(157.5 100 100)"/><path stroke-width="1.1" d="M100 34V20M100 29l6-6" transform="rotate(180.0 100 100)"/><path stroke-width="1.1" d="M100 34V22M94 18l6 6 6-6" transform="rotate(202.5 100 100)"/><path stroke-width="1.1" d="M100 34V20M96 30l8-4" transform="rotate(225.0 100 100)"/><path stroke-width="1.1" d="M100 34l4-5-8-4 4-5" transform="rotate(247.5 100 100)"/><path stroke-width="1.1" d="M100 34V20M100 29l6-6" transform="rotate(270.0 100 100)"/><path stroke-width="1.1" d="M100 34V22M94 18l6 6 6-6" transform="rotate(292.5 100 100)"/><path stroke-width="1.1" d="M100 34V20M96 30l8-4" transform="rotate(315.0 100 100)"/><path stroke-width="1.1" d="M100 34l4-5-8-4 4-5" transform="rotate(337.5 100 100)"/><circle cx="100" cy="100" r="62" stroke-width="1"/><circle cx="100" cy="100" r="59" stroke-width="4" stroke-dasharray="0.8 3.2" stroke-linecap="butt"/><circle cx="100" cy="100" r="46" stroke-width="1" stroke-dasharray="6 3"/><circle cx="100" cy="100" r="30" stroke-width="1"/><circle cx="100" cy="100" r="10" stroke-width="1"/><circle cx="100" cy="100" r="2" fill="currentColor"/></g></symbol>'''
RING = ('<symbol id="ring" viewBox="0 0 120 120"><g fill="none" stroke="currentColor" stroke-linejoin="round">'
 '<circle cx="60" cy="60" r="57" stroke-width="1.4"/><circle cx="60" cy="60" r="52" stroke-width="3" stroke-dasharray="1 5.6" stroke-linecap="butt"/>'
 '<circle cx="60" cy="60" r="44" stroke-width="1"/><circle cx="60" cy="60" r="30" stroke-width="1" stroke-dasharray="4 3"/><circle cx="60" cy="60" r="10" stroke-width="1"/><circle cx="60" cy="60" r="2.2" fill="currentColor"/></g></symbol>')
CORNER = ('<symbol id="corner" viewBox="0 0 60 60"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">'
 '<path stroke-width="1.6" d="M2 58V12Q2 2 12 2H58"/><path stroke-width="1" d="M8 58V16Q8 8 16 8H58"/>'
 '<circle cx="16" cy="16" r="5" stroke-width="1.2"/><circle cx="16" cy="16" r="1.6" fill="currentColor"/>'
 '<path stroke-width="1" d="M16 22Q16 34 26 34M22 16Q34 16 34 26"/><path stroke-width="1.2" d="M2 40l4-4 4 4-4 4zM40 2l4 4-4 4-4-4z" fill="currentColor"/>'
 '<circle cx="2" cy="52" r="1.2" fill="currentColor"/><circle cx="52" cy="2" r="1.2" fill="currentColor"/></g></symbol>')
sep = '<div class="sep"><svg class="ring" aria-hidden="true"><use href="#ring"/></svg></div>'

TJ = json.dumps(TXT, ensure_ascii=False).replace("<", "\\u003c")
page = f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<meta name="robots" content="noindex,nofollow">
<meta property="og:type" content="website"><meta property="og:locale" content="ja_JP">
<meta property="og:title" content="{TITLE}"><meta property="og:description" content="{DESC}">
<meta property="og:image" content="{URL}og.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@700;900&family=Noto+Sans+JP:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>{CORNER}{RING}{SIGIL}</defs></svg>
<div class="book">
<svg class="corner tl" aria-hidden="true"><use href="#corner"/></svg><svg class="corner tr" aria-hidden="true"><use href="#corner"/></svg><svg class="corner bl" aria-hidden="true"><use href="#corner"/></svg><svg class="corner br" aria-hidden="true"><use href="#corner"/></svg>
<header>
<div class="stage">
<svg class="sigil" viewBox="0 0 200 200" aria-hidden="true"><use href="#sigil"/></svg>
<span class="eyebrow">GRIMORIUM MESSIAE</span>
<h1><ruby>救世主<rt>メシア</rt></ruby>の<ruby>魔導書<rt>グリモワール</rt></ruby><span class="seal" aria-hidden="true">禁</span></h1>
<p class="lead"><span class="nb"><ruby>古き言葉<rt>ロスト・ワード</rt></ruby>を清め、</span><span class="nb">十の<ruby>術式<rt>アルス</rt></ruby>を授ける禁書。</span></p>
<p class="fact">{FACT}</p>
</div>
<ul class="facts"><li>記された日 <b>2026年10月12日</b></li><li>記す者 <b>ユウキ</b></li></ul>
</header>

<nav class="toc"><b>索引</b><ol>
<li><a href="#jo"><span>序</span><em>頁 1</em></a></li>
<li><a href="#fresh"><span>第Ⅰ章 古き言葉の検分</span><em>頁 2</em></a></li>
<li><a href="#ai"><span>第Ⅱ章 十の術式</span><em>頁 3</em></a></li>
<li><a href="#sauna"><span>第Ⅲ章 巡礼の日取り</span><em>頁 4</em></a></li>
<li><a href="#ketsu"><span>結</span><em>頁 5</em></a></li>
</ol></nav>

{sep}
<section id="jo" class="jo">
<div class="sh"><h2>序</h2></div>
<p class="addr">汝、この書を開きし者よ。</p>
<p class="body">{JO}</p>
</section>

{sep}
<section id="fresh">
<div class="sh"><span class="ch">第Ⅰ章</span><span class="n">Ⅰ</span><h2>古き言葉の<ruby>検分<rt>ジャッジメント</rt></ruby></h2></div>
<div class="tiles">
<div class="tile"><span class="l">記事</span><span class="v">{NA}<small>本</small></span></div>
<div class="tile"><span class="l">旧用語を含む記事</span><span class="v">{NH}<small>本</small></span></div>
<div class="tile"><span class="l">旧用語</span><span class="v">{NT}<small>箇所</small></span></div>
<div class="tile tile-date"><span class="l">最終更新</span><span class="v">2021<small>年4月</small></span></div>
</div>

<div class="fix" id="naoshi">
<h3>直し方（三手）</h3>
<ol>
<li><span>置換表を手元に置きます。<a href="#terms">旧き名の表</a>の見出しの横のボタンで、旧い名といまの名を10組コピーできます。貼り先はWordPressの検索置換プラグイン。タブ区切りなので、そのまま貼れる形です。</span></li>
<li><span>旧用語の多い記事から順に直します。<a href="#arts">{kanji(NA)}の章</a>の表は、多い順の並びです。記事名から元の記事を開けます。</span></li>
<li><span>上位三章は、<a href="#kijutsu">浄書の試み</a>をそのまま使えます。各案に「本文をコピー」のボタンつき。【要再確認】の印だけ、自分の目で確かめて消してください。</span></li>
</ol>
</div>

<div class="subrow" id="terms"><h3 class="sub">旧き名と、いまの名</h3><button type="button" class="btn sec sm" data-t="terms">置換表をコピー</button></div>
<p class="note">ブログ内で使われている古い呼び方と、いまの公式名称です。</p>
<table class="terms"><thead><tr><th>旧用語</th><th>現行</th><th>メモ</th><th class="num">件数</th><th>根拠</th></tr></thead><tbody>
{term_rows}
</tbody></table>

<h3 class="sub" id="arts">{kanji(NA)}の章</h3>
<p class="note">旧用語が多い順です。タイトルから元の記事を開けます。</p>
<table><thead><tr><th>タイトル</th><th>日付</th><th class="num">文字数</th><th>旧用語の内訳</th><th class="num">件数</th></tr></thead><tbody>
{art_rows}
</tbody></table>

<h3 class="sub" id="kijutsu">浄書の試み（上位三章）</h3>
<p class="note">旧用語が特に多かった3本です。</p>
<div class="rws">
{"".join(rw)}
</div>
</section>

{sep}
<section id="ai">
<div class="sh"><span class="ch">第Ⅱ章</span><span class="n">Ⅱ</span><h2>十の<ruby>術式<rt>アルス</rt></ruby></h2></div>
<p class="note">{E(menu["lead"])}</p>
{HINT}
<ol class="cards">{cards}</ol>
</section>

{sep}
<section id="sauna">
<div class="sh"><span class="ch">第Ⅲ章</span><span class="n">Ⅲ</span><h2><ruby class="ov">巡礼<rt>ピルグリメイジ</rt></ruby>の日取り</h2></div>
<p class="note">{E(sauna["lead"])}</p>
<div class="opts">{opts}</div>
<p class="ask">AかBか。どちらも難しければ、別の地平線を。</p>
<div class="act alt">{ALT}</div>
{HINT}
</section>

{sep}
<footer id="ketsu">
<div class="sh"><h2>結</h2></div>
<div class="exits">
<a class="exit" href="#ai"><span class="no">1</span><div><h3>術式を選ぶ</h3><p>十の術式から、先に作ってほしい1つを決める</p></div></a>
<a class="exit" href="#sauna"><span class="no">2</span><div><h3>巡礼の日を決める</h3><p>AかBか、別の週かを返す</p></div></a>
<a class="exit" href="#naoshi"><span class="no">3</span><div><h3>記事を直す</h3><p>置換表と浄書の案で、古い記事を自分で直す</p></div></a>
</div>
<b>汝の答えは、番号ひとつでよい。</b>
<span class="vo">——それでは、よい旅を</span>
<p>契約の証として、この書は検索に出ない。救世主ただひとりに渡している。</p>
</footer>
</div>
<script>const T={TJ};
{JS}</script>
</body></html>
'''
# 文節の切れ目に <wbr> を焼き込む（語中改行を防ぐ。keep-all と組む）
P = budoux.load_default_japanese_parser()
CJK = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
OPEN = re.compile(r"([「『（(【〈《［\[“])")  
def nb(c):  # 開き括弧を含む文節は丸ごと折り返さない
    return f'<span class="nb">{E(c)}</span>' if OPEN.search(c) and len(c) <= 9 else E(c)
def chunks(t):
    r = []
    for c in P.parse(t):
        if r and r[-1][-1] in "「『（(【〈《［[“": r[-1] += c  # 開き括弧を行末に残さない
        else: r.append(c)
    return r
def phrase(body):
    out, skip = [], 0
    for tok in re.split(r"(<[^>]+>)", body):
        if tok.startswith("<"):
            m = re.match(r"<(/?)(ruby|script|style|svg|symbol)\b", tok)
            if m: skip += -1 if m.group(1) else 1
            out.append(tok)
        elif not skip and CJK.search(tok):
            out.append("<wbr>".join(nb(c) for c in chunks(html.unescape(tok))))
        else:
            out.append(tok)
    return "".join(out)
head_, body_ = page.split("<body>", 1)
page = head_ + "<body>" + phrase(body_)
(pathlib.Path(__file__).parent / "index.html").write_text(page)
print("ok", len(page), "rewrites:", sum(1 for i in (1, 2, 3) if (D / f"rewrite{i}.md").exists()))
