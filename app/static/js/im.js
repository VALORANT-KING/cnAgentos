(function () {
    'use strict';

    var state = {
        username: IM_USERNAME,
        myUserId: typeof IM_USER_ID !== 'undefined' ? IM_USER_ID : 0,
        currentTab: 'chats',
        currentChat: null,
        friends: [],
        groups: [],
        employees: [],
        ws: null,
        wsReconnectTimer: null,
        servers: [],
        currentServer: null,
        pendingRequests: 0,
        unreadCounts: {},
        convPreviews: {},
        groupBlocked: ''
    };

    var UNREAD_STORAGE_KEY = 'im_unread_' + (typeof IM_USER_ID !== 'undefined' ? IM_USER_ID : '0');

    var EMOJIS = ['😀','😁','😂','🤣','😃','😄','😅','😆','😉','😊','😋','😎','😍','😘','🥰','😗','😙','😚','🙂','🤗','🤩','🤔','🤨','😐','😑','😶','🙄','😏','😣','😥','😮','🤐','😯','😪','😫','🥱','😴','😌','😛','😜','😝','🤤','😒','😓','😔','😕','🙃','🤑','😲','☹️','🙁','😖','😞','😟','😤','😢','😭','😦','😧','😨','😩','🤯','😬','😰','😱','🥵','🥶','😳','🤪','😵','🥴','😠','😡','🤬','😷','🤒','🤕','🤢','🤮','🤧','😇','🥳','🥺','🤠','🤡','🤥','🤫','🤭','🧐','🤓','😈','👋','👍','👎','👏','🙌','🤝','❤️','💔','💯','🔥','✨','🎉','🎵'];

    var STICKERS = ['🎉', '🔥', '💯', '✨', '🌟', '💫', '🎊', '🥳', '👏', '💪', '🌈', '⚡'];

    function getCookie(name) {
        var r = document.cookie.match('\\b' + name + '=([^;]*)\\b');
        return r ? r[1] : undefined;
    }

    function apiUrl(path) {
        // HTTP API 始终走当前页面同源，避免切换服务器后 Cookie 失效导致接口鉴权失败
        return path;
    }

    function buildServerBase(server) {
        var host = server.host || window.location.hostname;
        var port = server.port || window.location.port || 10086;
        return window.location.protocol + '//' + host + ':' + port;
    }

    function wsUrl() {
        var proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return proto + '//' + window.location.host + '/ws/im';
    }

    function ajax(method, url, data, isForm) {
        return new Promise(function (resolve, reject) {
            var xhr = new XMLHttpRequest();
            xhr.open(method, url, true);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            if (method === 'POST' && !isForm) {
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                xhr.setRequestHeader('X-XSRFToken', getCookie('_xsrf') || '');
            }
            if (method === 'POST' && isForm) {
                xhr.setRequestHeader('X-XSRFToken', getCookie('_xsrf') || '');
            }
            xhr.onload = function () {
                if (xhr.status < 200 || xhr.status >= 300) {
                    reject(new Error('HTTP ' + xhr.status + ': ' + (xhr.responseText || '').slice(0, 120)));
                    return;
                }
                try {
                    var res = JSON.parse(xhr.responseText);
                    resolve(res);
                } catch (e) {
                    reject(new Error('响应解析失败'));
                }
            };
            xhr.onerror = function () { reject(new Error('network')); };
            if (method === 'POST' && data) {
                if (isForm) xhr.send(data);
                else {
                    var body = '_xsrf=' + encodeURIComponent(getCookie('_xsrf') || '');
                    for (var k in data) {
                        if (data.hasOwnProperty(k)) body += '&' + encodeURIComponent(k) + '=' + encodeURIComponent(data[k]);
                    }
                    xhr.send(body);
                }
            } else xhr.send();
        });
    }

    function connectWs() {
        if (state.ws) {
            try { state.ws.close(); } catch (e) {}
        }
        var url = wsUrl();
        try {
            state.ws = new WebSocket(url);
        } catch (e) {
            scheduleReconnect();
            return;
        }
        state.ws.onopen = function () {
            setServerStatus(true);
            clearTimeout(state.wsReconnectTimer);
        };
        state.ws.onmessage = function (ev) {
            try {
                var payload = JSON.parse(ev.data);
                handleWsPayload(payload);
            } catch (e) {}
        };
        state.ws.onclose = function () {
            setServerStatus(false);
            scheduleReconnect();
        };
        state.ws.onerror = function () {
            setServerStatus(false);
        };
    }

    function scheduleReconnect() {
        clearTimeout(state.wsReconnectTimer);
        state.wsReconnectTimer = setTimeout(function () {
            tryNextServer().then(function () { connectWs(); });
        }, 3000);
    }

    function setServerStatus(online) {
        var el = document.getElementById('serverStatusDot');
        if (el) {
            el.className = 'server-status ' + (online ? 'online' : 'offline');
        }
    }

    function convKey(type, id) {
        return type + ':' + id;
    }

    function loadUnreadState() {
        try {
            var raw = localStorage.getItem(UNREAD_STORAGE_KEY);
            if (!raw) return;
            var data = JSON.parse(raw);
            state.unreadCounts = data.counts || {};
            state.convPreviews = data.previews || {};
        } catch (e) {}
    }

    function saveUnreadState() {
        try {
            localStorage.setItem(UNREAD_STORAGE_KEY, JSON.stringify({
                counts: state.unreadCounts,
                previews: state.convPreviews
            }));
        } catch (e) {}
    }

    function isMyMessage(msg) {
        return Number(msg.sender_id) === Number(state.myUserId);
    }

    function getConvFromMessage(msg) {
        if (msg.receiver_type === 'group') {
            return convKey('group', msg.receiver_id);
        }
        var myId = Number(state.myUserId);
        var peerId = Number(msg.sender_id) === myId ? Number(msg.receiver_id) : Number(msg.sender_id);
        return convKey('user', peerId);
    }

    function messagePreviewText(msg) {
        if (msg.msg_type === 'file') return msg.content || '[文件]';
        if (msg.msg_type === 'sticker') return '[动画表情]';
        if (msg.msg_type === 'employee_call') return '[数字员工]';
        var text = (msg.content || '').replace(/\s+/g, ' ').trim();
        return text.length > 24 ? text.slice(0, 24) + '…' : text;
    }

    function shouldMarkUnread(msg) {
        if (isMyMessage(msg)) return false;
        if (state.currentTab !== 'chats') return true;
        var panel = document.getElementById('chatPanel');
        if (!panel || panel.style.display === 'none') return true;
        if (!state.currentChat) return true;
        return !isMessageForCurrentChat(msg);
    }

    function getGroupStatus(groupId) {
        var g = state.groups.find(function (x) { return String(x.id) === String(groupId); });
        return g && g.status !== undefined ? g.status : 1;
    }

    function groupStatusPreview(status) {
        if (status === 0) return '[已封禁]';
        if (status === 2) return '[已解散]';
        return null;
    }

    function getListPreview(type, id, groupStatus) {
        if (type === 'group') {
            var statusText = groupStatusPreview(groupStatus);
            if (statusText) return statusText;
        }
        var key = convKey(type, id);
        if (state.convPreviews[key]) return state.convPreviews[key];
        return type === 'group' ? '群聊' : '私聊';
    }

    function syncGroupInState(group) {
        if (!group || group.id === undefined) return;
        var idx = state.groups.findIndex(function (x) {
            return String(x.id) === String(group.id);
        });
        if (idx >= 0) {
            state.groups[idx].status = group.status;
            if (group.name) state.groups[idx].name = group.name;
            if (group.announcement !== undefined) {
                state.groups[idx].announcement = group.announcement;
            }
        } else {
            state.groups.push({
                id: group.id,
                name: group.name,
                status: group.status,
                owner_id: group.owner_id,
                announcement: group.announcement
            });
        }
    }

    function refreshCurrentGroupStatus() {
        if (!state.currentChat || state.currentChat.type !== 'group') {
            return Promise.resolve(false);
        }
        var gid = state.currentChat.id;
        return ajax('GET', apiUrl('/api/im/groups/members?group_id=' + gid)).then(function (res) {
            if (res.code !== 0) return false;
            if (res.data.group) syncGroupInState(res.data.group);
            setGroupChatBlocked(res.data.block_message || '');
            renderChatList();
            if (state.currentTab === 'groups') renderGroupList();
            return !!res.data.block_message;
        });
    }

    function updateListItemBadge(key) {
        var parts = key.split(':');
        var selector = '.im-list-item[data-type="' + parts[0] + '"][data-id="' + parts[1] + '"]';
        document.querySelectorAll(selector).forEach(function (el) {
            var badge = el.querySelector('.im-unread-badge');
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'im-unread-badge';
                el.appendChild(badge);
            }
            var n = state.unreadCounts[key] || 0;
            if (badge) {
                if (n > 0) {
                    badge.textContent = n > 99 ? '99+' : String(n);
                    badge.style.display = 'inline-flex';
                } else {
                    badge.style.display = 'none';
                }
            }
            var preview = el.querySelector('.preview');
            if (preview) {
                var groupStatus = parts[0] === 'group' ? getGroupStatus(parts[1]) : 1;
                preview.textContent = getListPreview(parts[0], parts[1], groupStatus);
            }
        });
    }

    function clearUnread(type, id) {
        var key = convKey(type, id);
        if (state.unreadCounts[key]) {
            delete state.unreadCounts[key];
            saveUnreadState();
            updateListItemBadge(key);
        }
    }

    function handleWsPayload(payload) {
        if (payload.type === 'connected' && payload.user_id) {
            state.myUserId = payload.user_id;
            if (state.currentChat) state.currentChat.myId = payload.user_id;
            return;
        }
        if (payload.type === 'error' && payload.msg) {
            if (state.currentChat && state.currentChat.type === 'group') {
                refreshCurrentGroupStatus().then(function (blocked) {
                    if (!blocked) alert(payload.msg);
                });
                return;
            }
            alert(payload.msg);
            return;
        }
        if (payload.type === 'group_status') {
            if (state.currentChat && state.currentChat.type === 'group' &&
                String(state.currentChat.id) === String(payload.group_id)) {
                setGroupChatBlocked(payload.message || '');
            }
            loadGroups();
            return;
        }
        if (payload.type === 'message' && payload.data) {
            appendMessage(payload.data);
            if (isMessageForCurrentChat(payload.data)) {
                scrollMessagesBottom();
            }
            // 语音播报新消息（如果不是自己发送的）
            if (!isMyMessage(payload.data) && window.TTS) {
                var senderName = payload.data.sender_name || (payload.data.sender_id === 0 ? '数字员工' : '陌生人');
                var content = payload.data.content || '';
                if (payload.data.msg_type === 'file') {
                    content = '发来一个文件';
                } else if (payload.data.msg_type === 'sticker') {
                    content = '发来一个动画表情';
                }
                TTS.notifyNewMessage(senderName, content);
            }
            refreshConversationPreview(payload.data);
        }
        if (payload.type === 'friend_accepted') {
            loadFriends();
            loadFriendRequests();
        }
        if (payload.type === 'friend_request') {
            loadFriendRequests().then(function () {
                var n = state.pendingRequests || 0;
                if (n > 0) {
                    var tip = payload.from_username
                        ? (payload.from_username + ' 请求加你为好友')
                        : '收到新的好友申请';
                    if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
                        new Notification('好友申请', { body: tip });
                    }
                }
            });
        }
        if (payload.type === 'group_invite') {
            loadGroups();
        }
    }

    function sendWsMessage(obj) {
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify(obj));
            return true;
        }
        return false;
    }

    function parseEmployeeCalls(text) {
        var calls = [];
        state.employees.forEach(function (emp) {
            var alias = emp.alias || '';
            if (!alias || text.indexOf(alias) === -1) return;
            var idx = text.indexOf(alias);
            var after = text.slice(idx + alias.length).replace(/^[：:\s]+/, '');
            var param = '';
            var m = after.match(/^(\S+)/);
            if (m) param = m[1];
            calls.push({ alias: alias, param: param });
        });
        return calls;
    }

    function sendTextMessage() {
        if (!state.currentChat) return alert('请先选择聊天对象');
        if (state.groupBlocked) return alert(state.groupBlocked);
        var input = document.getElementById('msgInput');
        var content = (input.value || '').trim();
        if (!content && !state.pendingFile) return;

        var msgType = 'text';
        var fileId = 0;
        if (state.pendingFile) {
            msgType = 'file';
            fileId = state.pendingFile.id;
            content = content || '[文件] ' + state.pendingFile.file_name;
        }

        var employeeCalls = parseEmployeeCalls(content);

        var payload = {
            type: 'message',
            receiver_type: state.currentChat.type,
            receiver_id: state.currentChat.id,
            msg_type: msgType,
            content: content,
            file_id: fileId,
            employee_calls: employeeCalls.length ? employeeCalls : undefined
        };

        if (!sendWsMessage(payload)) {
            alert('连接已断开，正在尝试重连…');
            return;
        }
        input.value = '';
        state.pendingFile = null;
        clearPendingFileUI();
        document.getElementById('msgInput').placeholder = '输入消息，输入 @ 可唤起数字员工…';
    }

    function sendSticker(emoji) {
        if (!state.currentChat) return;
        if (state.groupBlocked) return alert(state.groupBlocked);
        sendWsMessage({
            type: 'message',
            receiver_type: state.currentChat.type,
            receiver_id: state.currentChat.id,
            msg_type: 'sticker',
            content: emoji
        });
        hidePanels();
    }

    function isMessageForCurrentChat(msg) {
        if (!state.currentChat) return false;
        if (state.currentChat.type === 'group') {
            return msg.receiver_type === 'group' && String(msg.receiver_id) === String(state.currentChat.id);
        }
        var peerId = parseInt(state.currentChat.id, 10);
        var myId = parseInt(state.currentChat.myId || state.myUserId, 10);
        if (!myId || !peerId) return false;
        return msg.receiver_type === 'user' && (
            (Number(msg.sender_id) === myId && Number(msg.receiver_id) === peerId) ||
            (Number(msg.sender_id) === peerId && Number(msg.receiver_id) === myId)
        );
    }

    function appendMessage(msg) {
        var box = document.getElementById('messagesBox');
        if (!box || !state.currentChat) return;
        if (!isMessageForCurrentChat(msg)) return;

        var myId = parseInt(state.currentChat.myId || state.myUserId, 10);
        var mine = msg.sender_id === myId;
        var isEmployee = msg.msg_type === 'employee_call' || msg.sender_id === 0;
        var div = document.createElement('div');
        div.className = 'im-msg' + (mine ? ' mine' : '') + (isEmployee ? ' employee' : '');
        div.dataset.id = msg.id;

        var html = '';
        var showGroupName = state.currentChat.type === 'group' && !mine;
        var displayName = msg.sender_name || (isEmployee ? '数字员工' : '');
        var avatarHtml = '<div class="im-avatar ' + (isEmployee ? 'bot' : '') + '">' +
            (isEmployee ? '<i class="fas fa-robot"></i>' : (msg.sender_name || '?').charAt(0).toUpperCase()) + '</div>';

        if (showGroupName) {
            div.className += ' im-msg-group';
            html += '<div class="im-msg-sender">' + escapeHtml(displayName) + '</div>';
            html += avatarHtml;
        } else {
            html += avatarHtml;
        }
        html += '<div class="im-msg-bubble">' + formatMessageContent(msg) + '</div>';
        div.innerHTML = html;
        box.appendChild(div);
    }

    function formatMessageContent(msg) {
        if (msg.msg_type === 'sticker') {
            return '<span class="sticker-anim" style="font-size:48px;display:inline-block;animation:im-bounce 0.6s ease infinite;">' +
                escapeHtml(msg.content) + '</span>';
        }
        if (msg.msg_type === 'file' || Number(msg.file_id) > 0) {
            var fid = Number(msg.file_id) || 0;
            if (!fid) {
                return '<span class="file-link"><i class="fas fa-file"></i> ' +
                    escapeHtml(msg.content || '[文件]') + '</span>';
            }
            return '<a class="file-link" href="' + apiUrl('/api/im/files/download?id=' + fid) + '" data-file-id="' + fid + '">' +
                '<i class="fas fa-file"></i> ' + escapeHtml(msg.content || '下载文件') + '</a>';
        }
        if (msg.msg_type === 'emoji') {
            return '<span style="font-size:28px;">' + msg.content + '</span>';
        }
        var cardHtml = renderImCard(msg.content);
        if (cardHtml) return cardHtml;
        var text = escapeHtml(msg.content || '');
        state.employees.forEach(function (emp) {
            var alias = emp.alias || '';
            if (alias) {
                text = text.replace(new RegExp(escapeReg(alias), 'g'),
                    '<span style="color:#1e9fff;font-weight:600;">' + alias + '</span>');
            }
        });
        return text;
    }

    function renderImCard(content) {
        if (!content) return '';
        var raw = content.trim();
        if (raw.charAt(0) !== '{') return '';
        try {
            var data = JSON.parse(raw);
            if (!data._im_card) return '';
            if (data._im_card === 'weather') {
                return renderWeatherCard(data);
            }
            if (data._im_card === 'toxic_soup') {
                return '<div class="im-toxic-card"><div class="im-toxic-title">' +
                    escapeHtml(data.title || '毒鸡汤') + '</div><p>' +
                    escapeHtml(data.quote || '') + '</p></div>';
            }
        } catch (e) { /* not json */ }
        return '';
    }

    function renderWeatherCard(data) {
        var effect = data.effect || 'default';
        var icons = { sunny: '☀️', rain: '🌧️', snow: '❄️', fog: '🌫️', cloudy: '⛅', default: '🌡️' };
        var icon = icons[effect] || icons.default;
        return '<div class="im-weather-card im-weather-' + effect + '" data-effect="' + effect + '">' +
            '<div class="im-weather-fx"></div>' +
            '<div class="im-weather-body">' +
            '<div class="im-weather-icon">' + icon + '</div>' +
            '<div class="im-weather-main">' +
            '<div class="im-weather-city">' + escapeHtml(data.city || '') + '</div>' +
            '<div class="im-weather-temp">' + escapeHtml(String(data.temp || '')) + '°C</div>' +
            '<div class="im-weather-desc">' + escapeHtml(data.weather || '') + '</div>' +
            '</div>' +
            '<div class="im-weather-extra">' +
            '最低 ' + escapeHtml(String(data.tempn || '')) + '°C<br>' +
            '风力 ' + escapeHtml(data.wind || '') + '<br>' +
            '湿度 ' + escapeHtml(data.humidity || '') + '<br>' +
            '空气 ' + escapeHtml(data.air || '') +
            '</div></div></div>';
    }

    function escapeHtml(s) {
        var d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function escapeReg(s) {
        return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function scrollMessagesBottom() {
        var box = document.getElementById('messagesBox');
        if (box) box.scrollTop = box.scrollHeight;
    }

    function setGroupChatBlocked(blockMsg) {
        state.groupBlocked = blockMsg || '';
        var bar = document.getElementById('groupStatusBar');
        var input = document.getElementById('msgInput');
        var sendBtn = document.getElementById('sendBtn');
        var filePickBtn = document.getElementById('filePickBtn');
        if (bar) {
            if (blockMsg) {
                bar.textContent = blockMsg;
                bar.className = 'im-group-status-bar' +
                    (blockMsg.indexOf('解散') >= 0 ? ' dissolved' : ' banned');
                bar.style.display = 'block';
            } else {
                bar.style.display = 'none';
                bar.textContent = '';
                bar.className = 'im-group-status-bar';
            }
        }
        var disabled = !!blockMsg;
        if (input) {
            input.disabled = disabled;
            if (disabled) {
                input.placeholder = blockMsg;
                input.value = '';
            } else if (!state.pendingFile) {
                input.placeholder = '输入消息，输入 @ 可唤起数字员工…';
            }
        }
        if (sendBtn) sendBtn.disabled = disabled;
        if (filePickBtn) filePickBtn.disabled = disabled;
    }

    function openChat(type, id, name) {
        hidePanels();
        clearUnread(type, id);
        setGroupChatBlocked('');
        state.currentChat = { type: type, id: id, name: name, myId: state.myUserId };
        document.getElementById('chatTitle').textContent = name;
        document.getElementById('messagesBox').innerHTML = '';
        document.getElementById('emptyChat').style.display = 'none';
        document.getElementById('chatPanel').style.display = 'flex';

        var isGroup = type === 'group';
        document.getElementById('showMembersBtn').style.display = isGroup ? 'inline-block' : 'none';
        document.getElementById('inviteGroupBtn').style.display = isGroup ? 'inline-block' : 'none';
        document.getElementById('deleteFriendBtn').style.display = (!isGroup && type === 'user') ? 'inline-block' : 'none';
        var annEl = document.getElementById('groupAnnouncement');
        annEl.style.display = 'none';
        annEl.textContent = '';

        document.querySelectorAll('.im-list-item').forEach(function (el) {
            el.classList.toggle('active',
                el.dataset.type === type && el.dataset.id === String(id));
        });

        if (isGroup) {
            ajax('GET', apiUrl('/api/im/groups/members?group_id=' + id)).then(function (res) {
                if (res.code !== 0) {
                    if (res.msg) alert(res.msg);
                    return;
                }
                if (res.data.block_message) {
                    setGroupChatBlocked(res.data.block_message);
                }
                if (res.data.group) {
                    syncGroupInState(res.data.group);
                    state.currentGroupEmployees = res.data.employees || [];
                    if (res.data.group.announcement && !res.data.block_message) {
                        annEl.textContent = '📢 ' + res.data.group.announcement;
                        annEl.style.display = 'block';
                    }
                    renderChatList();
                }
            });
        }

        ajax('GET', apiUrl('/api/im/messages/history?receiver_type=' + type + '&receiver_id=' + id))
            .then(function (res) {
                if (res.code !== 0) return alert(res.msg);
                if (res.data.employees) state.employees = res.data.employees;
                res.data.messages.forEach(function (m) { appendMessage(m); });
                scrollMessagesBottom();
            });
    }

    function loadFriends() {
        return ajax('GET', apiUrl('/api/im/friends/list')).then(function (res) {
            if (res.code === 0) {
                state.friends = res.data || [];
                if (state.currentTab === 'friends') renderFriendList();
                renderChatList();
            }
        });
    }

    function loadGroups() {
        return ajax('GET', apiUrl('/api/im/groups/list')).then(function (res) {
            if (res.code === 0) {
                state.groups = res.data || [];
                if (state.currentTab === 'groups') renderGroupList();
                renderChatList();
            }
        });
    }

    function loadFriendRequests() {
        return ajax('GET', apiUrl('/api/im/friends/requests')).then(function (res) {
            if (res.code !== 0) return;
            var incoming = (res.data.incoming || []).length;
            state.pendingRequests = incoming;
            var badge = document.getElementById('requestBadge');
            if (badge) {
                badge.style.display = incoming > 0 ? 'block' : 'none';
            }
            renderRequestsList(res.data);
        });
    }

    function renderChatList() {
        var list = document.getElementById('chatList');
        if (!list) return;
        list.innerHTML = '';
        state.friends.forEach(function (f) {
            list.appendChild(createListItem('user', f.friend_id, f.remark || f.username, f.username));
        });
        state.groups.forEach(function (g) {
            list.appendChild(createListItem('group', g.id, g.name, g.name, true, g.status));
        });
        if (!list.children.length) {
            list.innerHTML = '<div style="padding:20px;text-align:center;color:#999;font-size:13px;">暂无会话，请从通讯录选择好友或建群</div>';
            return;
        }
        state.friends.forEach(function (f) {
            updateListItemBadge(convKey('user', f.friend_id));
        });
        state.groups.forEach(function (g) {
            updateListItemBadge(convKey('group', g.id));
        });
    }

    function createListItem(type, id, title, avatarText, isGroup, groupStatus) {
        var el = document.createElement('div');
        el.className = 'im-list-item';
        el.dataset.type = type;
        el.dataset.id = String(id);
        if (type === 'group') {
            var status = groupStatus !== undefined ? groupStatus : getGroupStatus(id);
            var statusText = groupStatusPreview(status);
            if (statusText) {
                el.classList.add('im-list-item-group-inactive');
                el.classList.add(status === 2 ? 'dissolved' : 'banned');
            }
            groupStatus = status;
        }
        var preview = getListPreview(type, id, type === 'group' ? groupStatus : 1);
        el.innerHTML =
            '<div class="im-avatar-wrap">' +
            '<div class="im-avatar ' + (isGroup ? 'group' : '') + '">' +
            escapeHtml((avatarText || '?').charAt(0).toUpperCase()) + '</div>' +
            '</div>' +
            '<div class="im-list-info"><div class="name">' + escapeHtml(title) + '</div>' +
            '<div class="preview">' + escapeHtml(preview) + '</div></div>' +
            '<span class="im-unread-badge" style="display:none;"></span>';
        el.onclick = function () { openChat(type, id, title); };
        updateListItemBadge(convKey(type, id));
        return el;
    }

    function renderFriendList() {
        var list = document.getElementById('sideList');
        list.innerHTML = '';
        if (!state.friends.length) {
            list.innerHTML = '<div style="padding:20px;text-align:center;color:#999;font-size:13px;">暂无好友，请搜索用户名添加</div>';
            return;
        }
        state.friends.forEach(function (f) {
            list.appendChild(createFriendListItem(f));
        });
    }

    function createFriendListItem(f) {
        var el = document.createElement('div');
        el.className = 'im-list-item im-list-item-friend';
        el.innerHTML =
            '<div class="im-list-main">' +
            '<div class="im-avatar">' + escapeHtml((f.username || '?').charAt(0).toUpperCase()) + '</div>' +
            '<div class="im-list-info"><div class="name">' + escapeHtml(f.remark || f.username) + '</div>' +
            '<div class="preview">私聊</div></div></div>' +
            '<button type="button" class="im-friend-del" title="删除好友"><i class="fas fa-trash-alt"></i></button>';
        el.querySelector('.im-list-main').onclick = function () {
            openChat('user', f.friend_id, f.remark || f.username);
        };
        el.querySelector('.im-friend-del').onclick = function (e) {
            e.stopPropagation();
            deleteFriend(f.friend_id, f.username);
        };
        return el;
    }

    function deleteFriend(friendId, friendName) {
        var name = friendName || '该好友';
        if (!confirm('确定删除好友「' + name + '」吗？')) return;
        ajax('POST', apiUrl('/api/im/friends/delete'), { friend_id: friendId })
            .then(function (res) {
                alert(res.msg);
                if (res.code !== 0) return;
                if (state.currentChat && state.currentChat.type === 'user' &&
                    String(state.currentChat.id) === String(friendId)) {
                    state.currentChat = null;
                    document.getElementById('chatPanel').style.display = 'none';
                    document.getElementById('emptyChat').style.display = 'flex';
                }
                loadFriends();
            });
    }

    function renderGroupList() {
        var list = document.getElementById('sideList');
        list.innerHTML = '';
        state.groups.forEach(function (g) {
            list.appendChild(createListItem('group', g.id, g.name, g.name, true, g.status));
        });
    }

    function renderRequestsList(data) {
        var box = document.getElementById('requestsBox');
        if (!box) return;
        box.innerHTML = '';
        var incoming = data.incoming || [];
        if (!incoming.length) {
            box.innerHTML = '<p style="color:#999;font-size:13px;padding:8px 0;">暂无待处理的好友申请</p>';
        }
        incoming.forEach(function (r) {
            var div = document.createElement('div');
            div.className = 'request-item';
            div.innerHTML = '<span>' + escapeHtml(r.from_username) + ' 请求加好友</span>' +
                '<span><button class="btn btn-success btn-sm" data-id="' + r.id + '" data-act="accept">同意</button>' +
                '<button class="btn btn-outline-secondary btn-sm" data-id="' + r.id + '" data-act="reject">拒绝</button></span>';
            box.appendChild(div);
        });
        bindRequestButtons(box);

        var inlineBox = document.getElementById('incomingRequestsBox');
        if (inlineBox) {
            if (incoming.length && state.currentTab === 'friends') {
                inlineBox.style.display = 'block';
                inlineBox.innerHTML = '<p class="small text-muted mb-1">待处理申请：</p>';
                incoming.forEach(function (r) {
                    var div = document.createElement('div');
                    div.className = 'request-item';
                    div.innerHTML = '<span>' + escapeHtml(r.from_username) + '</span>' +
                        '<span><button class="btn btn-success btn-sm" data-id="' + r.id + '" data-act="accept">同意</button>' +
                        '<button class="btn btn-outline-secondary btn-sm" data-id="' + r.id + '" data-act="reject">拒绝</button></span>';
                    inlineBox.appendChild(div);
                });
                bindRequestButtons(inlineBox);
            } else {
                inlineBox.style.display = 'none';
                inlineBox.innerHTML = '';
            }
        }
    }

    function bindRequestButtons(container) {
        container.querySelectorAll('button').forEach(function (btn) {
            btn.onclick = function () {
                var id = btn.dataset.id;
                var act = btn.dataset.act;
                var url = act === 'accept' ? '/api/im/friends/accept' : '/api/im/friends/reject';
                ajax('POST', apiUrl(url), { request_id: id }).then(function (res) {
                    alert(res.msg);
                    loadFriendRequests();
                    loadFriends();
                });
            };
        });
    }

    function searchUsers() {
        var kw = document.getElementById('userSearchInput').value.trim();
        if (!kw) return;
        ajax('GET', apiUrl('/api/im/friends/search?keyword=' + encodeURIComponent(kw)))
            .then(function (res) {
                var box = document.getElementById('searchResults');
                box.innerHTML = '';
                if (res.code !== 0) return alert(res.msg);
                (res.data || []).forEach(function (u) {
                    var div = document.createElement('div');
                    div.className = 'request-item';
                    div.innerHTML = '<span>' + escapeHtml(u.username) + '</span>' +
                        '<button class="btn btn-primary btn-sm" data-id="' + u.id + '">加好友</button>';
                    div.querySelector('button').onclick = function () {
                        ajax('POST', apiUrl('/api/im/friends/add'), { friend_id: u.id })
                            .then(function (r) { alert(r.msg); });
                    };
                    box.appendChild(div);
                });
                if (!res.data.length) box.innerHTML = '<p style="color:#999;font-size:13px;">未找到用户</p>';
            });
    }

    function loadEmployees() {
        return ajax('GET', apiUrl('/api/employee/list')).then(function (res) {
            if (res.code === 0) state.employees = res.data || [];
        });
    }

    function loadServers() {
        return ajax('GET', apiUrl('/api/im/servers/list')).then(function (res) {
            if (res.code === 0) {
                state.servers = res.data || [];
                var sel = document.getElementById('serverSelect');
                sel.innerHTML = '';
                state.servers.forEach(function (s, i) {
                    var opt = document.createElement('option');
                    opt.value = i;
                    opt.textContent = s.name + ' (' + s.host + ':' + s.port + ')';
                    sel.appendChild(opt);
                });
                if (!state.currentServer && state.servers.length) {
                    state.currentServer = state.servers[0];
                }
            }
        });
    }

    function tryNextServer() {
        return loadServers().then(function () {
            if (!state.servers.length) {
                state.currentServer = { host: window.location.hostname, port: parseInt(window.location.port, 10) || 10086, name: '当前' };
                return;
            }
            var checks = state.servers.map(function (s, idx) {
                return fetch(buildServerBase(s) + '/api/im/health', { method: 'GET', credentials: 'include' })
                    .then(function (r) { return r.ok ? idx : -1; })
                    .catch(function () { return -1; });
            });
            return Promise.all(checks).then(function (results) {
                var ok = results.find(function (x) { return x >= 0; });
                if (ok !== undefined && ok >= 0) {
                    state.currentServer = state.servers[ok];
                    document.getElementById('serverSelect').value = ok;
                } else {
                    var next = (state.servers.indexOf(state.currentServer) + 1) % state.servers.length;
                    state.currentServer = state.servers[next];
                }
            });
        });
    }

    function initEmojiPanel() {
        var panel = document.getElementById('emojiPanel');
        EMOJIS.forEach(function (e) {
            var span = document.createElement('span');
            span.textContent = e;
            span.onclick = function () {
                var input = document.getElementById('msgInput');
                input.value += e;
                input.focus();
            };
            panel.appendChild(span);
        });
    }

    function initStickerPanel() {
        var panel = document.getElementById('stickerPanel');
        STICKERS.forEach(function (s) {
            var span = document.createElement('span');
            span.textContent = s;
            span.style.fontSize = '28px';
            span.onclick = function () { sendSticker(s); };
            panel.appendChild(span);
        });
    }

    function hidePanels() {
        document.getElementById('emojiPanel').classList.remove('show');
        document.getElementById('stickerPanel').classList.remove('show');
        document.getElementById('emojiBtn').classList.remove('active');
        document.getElementById('stickerBtn').classList.remove('active');
    }

    function toggleEmojiPanel(e) {
        if (e) e.stopPropagation();
        var emojiPanel = document.getElementById('emojiPanel');
        var stickerPanel = document.getElementById('stickerPanel');
        var show = !emojiPanel.classList.contains('show');
        stickerPanel.classList.remove('show');
        document.getElementById('stickerBtn').classList.remove('active');
        emojiPanel.classList.toggle('show', show);
        document.getElementById('emojiBtn').classList.toggle('active', show);
    }

    function toggleStickerPanel(e) {
        if (e) e.stopPropagation();
        var stickerPanel = document.getElementById('stickerPanel');
        var emojiPanel = document.getElementById('emojiPanel');
        var show = !stickerPanel.classList.contains('show');
        emojiPanel.classList.remove('show');
        document.getElementById('emojiBtn').classList.remove('active');
        stickerPanel.classList.toggle('show', show);
        document.getElementById('stickerBtn').classList.toggle('active', show);
    }

    function bindPanelDismiss() {
        ['emojiPanel', 'stickerPanel'].forEach(function (id) {
            var panel = document.getElementById(id);
            if (panel) panel.addEventListener('click', function (e) { e.stopPropagation(); });
        });
        document.addEventListener('click', function () {
            if (document.getElementById('emojiPanel').classList.contains('show') ||
                document.getElementById('stickerPanel').classList.contains('show')) {
                hidePanels();
            }
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') hidePanels();
        });
    }

    function showPendingFileUI(name) {
        var bar = document.getElementById('pendingFileBar');
        var label = document.getElementById('pendingFileName');
        if (bar) bar.style.display = 'flex';
        if (label) label.textContent = name || '';
    }

    function clearPendingFileUI() {
        var bar = document.getElementById('pendingFileBar');
        if (bar) bar.style.display = 'none';
        var label = document.getElementById('pendingFileName');
        if (label) label.textContent = '';
    }

    function uploadFile(file) {
        if (state.groupBlocked) {
            alert(state.groupBlocked);
            return Promise.reject(new Error('group blocked'));
        }
        if (!state.currentChat) {
            alert('请先选择聊天对象再发送文件');
            return Promise.reject(new Error('no chat'));
        }
        var fd = new FormData();
        fd.append('file', file);
        fd.append('_xsrf', getCookie('_xsrf') || '');
        return ajax('POST', apiUrl('/api/im/files/upload'), fd, true).then(function (res) {
            if (res.code !== 0) throw new Error(res.msg || '上传失败');
            state.pendingFile = res.data;
            showPendingFileUI(res.data.file_name);
            document.getElementById('msgInput').placeholder = '可输入文件说明，点击发送';
            document.getElementById('msgInput').focus();
        }).catch(function (err) {
            alert('文件上传失败：' + (err.message || '未知错误'));
            throw err;
        });
    }

    function refreshConversationPreview(msg) {
        var key = getConvFromMessage(msg);
        state.convPreviews[key] = messagePreviewText(msg);
        if (shouldMarkUnread(msg)) {
            state.unreadCounts[key] = (state.unreadCounts[key] || 0) + 1;
            saveUnreadState();
        }
        updateListItemBadge(key);
    }

    function switchTab(tab) {
        state.currentTab = tab;
        document.querySelectorAll('.im-nav-tabs button').forEach(function (b) {
            b.classList.toggle('active', b.dataset.tab === tab);
        });
        var chatList = document.getElementById('chatList');
        var sideList = document.getElementById('sideList');
        if (tab === 'chats') {
            document.getElementById('sideSearch').style.display = 'none';
            chatList.style.display = 'block';
            sideList.style.display = 'none';
            renderChatList();
        } else {
            chatList.style.display = 'none';
            sideList.style.display = 'block';
            document.getElementById('sideSearch').style.display = tab === 'friends' ? 'block' : 'none';
            if (tab === 'friends') { loadFriends().then(renderFriendList); loadFriendRequests(); }
            if (tab === 'groups') { loadGroups().then(renderGroupList); }
        }
    }

    function showCreateGroupModal() {
        document.getElementById('createGroupModal').classList.add('show');
        var memberBox = document.getElementById('groupMemberCheckboxes');
        var empBox = document.getElementById('groupEmployeeCheckboxes');
        memberBox.innerHTML = '';
        empBox.innerHTML = '';
        state.friends.forEach(function (f) {
            var label = document.createElement('label');
            label.innerHTML = '<input type="checkbox" value="' + f.friend_id + '"> ' + escapeHtml(f.username);
            memberBox.appendChild(label);
        });
        state.employees.forEach(function (emp) {
            var label = document.createElement('label');
            label.innerHTML = '<input type="checkbox" value="' + emp.id + '"> ' +
                escapeHtml(emp.name) + ' <span style="color:#1e9fff;">' + escapeHtml(emp.alias) + '</span>';
            empBox.appendChild(label);
        });
    }

    function showInviteGroupModal() {
        if (!state.currentChat || state.currentChat.type !== 'group') return;
        document.getElementById('inviteGroupModal').classList.add('show');
        var memberBox = document.getElementById('inviteMemberCheckboxes');
        var empBox = document.getElementById('inviteEmployeeCheckboxes');
        memberBox.innerHTML = '';
        empBox.innerHTML = '';
        state.friends.forEach(function (f) {
            var label = document.createElement('label');
            label.innerHTML = '<input type="checkbox" value="' + f.friend_id + '"> ' + escapeHtml(f.username);
            memberBox.appendChild(label);
        });
        state.employees.forEach(function (emp) {
            var label = document.createElement('label');
            label.innerHTML = '<input type="checkbox" value="' + emp.id + '"> ' +
                escapeHtml(emp.name) + ' <span style="color:#1e9fff;">' + escapeHtml(emp.alias) + '</span>';
            empBox.appendChild(label);
        });
    }

    function showGroupMembers() {
        if (!state.currentChat || state.currentChat.type !== 'group') return;
        ajax('GET', apiUrl('/api/im/groups/members?group_id=' + state.currentChat.id))
            .then(function (res) {
                if (res.code !== 0) return alert(res.msg);
                document.getElementById('membersModalTitle').textContent =
                    (res.data.group && res.data.group.name) || '群成员';
                var box = document.getElementById('membersBox');
                box.innerHTML = '';
                (res.data.members || []).forEach(function (m) {
                    var p = document.createElement('p');
                    p.innerHTML = '<i class="fas fa-user"></i> ' + escapeHtml(m.username) +
                        ' <span class="text-muted">(' + m.role + ')</span>';
                    box.appendChild(p);
                });
                (res.data.employees || []).forEach(function (e) {
                    var p = document.createElement('p');
                    p.innerHTML = '<i class="fas fa-robot" style="color:#fa8c16;"></i> ' +
                        escapeHtml(e.name) + ' <span style="color:#1e9fff;">' + escapeHtml(e.alias) + '</span> <span class="text-muted">(数字员工)</span>';
                    box.appendChild(p);
                });
                document.getElementById('membersModal').classList.add('show');
            });
    }

    function createGroup() {
        var name = document.getElementById('groupNameInput').value.trim();
        if (!name) return alert('请输入群名称');
        var ids = [];
        document.querySelectorAll('#groupMemberCheckboxes input:checked').forEach(function (cb) {
            ids.push(cb.value);
        });
        var empIds = [];
        document.querySelectorAll('#groupEmployeeCheckboxes input:checked').forEach(function (cb) {
            empIds.push(cb.value);
        });
        ajax('POST', apiUrl('/api/im/groups/create'), {
            name: name,
            member_ids: JSON.stringify(ids),
            employee_ids: JSON.stringify(empIds)
        }).then(function (res) {
            alert(res.msg);
            document.getElementById('createGroupModal').classList.remove('show');
            loadGroups();
            if (res.code === 0 && res.data) {
                openChat('group', res.data.id, res.data.name);
            }
        });
    }

    function inviteToGroup() {
        if (!state.currentChat || state.currentChat.type !== 'group') return;
        var ids = [];
        document.querySelectorAll('#inviteMemberCheckboxes input:checked').forEach(function (cb) {
            ids.push(cb.value);
        });
        var empIds = [];
        document.querySelectorAll('#inviteEmployeeCheckboxes input:checked').forEach(function (cb) {
            empIds.push(cb.value);
        });
        ajax('POST', apiUrl('/api/im/groups/invite'), {
            group_id: state.currentChat.id,
            member_ids: JSON.stringify(ids),
            employee_ids: JSON.stringify(empIds)
        }).then(function (res) {
            alert(res.msg);
            if (res.code === 0) {
                document.getElementById('inviteGroupModal').classList.remove('show');
                showGroupMembers();
            }
        });
    }

    function bindEmployeeHint() {
        var input = document.getElementById('msgInput');
        var hint = document.getElementById('employeeHint');
        input.addEventListener('input', function () {
            var text = input.value;
            var atPos = text.lastIndexOf('@');
            if (atPos >= 0 && (atPos === 0 || /\s/.test(text.charAt(atPos - 1)))) {
                var query = text.slice(atPos + 1).toLowerCase();
                var filtered = state.employees.filter(function (e) {
                    return !query || (e.alias && e.alias.toLowerCase().indexOf('@' + query) >= 0) ||
                        (e.name && e.name.toLowerCase().indexOf(query) >= 0);
                });
                if (filtered.length) {
                    hint.innerHTML = '';
                    filtered.slice(0, 8).forEach(function (emp) {
                        var item = document.createElement('div');
                        item.className = 'hint-item';
                        item.innerHTML = '<i class="fas ' + (emp.icon || 'fa-robot') + '"></i>' +
                            '<span>' + escapeHtml(emp.alias) + ' — ' + escapeHtml(emp.name) + '</span>';
                        item.onclick = function () {
                            input.value = text.slice(0, atPos) + emp.alias + ' ';
                            hint.style.display = 'none';
                            input.focus();
                        };
                        hint.appendChild(item);
                    });
                    hint.style.display = 'block';
                    return;
                }
            }
            hint.style.display = 'none';
        });
        input.addEventListener('blur', function () {
            setTimeout(function () { hint.style.display = 'none'; }, 200);
        });
    }

    function bindFileDownload() {
        var box = document.getElementById('messagesBox');
        if (!box) return;
        box.addEventListener('click', function (e) {
            var link = e.target.closest('a.file-link');
            if (!link) return;
            e.preventDefault();
            fetch(link.getAttribute('href'), { credentials: 'same-origin' })
                .then(function (resp) {
                    if (!resp.ok) throw new Error('HTTP ' + resp.status);
                    var disp = resp.headers.get('Content-Disposition') || '';
                    var m = disp.match(/filename\*=UTF-8''([^;]+)/i);
                    var fname = m ? decodeURIComponent(m[1]) : '';
                    if (!fname) fname = (link.textContent || '').trim() || 'download';
                    return resp.blob().then(function (blob) {
                        return { blob: blob, fname: fname };
                    });
                })
                .then(function (res) {
                    var a = document.createElement('a');
                    a.href = URL.createObjectURL(res.blob);
                    a.download = res.fname;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                })
                .catch(function (err) {
                    alert('文件下载失败：' + (err.message || '未知错误'));
                });
        });
    }

    function init() {
        loadUnreadState();
        initEmojiPanel();
        initStickerPanel();
        bindPanelDismiss();
        bindFileDownload();
        bindEmployeeHint();

        document.querySelectorAll('.im-nav-tabs button').forEach(function (btn) {
            btn.onclick = function () { switchTab(btn.dataset.tab); };
        });

        document.getElementById('sendBtn').onclick = sendTextMessage;
        document.getElementById('msgInput').onkeydown = function (e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendTextMessage(); }
        };

        document.getElementById('emojiBtn').onclick = toggleEmojiPanel;
        document.getElementById('stickerBtn').onclick = toggleStickerPanel;

        document.getElementById('deleteFriendBtn').onclick = function () {
            if (!state.currentChat || state.currentChat.type !== 'user') return;
            deleteFriend(state.currentChat.id, state.currentChat.name);
        };

        document.getElementById('filePickBtn').onclick = function () {
            if (!state.currentChat) {
                alert('请先选择聊天对象再发送文件');
                return;
            }
            document.getElementById('fileInput').click();
        };

        document.getElementById('fileInput').onchange = function () {
            var input = this;
            var file = input.files && input.files[0];
            if (!file) return;
            uploadFile(file).finally(function () {
                input.value = '';
            });
        };

        var cancelPendingFileBtn = document.getElementById('cancelPendingFileBtn');
        if (cancelPendingFileBtn) {
            cancelPendingFileBtn.onclick = function () {
                state.pendingFile = null;
                clearPendingFileUI();
                document.getElementById('msgInput').placeholder = '输入消息，输入 @ 可唤起数字员工…';
            };
        }

        document.getElementById('searchUserBtn').onclick = searchUsers;
        document.getElementById('showRequestsBtn').onclick = function () {
            document.getElementById('requestsModal').classList.add('show');
            loadFriendRequests();
        };
        document.getElementById('createGroupBtn').onclick = showCreateGroupModal;
        document.getElementById('confirmCreateGroup').onclick = createGroup;
        document.getElementById('showMembersBtn').onclick = showGroupMembers;
        document.getElementById('inviteGroupBtn').onclick = showInviteGroupModal;
        document.getElementById('confirmInviteGroup').onclick = inviteToGroup;

        document.getElementById('serverSelect').onchange = function () {
            var idx = parseInt(this.value, 10);
            state.currentServer = state.servers[idx];
            connectWs();
        };

        document.querySelectorAll('.modal-overlay').forEach(function (m) {
            m.addEventListener('click', function (e) {
                if (e.target === m) m.classList.remove('show');
            });
        });

        Promise.all([loadServers(), loadEmployees(), loadFriends(), loadGroups(), loadFriendRequests()])
            .then(function () {
                renderChatList();
                connectWs();
            });

        // 定时刷新好友申请（WebSocket 未连接时的兜底）
        setInterval(function () { loadFriendRequests(); }, 15000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
