/* Links every mention of a tool in the page text to its official documentation.
   To add or change a tool, edit TOOLS below. Names are matched case-sensitively,
   on whole words, longest first. */
(function(){
"use strict";
if(window.frameElement && document.getElementById("demo-only")) return;   // a demo embedded in the demo lab
const main = document.querySelector("main");
if(!main) return;

const TOOLS = [
  {names:["LangChain Inc.", "LangChain Inc", "LangChain"], url:"https://docs.langchain.com/oss/python/langchain/overview", what:"Framework of building blocks for LLM apps"},
  {names:["LangGraph Platform", "LangGraph"], url:"https://docs.langchain.com/oss/python/langgraph/overview", what:"Library for building agents as graphs of steps"},
  {names:["LangSmith Deployment", "LangSmith Studio", "LangSmith"], url:"https://docs.langchain.com/langsmith/home", what:"LangChain's tracing, evaluation and deployment platform"},
  {names:["Langfuse Cloud", "Langfuse"], url:"https://langfuse.com/docs", what:"Open-source tracing, prompt management and evals"},
  {names:["LlamaIndex"], url:"https://docs.llamaindex.ai/", what:"Framework for RAG over your own documents"},
  {names:["OpenAI Agents SDK"], url:"https://openai.github.io/openai-agents-python/", what:"OpenAI's lightweight agent framework"},
  {names:["Claude Agent SDK"], url:"https://code.claude.com/docs/en/agent-sdk/overview", what:"Anthropic's SDK for building agents with Claude"},
  {names:["Google's ADK", "Google ADK"], url:"https://google.github.io/adk-docs/", what:"Google's Agent Development Kit"},
  {names:["CrewAI"], url:"https://docs.crewai.com/", what:"Framework for role-based teams of agents"},
  {names:["Pydantic AI"], url:"https://ai.pydantic.dev/", what:"Type-safe Python agent framework"},
  {names:["Temporal"], url:"https://docs.temporal.io/", what:"Durable workflow engine for long-running jobs"},
  {names:["Arize Phoenix"], url:"https://arize.com/docs/phoenix", what:"Open-source LLM tracing and evals"},
  {names:["Braintrust"], url:"https://www.braintrust.dev/docs", what:"Platform for evals, datasets and prompt experiments"},
  {names:["Helicone"], url:"https://docs.helicone.ai/", what:"Open-source LLM logging proxy"},
  {names:["W&B Weave"], url:"https://weave-docs.wandb.ai/", what:"Tracing and evals from Weights & Biases"},
  {names:["Datadog LLM Observability", "Datadog"], url:"https://docs.datadoghq.com/llm_observability/", what:"LLM tracing inside Datadog"},
  {names:["OpenTelemetry"], url:"https://opentelemetry.io/docs/", what:"Open standard for traces, metrics and logs"},
  {names:["Model Context Protocol", "MCP"], url:"https://modelcontextprotocol.io/", what:"Open standard for connecting AI apps to tools and data"},
  {names:["LiteLLM"], url:"https://docs.litellm.ai/", what:"One interface and proxy for many model providers"},
  {names:["Vercel AI SDK"], url:"https://ai-sdk.dev/docs", what:"TypeScript toolkit for AI apps"},
  {names:["ClickHouse"], url:"https://clickhouse.com/docs", what:"Analytics database"},
  {names:["OWASP Top 10 for LLM applications", "OWASP"], url:"https://genai.owasp.org/llm-top-10/", what:"The OWASP list of top security risks for LLM apps"},
  {names:["uv"], url:"https://docs.astral.sh/uv/", what:"Installs Python, manages a project's packages and runs its code"},
  {names:["VS Code", "Visual Studio Code"], url:"https://code.visualstudio.com/docs", what:"Free code editor with a built-in terminal"},
  {names:["GitHub Copilot"], url:"https://docs.github.com/en/copilot", what:"AI coding assistant inside your editor"},
  {names:["GitHub"], url:"https://docs.github.com/en/get-started", what:"Hosts git repositories online"},
  {names:["Claude Code"], url:"https://docs.claude.com/en/docs/claude-code/overview", what:"Anthropic's AI coding assistant for the terminal and editor"},
  {names:["Cursor"], url:"https://cursor.com/docs", what:"Code editor built around an AI assistant"},
  {names:["Pydantic"], url:"https://docs.pydantic.dev/latest/", what:"Python package for describing and checking data with typed classes"},
  {names:["Claude Console"], url:"https://platform.claude.com/", what:"Where you manage API keys, billing and usage for the Claude API"},
  {names:["Chroma"], url:"https://docs.trychroma.com/", what:"Open-source vector database that runs inside your Python program"},
  {names:["pypdf"], url:"https://pypdf.readthedocs.io/", what:"Python package that reads text out of PDF files"},
  {names:["Voyage AI"], url:"https://docs.voyageai.com/", what:"Hosted embedding models, recommended by Anthropic for retrieval"},
  {names:["Node.js"], url:"https://nodejs.org/", what:"JavaScript runtime; some developer tools, like the MCP Inspector, need it"},
  {names:["GitHub Actions"], url:"https://docs.github.com/en/actions", what:"GitHub's built-in CI: runs workflows on pushes and pull requests"},
  {names:["FastAPI"], url:"https://fastapi.tiangolo.com/", what:"Python web framework for APIs, with request checking and streaming"},
  {names:["Uvicorn"], url:"https://www.uvicorn.org/", what:"The web server that runs FastAPI apps"},
  {names:["Render"], url:"https://render.com/docs", what:"Hosting platform with a free tier for web services, deploying from GitHub"},
  {names:["Railway"], url:"https://docs.railway.com/", what:"Usage-priced hosting platform for apps and databases"},
  {names:["Fly.io"], url:"https://fly.io/docs/", what:"Hosting platform that runs apps in small VMs near users"},
  {names:["Koyeb"], url:"https://www.koyeb.com/docs", what:"Serverless hosting platform for web services"},
  {names:["Hugging Face Spaces"], url:"https://huggingface.co/docs/hub/spaces", what:"Free hosting for machine-learning demos, often built with Gradio"},
  {names:["Redis"], url:"https://redis.io/docs/latest/", what:"In-memory database often used for counters, rate limits and caches"},
  {names:["Ollama"], url:"https://docs.ollama.com/", what:"Free app that downloads open-weight models and runs them on your computer"},
  {names:["OBS Studio"], url:"https://obsproject.com/", what:"Free screen recorder for Mac, Windows and Linux"},
  {names:["Loom"], url:"https://www.loom.com/", what:"Screen-recording service that gives each video a shareable link"},
  {names:["httpx"], url:"https://www.python-httpx.org/", what:"Python package for making web requests"},
  {names:["promptfoo"], url:"https://www.promptfoo.dev/docs/intro/", what:"Open-source CLI for testing prompts and running evals"},
  {names:["PostgreSQL", "Postgres"], url:"https://www.postgresql.org/docs/", what:"Open-source relational database"}
];

const byName = new Map();
TOOLS.forEach(t => t.names.forEach(n => byName.set(n, t)));
const names = [...byName.keys()].sort((a, b) => b.length - a.length);
const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const RE = new RegExp("(?<![\\w&-])(" + names.map(reEsc).join("|") + ")(?![\\w-])", "g");
const quick = new RegExp(names.map(reEsc).join("|"));

/* Where a link would be invalid, or would get in the way of a control */
const SKIP = "a,button,code,pre,kbd,svg,script,style,select,option,textarea,input,label,title,.topbar,.gs-ov,.demo,.sb,.rt,#termPop,.tl-tip";

/* ---------- Styles ---------- */
const css = document.createElement("style");
css.textContent = `
a.tool-link{white-space:nowrap;color:inherit;text-decoration:underline;text-decoration-thickness:1.5px;text-underline-offset:3px;text-decoration-color:color-mix(in srgb, var(--accent) 60%, transparent)}
a.tool-link::after{content:"\\2197";font-size:.68em;color:var(--accent);margin-left:.1em;vertical-align:.25em;text-decoration:none;display:inline-block}
a.tool-link:hover,a.tool-link:focus-visible{color:var(--accent);text-decoration-color:var(--accent)}
.tl-tip{position:absolute;z-index:60;max-width:300px;background:var(--surface);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:10px 12px;box-shadow:0 10px 30px rgba(0,0,0,.35);font:inherit;font-size:.86rem;line-height:1.4;display:grid;gap:3px;pointer-events:none}
.tl-tip[hidden]{display:none}
.tl-tip b{font-family:var(--font-display, inherit)}
.tl-tip .tl-k{font-family:var(--font-mono, monospace);font-size:.7rem;letter-spacing:.05em;text-transform:uppercase;color:var(--accent)}
.tl-tip .tl-d{color:var(--muted);font-size:.8rem;font-family:var(--font-mono, monospace);overflow-wrap:anywhere}
@media print{a.tool-link::after{content:none}}
`;
document.head.appendChild(css);

/* ---------- Link the text ---------- */
function linkAll(){
  const walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, {
    acceptNode: n => (!quick.test(n.nodeValue) || n.parentElement.closest(SKIP)) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT
  });
  const nodes = [];
  while(walker.nextNode()) nodes.push(walker.currentNode);
  let count = 0;
  for(const node of nodes){
    const text = node.nodeValue;
    RE.lastIndex = 0;
    let m, last = 0;
    const frag = document.createDocumentFragment();
    while((m = RE.exec(text))){
      const tool = byName.get(m[1]);
      if(m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
      const a = document.createElement("a");
      a.className = "tool-link";
      a.href = tool.url; a.target = "_blank"; a.rel = "noopener";
      a.textContent = m[1];
      a.dataset.tool = tool.names[tool.names.length - 1];
      a.setAttribute("aria-label", m[1] + " (official docs, opens in a new tab)");
      frag.appendChild(a);
      last = m.index + m[1].length;
      count++;
    }
    if(!last) continue;
    if(last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    node.parentNode.replaceChild(frag, node);
  }
  return count;
}

/* ---------- Hover and focus tooltip ---------- */
const tip = document.createElement("div");
tip.className = "tl-tip"; tip.hidden = true; tip.setAttribute("role", "tooltip"); tip.id = "toolTip";
document.body.appendChild(tip);
let tipFor = null;
function show(a){
  const tool = byName.get(a.dataset.tool) || byName.get(a.textContent);
  if(!tool) return;
  tip.innerHTML = "";
  const k = document.createElement("span"); k.className = "tl-k"; k.textContent = "Official docs ↗";
  const b = document.createElement("b"); b.textContent = tool.names[tool.names.length - 1];
  const w = document.createElement("span"); w.textContent = tool.what;
  const d = document.createElement("span"); d.className = "tl-d"; d.textContent = new URL(tool.url).hostname.replace(/^www\./, "");
  tip.append(k, b, w, d);
  tip.hidden = false;
  const vw = document.documentElement.clientWidth, pw = Math.min(300, vw - 32);
  tip.style.width = "auto"; tip.style.maxWidth = pw + "px";
  const r = a.getBoundingClientRect();
  tip.style.left = Math.max(scrollX + 16, Math.min(r.left + scrollX, scrollX + vw - tip.offsetWidth - 16)) + "px";
  tip.style.top = (r.bottom + scrollY + 6) + "px";
  if(tipFor && tipFor !== a) tipFor.removeAttribute("aria-describedby");
  tipFor = a; a.setAttribute("aria-describedby", "toolTip");
}
function hide(){ tip.hidden = true; if(tipFor) tipFor.removeAttribute("aria-describedby"); tipFor = null; }
main.addEventListener("mouseover", e => { const a = e.target.closest("a.tool-link"); if(a && a !== tipFor) show(a); });
main.addEventListener("mouseout", e => { const a = e.target.closest("a.tool-link"); if(a && !a.contains(e.relatedTarget)) hide(); });
main.addEventListener("focusin", e => { const a = e.target.closest("a.tool-link"); if(a) show(a); });
main.addEventListener("focusout", e => { if(e.target.closest("a.tool-link")) hide(); });
addEventListener("scroll", hide, {passive:true});
addEventListener("resize", hide);
document.addEventListener("keydown", e => { if(e.key === "Escape") hide(); });

window.GUIDES_TOOL_LINKS = linkAll();

/* Content redrawn after load, such as the filtered glossary cards, gets linked too */
let pending = null;
const obs = new MutationObserver(muts => {
  if(pending || !muts.some(m => m.addedNodes.length && !(m.target.closest && m.target.closest(SKIP)))) return;
  pending = setTimeout(() => { pending = null; obs.disconnect(); linkAll(); obs.observe(main, {childList:true, subtree:true}); }, 60);
});
obs.observe(main, {childList:true, subtree:true});
})();
