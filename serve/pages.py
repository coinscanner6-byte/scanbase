"""
The two pages a visitor sees: the front page and the interactive docs.

Both follow the coinscanner.tech look - pale blue-grey page, white cards,
blue as the one accent colour, green and red only for movement - so the
API does not look like a different company's product.
"""

BRAND = "CoinScanner API"

FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&"
         "family=JetBrains+Mono:wght@400;500&display=swap")

TOKENS = """
:root {
  --page: #F5F7FA;
  --card: #FFFFFF;
  --line: #E6EAF2;
  --ink: #0F172A;
  --muted: #64748B;
  --blue: #2563EB;
  --blue-soft: #E8F0FE;
  --up: #16A34A;
  --down: #EF4444;
  --sans: Inter, system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
  --shadow: 0 1px 2px rgba(15,23,42,.04), 0 8px 24px rgba(15,23,42,.05);
}
"""

LANDING = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__BRAND__ — crypto prices built for India</title>
<meta name="description" content="Live crypto prices from ten exchanges, one official price per coin, and the real cost of buying in India.">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="__FONTS__">
<style>
__TOKENS__
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--page); color: var(--ink);
  font-family: var(--sans); font-size: 16px; line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--blue); }
a:focus-visible, button:focus-visible { outline: 2px solid var(--blue); outline-offset: 3px; }
.wrap { max-width: 1160px; margin: 0 auto; padding: 0 28px; }

