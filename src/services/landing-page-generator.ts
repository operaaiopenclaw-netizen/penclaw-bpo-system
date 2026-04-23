// Landing Page generator. Takes a structured brief, optionally runs it
// through Claude for copy generation, and produces a branded HTML page
// using the Orkestra design tokens. The page is persisted to vault/
// and served publicly at /lp/:slug.

import { analyzeWithClaude, isClaudeAvailable } from "./claude-client";
import { logger } from "../utils/logger";

export type LPBrief = {
  product: string;
  audience: string;
  problem: string;
  offer: string;
  cta: string;
  ctaHref: string;
  tone?: "formal" | "direto" | "acolhedor" | "premium";
  highlights?: string[];
  contactEmail?: string;
  contactPhone?: string;
};

export type LPCopy = {
  tagline: string;
  headline: string;
  subhead: string;
  bullets: string[];
  proof: string;
  ctaLabel: string;
  closing: string;
};

const SYSTEM = `Você é um copywriter experiente em landing pages de alta conversão no Brasil. Gere texto objetivo, sem exagero, em português, adequado ao contexto B2B (BPO para eventos e agências). Nunca use emojis. Nunca use superlativos vazios ("o melhor", "incrível"). Mantenha o tom especificado.

Devolva APENAS um objeto JSON com as chaves: tagline, headline, subhead, bullets (array de strings, 3 a 5 itens), proof, ctaLabel, closing. Sem markdown, sem comentários, sem texto fora do JSON.`;

function userPrompt(b: LPBrief): string {
  return JSON.stringify(
    {
      produto: b.product,
      publico: b.audience,
      problema: b.problem,
      oferta: b.offer,
      cta: b.cta,
      tom: b.tone ?? "direto",
      destaques: b.highlights ?? [],
    },
    null,
    2,
  );
}

function stripCodeFence(s: string): string {
  const t = s.trim();
  if (t.startsWith("```")) {
    return t.replace(/^```(?:json)?\s*/, "").replace(/\s*```\s*$/, "");
  }
  return t;
}

function fallbackCopy(b: LPBrief): LPCopy {
  return {
    tagline: b.audience.toUpperCase(),
    headline: b.offer,
    subhead: b.problem,
    bullets: (b.highlights && b.highlights.length ? b.highlights : [b.product]).slice(0, 5),
    proof: "Operação orquestrada do pedido ao fechamento.",
    ctaLabel: b.cta,
    closing: "Fale com nosso time e descubra se a Orkestra encaixa na sua operação.",
  };
}

export async function generateCopy(brief: LPBrief): Promise<LPCopy> {
  if (!isClaudeAvailable()) return fallbackCopy(brief);

  try {
    const res = await analyzeWithClaude({
      systemPrompt: SYSTEM,
      userContent: userPrompt(brief),
      maxTokens: 700,
    });
    const parsed = JSON.parse(stripCodeFence(res.text));
    return {
      tagline: String(parsed.tagline ?? ""),
      headline: String(parsed.headline ?? ""),
      subhead: String(parsed.subhead ?? ""),
      bullets: Array.isArray(parsed.bullets) ? parsed.bullets.map(String) : [],
      proof: String(parsed.proof ?? ""),
      ctaLabel: String(parsed.ctaLabel ?? brief.cta),
      closing: String(parsed.closing ?? ""),
    };
  } catch (err) {
    logger.warn(
      { err: err instanceof Error ? err.message : String(err) },
      "landing-page-generator: Claude call failed, using fallback copy",
    );
    return fallbackCopy(brief);
  }
}

