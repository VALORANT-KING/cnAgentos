(function() {
    var currentDays = 7;
    var currentChartType = 'line';
    var charts = {};
    var refreshTimer = null;

    function disposeChart(key) {
        if (charts[key]) {
            try { charts[key].dispose(); } catch (e) {}
            charts[key] = null;
        }
    }

    function disposeAll() {
        var keys = ['wordcloud', 'earth3d', 'trend', 'sentiment'];
        for (var i = 0; i < keys.length; i++) {
            disposeChart(keys[i]);
        }
    }

    function initOrReuse(key, domId) {
        disposeChart(key);
        var dom = document.getElementById(domId);
        if (!dom) return null;
        var inst = echarts.init(dom);
        charts[key] = inst;
        return inst;
    }

    function ajaxGet(url, callback) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    try {
                        var data = JSON.parse(xhr.responseText);
                        callback(data);
                    } catch (e) {
                        console.error('JSON parse error for ' + url, e);
                    }
                } else {
                    console.error('HTTP ' + xhr.status + ' for ' + url);
                    showToast('数据加载失败，请刷新重试');
                }
            }
        };
        xhr.onerror = function() {
            console.error('Network error for ' + url);
            showToast('网络异常，请检查连接后重试');
        };
        xhr.timeout = 15000;
        xhr.ontimeout = function() {
            console.error('Timeout for ' + url);
            showToast('请求超时，请稍后重试');
        };
        xhr.send();
    }

    function ajaxPost(url, body, callback) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', url, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    try {
                        var data = JSON.parse(xhr.responseText);
                        callback(data);
                    } catch (e) {
                        console.error('JSON parse error for ' + url, e);
                    }
                } else {
                    console.error('HTTP ' + xhr.status + ' for ' + url);
                    showToast('请求失败，请稍后重试');
                }
            }
        };
        xhr.onerror = function() {
            console.error('Network error for ' + url);
            showToast('网络异常，请检查连接后重试');
        };
        xhr.timeout = 15000;
        xhr.ontimeout = function() {
            console.error('Timeout for ' + url);
            showToast('请求超时，请稍后重试');
        };
        xhr.send(JSON.stringify(body));
    }

    function showToast(msg) {
        var toast = document.getElementById('screenToast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'screenToast';
            toast.className = 'screen-toast';
            document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.style.display = 'block';
        toast.style.opacity = '1';
        clearTimeout(toast._timer);
        toast._timer = setTimeout(function() {
            toast.style.opacity = '0';
            setTimeout(function() { toast.style.display = 'none'; }, 300);
        }, 3000);
    }

    function loadStats(days) {
        ajaxGet('/api/screen/stats', function(res) {
            if (res.code !== 0 || !res.data) return;
            var d = res.data;

            var trendChartInst = initOrReuse('trend', 'trendChart');
            if (trendChartInst && d.trend_dates) {
                var seriesData = [
                    {
                        name: '采集数据量',
                        type: currentChartType,
                        data: d.trend_values || [],
                        smooth: currentChartType === 'line',
                        symbol: 'circle',
                        symbolSize: 6,
                        lineStyle: { color: '#00c6ff', width: 2 },
                        itemStyle: { color: '#00dcff' },
                        areaStyle: currentChartType === 'line' ? {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: 'rgba(0,198,255,0.3)' },
                                { offset: 1, color: 'rgba(0,100,200,0.02)' }
                            ])
                        } : undefined
                    },
                    {
                        name: '问数消息量',
                        type: currentChartType,
                        data: d.msg_trend_values || [],
                        smooth: currentChartType === 'line',
                        symbol: 'diamond',
                        symbolSize: 6,
                        lineStyle: { color: '#00c864', width: 2 },
                        itemStyle: { color: '#00e878' },
                        areaStyle: currentChartType === 'line' ? {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: 'rgba(0,200,100,0.25)' },
                                { offset: 1, color: 'rgba(0,150,80,0.02)' }
                            ])
                        } : undefined
                    }
                ];

                trendChartInst.setOption({
                    backgroundColor: 'transparent',
                    grid: { left: 50, right: 20, top: 35, bottom: 25 },
                    legend: {
                        data: ['采集数据量', '问数消息量'],
                        textStyle: { color: '#6a8099', fontSize: 11 },
                        top: 5
                    },
                    xAxis: {
                        type: 'category',
                        data: d.trend_dates,
                        axisLine: { lineStyle: { color: 'rgba(0,150,255,0.3)' } },
                        axisLabel: { color: '#6a8099', fontSize: 11 }
                    },
                    yAxis: {
                        type: 'value',
                        name: '数量',
                        nameTextStyle: { color: '#5a7494', fontSize: 11 },
                        axisLine: { lineStyle: { color: 'rgba(0,150,255,0.3)' } },
                        axisLabel: { color: '#6a8099', fontSize: 11 },
                        splitLine: { lineStyle: { color: 'rgba(0,150,255,0.08)' } }
                    },
                    series: seriesData,
                    tooltip: {
                        trigger: 'axis',
                        backgroundColor: 'rgba(10,20,44,0.9)',
                        borderColor: 'rgba(0,150,255,0.3)',
                        textStyle: { color: '#e0e6ed', fontSize: 12 }
                    }
                }, true);
            }

            var elSU = document.getElementById('statUsers');
            var elSS = document.getElementById('statSessions');
            var elSW = document.getElementById('statWatch');
            if (elSU) elSU.textContent = d.total_users || 0;
            if (elSS) elSS.textContent = d.total_sessions || 0;
            if (elSW) elSW.textContent = d.total_watch_data || 0;
        });
    }

    function loadWordcloud() {
        ajaxGet('/api/screen/wordcloud', function(res) {
            if (res.code !== 0 || !res.data || !res.data.length) return;

            var wcInst = initOrReuse('wordcloud', 'wordcloud');
            if (!wcInst) return;

            wcInst.off('click');
            wcInst.on('click', function(params) {
                if (params.data && params.data.name) {
                    showWordDetail(params.data.name);
                }
            });

            wcInst.setOption({
                backgroundColor: 'transparent',
                series: [{
                    type: 'wordCloud',
                    shape: 'circle',
                    left: 'center',
                    top: 'center',
                    width: '90%',
                    height: '90%',
                    sizeRange: [14, 48],
                    rotationRange: [-30, 30],
                    rotationStep: 15,
                    gridSize: 8,
                    drawOutOfBound: false,
                    textStyle: {
                        fontFamily: 'Microsoft YaHei, PingFang SC, sans-serif',
                        fontWeight: 'normal',
                        color: function() {
                            var colors = [
                                '#00c6ff', '#00dcff', '#0096ff', '#0072ff',
                                '#00b4d8', '#48cae4', '#90e0ef', '#ade8f4',
                                '#caf0f8', '#00a8e8'
                            ];
                            return colors[Math.floor(Math.random() * colors.length)];
                        }
                    },
                    emphasis: {
                        textStyle: {
                            fontWeight: 'bold',
                            color: '#ffffff',
                            shadowBlur: 8,
                            shadowColor: 'rgba(0,200,255,0.6)'
                        }
                    },
                    data: res.data.map(function(item) {
                        return {
                            name: item.name,
                            value: item.value
                        };
                    })
                }]
            });
        });
    }

    function showWordDetail(keyword) {
        ajaxGet('/api/screen/word-detail?keyword=' + encodeURIComponent(keyword), function(res) {
            var modal = document.getElementById('wordDetailModal');
            var list = document.getElementById('wordDetailList');
            var title = document.getElementById('wordDetailTitle');
            if (!modal || !list) return;

            if (title) title.textContent = '关键词：' + keyword;

            if (res.code !== 0 || !res.data || !res.data.length) {
                list.innerHTML = '<div class="word-detail-empty">暂无包含"' + keyword + '"的瞭望数据</div>';
            } else {
                var html = '';
                for (var i = 0; i < res.data.length; i++) {
                    var item = res.data[i];
                    html += '<div class="word-detail-item">';
                    html += '<div class="word-detail-title">' + escapeHtml(item.title || '无标题') + '</div>';
                    html += '<div class="word-detail-meta">';
                    if (item.url) {
                        html += '<a class="word-detail-link" href="' + escapeHtml(item.url) + '" target="_blank" rel="noopener">查看原文 <i class="fas fa-external-link-alt"></i></a>';
                    }
                    html += '<span class="word-detail-time">' + (item.create_at || '') + '</span>';
                    html += '</div></div>';
                }
                list.innerHTML = html;
            }
            modal.style.display = 'flex';
        });
    }

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    function closeWordDetail() {
        var modal = document.getElementById('wordDetailModal');
        if (modal) modal.style.display = 'none';
    }

    function showLocationNews(location) {
        ajaxGet('/api/screen/location-news?location=' + encodeURIComponent(location), function(res) {
            var modal = document.getElementById('locationNewsModal');
            var list = document.getElementById('locationNewsList');
            var title = document.getElementById('locationNewsTitle');
            if (!modal || !list) return;

            if (title) title.textContent = '地点：' + location;

            if (res.code !== 0 || !res.data || !res.data.length) {
                list.innerHTML = '<div class="word-detail-empty">暂无与"' + location + '"相关的瞭望数据</div>';
            } else {
                var html = '';
                for (var i = 0; i < res.data.length; i++) {
                    var item = res.data[i];
                    html += '<div class="word-detail-item">';
                    html += '<div class="word-detail-title">' + escapeHtml(item.title || '无标题') + '</div>';
                    if (item.summary) {
                        html += '<div class="word-detail-summary">' + escapeHtml(item.summary) + '</div>';
                    }
                    html += '<div class="word-detail-meta">';
                    if (item.url) {
                        html += '<a class="word-detail-link" href="' + escapeHtml(item.url) + '" target="_blank" rel="noopener">查看原文 <i class="fas fa-external-link-alt"></i></a>';
                    }
                    html += '<span class="word-detail-time">' + (item.create_at || '') + '</span>';
                    html += '</div></div>';
                }
                list.innerHTML = html;
            }
            modal.style.display = 'flex';
        });
    }

    function closeLocationNews() {
        var modal = document.getElementById('locationNewsModal');
        if (modal) modal.style.display = 'none';
    }

    var worldMapLoaded = false;
    var cachedEarthData = null;
    var cachedWorldGeoJSON = null;
    var cachedChinaGeoJSON = null;

    function loadWorldMap(callback) {
        if (worldMapLoaded) {
            callback();
            return;
        }
        var loadedCount = 0;
        function onBothLoaded() {
            loadedCount++;
            if (loadedCount >= 2) {
                worldMapLoaded = true;
                callback();
            }
        }
        ajaxGet('/static/data/world.json', function(worldJson) {
            try {
                echarts.registerMap('world', worldJson);
                cachedWorldGeoJSON = worldJson;
            } catch (e) {
                console.error('Failed to register world map:', e);
            }
            onBothLoaded();
        });
        ajaxGet('/static/data/china.json', function(chinaJson) {
            try {
                cachedChinaGeoJSON = chinaJson;
            } catch (e) {
                console.error('Failed to load china map:', e);
            }
            onBothLoaded();
        });
    }

    function generateEarthTexture() {
        if (!cachedWorldGeoJSON) return '';

        var canvas = document.createElement('canvas');
        canvas.width = 2048;
        canvas.height = 1024;
        var ctx = canvas.getContext('2d');

        ctx.fillStyle = '#0a1e3d';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        drawFeatureCollection(ctx, cachedWorldGeoJSON, canvas.width, canvas.height,
            '#13305a', 'rgba(80,200,240,0.5)', 0.5);

        if (cachedChinaGeoJSON) {
            drawFeatureCollection(ctx, cachedChinaGeoJSON, canvas.width, canvas.height,
                'rgba(0,180,255,0.12)', 'rgba(255,200,60,0.8)', 1.2);
        }

        return canvas;
    }

    function drawFeatureCollection(ctx, geojson, w, h, fillColor, strokeColor, lineWidth) {
        var features = geojson.features || [];
        ctx.fillStyle = fillColor;
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = lineWidth;
        for (var i = 0; i < features.length; i++) {
            var geom = features[i].geometry;
            if (!geom) continue;
            drawGeometrySimple(ctx, geom, w, h);
        }
    }

    function drawGeometrySimple(ctx, geom, w, h) {
        var coords = geom.coordinates;
        if (!coords) return;
        var type = geom.type;
        if (type === 'Polygon') {
            drawPolygon(ctx, coords, w, h);
        } else if (type === 'MultiPolygon') {
            for (var i = 0; i < coords.length; i++) {
                drawPolygon(ctx, coords[i], w, h);
            }
        }
    }

    function drawPolygon(ctx, rings, w, h) {
        for (var r = 0; r < rings.length; r++) {
            var ring = rings[r];
            if (ring.length < 3) continue;
            ctx.beginPath();
            var first = true;
            for (var i = 0; i < ring.length; i++) {
                var lng = ring[i][0];
                var lat = ring[i][1];
                var x = (lng + 180) / 360 * w;
                var y = (90 - lat) / 180 * h;
                if (first) {
                    ctx.moveTo(x, y);
                    first = false;
                } else {
                    ctx.lineTo(x, y);
                }
            }
            ctx.closePath();
            if (r === 0) {
                ctx.fill();
            }
            ctx.stroke();
        }
    }

    function loadEarthData() {
        ajaxGet('/api/screen/earth-data', function(res) {
            if (res.code !== 0 || !res.data) return;
            cachedEarthData = res.data;
            loadWorldMap(function() {
                renderEarth3D(cachedEarthData);
            });
        });
    }

    function renderEarth3D(earthData) {
        var dom = document.getElementById('earth3d');
        if (!dom) return;
        disposeChart('earth3d');
        var earthInst = echarts.init(dom);
        charts['earth3d'] = earthInst;

        var scatterData = earthData.map(function(item) {
            var isGreen = item.sentiment > 0.5;
            return {
                name: item.name,
                value: [item.lng, item.lat, item.value],
                symbolSize: Math.max((item.value || 5) / 4, 8),
                itemStyle: {
                    color: isGreen ? 'rgb(0,210,100)' : 'rgb(240,60,50)'
                }
            };
        });

        earthInst.off('click');
        earthInst.on('click', function(params) {
            if (params.seriesType === 'scatter3D' && params.data && params.data.name) {
                showLocationNews(params.data.name);
            }
        });

        earthInst.setOption({
            backgroundColor: 'transparent',
            tooltip: {
                show: true,
                trigger: 'item',
                backgroundColor: 'rgba(10,22,44,0.92)',
                borderColor: 'rgba(0,200,255,0.3)',
                textStyle: { color: '#e0e6ed', fontSize: 12 },
                formatter: function(p) {
                    if (p.seriesType === 'scatter3D' && p.data && p.data.name) {
                        var found = null;
                        for (var i = 0; i < earthData.length; i++) {
                            if (earthData[i].name === p.data.name) {
                                found = earthData[i];
                                break;
                            }
                        }
                        var val = found ? found.value : '--';
                        return '<b>' + p.data.name + '</b><br/>热度: ' + val;
                    }
                    return p.name || '';
                }
            },
            globe: {
                globeRadius: 95,
                globeOuterRadius: 95,
                baseTexture: generateEarthTexture(),
                shading: 'lambert',
                displacementScale: 0.02,
                light: {
                    main: { intensity: 1.2, shadow: false, alpha: 30, beta: 15 },
                    ambient: { intensity: 1.6 }
                },
                viewControl: {
                    autoRotate: true,
                    autoRotateSpeed: 6,
                    targetCoord: [104, 34],
                    distance: 200,
                    alpha: 35,
                    beta: -10,
                    minDistance: 60,
                    maxDistance: 600,
                    zoomSensitivity: 2.5,
                    animation: true,
                    animationDurationUpdate: 600
                },
                atmosphere: {
                    show: true,
                    offset: 10,
                    color: '#00aaff'
                },
                label: { show: false }
            },
            series: [{
                type: 'scatter3D',
                coordinateSystem: 'globe',
                symbol: 'pin',
                data: scatterData,
                emphasis: {
                    label: {
                        show: true,
                        formatter: '{b}',
                        color: '#ffffff',
                        fontSize: 13,
                        distance: 10
                    },
                    itemStyle: {
                        shadowBlur: 10,
                        shadowColor: '#ffffff'
                    }
                },
                zlevel: 1
            }]
        }, true);
    }

    function loadAnalyze(days, force) {
        var elRisk = document.getElementById('riskLevel');
        var elNormal = document.getElementById('normalRate');
        var elViolation = document.getElementById('violationRate');
        var elNeu = document.getElementById('neutralRate');
        var elBarNormal = document.getElementById('barNormal');
        var elBarViolation = document.getElementById('barViolation');
        var elBarNeu = document.getElementById('barNeutral');
        var elSummary = document.getElementById('analyzeSummary');
        var elSuggestion = document.getElementById('analyzeSuggestion');
        var elViolationWords = document.getElementById('topViolationWords');
        var elHotTopics = document.getElementById('hotTopics');
        var elBtn = document.getElementById('analyzeBtn');
        var elMarquee = document.getElementById('warningMarquee');

        if (elRisk) { elRisk.textContent = '分析中...'; elRisk.className = 'risk-badge risk-medium'; }
        if (elBtn) { elBtn.disabled = true; elBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 分析中...'; }

        ajaxPost('/api/screen/analyze', { days: days, force: !!force }, function(res) {
            if (elBtn) { elBtn.disabled = false; elBtn.innerHTML = '<i class="fas fa-sync-alt"></i> 开始分析'; }

            if (res.code !== 0 || !res.data) {
                if (elRisk) elRisk.textContent = '获取失败';
                return;
            }
            var d = res.data;

            if (elRisk) {
                elRisk.textContent = d.risk_level || '--';
                var cls = 'risk-badge ';
                if (d.risk_level === '高') cls += 'risk-high';
                else if (d.risk_level === '中') cls += 'risk-medium';
                else cls += 'risk-low';
                elRisk.className = cls;
            }

            if (elNormal) elNormal.textContent = Math.round((d.normal_rate || 0) * 100) + '%';
            if (elViolation) elViolation.textContent = Math.round((d.violation_rate || 0) * 100) + '%';
            if (elNeu) elNeu.textContent = Math.round((d.neutral_rate || 0) * 100) + '%';

            if (elBarNormal) elBarNormal.style.width = Math.round((d.normal_rate || 0) * 100) + '%';
            if (elBarViolation) elBarViolation.style.width = Math.round((d.violation_rate || 0) * 100) + '%';
            if (elBarNeu) elBarNeu.style.width = Math.round((d.neutral_rate || 0) * 100) + '%';

            if (elSummary) elSummary.textContent = d.summary || '';
            if (elSuggestion && d.suggestion) {
                elSuggestion.textContent = '💡 ' + d.suggestion;
                elSuggestion.style.display = 'block';
            } else if (elSuggestion) {
                elSuggestion.style.display = 'none';
            }
            if (elViolationWords && d.top_violation_words) {
                elViolationWords.textContent = d.top_violation_words.join('、') || '无';
            }
            if (elHotTopics && d.hot_topics) {
                elHotTopics.textContent = d.hot_topics.join('、') || '无';
            }

            if (d.risk_level === '高' && elMarquee) {
                elMarquee.style.display = 'flex';
            } else if (elMarquee) {
                elMarquee.style.display = 'none';
            }

            var sentInst = initOrReuse('sentiment', 'sentimentChart');
            if (sentInst) {
                sentInst.setOption({
                    backgroundColor: 'transparent',
                    grid: { left: 50, right: 20, top: 30, bottom: 25 },
                    tooltip: {
                        trigger: 'axis',
                        backgroundColor: 'rgba(10,20,44,0.9)',
                        borderColor: 'rgba(0,150,255,0.3)',
                        textStyle: { color: '#e0e6ed', fontSize: 12 }
                    },
                    xAxis: {
                        type: 'category',
                        data: ['正常', '中性', '违规'],
                        axisLine: { lineStyle: { color: 'rgba(0,150,255,0.3)' } },
                        axisLabel: { color: '#6a8099', fontSize: 12 }
                    },
                    yAxis: {
                        type: 'value',
                        max: 100,
                        axisLabel: { color: '#6a8099', formatter: '{value}%' },
                        splitLine: { lineStyle: { color: 'rgba(0,150,255,0.08)' } }
                    },
                    series: [{
                        type: 'bar',
                        barWidth: 50,
                        data: [
                            {
                                value: Math.round((d.normal_rate || 0) * 100),
                                itemStyle: { color: '#00c864' }
                            },
                            {
                                value: Math.round((d.neutral_rate || 0) * 100),
                                itemStyle: { color: '#5a7494' }
                            },
                            {
                                value: Math.round((d.violation_rate || 0) * 100),
                                itemStyle: { color: '#ff5555' }
                            }
                        ],
                        itemStyle: { borderRadius: [4, 4, 0, 0] }
                    }]
                });
            }
        });
    }

    function startAutoRefresh() {
        stopAutoRefresh();
        refreshTimer = setInterval(function() {
            loadStats(currentDays);
        }, 60000);
    }

    function stopAutoRefresh() {
        if (refreshTimer) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }
    }

    window.switchDays = function(days) {
        currentDays = days;
        var btns = document.querySelectorAll('.time-btn');
        btns.forEach(function(b) { b.classList.remove('active'); });
        if (days === 7) btns[0].classList.add('active');
        else btns[1].classList.add('active');
        loadStats(days);
        loadAnalyze(days);
    };

    window.toggleChartType = function() {
        currentChartType = (currentChartType === 'line') ? 'bar' : 'line';
        var btn = document.getElementById('chartTypeBtn');
        if (btn) {
            btn.innerHTML = currentChartType === 'line'
                ? '<i class="fas fa-chart-bar"></i> 柱状图'
                : '<i class="fas fa-chart-line"></i> 折线图';
        }
        loadStats(currentDays);
    };

    window.refreshAnalyze = function() {
        loadAnalyze(currentDays, true);
    };

    window.refreshAll = function() {
        loadStats(currentDays);
        loadWordcloud();
        loadEarthData();
        loadAnalyze(currentDays);
    };

    window.closeWordDetail = closeWordDetail;
    window.closeLocationNews = closeLocationNews;

    window.addEventListener('resize', function() {
        var keys = Object.keys(charts);
        for (var i = 0; i < keys.length; i++) {
            if (charts[keys[i]]) {
                charts[keys[i]].resize();
            }
        }
    });

    window.addEventListener('beforeunload', function() {
        stopAutoRefresh();
        disposeAll();
    });

    // === 手势识别相关代码 ===
    var gestureRunning = false;
    var gesturePreviewCtx = null;
    var gesturePreviewAnim = null;
    var gestureLoadCheckTimer = null;

    // 检查手势模块是否已加载
    function checkGestureModule(callback) {
        console.log('Checking HandGesture module...');
        console.log('window.HandGesture:', window.HandGesture);
        console.log('window.Hands:', typeof Hands !== 'undefined' ? 'loaded' : 'not loaded');
        
        if (window.HandGesture) {
            callback(true);
            return;
        }
        
        console.log('HandGesture module not found, waiting...');
        var checkCount = 0;
        var maxChecks = 100; // 50秒超时（更久的等待）
        
        gestureLoadCheckTimer = setInterval(function() {
            checkCount++;
            if (window.HandGesture) {
                console.log('HandGesture loaded after', checkCount * 500, 'ms');
                clearInterval(gestureLoadCheckTimer);
                gestureLoadCheckTimer = null;
                callback(true);
            } else if (checkCount >= maxChecks) {
                console.log('HandGesture load timeout');
                clearInterval(gestureLoadCheckTimer);
                gestureLoadCheckTimer = null;
                callback(false);
            }
        }, 500); // 检测间隔
    }

    // 启动/停止手势控制
    window.toggleGestureControl = function() {
        console.log('Gesture toggle clicked');
        var btn = document.getElementById('gestureToggleBtn');
        var content = document.getElementById('gestureContent');
        var status = document.getElementById('gestureStatus');
        var preview = document.getElementById('gesturePreviewCanvas');

        console.log('Current gestureRunning:', gestureRunning);

        if (!gestureRunning) {
            console.log('Starting gesture control');
            status.textContent = '正在加载模块...';
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 加载中...';
            
            // 立即检查一次
            if (window.HandGesture) {
                initAndStartGesture(btn, content, status, preview);
            } else {
                // 轮询检查
                checkGestureModule(function(loaded) {
                    if (!loaded) {
                        console.error('HandGesture module load timeout');
                        showToast('模块加载较慢，建议：\n1. 检查网络连接\n2. 使用Chrome/Edge浏览器\n3. 刷新页面重试');
                        status.textContent = '加载超时';
                        btn.disabled = false;
                        btn.innerHTML = '<i class="fas fa-play-circle"></i> 启用';
                        return;
                    }

                    console.log('HandGesture module loaded');
                    initAndStartGesture(btn, content, status, preview);
                });
            }
        } else {
            console.log('Stopping gesture control');
            if (window.HandGesture && window.HandGesture.stop) {
                window.HandGesture.stop();
            }
            gestureRunning = false;
            btn.classList.remove('active');
            btn.innerHTML = '<i class="fas fa-play-circle"></i> 启用';
            content.style.display = 'none';
            stopPreviewRender();
            status.textContent = '已停止';
            showToast('手势控制已停用');
        }
    };

    // 初始化并启动手势识别
    function initAndStartGesture(btn, content, status, preview) {
        status.textContent = '正在初始化...';
        
        window.HandGesture.init().then(function() {
            console.log('HandGesture initialized successfully');
            return window.HandGesture.start();
        }).then(function() {
            console.log('HandGesture started successfully');
            gestureRunning = true;
            btn.disabled = false;
            btn.classList.add('active');
            btn.innerHTML = '<i class="fas fa-stop-circle"></i> 停用';
            content.style.display = 'block';
            status.textContent = '摄像头已启动，等待手势...';

            if (preview && window.HandGesture.getCanvas) {
                var sourceCanvas = window.HandGesture.getCanvas();
                gesturePreviewCtx = preview.getContext('2d');
                preview.width = 280;
                preview.height = 150;
                renderGesturePreview();
            }

            window.HandGesture.on('gesture', handleGesture);
            window.HandGesture.on('started', function() {
                status.textContent = '手势识别已就绪';
            });
            window.HandGesture.on('stopped', function() {
                status.textContent = '已停止';
            });

            showToast('手势控制已启动，请对着摄像头做手势');
        }).catch(function(err) {
            console.error('手势启动失败:', err);
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play-circle"></i> 启用';
            var errMsg = err.message || '请检查摄像头权限';
            if (errMsg.includes('Permission') || errMsg.includes('permission')) {
                errMsg = '请允许浏览器访问摄像头';
            } else if (errMsg.includes('notFound') || errMsg.includes('NotFound')) {
                errMsg = '未找到摄像头设备';
            }
            showToast('失败: ' + errMsg);
            status.textContent = '启动失败';
        });
    }

    // 渲染预览画面
    function renderGesturePreview() {
        if (!gestureRunning) return;
        
        if (window.HandGesture && window.HandGesture.getCanvas && gesturePreviewCtx) {
            var sourceCanvas = window.HandGesture.getCanvas();
            if (sourceCanvas && sourceCanvas.width > 0) {
                var preview = document.getElementById('gesturePreviewCanvas');
                gesturePreviewCtx.clearRect(0, 0, preview.width, preview.height);
                
                // 绘制图像
                gesturePreviewCtx.drawImage(sourceCanvas, 0, 0, preview.width, preview.height);
                
                // 添加扫描线效果
                gesturePreviewCtx.strokeStyle = 'rgba(0, 220, 255, 0.3)';
                gesturePreviewCtx.lineWidth = 2;
                gesturePreviewCtx.beginPath();
                var scanLineY = (Date.now() % 3000) / 3000 * preview.height;
                gesturePreviewCtx.moveTo(0, scanLineY);
                gesturePreviewCtx.lineTo(preview.width, scanLineY);
                gesturePreviewCtx.stroke();
            }
        }
        
        gesturePreviewAnim = requestAnimationFrame(renderGesturePreview);
    }

    // 停止预览渲染
    function stopPreviewRender() {
        if (gesturePreviewAnim) {
            cancelAnimationFrame(gesturePreviewAnim);
            gesturePreviewAnim = null;
        }
    }

    // 处理手势事件
    function handleGesture(gestureName) {
        var status = document.getElementById('gestureStatus');
        var panel = document.getElementById('gestureControlPanel');
        
        // 添加动画效果
        if (panel) {
            panel.classList.remove('gesture-active');
            void panel.offsetWidth; // 触发重绘
            panel.classList.add('gesture-active');
        }

        // 手势名称映射
        var gestureMap = {
            'open_palm': '张开手掌',
            'closed_fist': '握拳',
            'point_up': '食指向上',
            'three_fingers': '三指伸直',
            'peace': '剪刀手',
            'thumbs_up': '点赞',
            'thumbs_down': '向下',
            'unknown': '未知手势'
        };

        var displayName = gestureMap[gestureName] || gestureName;
        if (status) {
            status.textContent = '识别到: ' + displayName;
        }

        // 执行对应操作
        switch (gestureName) {
            case 'open_palm':
                // 张开手掌 → 刷新分析
                showToast('手势: 张开手掌 → 刷新分析');
                refreshAnalyze();
                break;
            case 'closed_fist':
                // 握拳 → 切换图表类型
                showToast('手势: 握拳 → 切换图表');
                toggleChartType();
                break;
            case 'point_up':
                // 食指向上 → 切换为7天
                showToast('手势: 食指向上 → 显示最近7天');
                switchDays(7);
                break;
            case 'three_fingers':
                // 三指伸直 → 刷新数据
                showToast('手势: 三指伸直 → 刷新数据');
                refreshAll();
                break;
            case 'thumbs_up':
                // 点赞 → 切换为30天
                showToast('手势: 点赞 → 显示最近30天');
                switchDays(30);
                break;
            case 'peace':
                // 剪刀手 → 暂停/继续自动刷新
                showToast('手势: 剪刀手 → 切换自动刷新');
                toggleAutoRefresh();
                break;
        }
    }

    // 切换自动刷新
    function toggleAutoRefresh() {
        if (refreshTimer) {
            stopAutoRefresh();
            showToast('自动刷新已暂停');
        } else {
            startAutoRefresh();
            showToast('自动刷新已恢复');
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        if (typeof echarts === 'undefined') {
            console.error('ECharts not loaded');
            return;
        }

        var trendInst = initOrReuse('trend', 'trendChart');
        if (trendInst) {
            trendInst.clear();
        }

        ajaxGet('/api/screen/stats', function(res) {
            if (res.code === 0 && res.data) {
                var d = res.data;
                var elSU = document.getElementById('statUsers');
                var elSS = document.getElementById('statSessions');
                var elSW = document.getElementById('statWatch');
                if (elSU) elSU.textContent = d.total_users || 0;
                if (elSS) elSS.textContent = d.total_sessions || 0;
                if (elSW) elSW.textContent = d.total_watch_data || 0;
            }
            loadWordcloud();
            loadEarthData();
            loadStats(currentDays);
            startAutoRefresh();
        });
    });
})();
