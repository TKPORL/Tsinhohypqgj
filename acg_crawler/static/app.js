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

            if (this.dataset.panel === "result") loadPosts();
            if (this.dataset.panel === "history") loadHistory();
            if (this.dataset.panel === "export") loadExportInfo();
        });
    });

    // 爬取模式切换
    const modeRadios = document.querySelectorAll('input[name="crawlMode"]');
    const dateGroup = document.getElementById("dateGroup");
    const pageGroup = document.getElementById("pageGroup");
    const incrementalGroup = document.getElementById("incrementalGroup");
    modeRadios.forEach(radio => {
        radio.addEventListener("change", function() {
            dateGroup.classList.add("hidden");
            pageGroup.classList.add("hidden");
            incrementalGroup.classList.add("hidden");
            if (this.value === "by_date") {
                dateGroup.classList.remove("hidden");
            } else if (this.value === "by_page") {
                pageGroup.classList.remove("hidden");
            } else if (this.value === "incremental") {
                incrementalGroup.classList.remove("hidden");
            }
        });
    });

    // 开始爬取
    const startBtn = document.getElementById("startBtn");
    const stopBtn = document.getElementById("stopBtn");
    const progressSection = document.getElementById("progressSection");
    const progressFill = document.getElementById("progressFill");
    const progressText = document.getElementById("progressText");
    const logBox = document.getElementById("logBox");
    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");
    let pollTimer = null;

    startBtn.addEventListener("click", function() {
        const sites = [];
        document.querySelectorAll('.checkbox-group input:checked').forEach(cb => {
            sites.push(cb.value);
        });
        if (sites.length === 0) {
            alert("请至少选择一个站点");
            return;
        }

        const mode = document.querySelector('input[name="crawlMode"]:checked').value;
        const body = { mode: mode, sites: sites };

        if (mode === "by_page") {
            body.start_page = parseInt(document.getElementById("startPage").value) || 1;
            body.end_page = parseInt(document.getElementById("endPage").value) || 10;
        } else {
            body.start_date = document.getElementById("startDate").value;
            body.end_date = document.getElementById("endDate").value;
        }

        fetch("/api/start_crawl", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)
        })
        .then(r => r.json())
        .then(data => {
            if (data.status === "ok") {
                startBtn.classList.add("hidden");
                stopBtn.classList.remove("hidden");
                progressSection.classList.remove("hidden");
                statusDot.classList.add("running");
                statusText.textContent = "爬取中...";
                logBox.innerHTML = "";
                pollProgress();
            } else {
                alert(data.message || "启动失败");
            }
        });
    });

    stopBtn.addEventListener("click", function() {
        fetch("/api/stop_crawl", {method: "POST"});
        clearInterval(pollTimer);
        startBtn.classList.remove("hidden");
        stopBtn.classList.add("hidden");
        statusDot.classList.remove("running");
        statusText.textContent = "已停止";
    });

    function pollProgress() {
        pollTimer = setInterval(function() {
            fetch("/api/progress")
                .then(r => r.json())
                .then(data => {
                    const pct = data.total > 0 ? Math.round((data.current / data.total) * 100) : 0;
                    progressFill.style.width = pct + "%";
                    progressText.textContent = data.current + " / " + data.total;
                    document.getElementById("statSuccess").textContent = data.success;
                    document.getElementById("statSkipped").textContent = data.skipped;
                    document.getElementById("statError").textContent = data.error;

                    if (data.recent_logs) {
                        logBox.innerHTML = "";
                        data.recent_logs.forEach(log => {
                            const line = document.createElement("div");
                            line.className = "log-line" + (log.level === "error" ? " error" : "");
                            line.textContent = log.text;
                            logBox.appendChild(line);
                        });
                        logBox.scrollTop = logBox.scrollHeight;
                    }

                    if (!data.running) {
                        clearInterval(pollTimer);
                        startBtn.classList.remove("hidden");
                        stopBtn.classList.add("hidden");
                        statusDot.classList.remove("running");
                        statusText.textContent = "完成";
                    }
                });
        }, 1000);
    }

    // ========== 结果面板 - 多选 + 批量操作 ==========
    let postOffset = 0;
    const selectedIds = new Set();

    function loadPosts() {
        postOffset = 0;
        selectedIds.clear();
        updateBatchBar();
        const source = document.getElementById("filterSource").value;
        const platform = document.getElementById("filterPlatform").value;
        fetch(`/api/posts?source=${source}&platform=${platform}&limit=50&offset=0`)
            .then(r => r.json())
            .then(data => {
                document.getElementById("resultCount").textContent = data.total;
                renderCards(data.posts);
                document.getElementById("loadMore").classList.toggle("hidden", data.posts.length < 50);
                postOffset = data.posts.length;
            });
    }

    document.getElementById("filterSource").addEventListener("change", loadPosts);
    document.getElementById("filterPlatform").addEventListener("change", loadPosts);

    document.getElementById("loadMoreBtn").addEventListener("click", function() {
        const source = document.getElementById("filterSource").value;
        const platform = document.getElementById("filterPlatform").value;
        fetch(`/api/posts?source=${source}&platform=${platform}&limit=50&offset=${postOffset}`)
            .then(r => r.json())
            .then(data => {
                appendCards(data.posts);
                postOffset += data.posts.length;
                if (data.posts.length < 50) {
                    document.getElementById("loadMore").classList.add("hidden");
                }
            });
    });

    // 全选/取消全选
    document.getElementById("selectAll").addEventListener("change", function() {
        const checked = this.checked;
        document.querySelectorAll(".card-select input[type='checkbox']").forEach(cb => {
            cb.checked = checked;
            const id = parseInt(cb.dataset.id);
            if (checked) {
                selectedIds.add(id);
            } else {
                selectedIds.delete(id);
            }
        });
        updateBatchBar();
    });

    function updateBatchBar() {
        const bar = document.getElementById("batchBar");
        const count = selectedIds.size;
        document.getElementById("selectedCount").textContent = count;
        bar.classList.toggle("active", count > 0);
    }

    function renderCards(posts) {
        const grid = document.getElementById("cardGrid");
        grid.innerHTML = "";
        document.getElementById("selectAll").checked = false;
        appendCards(posts);
    }

    function appendCards(posts) {
        const grid = document.getElementById("cardGrid");
        posts.forEach(post => {
            const card = document.createElement("div");
            card.className = "card";

            let images = [];
            try { images = JSON.parse(post.images || "[]"); } catch(e) {}
            const rawImage = images[0] || "";
            const image = rawImage ? ("/api/proxy_image?url=" + encodeURIComponent(rawImage)) : "";

            const platformTags = {
                pc: '<span class="tag tag-pc">PC</span>',
                android: '<span class="tag tag-android">安卓</span>',
                pc_android: '<span class="tag tag-pc">PC</span><span class="tag tag-android">安卓</span>',
                unknown: '<span class="tag tag-pc">未知</span>'
            };
            const platformTag = platformTags[post.platform] || platformTags.unknown;

            const hasDual = post.baidu_link && post.mobile_link;
            const dualTag = hasDual ? '<span class="tag tag-dual">双网盘</span>' : '';

            let linksHtml = "";
            if (post.baidu_link) {
                linksHtml += `<a href="${post.baidu_link}" class="link-btn link-baidu" target="_blank">百度网盘${post.baidu_code ? ' ('+post.baidu_code+')' : ''}</a>`;
            }
            if (post.mobile_link) {
                linksHtml += `<a href="${post.mobile_link}" class="link-btn link-mobile" target="_blank">移动云盘${post.mobile_code ? ' ('+post.mobile_code+')' : ''}</a>`;
            }
            linksHtml += `<a href="${post.source_url}" class="link-btn link-source" target="_blank">原帖</a>`;

            let footerHtml = "";
            if (post.unzip_code || post.cheat_code) {
                footerHtml = '<div class="card-footer"><div class="footer-left">';
                if (post.unzip_code) footerHtml += `<span>解压码: <span class="copy-text" data-copy="解压码：${post.unzip_code}" onclick="copyText(this)">${post.unzip_code}</span></span>`;
                if (post.cheat_code) footerHtml += `<span>作弊码: <span class="copy-text" data-copy="作弊码：${post.cheat_code}" onclick="copyText(this)">${post.cheat_code}</span></span>`;
                footerHtml += '</div></div>';
            }

            card.innerHTML = `
                <div class="card-header">
                    <div class="card-select"><input type="checkbox" data-id="${post.id}" onchange="toggleSelect(this)"></div>
                    <div class="card-tags">${platformTag}${dualTag}<span class="tag tag-source">${post.source}</span></div>
                    <span class="tag tag-date">${post.post_date || ''}</span>
                </div>
                <div class="card-images">
                    <img src="${image}" alt="" onerror="this.style.display='none'">
                </div>
                <div class="card-body">
                    <div class="card-title">${post.title}</div>
                    <div class="card-stats">
                        <span class="stat-item">❤ ${post.likes || 0}</span>
                        <span class="stat-item">💬 ${post.comments || 0}</span>
                        <span class="stat-item">👁 ${formatNumber(post.views || 0)}</span>
                    </div>
                    <div class="card-links">${linksHtml}</div>
                </div>
                ${footerHtml}
                <div class="card-actions">
                    <button class="btn btn-sm btn-danger" onclick="deletePost(${post.id})">删除</button>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    function formatNumber(n) {
        if (n >= 10000) return (n / 10000).toFixed(1) + "w";
        if (n >= 1000) return (n / 1000).toFixed(1) + "k";
        return n;
    }

    // 单选切换
    window.toggleSelect = function(cb) {
        const id = parseInt(cb.dataset.id);
        if (cb.checked) {
            selectedIds.add(id);
        } else {
            selectedIds.delete(id);
        }
        updateBatchBar();
    };

    // 删除帖子
    window.deletePost = function(id) {
        if (!confirm("确定删除这条记录？")) return;
        fetch("/api/delete_post", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id: id})
        }).then(() => loadPosts());
    };

    // 批量删除
    document.getElementById("batchDeleteBtn").addEventListener("click", function() {
        if (selectedIds.size === 0) return;
        if (!confirm(`确定删除选中的 ${selectedIds.size} 条记录？`)) return;
        fetch("/api/batch_delete", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ids: Array.from(selectedIds)})
        }).then(() => {
            selectedIds.clear();
            loadPosts();
        });
    });

    // 批量导出选中
    document.getElementById("batchExportBtn").addEventListener("click", function() {
        if (selectedIds.size === 0) return;
        const ids = Array.from(selectedIds).join(",");
        window.location.href = "/api/export_download?type=selected&ids=" + ids;
    });

    // 加载历史
    function loadHistory() {
        fetch("/api/tasks")
            .then(r => r.json())
            .then(data => {
                const tbody = document.getElementById("historyBody");
                tbody.innerHTML = "";
                data.forEach(task => {
                    const tr = document.createElement("tr");
                    const statusBadge = {
                        completed: '<span class="badge badge-success">完成</span>',
                        running: '<span class="badge badge-warning">运行中</span>',
                        failed: '<span class="badge badge-error">失败</span>',
                        cancelled: '<span class="badge badge-warning">已取消</span>',
                    }[task.status] || task.status;
                    tr.innerHTML = `
                        <td>${task.id}</td>
                        <td>${task.task_type === 'by_page' ? '按页码' : task.task_type === 'incremental' ? '增量' : '按日期'}</td>
                        <td>${task.sites || ''}</td>
                        <td>${statusBadge}</td>
                        <td>${task.success_posts}</td>
                        <td>${task.skipped_posts}</td>
                        <td>${task.error_posts}</td>
                        <td>${task.created_at || ''}</td>
                        <td>
                            <button class="btn btn-sm btn-danger" onclick="deleteTask(${task.id})">删除</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            });
    }

    window.deleteTask = function(id) {
        if (!confirm("确定删除这条历史记录？")) return;
        fetch("/api/delete_task", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id: id})
        }).then(() => loadHistory());
    };

    // 导出页面
    function loadExportInfo() {
        fetch("/api/posts?limit=1")
            .then(r => r.json())
            .then(data => {
                document.getElementById("exportTotal").textContent = data.total;
            });
    }

    // 直接下载导出文件
    window.doExport = function(type) {
        window.location.href = "/api/export_download?type=" + type;
    };
});

// 复制文本 - 复制完整文本（含前缀）
function copyText(el) {
    const text = el.dataset.copy || el.textContent;
    navigator.clipboard.writeText(text).then(function() {
        el.classList.add("copied");
        const orig = el.textContent;
        el.textContent = "已复制!";
        setTimeout(function() {
            el.classList.remove("copied");
            el.textContent = orig;
        }, 800);
    });
}
