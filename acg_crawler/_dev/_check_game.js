const { chromium } = require("playwright-core");
const EXE = "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe";
(async () => {
  const b = await chromium.launch({ executablePath: EXE, headless: true });
  const ctx = await b.newContext({ viewport: { width: 1280, height: 1100 }, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  p.on("pageerror", e => console.log("EXC:", e.message));
  await p.goto("http://127.0.0.1:5000", { waitUntil: "networkidle" });
  await p.click('.nav-btn[data-panel="result"]');
  await p.waitForTimeout(3000);
  try { await p.click('button:has-text("展开")'); } catch(e) {}
  await p.waitForTimeout(2500);
  const stat = await p.evaluate(() => {
    const out = [];
    document.querySelectorAll(".card").forEach((c, i) => {
      if (i > 3) return;
      const links = c.querySelector(".card-links");
      out.push({
        linksRow: links ? [...links.children].map(x => x.textContent.trim().slice(0, 16)) : [],
      });
    });
    return out;
  });
  console.log(JSON.stringify(stat, null, 1));
  // 只截前两张卡片区域
  const card = await p.$(".card");
  if (card) await card.screenshot({ path: "_dev/_shots/card_game.png" });
  await b.close();
})().catch(e => { console.error("FAILED:", e.message); process.exit(1); });
