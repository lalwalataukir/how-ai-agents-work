/* Site-wide search for the Agent Field Guides.
   Adds a Search button to the top bar of any page that loads this script. The index
   (search-index.js, built by build-search.py) is fetched the first time search opens. */
(function(){
"use strict";
const bar = document.querySelector(".topbar-in");
if(!bar || document.getElementById("gsBtn")) return;
if(window.frameElement && document.getElementById("demo-only")) return;   // a demo embedded in the demo lab

const BASE = (document.currentScript && document.currentScript.src) ? document.currentScript.src.replace(/[^/]*$/, "") : "";
const SITE = "https://lalwalataukir.github.io/how-ai-agents-work/";
const onSite = /^(localhost|127\.0\.0\.1)$/.test(location.hostname) || location.hostname.endsWith("github.io");
const here = location.pathname.split("/").pop() || "index.html";
const esc = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/* ---------- Styles (use each page's own colour tokens) ---------- */
const css = document.createElement("style");
css.textContent = `
.gs-btn{flex:none;display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);background:var(--surface);color:var(--muted);border-radius:999px;padding:5px 10px 5px 11px;font:inherit;font-size:.85rem;cursor:pointer}
.gs-btn:hover{color:var(--ink);border-color:var(--accent)}
.gs-btn svg{width:15px;height:15px;flex:none}
.gs-btn kbd{font-family:var(--font-mono, monospace);font-size:.7rem;border:1px solid var(--line);border-radius:4px;padding:0 5px;line-height:1.4}
@media (max-width:760px){.gs-btn .gs-l,.gs-btn kbd{display:none}.gs-btn{padding:6px 9px}}
.gs-ov{position:fixed;inset:0;z-index:100;background:rgba(5,3,10,.62);display:flex;justify-content:center;align-items:flex-start;padding:min(10vh,90px) 16px 16px}
.gs-ov[hidden]{display:none}
.gs-box{width:100%;max-width:680px;max-height:min(76vh,720px);display:flex;flex-direction:column;background:var(--surface);color:var(--ink);border:1px solid var(--line);border-radius:14px;box-shadow:0 24px 60px rgba(0,0,0,.45);overflow:hidden}
.gs-top{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid var(--line)}
.gs-top svg{width:18px;height:18px;color:var(--muted);flex:none}
.gs-in{flex:1;min-width:0;font:inherit;font-size:1.05rem;background:transparent;color:var(--ink);border:0;outline:none;padding:4px 0}
.gs-in:focus,.gs-in:focus-visible{outline:none;box-shadow:none}
.gs-x{flex:none;font:inherit;font-size:.8rem;border:1px solid var(--line);background:var(--surface-2);color:var(--muted);border-radius:6px;padding:3px 8px;cursor:pointer}
.gs-meta{padding:8px 16px;font-size:.78rem;color:var(--muted);font-family:var(--font-mono, monospace);border-bottom:1px solid var(--line)}
.gs-list{list-style:none;margin:0;padding:6px;overflow-y:auto;flex:1}
.gs-list li{margin:0}
.gs-list a{display:grid;gap:3px;padding:10px 12px;border-radius:10px;text-decoration:none;color:var(--ink)}
.gs-list li[aria-selected="true"] a{background:var(--accent-soft, var(--surface-2));outline:1.5px solid var(--accent)}
.gs-where{font-family:var(--font-mono, monospace);font-size:.7rem;letter-spacing:.04em;text-transform:uppercase;color:var(--accent)}
.gs-h{font-family:var(--font-display, inherit);font-weight:700;font-size:.98rem;line-height:1.3}
.gs-h span{font-weight:400;color:var(--muted)}
.gs-snip{font-size:.86rem;color:var(--muted);line-height:1.45}
.gs-list mark{background:var(--accent-soft, var(--surface-2));color:var(--ink);border-radius:3px;padding:0 1px;box-shadow:inset 0 -2px 0 var(--accent)}
.gs-empty{padding:22px 16px;color:var(--muted);font-size:.92rem}
.gs-foot{display:flex;flex-wrap:wrap;gap:4px 14px;padding:8px 16px;border-top:1px solid var(--line);font-size:.75rem;color:var(--muted)}
.gs-foot kbd{font-family:var(--font-mono, monospace);border:1px solid var(--line);border-radius:4px;padding:0 4px}
.gs-flash{outline:2px solid var(--accent);outline-offset:4px;border-radius:6px;transition:outline-color 1.5s}
@media (max-width:600px){.gs-ov{padding:0}.gs-box{max-width:none;max-height:none;height:100%;border-radius:0;border:0}}
`;
document.head.appendChild(css);

/* ---------- Button in the top bar ---------- */
const ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/></svg>';
const btn = document.createElement("button");
btn.type = "button"; btn.id = "gsBtn"; btn.className = "gs-btn";
btn.setAttribute("aria-label", "Search the guides");
btn.innerHTML = ICON + '<span class="gs-l">Search</span><kbd>/</kbd>';
const theme = document.getElementById("themeBtn");
bar.insertBefore(btn, theme && theme.parentElement === bar ? theme : null);

/* ---------- Overlay ---------- */
const ov = document.createElement("div");
ov.className = "gs-ov"; ov.hidden = true;
ov.innerHTML =
  '<div class="gs-box" role="dialog" aria-modal="true" aria-label="Search the guides">' +
    '<div class="gs-top">' + ICON +
      '<input class="gs-in" id="gsIn" type="search" autocomplete="off" spellcheck="false" placeholder="Search all modules, e.g. checkpoint, MCP, p95" role="combobox" aria-expanded="true" aria-controls="gsList" aria-autocomplete="list">' +
      '<button type="button" class="gs-x" id="gsClose">Esc</button>' +
    '</div>' +
    '<div class="gs-meta" id="gsMeta" aria-live="polite"></div>' +
    '<ul class="gs-list" id="gsList" role="listbox" aria-label="Results"></ul>' +
    '<div class="gs-foot"><span><kbd>↑</kbd> <kbd>↓</kbd> move</span><span><kbd>Enter</kbd> open</span><span><kbd>Esc</kbd> close</span></div>' +
  '</div>';
document.body.appendChild(ov);
const input = ov.querySelector("#gsIn"), list = ov.querySelector("#gsList"), meta = ov.querySelector("#gsMeta");

/* ---------- Index loading ---------- */
let loading = null;
function loadIndex(){
  if(window.GUIDES_INDEX) return Promise.resolve(window.GUIDES_INDEX);
  if(loading) return loading;
  loading = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = BASE + "search-index.js";
    s.onload = () => window.GUIDES_INDEX ? resolve(window.GUIDES_INDEX) : reject(new Error("empty index"));
    s.onerror = () => { loading = null; reject(new Error("index not found")); };
    document.head.appendChild(s);
  });
  return loading;
}

