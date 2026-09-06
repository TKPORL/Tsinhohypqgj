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

    // ========== 结果面板 - 分组 + 多选 + 批量操作 ==========
    const selectedIds = new Set();

    function loadPosts() {
        selectedIds.clear();
        updateBatchBar();
        var source = document.getElementById("filterSource").value;
        var platTab = document.querySelector(".plat-tab.active");
        var platform = platTab ? platTab.dataset.plat : "all";
        fetch("/api/posts_grouped?source=" + source + "&platform=" + platform)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var totalPosts = 0;
                data.groups.forEach(function(g) { totalPosts += g.total; });
                document.getElementById("resultCount").textContent = totalPosts;
                renderGroups(data.groups);
            });
    }

    document.getElementById("filterSource").addEventListener("change", loadPosts);

    window.switchPlatTab = function(btn) {
        document.querySelectorAll(".plat-tab").forEach(function(b) { b.classList.remove("active"); });
        btn.classList.add("active");
        loadPosts();
    };

    function renderGroups(groups) {
        const container = document.getElementById("groupedResults");
        container.innerHTML = "";
        const stickyBtns = document.getElementById("stickyBtns");
        stickyBtns.innerHTML = "";

        groups.forEach((group, idx) => {
            // 吸顶按钮
            const btn = document.createElement("button");
            btn.className = "sticky-date-btn";
            btn.textContent = group.date + " (" + group.total + ")";
            btn.dataset.group = idx;
            btn.addEventListener("click", function() {
                const targetGroup = document.getElementById("group-" + idx);
                const wasExpanded = targetGroup.classList.contains("expanded");
                document.querySelectorAll(".date-group").forEach(g => g.classList.remove("expanded"));
                document.querySelectorAll(".sticky-date-btn").forEach(b => b.classList.remove("active"));
                if (!wasExpanded) {
                    targetGroup.classList.add("expanded");
                    this.classList.add("active");
                    targetGroup.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });
            stickyBtns.appendChild(btn);

            // 分组容器
            const groupEl = document.createElement("div");
            groupEl.className = "date-group";
            groupEl.id = "group-" + idx;

            const headerEl = document.createElement("div");
            headerEl.className = "date-group-header";
            headerEl.innerHTML = '<span class="date-label">' + group.date + '</span><span class="date-count">' + group.total + ' 条</span><button class="btn btn-sm toggle-btn" onclick="toggleGroup(' + idx + ')">展开</button>';
            groupEl.appendChild(headerEl);

            const gridEl = document.createElement("div");
            gridEl.className = "card-grid group-cards";
            group.posts.forEach(function(post) {
                gridEl.appendChild(createCard(post));
            });
            groupEl.appendChild(gridEl);

            container.appendChild(groupEl);
        });
    }

    window.toggleGroup = function(idx) {
        const group = document.getElementById("group-" + idx);
        const wasExpanded = group.classList.contains("expanded");
        document.querySelectorAll(".date-group").forEach(function(g) { g.classList.remove("expanded"); });
        document.querySelectorAll(".sticky-date-btn").forEach(function(b) { b.classList.remove("active"); });
        if (!wasExpanded) {
            group.classList.add("expanded");
            var btn = document.querySelector('.sticky-date-btn[data-group="' + idx + '"]');
            if (btn) btn.classList.add("active");
        }
    };

    function createCard(post) {
        const card = document.createElement("div");
        card.className = "card";

        var images = [];
        try { images = JSON.parse(post.images || "[]"); } catch(e) {}
        var rawImage = images[0] || "";
        var image = rawImage ? (rawImage.indexOf("/images/") === 0 ? rawImage : "/api/proxy_image?url=" + encodeURIComponent(rawImage)) : "";

        var platformTags = {
            pc: '<span class="tag tag-pc">PC</span>',
            android: '<span class="tag tag-android">安卓</span>',
            pc_android: '<span class="tag tag-pc">PC</span><span class="tag tag-android">安卓</span>',
            unknown: '<span class="tag tag-pc">未知</span>'
        };
        var platformTag = platformTags[post.platform] || platformTags.unknown;

        var hasDual = post.baidu_link && post.mobile_link;
        var dualTag = hasDual ? '<span class="tag tag-dual">双网盘</span>' : '';

        var linksHtml = "";
        if (post.baidu_link) {
            linksHtml += '<a href="' + post.baidu_link + '" class="link-btn link-baidu" target="_blank">百度网盘' + (post.baidu_code ? ' ('+post.baidu_code+')' : '') + '</a>';
        }
        if (post.mobile_link) {
            linksHtml += '<a href="' + post.mobile_link + '" class="link-btn link-mobile" target="_blank">移动云盘' + (post.mobile_code ? ' ('+post.mobile_code+')' : '') + '</a>';
        }
        linksHtml += '<a href="' + post.source_url + '" class="link-btn link-source" target="_blank">原帖</a>';

        var footerHtml = "";
        if (post.unzip_code || post.cheat_code) {
            footerHtml = '<div class="card-footer"><div class="footer-left">';
            if (post.unzip_code) {
                footerHtml += '<button class="btn btn-sm btn-unzip" data-copy="解压码：' + post.unzip_code + '" onclick="copyText(this)">解压码</button>';
            }
            if (post.cheat_code) {
                footerHtml += '<button class="btn btn-sm btn-unzip" data-copy="作弊码：' + post.cheat_code + '" onclick="copyText(this)">作弊码</button>';
            }
            footerHtml += '</div></div>';
        }

        var displayTitle = post.title.replace(/【([^】]*)\/([^】]*)】/g, '【$1 $2】');

        var statsHtml = '';
        if (post.source !== '萌幻ACG') {
            statsHtml = '<div class="card-stats"><span class="stat-item">❤ ' + (post.likes || 0) + '</span><span class="stat-item">💬 ' + (post.comments || 0) + '</span><span class="stat-item">👁 ' + formatNumber(post.views || 0) + '</span></div>';
        }

        card.innerHTML = '<div class="card-header"><div class="card-select"><input type="checkbox" data-id="' + post.id + '" onchange="toggleSelect(this)"></div><div class="card-tags">' + platformTag + dualTag + '<span class="tag tag-source">' + post.source + '</span></div><span class="tag tag-date">' + (post.post_date || '') + '</span></div><div class="card-images"><img src="' + image + '" alt="" onerror="this.style.display=\'none\'"></div><div class="card-body"><div class="card-title" onclick="copyTitle(this)" title="点击复制标题">' + displayTitle + '</div>' + statsHtml + '<div class="card-links">' + linksHtml + '</div></div>' + footerHtml + '<div class="card-actions"><button class="btn btn-sm btn-danger" onclick="deletePost(' + post.id + ')">删除</button></div>';
        return card;
    }

    function formatNumber(n) {
        if (n >= 10000) return (n / 10000).toFixed(1) + "w";
        if (n >= 1000) return (n / 1000).toFixed(1) + "k";
        return n;
    }

    // 全选/取消全选
    document.getElementById("selectAll").addEventListener("change", function() {
        var checked = this.checked;
        document.querySelectorAll(".card-select input[type='checkbox']").forEach(function(cb) {
            cb.checked = checked;
            var id = parseInt(cb.dataset.id);
            if (checked) { selectedIds.add(id); } else { selectedIds.delete(id); }
        });
        updateBatchBar();
    });

    function updateBatchBar() {
        var bar = document.getElementById("batchBar");
        var count = selectedIds.size;
        document.getElementById("selectedCount").textContent = count;
        bar.classList.toggle("active", count > 0);
    }

    // 单选切换
    window.toggleSelect = function(cb) {
        var id = parseInt(cb.dataset.id);
        if (cb.checked) { selectedIds.add(id); } else { selectedIds.delete(id); }
        updateBatchBar();
    };

    // 删除帖子
    window.deletePost = function(id) {
        if (!confirm("确定删除这条记录？")) return;
        fetch("/api/delete_post", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id: id})
        }).then(function() { loadPosts(); });
    };

    // 批量删除
    document.getElementById("batchDeleteBtn").addEventListener("click", function() {
        if (selectedIds.size === 0) return;
        if (!confirm("确定删除选中的 " + selectedIds.size + " 条记录？")) return;
        fetch("/api/batch_delete", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ids: Array.from(selectedIds)})
        }).then(function() {
            selectedIds.clear();
            loadPosts();
        });
    });

    // 批量导出选中
    document.getElementById("batchExportBtn").addEventListener("click", function() {
        if (selectedIds.size === 0) return;
        var ids = Array.from(selectedIds).join(",");
        window.location.href = "/api/export_download?type=selected&ids=" + ids;
    });

    // 加载历史
    function loadHistory() {
        fetch("/api/tasks")
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var tbody = document.getElementById("historyBody");
                tbody.innerHTML = "";
                data.forEach(function(task) {
                    var tr = document.createElement("tr");
                    var statusBadge = {
                        completed: '<span class="badge badge-success">完成</span>',
                        running: '<span class="badge badge-warning">运行中</span>',
                        failed: '<span class="badge badge-error">失败</span>',
                        cancelled: '<span class="badge badge-warning">已取消</span>',
                    }[task.status] || task.status;

                    var dlBtns = '';
                    if (task.status === 'completed') {
                        dlBtns = '<div class="history-dl-btns">' +
                            '<a href="/api/export_download?type=pc" class="btn btn-sm btn-dl" download>PC.html</a>' +
                            '<a href="/api/export_download?type=android" class="btn btn-sm btn-dl" download>安卓.html</a>' +
                            '<a href="/api/export_download?type=mixed" class="btn btn-sm btn-dl" download>PC+安卓.html</a>' +
                            '</div>';
                    }

                    tr.innerHTML = '<td>' + task.id + '</td><td>' + (task.task_type === 'by_page' ? '按页码' : task.task_type === 'incremental' ? '增量' : '按日期') + '</td><td>' + (task.sites || '') + '</td><td>' + statusBadge + '</td><td>' + task.success_posts + '</td><td>' + task.skipped_posts + '</td><td>' + task.error_posts + '</td><td>' + (task.created_at || '') + '</td><td>' + dlBtns + '<button class="btn btn-sm btn-danger" onclick="deleteTask(' + task.id + ')">删除</button></td>';
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
        }).then(function() { loadHistory(); });
    };

    // 导出页面
    function loadExportInfo() {
        fetch("/api/posts?limit=1")
            .then(function(r) { return r.json(); })
            .then(function(data) {
                document.getElementById("exportTotal").textContent = data.total;
            });
        // 获取各平台数量
        fetch("/api/export_counts")
            .then(function(r) { return r.json(); })
            .then(function(data) {
                document.getElementById("countPc").textContent = data.pc || 0;
                document.getElementById("countAndroid").textContent = data.android || 0;
                document.getElementById("countMixed").textContent = data.mixed || 0;
            });
    }

    // 直接下载导出文件
    window.doExport = function(type) {
        window.location.href = "/api/export_download?type=" + type;
    };
});

// 复制文本
function copyText(el) {
    var text = el.dataset.copy || el.textContent;
    navigator.clipboard.writeText(text).then(function() {
        var orig = el.textContent;
        el.textContent = "已复制!";
        el.disabled = true;
        setTimeout(function() {
            el.textContent = orig;
            el.disabled = false;
        }, 800);
    });
}

// 复制标题
function copyTitle(el) {
    var text = el.textContent;
    navigator.clipboard.writeText(text).then(function() {
        el.classList.add("copied-title");
        var orig = el.textContent;
        el.textContent = "已复制!";
        setTimeout(function() {
            el.classList.remove("copied-title");
            el.textContent = orig;
        }, 800);
    });
}
