#!/usr/bin/env python3
"""data/ から index.html を生成する。rewrite1..3.md が置かれたら再実行で差し込まれる。"""
import json, html, re, pathlib
from urllib.parse import urlparse

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
        if s.startswith("#"):
            if on: break
            on = "変更点サマリー" in s; continue
        if on and s:
            lines.append(re.sub(r"\*\*(.+?)\*\*", r"\1", re.sub(r"^[-*]\s+", "", s)))
            if len(lines) == n: break
    return lines

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
rows = sorted(arts, key=lambda a: (-a["total"], a["date"]), reverse=False)
rows = sorted(arts, key=lambda a: (a["total"], a["date"]), reverse=True)
def chips(a):
    if not a["hits"]: return '<span class="none">なし</span>'
    return "".join(f'<span class="chip">{E(h["old"])} <b>{h["count"]}</b></span>' for h in a["hits"])
art_rows = "".join(
    f'<tr><td class="main"><a href="{E(a["url"])}" target="_blank" rel="noopener">{E(a["title"])}</a></td>'
    f'<td data-l="日付">{a["date"].replace("-", ".")}</td>'
    f'<td data-l="文字数" class="num">{a["chars"]:,}</td>'
    f'<td data-l="旧用語の内訳" class="chips">{chips(a)}</td>'
    f'<td data-l="件数" class="num">{a["total"]}</td></tr>'
    for a in rows)

# ---- 書き直し案 上位3本 ----
slugs = ["ads-introduction3", "3c-analysis", "ads-introduction2"]
rw = []
for i, slug in enumerate(slugs, 1):
    a = next(x for x in arts if slug in x["url"])
    f = D / f"rewrite{i}.md"
    orig = D / f"orig{i}.txt"
    head = f'<span class="dn">{i}</span><span class="ds"><b>{E(a["title"])}</b>'
    meta_line = f'<span class="dm">旧用語 {a["total"]}箇所</span>'
    if f.exists():
        t = f.read_text()
        sl = summary_lines(t)
        sub = "".join(f'<span class="dl">{E(x)}</span>' for x in sl) or '<span class="dl">変更点サマリーは本文の冒頭にあります</span>'
        o = ""
        if orig.exists():
            paras = [p.strip() for p in re.split(r"\n\s*\n", orig.read_text().split("\n", 1)[-1]) if p.strip()]
            o = '<details class="orig"><summary>原文を見る</summary>' + "".join(f"<p>{E(re.sub(chr(10), ' ', p))}</p>" for p in paras) + "</details>"
        rw.append(f'<details class="rw"><summary>{head}{sub}</span>{meta_line}</summary><div class="rwbody">{md(t)}{o}</div></details>')
    else:
        rw.append(f'<div class="rw pend">{head}<span class="dl">書き直し案は準備中</span></span>{meta_line}</div>')

# ---- 10案 ----
cards = "".join(
    f'<li class="card"><span class="no">{it["n"]}</span><div><h3>{E(it["name"])}</h3>'
    f'<p class="io"><span class="lab">入力</span><span>{E(it["in"])}</span></p>'
    f'<p class="io"><span class="lab">出力</span><span>{E(it["out"])}</span></p></div></li>'
    for it in menu["items"])

# ---- サウナ ----
opts = "".join(
    f'<div class="opt"><span class="k">{E(o["k"])}</span><div><h3>{E(o["dates"])}</h3><p>{E(o["note"])}</p></div></div>'
    for o in sauna["options"])

TITLE = "めしあぴ便利帳"
DESC = "運用型広告研究所の鮮度チェックと、AIでできること10案"
URL = "https://yukitchy.github.io/meshiapi-benricho/"

