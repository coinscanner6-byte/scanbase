"""
The two pages a visitor sees: the front page and the interactive docs.

Kept out of main.py so the API routes stay readable. Everything here is
plain HTML and CSS built in Python - no build step, no framework, and
nothing to keep in sync.
"""

BRAND = "CoinScanner API"

FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&"
         "family=IBM+Plex+Sans:wght@400;500;600&"
         "family=IBM+Plex+Serif:wght@500;600&display=swap")

TOKENS = """
:root {
  --ink: #141A2E;
  --panel: #1E2742;
  --line: #303C63;
  --text: #F2EFE6;
  --muted: #8B98B8;
  --india: #E8A33D;
  --global: #7FA8D9;
  --up: #6FCF97;
  --down: #E88C8C;
  --sans: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --serif: "IBM Plex Serif", Georgia, "Times New Roman", serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
"""

LANDING = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__BRAND__ — crypto prices built for India</title>
<meta name="description" content="Live crypto prices from ten exchanges, an official price per coin, and the real cost of buying in India.">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="__FONTS__">
<style>
__TOKENS__
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--ink); color: var(--text);
  font-family: var(--sans); font-size: 17px; line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--global); }
a:focus-visible, button:focus-visible { outline: 2px solid var(--india); outline-offset: 3px; }
.wrap { max-width: 1060px; margin: 0 auto; padding: 0 24px; }
.mast {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; padding: 22px 0; border-bottom: 1px solid var(--line);
}
.mark { font-family: var(--serif); font-weight: 600; font-size: 19px; letter-spacing: .01em; }
.mark span { color: var(--india); }
.mast nav { display: flex; gap: 22px; font-size: 15px; }
.mast nav a { color: var(--muted); text-decoration: none; }
.mast nav a:hover { color: var(--text); }

.hero { padding: 64px 0 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 56px; align-items: start; }
h1 {
  font-family: var(--serif); font-weight: 600; font-size: clamp(34px, 4.6vw, 52px);
  line-height: 1.12; margin: 0 0 20px; letter-spacing: -.015em;
}
.lede { color: var(--muted); margin: 0 0 28px; max-width: 46ch; }
.cta { display: flex; gap: 12px; flex-wrap: wrap; }
.btn {
  display: inline-block; padding: 11px 20px; border-radius: 3px; font-size: 15px;
  font-weight: 500; text-decoration: none; border: 1px solid var(--line);
  color: var(--text); background: transparent;
}
.btn.solid { background: var(--india); border-color: var(--india); color: #1A1406; }

/* the rate board - the one loud element on the page */
.board { border: 1px solid var(--line); background: var(--panel); border-radius: 4px; }
.board-head {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 14px 20px; border-bottom: 1px solid var(--line);
  font-size: 13px; color: var(--muted); font-family: var(--mono);
}
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--up); display: inline-block; margin-right: 7px; }
.sides { display: grid; grid-template-columns: 1fr auto 1fr; }
.side { padding: 24px 20px; }
.side.right { text-align: right; }
.side h3 { margin: 0 0 10px; font-size: 13px; font-weight: 500; color: var(--muted); font-family: var(--mono); }
.rate { font-family: var(--mono); font-size: clamp(22px, 3vw, 30px); letter-spacing: -.02em; }
.left .rate { color: var(--global); }
.right .rate { color: var(--india); }
.side p { margin: 8px 0 0; font-size: 13px; color: var(--muted); }
.gap { border-left: 1px solid var(--line); border-right: 1px solid var(--line);
       padding: 24px 18px; text-align: center; min-width: 138px; }
.gap .big { font-family: var(--mono); font-size: 26px; color: var(--text); }
.gap .label { font-size: 12px; color: var(--muted); margin-top: 6px; line-height: 1.4; }
.board-foot { padding: 12px 20px; border-top: 1px solid var(--line); font-size: 12.5px;
              color: var(--muted); font-family: var(--mono); }

section { padding: 56px 0; border-top: 1px solid var(--line); }
h2 { font-family: var(--serif); font-weight: 600; font-size: 27px; margin: 0 0 8px; letter-spacing: -.01em; }
.sub { color: var(--muted); margin: 0 0 30px; max-width: 62ch; }