/* ---------- Search ---------- */
const MAX = 30;
let results = [], active = -1, lastFocus = null;

function search(idx, q){
  const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
  if(!terms.length) return [];
  const phrase = terms.join(" ");
  const out = [];
  for(const e of idx.entries){
    const h = e.h.toLowerCase(), s = e.s.toLowerCase(), t = e.t.toLowerCase();
    let score = 0, ok = true;
    for(const w of terms){
      const inH = h.includes(w), inS = s.includes(w);
      const n = t.split(w).length - 1;
      if(!inH && !inS && !n){ ok = false; break; }
      score += (inH ? 8 : 0) + (inS ? 5 : 0) + Math.min(n, 3);
      if(e.g && inH) score += 6;                                  // a glossary term that matches by name
      if(new RegExp("\\b" + reEsc(w) + "\\b").test(h + " " + s)) score += 3;   // whole-word heading match
    }
    if(!ok) continue;
    if(terms.length > 1 && (h.includes(phrase) || s.includes(phrase) || t.includes(phrase))) score += 6;
    out.push({e, score});
  }
  out.sort((a, b) => b.score - a.score || a.e.p - b.e.p);
  return out.slice(0, MAX);
}

function snippet(text, terms){
  const lower = text.toLowerCase();
  let at = -1;
  for(const w of terms){ const i = lower.indexOf(w); if(i >= 0 && (at < 0 || i < at)) at = i; }
  let start = Math.max(0, at - 70), end = Math.min(text.length, start + 190);
  if(start > 0){ const sp = text.indexOf(" ", start); if(sp > 0 && sp < at) start = sp + 1; }
  let snip = esc(text.slice(start, end));
  for(const w of terms) snip = snip.replace(new RegExp("\\b(" + reEsc(esc(w)) + ")", "gi"), "<mark>$1</mark>");   // only at the start of a word
  return (start > 0 ? "…" : "") + snip + (end < text.length ? "…" : "");
}

/* The word in the section text that the first search term falls inside, for the text fragment */
function matchedWords(e, terms){
  const src = e.s + " " + e.h + " " + e.t;
  const words = terms.map(w => { const m = src.match(new RegExp("[\\w'-]*" + reEsc(w) + "[\\w'-]*", "i")); return m ? m[0] : ""; }).filter(Boolean);
  const phrase = terms.join(" ");
  const i = src.toLowerCase().indexOf(phrase);
  return terms.length > 1 && i >= 0 ? src.substr(i, phrase.length) : (words[0] || "");
}

function hrefFor(idx, e, terms){
  const page = idx.pages[e.p];
  const word = e.g ? "" : matchedWords(e, terms);
  const frag = e.g ? "?q=" + encodeURIComponent(e.h) : "#" + e.a + (word ? ":~:text=" + encodeURIComponent(word) : "");
  return (onSite ? page : SITE + page) + frag;
}