page = f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<meta name="robots" content="noindex,nofollow">
<meta property="og:type" content="website"><meta property="og:locale" content="ja_JP">
<meta property="og:title" content="{TITLE}"><meta property="og:description" content="{DESC}">
<meta property="og:url" content="{URL}"><meta property="og:image" content="{URL}og.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@400;500;700;900&family=Inter:wght@500;600;800&display=swap" rel="stylesheet">
<style>
:root{{--bg:#fffdf8;--card:#fff;--tint:#faf8f1;--ink:#14151a;--mute:#6b6a63;--line:#e7e3d8;--acc:#1f4fd8;--old:#c2410c;--r:10px;--r-s:4px;--pad:20px;--gap:14px;--font:"Zen Kaku Gothic New",Inter,-apple-system,"Hiragino Sans",sans-serif;--font-num:Inter,var(--font);--w-head:900;--w-sub:700}}
*{{box-sizing:border-box;min-width:0}}
html,body{{max-width:100%;overflow-x:hidden}}
body{{margin:0;font-family:var(--font);color:var(--ink);background:var(--bg);line-height:1.7;font-size:16px;word-break:auto-phrase}}
a{{color:var(--acc);text-underline-offset:3px}}
.wrap{{max-width:1040px;margin:0 auto;padding:0 var(--pad)}}
h1,h2,h3,h4,p{{margin:0}}
h1,h2,h3{{text-wrap:balance}}
header{{padding:56px 0 40px}}
h1{{font-weight:var(--w-head);font-size:clamp(40px,7vw,64px);line-height:1.1;letter-spacing:-.02em;white-space:nowrap}}
.lead{{font-size:18px;color:var(--mute);margin-top:14px;max-width:34em}}
.facts{{display:flex;flex-wrap:wrap;gap:4px 24px;margin:22px 0 0;padding:0;list-style:none;font-size:14px;color:var(--mute)}}
.facts b{{color:var(--ink);font-weight:700}}
section{{padding:44px 0 8px;border-top:1px solid var(--line)}}
.sh{{display:flex;align-items:baseline;gap:14px;margin-bottom:22px}}
.sh .n{{font:800 15px/1 var(--font-num);letter-spacing:.1em;color:var(--acc)}}
h2{{font-weight:var(--w-head);font-size:clamp(28px,4.6vw,38px);line-height:1.2;letter-spacing:-.02em;white-space:nowrap}}
h3.sub{{font-weight:700;font-size:20px;margin:40px 0 14px;letter-spacing:-.01em}}
.note{{color:var(--mute);font-size:15px;margin:-6px 0 16px}}
.tiles{{display:grid;grid-template-columns:repeat(4,1fr);gap:var(--gap)}}
.tile{{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:20px 20px 18px}}
.tile .l{{display:block;font-size:14px;color:var(--mute);font-weight:500}}
.tile .v{{display:block;margin-top:8px;font:800 clamp(40px,5.4vw,56px)/1 var(--font-num);letter-spacing:-.03em;white-space:nowrap}}
.tile .v small{{font:700 16px/1 var(--font);letter-spacing:0;margin-left:4px;color:var(--mute)}}
.tile.hot .v{{color:var(--old)}}
table{{width:100%;border-collapse:collapse;font-size:15px;background:var(--card);border:1px solid var(--line);border-radius:var(--r);overflow:hidden}}
th{{text-align:left;font-size:13px;font-weight:700;color:var(--mute);padding:11px 14px;border-bottom:1px solid var(--line);background:var(--tint);white-space:nowrap}}
td{{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top;line-height:1.55}}
tr:last-child td{{border-bottom:0}}
.num{{text-align:right;font-family:var(--font-num);font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap}}
th.num{{font-family:inherit}}
.old{{color:var(--old);font-weight:700}}
.new{{font-weight:700}}
.chips{{display:flex;flex-wrap:wrap;gap:4px 6px}}
.chip{{font-size:12.5px;border:1px solid var(--line);border-radius:var(--r-s);padding:1px 7px;white-space:nowrap;background:var(--tint)}}
.chip b{{font-family:var(--font-num);color:var(--old)}}
.none{{color:var(--mute);font-size:13px}}
td.main a{{font-weight:500}}
.rws{{display:grid;gap:12px}}
.rw{{background:var(--card);border:1px solid var(--line);border-radius:var(--r)}}
.rw>summary,.rw.pend{{display:flex;align-items:flex-start;gap:14px;padding:16px 18px;cursor:pointer;list-style:none}}
.rw.pend{{cursor:default}}
.rw>summary::-webkit-details-marker{{display:none}}
.rw>summary::after{{content:"開く";margin-left:auto;flex:none;font-size:13px;font-weight:700;color:var(--acc);border:1px solid var(--acc);border-radius:999px;padding:3px 12px}}
.rw[open]>summary::after{{content:"閉じる"}}
.dn{{flex:none;font:800 26px/1.1 var(--font-num);color:var(--acc);width:1.1em}}
.ds{{display:flex;flex-direction:column;gap:3px;flex:1}}
.ds b{{font-weight:700;line-height:1.5}}
.dl{{font-size:14px;color:var(--mute);line-height:1.6}}
.pend .dl{{color:var(--old)}}
.dm{{flex:none;font-size:13px;color:var(--mute);white-space:nowrap}}
.rwbody{{border-top:1px solid var(--line);padding:22px 24px 26px;max-width:46em}}
.rwbody h4{{font-size:17px;font-weight:700;margin:26px 0 8px}}
.rwbody h4:first-child{{margin-top:0}}
.rwbody p{{line-height:2;margin:0 0 12px}}
.rwbody ul{{margin:0 0 14px;padding-left:1.3em;line-height:1.95}}
.orig{{margin-top:24px;border-top:1px dashed var(--line);padding-top:14px}}
.orig summary{{cursor:pointer;color:var(--acc);font-size:14px;font-weight:700}}
.orig p{{font-size:14px;color:var(--mute);line-height:1.9;margin-top:10px}}
.cards{{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}
.card{{display:flex;gap:18px;background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:22px 22px 24px}}
.no{{flex:none;width:1.25em;font:800 46px/1 var(--font-num);letter-spacing:-.04em;color:var(--acc)}}
.card h3{{font-size:19px;font-weight:700;line-height:1.4;margin:2px 0 12px}}
.io{{display:grid;grid-template-columns:2.6em 1fr;gap:10px;font-size:15px;line-height:1.65;margin-top:8px}}
.lab{{font-size:12px;font-weight:700;color:var(--mute);border:1px solid var(--line);border-radius:var(--r-s);text-align:center;height:1.7em;line-height:1.6em;margin-top:.1em;background:var(--tint)}}
.opts{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}
.opt{{display:flex;gap:18px;background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:22px}}
.opt .k{{flex:none;font:800 46px/1 var(--font-num);color:var(--acc);width:1em}}
.opt h3{{font-size:19px;font-weight:700;line-height:1.45;margin:2px 0 6px}}
.opt p{{color:var(--mute);font-size:15px}}
.ask{{margin-top:18px}}
footer{{margin-top:48px;border-top:1px solid var(--line);padding:30px 0 56px}}
footer b{{display:block;font-size:20px;font-weight:700;margin-bottom:6px}}
footer p{{color:var(--mute);font-size:14px}}
@media(max-width:860px){{
 .tiles{{grid-template-columns:repeat(2,1fr)}}
 .cards,.opts{{grid-template-columns:1fr}}
}}
@media(max-width:720px){{
 .wrap{{padding:0 16px}}
 header{{padding:40px 0 32px}}
 thead{{display:none}}
 table,tbody{{display:block;background:none;border:0}}
 tr{{display:block;background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:12px 14px;margin-bottom:10px}}
 td{{display:flex;gap:12px;justify-content:space-between;align-items:baseline;border:0;padding:3px 0}}
 td::before{{content:attr(data-l);flex:none;width:5.5em;font-size:12px;font-weight:700;color:var(--mute)}}
 td.main{{display:block;padding:0 0 6px}}
 td.main::before{{content:none}}
 td.num,td.chips{{text-align:left}}
 td.num{{justify-content:flex-start}}
 td.num::before{{width:5.5em}}
 td>a,td.new,td:not(.main):not(.num):not(.chips){{flex:1}}
 td.chips{{display:flex}}
 td.chips .chip,td.chips .none{{flex:none}}
 td.chips{{flex-wrap:wrap}}
 td.chips::before{{width:100%}}
 .rw>summary,.rw.pend{{flex-wrap:wrap;padding:14px}}
 .rw>summary::after{{margin-left:calc(1.1em + 14px)}}
 .dm{{margin-left:calc(1.1em + 14px);flex-basis:100%}}
 .rwbody{{padding:18px 16px 22px}}
 .card,.opt{{padding:18px 16px;gap:6px;flex-direction:column}}
 .card h3,.opt h3{{font-size:17px}}
 .tile .l{{font-size:13px}}
 .no,.opt .k{{font-size:38px}}
 .tile{{padding:16px 14px}}
}}
</style></head><body>
<div class="wrap">
<header>
<h1>{TITLE}</h1>
<p class="lead">{DESC}</p>
<ul class="facts"><li>日付 <b>2026年10月12日</b></li><li>差出人 <b>ユウキ</b></li></ul>
</header>

<section id="fresh">
<div class="sh"><span class="n">01</span><h2>鮮度チェック</h2></div>
<div class="tiles">
<div class="tile"><span class="l">記事</span><span class="v">{meta["articles"]}<small>本</small></span></div>
<div class="tile hot"><span class="l">旧用語を含む記事</span><span class="v">{meta["with_hits"]}<small>本</small></span></div>
<div class="tile hot"><span class="l">旧用語</span><span class="v">{meta["total_hits"]}<small>箇所</small></span></div>
<div class="tile"><span class="l">最終更新</span><span class="v">2021<small>年4月</small></span></div>
</div>

<h3 class="sub">旧用語の一覧</h3>
<p class="note">ブログ内で使われている古い呼び方と、いまの公式名称です。</p>
<table><thead><tr><th>旧用語</th><th>現行</th><th>メモ</th><th class="num">件数</th><th>根拠</th></tr></thead><tbody>
{term_rows}
</tbody></table>

<h3 class="sub">記事{meta["articles"]}本の一覧</h3>
<p class="note">旧用語が多い順です。タイトルから元の記事を開けます。</p>
<table><thead><tr><th>タイトル</th><th>日付</th><th class="num">文字数</th><th>旧用語の内訳</th><th class="num">件数</th></tr></thead><tbody>
{art_rows}
</tbody></table>

<h3 class="sub">書き直し案 上位3本</h3>
<p class="note">旧用語が特に多かった3本です。</p>
<div class="rws">
{"".join(rw)}
</div>
</section>

<section id="ai">
<div class="sh"><span class="n">02</span><h2>{E(menu["title"])}</h2></div>
<p class="note">{E(menu["lead"])}</p>
<ol class="cards">{cards}</ol>
</section>

<section id="sauna">
<div class="sh"><span class="n">03</span><h2>{E(sauna["title"])}</h2></div>
<p class="note">{E(sauna["lead"])}</p>
<div class="opts">{opts}</div>
<p class="ask">{E(sauna["ask"])}</p>
</section>

<footer>
<b>返事は番号ひとつで大丈夫です</b>
<p>このページは検索に出ません（樋爪さんだけに渡しています）</p>
</footer>
</div>
</body></html>
'''
(pathlib.Path(__file__).parent / "index.html").write_text(page)
print("ok", len(page), "rewrites:", sum(1 for i in (1, 2, 3) if (D / f"rewrite{i}.md").exists()))