// Kikumon SVG inline so the page is self-contained and prints without
// relying on /ui/favicon.svg when served from /lp/:slug.
const KIKUMON_SVG = `<svg class="mark" viewBox="-70 -70 140 140" aria-hidden="true">
  <g fill="currentColor">
    ${[0, 22.5, 45, 67.5, 90, 112.5, 135, 157.5, 180, 202.5, 225, 247.5, 270, 292.5, 315, 337.5]
      .map(
        (r) =>
          `<path d="M -3 -20 C -10 -28 -13 -44 0 -54 C 13 -44 10 -28 3 -20 C 2 -18 -2 -18 -3 -20 Z" transform="rotate(${r})"/>`,
      )
      .join("\n    ")}
    <circle r="20"/>
  </g>
  <circle r="14" fill="#0B0B0C"/>
  <circle r="8" fill="currentColor"/>
</svg>`;

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function renderLandingPage(
  brief: LPBrief,
  copy: LPCopy,
  opts: { slug: string; lpId: string },
): string {
  const bulletHtml = copy.bullets
    .map((b) => `<li>${esc(b)}</li>`)
    .join("\n      ");

  const contactLine = [
    brief.contactEmail ? `<a href="mailto:${esc(brief.contactEmail)}">${esc(brief.contactEmail)}</a>` : "",
    brief.contactPhone ? `<a href="https://wa.me/${brief.contactPhone.replace(/\D/g, "")}">${esc(brief.contactPhone)}</a>` : "",
  ]
    .filter(Boolean)
    .join(" · ");

  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="${esc(copy.subhead)}">
<title>${esc(copy.headline)} · Orkestra</title>
<meta property="og:title" content="${esc(copy.headline)}">
<meta property="og:description" content="${esc(copy.subhead)}">
<meta name="theme-color" content="#0B0B0C">
<style>
  :root {
    --bg:#0B0B0C; --surface:#141416; --text:#F5F3EF; --text-2:#A8A8AF;
    --border:#26262A; --gold:#C9A961; --emerald:#00B38A;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family:'Inter',-apple-system,system-ui,sans-serif;
    background:
      radial-gradient(900px 600px at 85% 5%, rgba(201,169,97,0.1), transparent 65%),
      radial-gradient(700px 500px at 10% 90%, rgba(0,179,138,0.06), transparent 60%),
      var(--bg);
    color:var(--text); line-height:1.5;
    min-height:100vh;
  }
  .nav {
    position:sticky; top:0; z-index:10; backdrop-filter:blur(12px);
    background:rgba(11,11,12,0.7); border-bottom:1px solid var(--border);
  }
  .nav-inner {
    max-width:1200px; margin:0 auto; padding:14px 32px;
    display:flex; align-items:center; gap:12px;
  }
  .mark { width:26px; height:26px; color:var(--text); }
  .brand-text { font-weight:600; letter-spacing:4px; text-transform:uppercase; font-size:13px; }
  .hero {
    max-width:1200px; margin:0 auto; padding:90px 32px 60px;
    display:grid; grid-template-columns:1.2fr 1fr; gap:60px; align-items:center;
  }
  .tagline {
    color:var(--gold); font-size:12px; letter-spacing:6px;
    text-transform:uppercase; margin-bottom:18px;
  }
  h1 {
    font-size:58px; font-weight:700; letter-spacing:-1.5px; line-height:1.05;
    margin-bottom:22px;
    background:linear-gradient(180deg,#F5F3EF 0%,#8C8C92 140%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  }
  .subhead {
    font-size:19px; color:var(--text-2); max-width:520px; margin-bottom:34px;
  }
  .cta {
    display:inline-flex; align-items:center; gap:10px;
    background:var(--gold); color:var(--bg);
    padding:16px 30px; border-radius:8px;
    font-weight:600; letter-spacing:2px; text-transform:uppercase; font-size:13px;
    text-decoration:none; transition:opacity .15s;
  }
  .cta:hover { opacity:0.9; }
  .hero-mark {
    width:340px; height:340px; color:var(--text);
    justify-self:end; opacity:0.85;
    filter:drop-shadow(0 0 60px rgba(201,169,97,0.28));
  }
  .highlights {
    background:var(--surface); border-top:1px solid var(--border);
    border-bottom:1px solid var(--border);
  }
  .highlights-inner {
    max-width:1200px; margin:0 auto; padding:56px 32px;
  }
  .section-title {
    color:var(--gold); font-size:11px; letter-spacing:5px;
    text-transform:uppercase; margin-bottom:18px;
  }
  ul.bullets {
    list-style:none; display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px;
  }
  ul.bullets li {
    padding:18px 20px; background:var(--bg);
    border:1px solid var(--border); border-radius:10px;
    color:var(--text); font-size:15px;
  }
  ul.bullets li::before {
    content:'—'; color:var(--gold); margin-right:10px; font-weight:600;
  }
  .proof {
    max-width:1200px; margin:0 auto; padding:60px 32px;
    text-align:center;
  }
  .proof blockquote {
    font-size:24px; color:var(--text); line-height:1.4;
    max-width:760px; margin:0 auto;
    border-left:3px solid var(--gold); padding-left:22px; text-align:left;
  }
  .closing {
    background:var(--surface); border-top:1px solid var(--border);
  }
  .closing-inner {
    max-width:760px; margin:0 auto; padding:70px 32px; text-align:center;
  }
  .closing h2 {
    font-size:28px; font-weight:700; letter-spacing:-0.5px; margin-bottom:18px;
  }
  .closing p { color:var(--text-2); font-size:16px; margin-bottom:26px; }
  footer {
    max-width:1200px; margin:0 auto; padding:28px 32px;
    display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;
    border-top:1px solid var(--border);
    color:var(--text-2); font-size:11px; letter-spacing:2px; text-transform:uppercase;
  }
  footer a { color:var(--text-2); text-decoration:none; margin-left:18px; }
  footer a:hover { color:var(--gold); }
  @media (max-width: 900px) {
    .hero { grid-template-columns:1fr; padding:60px 24px; gap:32px; }
    .hero-mark { width:200px; height:200px; justify-self:center; }
    h1 { font-size:42px; }
  }
</style>
</head>
<body>
<header class="nav">
  <div class="nav-inner">
    ${KIKUMON_SVG.replace('class="mark"', 'class="mark" style="width:26px;height:26px"')}
    <div class="brand-text">Orkestra</div>
  </div>
</header>

<section class="hero">
  <div>
    <div class="tagline">${esc(copy.tagline)}</div>
    <h1>${esc(copy.headline)}</h1>
    <p class="subhead">${esc(copy.subhead)}</p>
    <a class="cta" href="${esc(brief.ctaHref)}">${esc(copy.ctaLabel)}</a>
  </div>
  <div>${KIKUMON_SVG.replace('class="mark"', 'class="hero-mark"')}</div>
</section>

<section class="highlights">
  <div class="highlights-inner">
    <div class="section-title">Por que Orkestra</div>
    <ul class="bullets">
      ${bulletHtml}
    </ul>
  </div>
</section>

<section class="proof">
  <blockquote>${esc(copy.proof)}</blockquote>
</section>

<section class="closing">
  <div class="closing-inner">
    <h2>${esc(copy.closing)}</h2>
    <p>${esc(brief.offer)}</p>
    <a class="cta" href="${esc(brief.ctaHref)}">${esc(copy.ctaLabel)}</a>
  </div>
</section>

<footer>
  <div>© Orkestra · Orchestrated Operations</div>
  <div>
    ${contactLine}
    <a href="/ui/privacy.html">Privacidade</a>
  </div>
</footer>

<!-- lp-id:${opts.lpId} · slug:${opts.slug} -->
</body>
</html>`;
}