ol.steps { counter-reset: s; list-style: none; margin: 0; padding: 0; display: grid; gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 4px; }
ol.steps li { counter-increment: s; background: var(--ink); padding: 20px 22px; display: grid; grid-template-columns: 34px 1fr; gap: 14px; }
ol.steps li::before { content: counter(s); font-family: var(--mono); color: var(--india); font-size: 14px; padding-top: 3px; }
ol.steps b { font-weight: 600; display: block; margin-bottom: 3px; }
ol.steps span { color: var(--muted); font-size: 15.5px; }

table { width: 100%; border-collapse: collapse; font-size: 15.5px; }
th, td { text-align: left; padding: 13px 14px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--muted); font-weight: 500; font-size: 13px; font-family: var(--mono); }
td code, code.path { font-family: var(--mono); font-size: 14px; color: var(--text); }
td .m { color: var(--muted); }

pre { background: var(--panel); border: 1px solid var(--line); border-radius: 4px;
      padding: 18px 20px; overflow-x: auto; font-family: var(--mono); font-size: 14px; margin: 0 0 14px; }
pre .c { color: var(--muted); }
pre .k { color: var(--india); }

footer { padding: 34px 0 60px; color: var(--muted); font-size: 14px;
         display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
footer a { color: var(--muted); }

@media (max-width: 860px) {
  .hero { grid-template-columns: 1fr; gap: 36px; padding-top: 44px; }
  .sides { grid-template-columns: 1fr; }
  .gap { border: none; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
  .side.right { text-align: left; }
  .mast nav { gap: 16px; }
}
</style>
</head>
<body>
<div class="wrap">

  <header class="mast">
    <div class="mark">Coin<span>Scanner</span> API</div>
    <nav>
      <a href="#method">How the price is made</a>
      <a href="#endpoints">Endpoints</a>
      <a href="/docs">Try it</a>
    </nav>
  </header>

  <div class="hero">
    <div>
      <h1>The price an Indian actually pays.</h1>
      <p class="lede">Ten exchanges, read every few minutes. One official price per coin,
      in dollars and in rupees, with the outliers thrown out and the gap between the
      two spelled out rather than hidden.</p>
      <div class="cta">
        <a class="btn solid" href="/docs">Open the interactive docs</a>
        <a class="btn" href="#endpoints">See what it returns</a>
      </div>
    </div>

    <div class="board" id="board">
      <div class="board-head">
        <span><span class="dot"></span>Bitcoin, live</span>
        <span id="sources">reading…</span>
      </div>
      <div class="sides">
        <div class="side left">
          <h3>Global</h3>
          <div class="rate" id="usd">—</div>
          <p>Volume-weighted across global exchanges, in true dollars.</p>
        </div>
        <div class="gap">
          <div class="big" id="premium">—</div>
          <div class="label">above the bank rate</div>
        </div>
        <div class="side right">
          <h3>India</h3>
          <div class="rate" id="inr">—</div>
          <p>Read straight from Indian exchanges, never converted.</p>
        </div>
      </div>
      <div class="board-foot" id="foot">&nbsp;</div>
    </div>
  </div>

  <section id="method">
    <h2>Where the number comes from</h2>
    <p class="sub">Every few minutes, in this order. Nothing is bought in from another
    data provider, so there is no second source to trust or pay for.</p>
    <ol class="steps">
      <li><div><b>Read ten exchanges</b><span>Six global, four Indian. A failure at one
        never stops the rest, and an exchange that quietly breaks is flagged, not ignored.</span></div></li>
      <li><div><b>Throw out what cannot be trusted</b><span>Wide buy-sell gaps, dead
        volume, and prices too far from the middle. An exchange that is regularly wrong
        loses its rating.</span></div></li>
      <li><div><b>Weight by real trading</b><span>A price backed by a billion dollars of
        volume counts for more than one backed by nothing.</span></div></li>
      <li><div><b>Keep dollars and rupees apart</b><span>Indian prices never move the
        dollar price. That separation is what makes the India number mean something.</span></div></li>
    </ol>
  </section>

  <section>
    <h2>Two questions that sound the same</h2>
    <p class="sub">Both are returned for every coin. Only one of them costs a buyer money.</p>
    <table>
      <tr><th>Field</th><th>Asks</th><th>Usually</th></tr>
      <tr>
        <td><code>india_premium_pct</code></td>
        <td>Are Indian exchanges dearer than global ones, for someone already holding USDT?</td>
        <td class="m">Near zero</td>
      </tr>
      <tr>
        <td><code>india_premium_vs_bank_pct</code></td>
        <td>Is a buyer paying more than the plain dollar value of the coin at the bank rate?</td>
        <td class="m">A few percent</td>
      </tr>
    </table>
  </section>

  <section id="endpoints">
    <h2>What you can ask for</h2>
    <p class="sub">Send your key in the <code class="path">X-API-Key</code> header.
    Every price carries its age, so nothing can be mistaken for live when it is not.</p>
    <table>
      <tr><th>Endpoint</th><th>Returns</th></tr>
      <tr><td><code class="path">/v1/prices</code></td><td>Market list: price, market cap, 1h, 24h and 7d change, sortable</td></tr>
      <tr><td><code class="path">/v1/prices/{coin}</code></td><td>One coin in dollars and rupees, with both premiums</td></tr>
      <tr><td><code class="path">/v1/candles/{coin}</code></td><td>Open, high, low, close of the official price</td></tr>
      <tr><td><code class="path">/v1/global</code></td><td>Combined market cap, volume, Bitcoin's share</td></tr>
      <tr><td><code class="path">/v1/ticker/{symbol}</code></td><td>One pair on every exchange, with quality flags</td></tr>
      <tr><td><code class="path">/v1/best/{symbol}</code></td><td>Cheapest place to buy, best place to sell</td></tr>
      <tr><td><code class="path">/v1/exchanges</code></td><td>Every exchange with our own A to D rating</td></tr>
      <tr><td><code class="path">/v1/coins</code></td><td>Coin details and logos</td></tr>
    </table>
  </section>

  <section>
    <h2>Start in one line</h2>
    <p class="sub">A key is issued per user. Rate limits are hourly and returned with every answer.</p>
<pre><span class="c"># the official Bitcoin price, both currencies</span>
curl -H <span class="k">"X-API-Key: YOUR_KEY"</span> \\
  __BASE__/v1/prices/bitcoin

<span class="c"># top 20 coins by market cap</span>
curl -H <span class="k">"X-API-Key: YOUR_KEY"</span> \\
  <span class="k">"__BASE__/v1/prices?sort=market_cap&limit=20"</span></pre>
    <p class="sub" style="margin:0">Prefer clicking? <a href="/docs">The interactive docs</a>
    run every request against live data.</p>
  </section>

  <footer>
    <span>Built and run in India. Market data only, never advice.</span>
    <span><a href="/docs">Docs</a> · <a href="/v1/health">Status</a></span>
  </footer>
</div>

<script>
(function () {
  var money = function (n, sym, dp) {
    if (n === null || n === undefined) return "—";
    return sym + n.toLocaleString(sym === "\\u20b9" ? "en-IN" : "en-US",
      { minimumFractionDigits: dp, maximumFractionDigits: dp });
  };
  fetch("/v1/demo/snapshot").then(function (r) { return r.json(); }).then(function (d) {
    var set = function (id, v) { document.getElementById(id).textContent = v; };
    set("usd", money(d.usd, "$", 2));
    set("inr", money(d.inr, "\\u20b9", 0));
    set("premium", d.india_premium_vs_bank_pct === null ? "—"
        : (d.india_premium_vs_bank_pct > 0 ? "+" : "") + d.india_premium_vs_bank_pct.toFixed(2) + "%");
    set("sources", d.sources ? d.sources + " exchanges agreeing" : "");
    set("foot", d.coins_priced
      ? d.coins_priced.toLocaleString("en-US") + " coins priced · "
        + d.exchanges + " exchanges · updated " + (d.age_seconds || 0) + "s ago"
      : "");
  }).catch(function () {
    document.getElementById("foot").textContent = "Live prices are not reachable right now.";
  });
})();
</script>
</body>
</html>
"""


def landing_html(base_url):
    return (LANDING
            .replace("__TOKENS__", TOKENS)
            .replace("__FONTS__", FONTS)
            .replace("__BRAND__", BRAND)
            .replace("__BASE__", base_url))


DOCS = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__BRAND__ — reference</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="__FONTS__">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css">
<style>
__TOKENS__
body { margin: 0; background: var(--ink); color: var(--text); font-family: var(--sans); }
.topbar { display: none; }
.bar { border-bottom: 1px solid var(--line); }
.bar-in { max-width: 1160px; margin: 0 auto; padding: 18px 24px; display: flex;
          align-items: center; justify-content: space-between; gap: 16px; }
.bar .mark { font-family: var(--serif); font-weight: 600; font-size: 18px; }
.bar .mark span { color: var(--india); }
.bar a { color: var(--muted); text-decoration: none; font-size: 15px; }
.bar a:hover { color: var(--text); }
.hint { max-width: 1160px; margin: 0 auto; padding: 20px 24px 0; color: var(--muted); font-size: 15px; }
.hint code { font-family: var(--mono); color: var(--text); }

/* Swagger, dressed in the same clothes as the rest of the site */
.swagger-ui, .swagger-ui .info .title, .swagger-ui .opblock-tag,
.swagger-ui .opblock .opblock-summary-path, .swagger-ui table thead tr td,
.swagger-ui table thead tr th, .swagger-ui .parameter__name,
.swagger-ui .response-col_status, .swagger-ui label, .swagger-ui .tab li button.tablinks,
.swagger-ui .opblock-description-wrapper p, .swagger-ui .markdown p,
.swagger-ui .renderedMarkdown p, .swagger-ui .model-title, .swagger-ui .model {
  color: var(--text); font-family: var(--sans);
}
.swagger-ui .info .title, .swagger-ui .opblock-tag { font-family: var(--serif); }
.swagger-ui .opblock-summary-path, .swagger-ui .parameter__name,
.swagger-ui .prop-type, .swagger-ui .microlight, .swagger-ui input,
.swagger-ui textarea, .swagger-ui select { font-family: var(--mono) !important; }
.swagger-ui .scheme-container, .swagger-ui section.models,
.swagger-ui .opblock .opblock-section-header { background: var(--panel); box-shadow: none; }
.swagger-ui .opblock { background: var(--panel); border-color: var(--line);
  border-radius: 4px; box-shadow: none; margin: 0 0 12px; }
.swagger-ui .opblock.opblock-get .opblock-summary-method { background: var(--global); color: #0E1526; }
.swagger-ui .opblock.opblock-get { border-color: var(--line); }
.swagger-ui .opblock.opblock-get .opblock-summary { border-color: var(--line); }
.swagger-ui .opblock-tag { border-color: var(--line); }
.swagger-ui .opblock-tag small { color: var(--muted); font-family: var(--sans); }
.swagger-ui .btn { border-radius: 3px; border-color: var(--line); color: var(--text); }
.swagger-ui .btn.execute { background: var(--india); border-color: var(--india); color: #1A1406; }
.swagger-ui .btn.authorize { color: var(--india); border-color: var(--india); }
.swagger-ui .btn.authorize svg { fill: var(--india); }
.swagger-ui input, .swagger-ui textarea, .swagger-ui select {
  background: var(--ink); color: var(--text); border: 1px solid var(--line); }
.swagger-ui .microlight { background: #0F1424 !important; }
.swagger-ui .responses-inner { background: transparent; }
.swagger-ui .model-box, .swagger-ui section.models .model-container { background: var(--ink); }
.swagger-ui svg.arrow { fill: var(--muted); }
.swagger-ui .info { margin: 22px 0 28px; }
.swagger-ui .wrapper { max-width: 1160px; }
</style>
</head>
<body>
<div class="bar"><div class="bar-in">
  <div class="mark">Coin<span>Scanner</span> API</div>
  <a href="/">Back to the front page</a>
</div></div>
<p class="hint">Click <b>Authorize</b>, paste your key, then open any endpoint and press
<b>Execute</b>. Requests run against live data.</p>
<div id="ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
<script>
window.ui = SwaggerUIBundle({
  url: "__OPENAPI__",
  dom_id: "#ui",
  deepLinking: true,
  docExpansion: "none",
  defaultModelsExpandDepth: -1,
  tryItOutEnabled: true,
  persistAuthorization: true,
  presets: [SwaggerUIBundle.presets.apis]
});
</script>
</body>
</html>
"""


def docs_html(openapi_url):
    return (DOCS
            .replace("__TOKENS__", TOKENS)
            .replace("__FONTS__", FONTS)
            .replace("__BRAND__", BRAND)
            .replace("__OPENAPI__", openapi_url))
