const { chromium } = require("playwright-core");
const EXE = "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe";
const TARGET = process.argv[2];
const OUT = process.argv[3] || "_shots/check.png";

(async () => {
  const b = await chromium.launch({ executablePath: EXE, headless: true });
  const ctx = await b.newContext({ viewport: { width: 1200, height: 1000 }, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  p.on("pageerror", e => console.log("EXC:", e.message));
  p.on("console", m => { if (m.type() === "error") console.log("ERR:", m.text()); });

  await p.goto(TARGET, { waitUntil: "networkidle" });
  await p.waitForTimeout(800);

  // 断言：解压码/作弊码按钮必须和「原帖」按钮在同一个 .card-links 容器里
  const stat = await p.evaluate(() => {
    const out = [];
    document.querySelectorAll(".card").forEach((c, i) => {
      if (i > 3) return;
      const links = c.querySelector(".card-links");
      const title = c.querySelector(".card-title");
      out.push({
        title: title ? title.textContent.trim().slice(0, 60) : "",
        linksRow: links ? [...links.children].map(x => x.textContent.trim().slice(0, 18)) : [],
        hasOldFooter: !!c.querySelector(".card-footer"),
      });
    });
    return out;
  });
  console.log(JSON.stringify(stat, null, 1));

  await p.screenshot({ path: OUT, fullPage: false });
  await b.close();
  console.log("shot:", OUT);
})().catch(e => { console.error("FAILED:", e); process.exit(1); });
