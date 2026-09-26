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
        const gameBtn = c.querySelector(".btn-game");
        const bareBtn = c.querySelector(".btn-bare");
        const btns = links ? [...links.children].map(x => (x.textContent.trim().match(/^(游戏名|复制名称|百度网盘|原帖|解压码|作弊码)/) || [""])[0]).filter(Boolean) : [];
        // 规则：游戏名 → 复制名称 → 百度网盘 → 原帖 → (解压码/作弊码)
        const headOK = btns[0] === "游戏名" && btns[1] === "复制名称" && btns[2] === "百度网盘" && (!btns[3] || btns[3] === "原帖");
        // 纯名字不该带「平台括号」「爬虫编号」
        // 但下面这些算合法，不判异常：
        //   - 书名号内的括号（游戏副标题）『…【xx】…』
        //   - 版本号括号 【v0.2.8d】/【v0.15】
        //   - 名字里的中文短括号 [呉]、[美空編]
        //   - 版本号尾巴 v0.0.9971
        const bare = bareBtn ? (bareBtn.getAttribute("data-copy") || "") : "";
        let bStripped = bare
          .replace(/[『』《》〈〉][^『』《》〈〉]*[『』《》〈〉]/g, "")   // 书名号段
          .replace(/[【\[]\s*[vV]?\d[\w.\-]*\s*[】\]]/g, "")          // 版本号括号
          .replace(/[【\[]\s*[^【】\]]{1,4}\s*[】\]]/g, "")            // 名字里的短括号
          .replace(/\s*[vV]?\d+(?:\.\d+)+\w*\s*$/g, "");              // 版本号尾巴
        const bareOK = bare && !/【|\[/.test(bStripped);
        if (!headOK || !bareOK) { bad++; if (badSamples.length < 3) badSamples.push(btns.join("→") + (bareOK ? "" : " | 名字含括号: " + bare)); }
        if (samples.length < 2) samples.push({
          btns: btns.join(" → "),
          net: gameBtn ? (gameBtn.getAttribute("data-copy") || "").slice(0, 45) : "(无)",
          bare: bare.slice(0, 45) || "(无)",
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
      console.log("   网盘名: " + s.net);
      console.log("   纯名字: " + s.bare);
    }
    if (stat.badSamples.length) console.log("   !! 异常样例: " + stat.badSamples.join(" | "));
    await p.screenshot({ path: "_dev/_shots/exp_" + FILES.indexOf(f) + ".png" });
  }

  console.log("\n合计 " + stat_total.total + " 张，异常 " + stat_total.bad + " 张 → " + (allOK ? "全部合格" : "有问题"));
  await b.close();
})().catch(e => { console.error("FAILED:", e.message); process.exit(1); });
