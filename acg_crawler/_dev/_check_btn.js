const { chromium } = require("playwright-core");
const EXE = "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe";

(async () => {
  const b = await chromium.launch({ executablePath: EXE, headless: true });
  const ctx = await b.newContext({ viewport: { width: 1400, height: 1100 }, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  p.on("pageerror", e => console.log("EXC:", e.message));

  await p.goto("http://127.0.0.1:5000", { waitUntil: "networkidle" });
  await p.click('.nav-btn[data-panel="result"]');
  await p.waitForTimeout(2500);
  try { await p.click('button:has-text("展开")'); } catch (e) {}
  await p.waitForTimeout(3000);

  const stat = await p.evaluate(() => {
    const out = [];
    document.querySelectorAll(".card").forEach((c, i) => {
      if (i > 4) return;
      const links = c.querySelector(".card-links");
      const gBtn = c.querySelector(".btn-game");
      const bBtn = c.querySelector(".btn-bare");
      out.push({
        btns: links ? [...links.children].map(x => (x.textContent.trim().match(/^(游戏名|复制名称|百度网盘|原帖|解压码|作弊码)/) || [""])[0]).filter(Boolean).join(" → ") : "",
        net: gBtn ? (gBtn.getAttribute("data-copy") || "").slice(0, 50) : "(无)",
        bare: bBtn ? (bBtn.getAttribute("data-copy") || "").slice(0, 50) : "(无)",
      });
    });
    return out;
  });
  stat.forEach(s => {
    console.log("按钮  : " + s.btns);
    console.log("网盘名: " + s.net);
    console.log("纯名字: " + s.bare);
    console.log("-".repeat(55));
  });
  await p.screenshot({ path: "_dev/_shots/cards.png" });
  await b.close();
})().catch(e => { console.error("FAILED:", e.message); process.exit(1); });