function render(idx){
  const q = input.value.trim();
  const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
  results = q ? search(idx, q) : [];
  active = results.length ? 0 : -1;
  if(!q){ meta.textContent = idx.entries.length + " sections and terms across all modules"; list.innerHTML = ""; return; }
  meta.textContent = results.length ? (results.length === MAX ? "Top " + MAX + " results" : results.length + " result" + (results.length === 1 ? "" : "s")) : "";
  if(!results.length){ list.innerHTML = '<li class="gs-empty">No matches for “' + esc(q) + '”. Try a shorter or different word.</li>'; return; }
  list.innerHTML = results.map((r, i) => {
    const e = r.e;
    const where = idx.labels[e.p];
    const head = e.g ? esc(e.h) : esc(e.h) + (e.s ? " <span>› " + esc(e.s) + "</span>" : "");
    return '<li role="option" id="gsOpt' + i + '" aria-selected="' + (i === active) + '"><a href="' + esc(hrefFor(idx, e, terms)) + '" tabindex="-1"' + (onSite ? "" : ' target="_blank" rel="noopener"') + ' data-i="' + i + '">' +
      '<span class="gs-where">' + esc(where) + '</span><span class="gs-h">' + head + '</span><span class="gs-snip">' + snippet(e.t, terms) + '</span></a></li>';
  }).join("");
  input.setAttribute("aria-activedescendant", active >= 0 ? "gsOpt" + active : "");
}

function setActive(i){
  const opts = list.querySelectorAll('[role="option"]');
  if(!opts.length) return;
  active = (i + opts.length) % opts.length;
  opts.forEach((o, k) => o.setAttribute("aria-selected", String(k === active)));
  opts[active].scrollIntoView({block:"nearest"});
  input.setAttribute("aria-activedescendant", "gsOpt" + active);
}

/* Same-page results: scroll to the section and outline the first element that contains the word */
function jumpHere(a){
  const url = new URL(a.href, location.href);
  const [anchor, dir] = url.hash.slice(1).split(":~:text=");
  const sec = document.getElementById(anchor);
  if(!sec) return false;
  close();
  const word = dir ? decodeURIComponent(dir).toLowerCase() : "";
  let target = sec;
  if(word){
    const walk = document.createTreeWalker(sec, NodeFilter.SHOW_TEXT);
    let n;
    while((n = walk.nextNode())){
      if(n.nodeValue.toLowerCase().includes(word) && n.parentElement.offsetParent !== null){ target = n.parentElement; break; }
    }
  }
  history.replaceState(null, "", "#" + anchor);
  target.scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: target === sec ? "start" : "center"});
  target.classList.add("gs-flash");
  setTimeout(() => target.classList.remove("gs-flash"), 1800);
  return true;
}

function go(i){
  const a = list.querySelector('a[data-i="' + i + '"]');
  if(!a) return;
  const page = new URL(a.href, location.href).pathname.split("/").pop() || "index.html";
  if(onSite && page === here && jumpHere(a)) return;
  if(a.target === "_blank") window.open(a.href, "_blank", "noopener"); else location.href = a.href;
}

/* ---------- Open / close ---------- */
function open(){
  if(!ov.hidden) return;
  lastFocus = document.activeElement;
  ov.hidden = false;
  document.documentElement.style.overflow = "hidden";
  input.focus(); input.select();
  meta.textContent = "Loading the search index…";
  loadIndex().then(render).catch(() => { meta.textContent = "Search isn't available here. Try the site at lalwalataukir.github.io/how-ai-agents-work."; });
}
function close(){
  if(ov.hidden) return;
  ov.hidden = true;
  document.documentElement.style.overflow = "";
  if(lastFocus && lastFocus.focus) lastFocus.focus();
}

btn.addEventListener("click", open);
ov.querySelector("#gsClose").addEventListener("click", close);
ov.addEventListener("mousedown", e => { if(e.target === ov) close(); });
input.addEventListener("input", () => { if(window.GUIDES_INDEX) render(window.GUIDES_INDEX); });
list.addEventListener("click", e => { const a = e.target.closest("a[data-i]"); if(!a) return; e.preventDefault(); go(+a.dataset.i); });
list.addEventListener("mousemove", e => { const a = e.target.closest("a[data-i]"); if(a && +a.dataset.i !== active) setActive(+a.dataset.i); });
ov.addEventListener("keydown", e => {
  if(e.key === "Escape"){ e.preventDefault(); e.stopPropagation(); close(); }
  else if(e.key === "ArrowDown"){ e.preventDefault(); setActive(active + 1); }
  else if(e.key === "ArrowUp"){ e.preventDefault(); setActive(active - 1); }
  else if(e.key === "Enter" && active >= 0){ e.preventDefault(); go(active); }
  else if(e.key === "Tab"){                       // keep focus inside the dialog
    e.preventDefault();
    const closeBtn = ov.querySelector("#gsClose");
    (document.activeElement === input ? closeBtn : input).focus();
  }
});
document.addEventListener("keydown", e => {
  const typing = e.target.closest && e.target.closest("input,textarea,select,[contenteditable]");
  if((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)){ e.preventDefault(); ov.hidden ? open() : close(); }
  else if(e.key === "/" && !typing && ov.hidden && !e.metaKey && !e.ctrlKey && !e.altKey){ e.preventDefault(); open(); }
});
})();
