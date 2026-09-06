document.addEventListener("DOMContentLoaded", function() {
    // 导航切换
    const navBtns = document.querySelectorAll(".nav-btn");
    const panels = document.querySelectorAll(".panel");
    navBtns.forEach(btn => {
        btn.addEventListener("click", function() {
            navBtns.forEach(b => b.classList.remove("active"));
            panels.forEach(p => p.classList.remove("active"));
            this.classList.add("active");
            document.getElementById("panel-" + this.dataset.panel).classList.add("active");
        });
    });

    // 爬取模式切换
    const modeRadios = document.querySelectorAll('input[name="crawlMode"]');
    const dateGroup = document.getElementById("dateGroup");
    const pageGroup = document.getElementById("pageGroup");
    modeRadios.forEach(radio => {
        radio.addEventListener("change", function() {
            if (this.value === "by_date") {
                dateGroup.classList.remove("hidden");
                pageGroup.classList.add("hidden");
            } else {
                dateGroup.classList.add("hidden");
                pageGroup.classList.remove("hidden");
            }
        });
    });

    // 模拟爬取
    const startBtn = document.getElementById("startBtn");
    const stopBtn = document.getElementById("stopBtn");
    const progressSection = document.getElementById("progressSection");
    const progressFill = document.getElementById("progressFill");
    const progressText = document.getElementById("progressText");
    const logBox = document.getElementById("logBox");
    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");
    let crawlTimer = null;

    startBtn.addEventListener("click", function() {
        startBtn.classList.add("hidden");
        stopBtn.classList.remove("hidden");
        progressSection.classList.remove("hidden");
        statusDot.classList.add("running");
        statusText.textContent = "爬取中...";
        logBox.innerHTML = "";
        addLog("系统", "开始爬取任务...");
        addLog("系统", "正在连接代理 127.0.0.1:7890...");
        simulateCrawl();
    });

    stopBtn.addEventListener("click", function() {
        clearInterval(crawlTimer);
        startBtn.classList.remove("hidden");
        stopBtn.classList.add("hidden");
        statusDot.classList.remove("running");
        statusText.textContent = "已停止";
        addLog("系统", "用户取消了爬取任务", "error");
    });

    function simulateCrawl() {
        let current = 0;
        const total = 50;
        crawlTimer = setInterval(function() {
            current++;
            if (current > total) {
                clearInterval(crawlTimer);
                startBtn.classList.remove("hidden");
                stopBtn.classList.add("hidden");
                statusDot.classList.remove("running");
                statusText.textContent = "完成";
                addLog("系统", "爬取任务完成！共爬取 89 条，跳过 61 条", "success");
                loadPosts();
                return;
            }
            const pct = Math.round((current / total) * 100);
            progressFill.style.width = pct + "%";
            progressText.textContent = current + " / " + total;
            const sites = ["ACG游戏姬", "萌幻ACG", "ACG图书馆"];
            const site = sites[Math.floor(Math.random() * sites.length)];
            addLog(site, "正在爬取第 " + current + " 页...");
            if (Math.random() > 0.6) {
                const count = Math.floor(Math.random() * 15) + 5;
                addLog(site, "发现 " + count + " 个帖子");
            }
            if (Math.random() > 0.7) {
                const skip = Math.floor(Math.random() * 5) + 1;
                addLog(site, "跳过 " + skip + " 个(无百度/移动云盘链接)");
            }
            if (Math.random() > 0.9) {
                addLog(site, "请求超时，重试中...", "error");
            }
        }, 200);
    }

    function addLog(source, msg, type) {
        const time = new Date().toLocaleTimeString("zh-CN", {hour12: false});
        const line = document.createElement("div");
        line.className = "log-line" + (type ? " " + type : "");
        line.textContent = "[" + time + "] [" + source + "] " + msg;
        logBox.appendChild(line);
        logBox.scrollTop = logBox.scrollHeight;
    }

    // 加载帖子
    function loadPosts() {
        fetch("/api/posts")
            .then(r => r.json())
            .then(data => {
                document.getElementById("resultCount").textContent = data.length;
                renderCards(data);
            });
    }

    function renderCards(posts) {
        const grid = document.getElementById("cardGrid");
        grid.innerHTML = "";
        posts.forEach(post => {
            const card = document.createElement("div");
            card.className = "card";
            const platformTag = {
                pc: '<span class="tag tag-pc">PC</span>',
                android: '<span class="tag tag-android">安卓</span>',
                pc_android: '<span class="tag tag-pc">PC</span><span class="tag tag-android">安卓</span>',
                unknown: '<span class="tag tag-pc">未知</span>'
            }[post.platform] || "";
            const imagesHtml = post.images.map((img, i) =>
                '<img src="' + img + '" alt="" style="' + (i > 0 ? 'display:none' : '') + '" class="card-img">'
            ).join("");
            const dotsHtml = post.images.map((_, i) =>
                '<span class="image-dot' + (i === 0 ? ' active' : '') + '"></span>'
            ).join("");
            let linksHtml = "";
            if (post.baidu_link) {
                linksHtml += '<a href="' + post.baidu_link + '" class="link-btn link-baidu" target="_blank">百度网盘' + (post.baidu_code ? ' (' + post.baidu_code + ')' : '') + '</a>';
            }
            if (post.mobile_link) {
                linksHtml += '<a href="' + post.mobile_link + '" class="link-btn link-mobile" target="_blank">移动云盘' + (post.mobile_code ? ' (' + post.mobile_code + ')' : '') + '</a>';
            }
            linksHtml += '<a href="' + post.source_url + '" class="link-btn link-source" target="_blank">原帖</a>';
            let footerHtml = "";
            if (post.unzip_code) {
                footerHtml += '<span>解压码: <span class="copy-text" onclick="copyText(this)">' + post.unzip_code + '</span></span>';
            }
            if (post.cheat_code) {
                footerHtml += '<span>作弊码: <span class="copy-text" onclick="copyText(this)">' + post.cheat_code + '</span></span>';
            }
            card.innerHTML =
                '<div class="card-header">' +
                    '<div class="card-tags">' + platformTag + '<span class="tag tag-source">' + post.source + '</span></div>' +
                    '<span class="tag tag-date">' + post.date + '</span>' +
                '</div>' +
                '<div class="card-images">' + imagesHtml +
                    '<div class="image-nav">' + dotsHtml + '</div>' +
                '</div>' +
                '<div class="card-body">' +
                    '<div class="card-title">' + post.title + '</div>' +
                    '<div class="card-stats">' +
                        '<span class="stat-item">❤ ' + post.likes + '</span>' +
                        '<span class="stat-item">💬 ' + post.comments + '</span>' +
                        '<span class="stat-item">👁 ' + formatNumber(post.views) + '</span>' +
                    '</div>' +
                    '<div class="card-links">' + linksHtml + '</div>' +
                '</div>' +
                (footerHtml ? '<div class="card-footer">' + footerHtml + '</div>' : '');
            grid.appendChild(card);
            // 图片轮播
            const imgs = card.querySelectorAll(".card-img");
            const dotEls = card.querySelectorAll(".image-dot");
            if (imgs.length > 1) {
                let idx = 0;
                setInterval(function() {
                    imgs[idx].style.display = "none";
                    dotEls[idx].classList.remove("active");
                    idx = (idx + 1) % imgs.length;
                    imgs[idx].style.display = "block";
                    dotEls[idx].classList.add("active");
                }, 3000);
            }
        });
    }

    function formatNumber(n) {
        if (n >= 10000) return (n / 10000).toFixed(1) + "w";
        if (n >= 1000) return (n / 1000).toFixed(1) + "k";
        return n;
    }

    // 初始加载
    loadPosts();
});

function copyText(el) {
    const text = el.textContent;
    navigator.clipboard.writeText(text).then(function() {
        const orig = el.style.background;
        el.style.background = "rgba(102, 187, 106, 0.3)";
        setTimeout(function() { el.style.background = orig; }, 500);
    });
}