.mast { background: var(--card); border-bottom: 1px solid var(--line); }
.mast-in { max-width: 1160px; margin: 0 auto; padding: 16px 28px;
  display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.brand { display: flex; align-items: center; gap: 11px; }
.brand .badge {
  width: 38px; height: 38px; border-radius: 11px; background: var(--blue-soft);
  color: var(--blue); display: grid; place-items: center; font-weight: 700; font-size: 15px;
}
.brand b { display: block; font-size: 16.5px; font-weight: 700; letter-spacing: .04em; }
.brand span { display: block; font-size: 12.5px; color: var(--muted); }
.mast nav { display: flex; align-items: center; gap: 6px; }
.mast nav a {
  padding: 8px 15px; border-radius: 999px; font-size: 14.5px; font-weight: 500;
  color: var(--muted); text-decoration: none;
}
.mast nav a:hover { color: var(--ink); background: var(--page); }
.mast nav a.on { background: var(--blue-soft); color: var(--blue); font-weight: 600; }

.hero { padding: 54px 0 12px; display: grid; grid-template-columns: 1fr 1.05fr; gap: 52px; align-items: center; }
h1 { font-size: clamp(32px, 4.2vw, 46px); font-weight: 700; line-height: 1.12;
     margin: 0 0 18px; letter-spacing: -.025em; }
.lede { color: var(--muted); margin: 0 0 26px; max-width: 46ch; font-size: 17px; }
.cta { display: flex; gap: 12px; flex-wrap: wrap; }
.btn { display: inline-block; padding: 12px 22px; border-radius: 11px; font-size: 15px;
       font-weight: 600; text-decoration: none; border: 1px solid var(--line);
       background: var(--card); color: var(--ink); }
.btn.solid { background: var(--blue); border-color: var(--blue); color: #fff; }

.board { background: var(--card); border: 1px solid var(--line); border-radius: 16px;
         box-shadow: var(--shadow); overflow: hidden; }
.board-head { display: flex; align-items: center; justify-content: space-between;
  gap: 12px; padding: 13px 18px; border-bottom: 1px solid var(--line); }
.live { display: inline-flex; align-items: center; gap: 7px; background: var(--ink);
  color: #fff; padding: 5px 13px; border-radius: 999px; font-size: 12px;
  font-weight: 600; letter-spacing: .06em; }
.live i { width: 6px; height: 6px; border-radius: 50%; background: #4ADE80; display: block; }
.board-head .who { font-size: 13.5px; color: var(--muted); font-family: var(--mono); }
.sides { display: grid; grid-template-columns: 1fr auto 1fr; }
.side { padding: 26px 22px; }
.side.right { text-align: right; }
.side h3 { margin: 0 0 9px; font-size: 13px; font-weight: 600; color: var(--muted); }
.rate { font-size: clamp(24px, 3.1vw, 32px); font-weight: 700; letter-spacing: -.025em; }
.side p { margin: 9px 0 0; font-size: 13px; color: var(--muted); line-height: 1.5; }
.gap { border-left: 1px solid var(--line); border-right: 1px solid var(--line);
       padding: 26px 20px; text-align: center; min-width: 150px;
       display: flex; flex-direction: column; justify-content: center; }
.gap .big { font-size: 27px; font-weight: 700; color: var(--blue); letter-spacing: -.02em; }
.gap .label { font-size: 12.5px; color: var(--muted); margin-top: 5px; line-height: 1.4; }
.board-foot { padding: 12px 18px; border-top: 1px solid var(--line);
  background: #FBFCFE; font-size: 12.5px; color: var(--muted); font-family: var(--mono); }

section { padding: 52px 0; }
section + section { border-top: 1px solid var(--line); }
h2 { font-size: 26px; font-weight: 700; margin: 0 0 8px; letter-spacing: -.02em; }
.sub { color: var(--muted); margin: 0 0 26px; max-width: 64ch; }

ol.steps { counter-reset: s; list-style: none; margin: 0; padding: 0;
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
ol.steps li { counter-increment: s; background: var(--card); border: 1px solid var(--line);
  border-radius: 14px; padding: 20px 22px; display: grid; grid-template-columns: 30px 1fr; gap: 14px; }
ol.steps li::before { content: counter(s); width: 26px; height: 26px; border-radius: 8px;
  background: var(--blue-soft); color: var(--blue); font-size: 13px; font-weight: 700;
  display: grid; place-items: center; }
ol.steps b { display: block; margin-bottom: 4px; font-size: 15.5px; }
ol.steps span { color: var(--muted); font-size: 14.5px; }

.panel { background: var(--card); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; font-size: 15px; }
th, td { text-align: left; padding: 14px 18px; border-bottom: 1px solid var(--line); vertical-align: top; }
tr:last-child td { border-bottom: none; }
th { color: var(--muted); font-weight: 600; font-size: 12.5px; background: #FBFCFE; }
code, .path { font-family: var(--mono); font-size: 13.5px; color: var(--blue); }
td .m { color: var(--muted); }

pre { background: var(--ink); color: #E2E8F0; border-radius: 14px; padding: 20px 22px;
      overflow-x: auto; font-family: var(--mono); font-size: 13.5px; line-height: 1.7; margin: 0 0 16px; }
pre .c { color: #94A3B8; }
pre .k { color: #7DD3FC; }

footer { border-top: 1px solid var(--line); padding: 28px 0 56px; color: var(--muted);
         font-size: 14px; display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
footer a { color: var(--muted); }

@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; gap: 34px; padding-top: 38px; }
  .sides { grid-template-columns: 1fr; }
  .gap { border: none; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
  .side.right { text-align: left; }
  ol.steps { grid-template-columns: 1fr; }
  .mast nav a { padding: 8px 11px; font-size: 14px; }
  .brand span { display: none; }
}
</style>
</head>
<body>

<header class="mast"><div class="mast-in">
  <div class="brand">
    <div class="badge">CS</div>
    <div><b>COIN SCANNER</b><span>Market data API</span></div>
  </div>
  <nav>
    <a class="on" href="/">Overview</a>
    <a href="#method">How it works</a>
    <a href="#endpoints">Endpoints</a>
    <a href="/docs">Try it</a>
  </nav>
</div></header>

<div class="wrap">

  <div class="hero">
    <div>
      <h1>The price an Indian actually pays.</h1>
      <p class="lede">Ten exchanges, read every few minutes. One official price per coin,
      in dollars and in rupees, with the outliers thrown out and the gap between the two
      spelled out rather than hidden.</p>
      <div class="cta">
        <a class="btn solid" href="/docs">Open the interactive docs</a>
        <a class="btn" href="#endpoints">See what it returns</a>
      </div>
    </div>

    <div class="board">
      <div class="board-head">
        <span class="live"><i></i>LIVE</span>
        <span class="who">Bitcoin · <span id="sources">reading…</span></span>
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
    <p class="sub">Every few minutes, in this order. Nothing is bought in from another data
    provider, so there is no second source to trust or pay for.</p>
    <ol class="steps">
      <li><div><b>Read ten exchanges</b><span>Six global, four Indian. A failure at one never
        stops the rest, and an exchange that quietly breaks is flagged, not ignored.</span></div></li>
      <li><div><b>Throw out what cannot be trusted</b><span>Wide buy-sell gaps, dead volume,
        and prices too far from the middle. An exchange that is regularly wrong loses its
        rating.</span></div></li>
      <li><div><b>Weight by real trading</b><span>A price backed by a billion dollars of volume
        counts for more than one backed by nothing.</span></div></li>
      <li><div><b>Keep dollars and rupees apart</b><span>Indian prices never move the dollar
        price. That separation is what makes the India number mean something.</span></div></li>
    </ol>
  </section>

  <section>
    <h2>Two questions that sound the same</h2>
    <p class="sub">Both are returned for every coin. Only one of them costs a buyer money.</p>
    <div class="panel"><table>
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
    </table></div>
  </section>

  <section id="endpoints">
    <h2>What you can ask for</h2>
    <p class="sub">Send your key in the <code>X-API-Key</code> header. Every price carries its
    age, so nothing can be mistaken for live when it is not.</p>
    <div class="panel"><table>
      <tr><th>Endpoint</th><th>Returns</th></tr>
      <tr><td><span class="path">/v1/prices</span></td><td>Market list: price, market cap, 1h, 24h and 7d change, sortable</td></tr>
      <tr><td><span class="path">/v1/prices/{coin}</span></td><td>One coin in dollars and rupees, with both premiums</td></tr>
      <tr><td><span class="path">/v1/candles/{coin}</span></td><td>Open, high, low, close of the official price</td></tr>
      <tr><td><span class="path">/v1/global</span></td><td>Combined market cap, volume, Bitcoin's share</td></tr>
      <tr><td><span class="path">/v1/ticker/{symbol}</span></td><td>One pair on every exchange, with quality flags</td></tr>
      <tr><td><span class="path">/v1/best/{symbol}</span></td><td>Cheapest place to buy, best place to sell</td></tr>
      <tr><td><span class="path">/v1/exchanges</span></td><td>Every exchange with our own A to D rating</td></tr>
      <tr><td><span class="path">/v1/coins</span></td><td>Coin details and logos</td></tr>
    </table></div>
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
    set("sources", d.sources ? d.sources + " exchanges agreeing" : "live");
    set("foot", d.coins_priced
      ? d.coins_priced.toLocaleString("en-US") + " coins priced · " + d.exchanges
        + " exchanges · updated " + (d.age_seconds || 0) + "s ago"
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
body { margin: 0; background: var(--page); color: var(--ink); font-family: var(--sans); }
.topbar { display: none; }

.mast { background: var(--card); border-bottom: 1px solid var(--line); }
.mast-in { max-width: 1160px; margin: 0 auto; padding: 16px 28px;
  display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.brand { display: flex; align-items: center; gap: 11px; }
.brand .badge { width: 38px; height: 38px; border-radius: 11px; background: var(--blue-soft);
  color: var(--blue); display: grid; place-items: center; font-weight: 700; font-size: 15px; }
.brand b { display: block; font-size: 16.5px; font-weight: 700; letter-spacing: .04em; }
.brand span { display: block; font-size: 12.5px; color: var(--muted); }
.mast a.back { font-size: 14.5px; color: var(--muted); text-decoration: none;
  padding: 8px 15px; border-radius: 999px; }
.mast a.back:hover { background: var(--page); color: var(--ink); }
.hint { max-width: 1160px; margin: 0 auto; padding: 22px 28px 0; color: var(--muted); font-size: 15px; }
.hint b { color: var(--ink); }

/* Swagger, wearing the CoinScanner clothes */
.swagger-ui, .swagger-ui .info .title, .swagger-ui .opblock-tag,
.swagger-ui .opblock .opblock-summary-path, .swagger-ui table thead tr td,
.swagger-ui table thead tr th, .swagger-ui .parameter__name, .swagger-ui label,
.swagger-ui .response-col_status, .swagger-ui .tab li button.tablinks,
.swagger-ui .markdown p, .swagger-ui .renderedMarkdown p, .swagger-ui .model-title {
  color: var(--ink); font-family: var(--sans);
}
.swagger-ui .info hgroup.main a, .swagger-ui .info .title small { display: none; }
.swagger-ui .info .title { font-size: 30px; font-weight: 700; letter-spacing: -.02em; }
.swagger-ui .opblock-tag { font-size: 20px; font-weight: 700; border-color: var(--line); }
.swagger-ui .opblock-tag small { color: var(--muted); font-weight: 400; }
.swagger-ui .opblock-summary-path, .swagger-ui .parameter__name, .swagger-ui .prop-type,
.swagger-ui .microlight, .swagger-ui input, .swagger-ui textarea, .swagger-ui select {
  font-family: var(--mono) !important;
}
.swagger-ui .scheme-container { background: var(--card); box-shadow: none;
  border: 1px solid var(--line); border-radius: 14px; margin: 22px 0; padding: 18px 20px; }
.swagger-ui .opblock { background: var(--card); border: 1px solid var(--line);
  border-radius: 14px; box-shadow: var(--shadow); margin: 0 0 12px; }
.swagger-ui .opblock.opblock-get .opblock-summary-method { background: var(--blue); }
.swagger-ui .opblock.opblock-get, .swagger-ui .opblock.opblock-get .opblock-summary {
  border-color: var(--line); }
.swagger-ui .opblock .opblock-section-header { background: #FBFCFE; box-shadow: none;
  border-top: 1px solid var(--line); }
.swagger-ui .btn { border-radius: 10px; border-color: var(--line); color: var(--ink);
  box-shadow: none; font-weight: 600; }
.swagger-ui .btn.execute { background: var(--blue); border-color: var(--blue); color: #fff; }
.swagger-ui .btn.authorize { color: var(--blue); border-color: var(--blue); }
.swagger-ui .btn.authorize svg { fill: var(--blue); }
.swagger-ui input, .swagger-ui textarea, .swagger-ui select {
  border: 1px solid var(--line); border-radius: 9px; }
.swagger-ui section.models { border-color: var(--line); border-radius: 14px; background: var(--card); }
.swagger-ui .wrapper { max-width: 1160px; }
.swagger-ui .info { margin: 24px 0 26px; }
</style>
</head>
<body>

<header class="mast"><div class="mast-in">
  <div class="brand">
    <div class="badge">CS</div>
    <div><b>COIN SCANNER</b><span>Market data API</span></div>
  </div>
  <a class="back" href="/">Back to overview</a>
</div></header>

<p class="hint">Press <b>Authorize</b>, paste your key, then open any endpoint and press
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
