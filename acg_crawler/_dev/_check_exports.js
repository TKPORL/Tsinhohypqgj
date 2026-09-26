const { chromium } = require("playwright-core");
const EXE = "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe";
const path = require("path");

const FILES = [
  "D:/下载目录/PC+安卓下载1/PC+安卓下载-ACG俱乐部-ACG图书馆-ACG游戏姬-萌幻ACG-鲲Galgame-20260925-082419.html",
  "D:/下载目录/PC下载-鲲/PC下载-鲲Galgame-20260924-191648.html",
  "D:/下载目录/PC+安卓下载-鲲/PC+安卓下载-鲲Galgame-20260924-191650.html",
  "D:/下载目录/PC1/PC下载-ACG俱乐部-ACG图书馆-ACG游戏姬-萌幻ACG-鲲Galgame-20260925-082347.html",
];

const EXPECT = ["游戏名", "百度网盘", "原帖", "解压码"];  // 作弊码极少，作为可选项

(async () => {
  const b = await chromium.launch({ executablePath: EXE, headless: true });
  const ctx = await b.newContext({ viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 1 });
  const p = await ctx.newPage();
  p.on("pageerror", e => console.log("  EXC:", e.message));

  let allOK = true;
  const stat_total = { total: 0, bad: 0 };

  for (const f of FILES) {
    const url = "file:///" + f.replace(/\\/g, "/");
    await p.goto(url, { waitUntil: "load" });
    await p.waitForTimeout(400);

    const stat = await p.evaluate(() => {
      const cards = [...document.querySelectorAll(".card")];
      let bad = 0;
      const badSamples = [];
      const samples = [];
      for (const c of cards) {
        const links = c.querySelector(".card-links");
        const title = c.querySelector(".card-title");
        const gameBtn = c.querySelector(".btn-game");
        const btns = links ? [...links.children].map(x => (x.textContent.trim().match(/^(游戏名|百度网盘|原帖|解压码|作弊码)/) || [""])[0]).filter(Boolean) : [];
        // 规则：游戏名 → 百度网盘 → 原帖 必须在前三；解压码/作弊码 在其后
        const headOK = btns[0] === "游戏名" && btns[1] === "百度网盘" && (!btns[2] || btns[2] === "原帖");
        if (!headOK) { bad++; if (badSamples.length < 2) badSamples.push(btns.join("→")); }
        if (samples.length < 2) samples.push({
          btns: btns.join(" → "),
          copy: gameBtn ? (gameBtn.getAttribute("data-copy") || "").slice(0, 55) : "(无)",
        });
      }
      return { total: cards.length, bad, badSamples, samples };
    });

    stat_total.total += stat.total;
    stat_total.bad += stat.bad;
    if (stat.bad > 0) allOK = false;

    console.log("\n== " + path.basename(f).slice(0, 40) + "  共 " + stat.total + " 张，异常 " + stat.bad + " 张");
    for (const s of stat.samples) {
      console.log("   按钮: " + s.btns);
      console.log("   复制: " + s.copy);
    }
    if (stat.badSamples.length) console.log("   !! 异常样例: " + stat.badSamples.join(" | "));
    await p.screenshot({ path: "_dev/_shots/exp_" + FILES.indexOf(f) + ".png" });
  }

  console.log("\n合计 " + stat_total.total + " 张，异常 " + stat_total.bad + " 张 → " + (allOK ? "全部合格" : "有问题"));
  await b.close();
})().catch(e => { console.error("FAILED:", e.message); process.exit(1); });
