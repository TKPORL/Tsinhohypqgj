const { chromium } = require("playwright-core");
const EXE = "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe";

(async () => {
  const b = await chromium.launch({ executablePath: EXE, headless: true });
  const ctx = await b.newContext({ viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  p.on("pageerror", e => console.log("EXC:", e.message));

  await p.goto("http://127.0.0.1:5000", { waitUntil: "networkidle" });

  // 切到「爬取结果」
  await p.click('.nav-btn[data-panel="result"]');
  await p.waitForTimeout(2500);
  // 展开第一组
  try { await p.click('.group-card button:has-text("展开"), .group-row button:has-text("展开"), button:has-text("展开")'); } catch (e) {}
  await p.waitForTimeout(3000);

  const stat = await p.evaluate(() => {
    const out = [];
    document.querySelectorAll(".card").forEach((c, i) => {
      if (i > 3) return;
      const links = c.querySelector(".card-links");
      const title = c.querySelector(".card-title");
      out.push({
        title: title ? title.textContent.trim().slice(0, 55) : "",
        linksRow: links ? [...links.children].map(x => x.textContent.trim().slice(0, 14)) : [],
        hasOldFooter: !!c.querySelector(".card-footer"),
      });
    });
    return out;
  });
  console.log(JSON.stringify(stat, null, 1));
  await p.screenshot({ path: "_dev/_shots/cards.png" });
  await b.close();
})().catch(e => { console.error("FAILED:", e.message); process.exit(1); });
