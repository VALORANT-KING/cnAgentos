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
        pendingRequests: 0
    };

    var EMOJIS = ['😀','😁','😂','🤣','😃','😄','😅','😆','😉','😊','😋','😎','😍','😘','🥰','😗','😙','😚','🙂','🤗','🤩','🤔','🤨','😐','😑','😶','🙄','😏','😣','😥','😮','🤐','😯','😪','😫','🥱','😴','😌','😛','😜','😝','🤤','😒','😓','😔','😕','🙃','🤑','😲','☹️','🙁','😖','😞','😟','😤','😢','😭','😦','😧','😨','😩','🤯','😬','😰','😱','🥵','🥶','😳','🤪','😵','🥴','😠','😡','🤬','😷','🤒','🤕','🤢','🤮','🤧','😇','🥳','🥺','🤠','🤡','🤥','🤫','🤭','🧐','🤓','😈','👋','👍','👎','👏','🙌','🤝','❤️','💔','💯','🔥','✨','🎉','🎵'];

    var STICKERS = ['🎉', '🔥', '💯', '✨', '🌟', '💫', '🎊', '🥳', '👏', '💪', '🌈', '⚡'];

    function getCookie(name) {
        var r = document.cookie.match('\\b' + name + '=([^;]*)\\b');
        return r ? r[1] : undefined;
    }

    function apiUrl(path) {
        var base = state.currentServer ? buildServerBase(state.currentServer) : '';
        return base + path;
    }

    function buildServerBase(server) {
        var host = server.host || window.location.hostname;
        var port = server.port || window.location.port || 10086;
        return window.location.protocol + '//' + host + ':' + port;
    }

    function wsUrl() {
        var base = state.currentServer ? buildServerBase(state.currentServer) : (window.location.protocol + '//' + window.location.host);
        var u = new URL(base);
        var proto = u.protocol === 'https:' ? 'wss:' : 'ws:';
        return proto + '//' + u.host + '/ws/im';
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
                try {
                    var res = JSON.parse(xhr.responseText);
                    resolve(res);
                } catch (e) {
                    reject(e);
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

    function handleWsPayload(payload) {
        if (payload.type === 'message' && payload.data) {
            appendMessage(payload.data, true);
            if (state.currentChat &&
                payload.data.receiver_type === state.currentChat.type &&
                String(payload.data.receiver_id) === String(state.currentChat.id)) {
                scrollMessagesBottom();
            }
            refreshConversationPreview(payload.data);
        }
        if (payload.type === 'friend_accepted') {
            loadFriends();
            loadFriendRequests();
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

        var employeeCalls = state.currentChat.type === 'group' ? parseEmployeeCalls(content) : [];

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
    }

    function sendSticker(emoji) {
        if (!state.currentChat) return;
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
        return msg.receiver_type === 'user' && (
            (msg.sender_id === myId && msg.receiver_id === peerId) ||
            (msg.sender_id === peerId && msg.receiver_id === myId)
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
        if (state.currentChat.type === 'group' && !mine && !isEmployee) {
            html += '<div class="im-msg-sender">' + escapeHtml(msg.sender_name || '') + '</div>';
        }
        html += '<div class="im-avatar ' + (isEmployee ? 'bot' : '') + '">' +
            (isEmployee ? '<i class="fas fa-robot"></i>' : (msg.sender_name || '?').charAt(0).toUpperCase()) + '</div>';
        html += '<div class="im-msg-bubble">' + formatMessageContent(msg) + '</div>';
        div.innerHTML = html;
        box.appendChild(div);
    }

    function formatMessageContent(msg) {
        if (msg.msg_type === 'sticker') {
            return '<span class="sticker-anim" style="font-size:48px;display:inline-block;animation:im-bounce 0.6s ease infinite;">' +
                escapeHtml(msg.content) + '</span>';
        }
        if (msg.msg_type === 'file' || (msg.file_id && msg.file_id > 0)) {
            var fid = msg.file_id || 0;
            return '<a class="file-link" href="' + apiUrl('/api/im/files/download?id=' + fid) + '" target="_blank">' +
                '<i class="fas fa-file"></i> ' + escapeHtml(msg.content || '下载文件') + '</a>';
        }
        if (msg.msg_type === 'emoji') {
            return '<span style="font-size:28px;">' + msg.content + '</span>';
        }
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

    function openChat(type, id, name) {
        state.currentChat = { type: type, id: id, name: name, myId: state.myUserId };
        document.getElementById('chatTitle').textContent = name;
        document.getElementById('messagesBox').innerHTML = '';
        document.getElementById('emptyChat').style.display = 'none';
        document.getElementById('chatPanel').style.display = 'flex';

        document.querySelectorAll('.im-list-item').forEach(function (el) {
            el.classList.toggle('active',
                el.dataset.type === type && el.dataset.id === String(id));
        });

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
                badge.textContent = incoming;
                badge.style.display = incoming ? 'inline' : 'none';
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
            list.appendChild(createListItem('group', g.id, g.name, g.name, true));
        });
        if (!list.children.length) {
            list.innerHTML = '<div style="padding:20px;text-align:center;color:#999;font-size:13px;">暂无会话，请从通讯录选择好友或建群</div>';
        }
    }

    function createListItem(type, id, title, avatarText, isGroup) {
        var el = document.createElement('div');
        el.className = 'im-list-item';
        el.dataset.type = type;
        el.dataset.id = id;
        el.innerHTML = '<div class="im-avatar ' + (isGroup ? 'group' : '') + '">' +
            escapeHtml((avatarText || '?').charAt(0).toUpperCase()) + '</div>' +
            '<div class="im-list-info"><div class="name">' + escapeHtml(title) + '</div>' +
            '<div class="preview">' + (type === 'group' ? '群聊' : '私聊') + '</div></div>';
        el.onclick = function () { openChat(type, id, title); };
        return el;
    }

    function renderFriendList() {
        var list = document.getElementById('sideList');
        list.innerHTML = '';
        state.friends.forEach(function (f) {
            var el = createListItem('user', f.friend_id, f.remark || f.username, f.username);
            list.appendChild(el);
        });
    }

    function renderGroupList() {
        var list = document.getElementById('sideList');
        list.innerHTML = '';
        state.groups.forEach(function (g) {
            list.appendChild(createListItem('group', g.id, g.name, g.name, true));
        });
    }

    function renderRequestsList(data) {
        var box = document.getElementById('requestsBox');
        if (!box) return;
        box.innerHTML = '';
        (data.incoming || []).forEach(function (r) {
            var div = document.createElement('div');
            div.className = 'request-item';
            div.innerHTML = '<span>' + escapeHtml(r.from_username) + ' 请求加好友</span>' +
                '<span><button class="btn btn-success btn-sm" data-id="' + r.id + '" data-act="accept">同意</button>' +
                '<button class="btn btn-outline-secondary btn-sm" data-id="' + r.id + '" data-act="reject">拒绝</button></span>';
            box.appendChild(div);
        });
        box.querySelectorAll('button').forEach(function (btn) {
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
    }

    function uploadFile(file) {
        var fd = new FormData();
        fd.append('file', file);
        fd.append('_xsrf', getCookie('_xsrf') || '');
        return ajax('POST', apiUrl('/api/im/files/upload'), fd, true).then(function (res) {
            if (res.code !== 0) throw new Error(res.msg);
            state.pendingFile = res.data;
            document.getElementById('msgInput').placeholder = '已选文件: ' + res.data.file_name + '，可输入说明后发送';
        });
    }

    function refreshConversationPreview(msg) {}

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
            if (tab === 'friends') { loadFriends().then(renderFriendList); }
            if (tab === 'groups') { loadGroups().then(renderGroupList); }
        }
    }

    function showCreateGroupModal() {
        document.getElementById('createGroupModal').classList.add('show');
        var box = document.getElementById('groupMemberCheckboxes');
        box.innerHTML = '';
        state.friends.forEach(function (f) {
            var label = document.createElement('label');
            label.innerHTML = '<input type="checkbox" value="' + f.friend_id + '"> ' + escapeHtml(f.username);
            box.appendChild(label);
        });
    }

    function createGroup() {
        var name = document.getElementById('groupNameInput').value.trim();
        if (!name) return alert('请输入群名称');
        var ids = [];
        document.querySelectorAll('#groupMemberCheckboxes input:checked').forEach(function (cb) {
            ids.push(cb.value);
        });
        ajax('POST', apiUrl('/api/im/groups/create'), {
            name: name,
            member_ids: JSON.stringify(ids)
        }).then(function (res) {
            alert(res.msg);
            document.getElementById('createGroupModal').classList.remove('show');
            loadGroups();
        });
    }

    function init() {
        initEmojiPanel();
        initStickerPanel();

        document.querySelectorAll('.im-nav-tabs button').forEach(function (btn) {
            btn.onclick = function () { switchTab(btn.dataset.tab); };
        });

        document.getElementById('sendBtn').onclick = sendTextMessage;
        document.getElementById('msgInput').onkeydown = function (e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendTextMessage(); }
        };

        document.getElementById('emojiBtn').onclick = function () {
            document.getElementById('stickerPanel').classList.remove('show');
            document.getElementById('emojiPanel').classList.toggle('show');
        };
        document.getElementById('stickerBtn').onclick = function () {
            document.getElementById('emojiPanel').classList.remove('show');
            document.getElementById('stickerPanel').classList.toggle('show');
        };

        document.getElementById('fileInput').onchange = function () {
            if (this.files[0]) uploadFile(this.files[0]);
        };

        document.getElementById('searchUserBtn').onclick = searchUsers;
        document.getElementById('showRequestsBtn').onclick = function () {
            document.getElementById('requestsModal').classList.add('show');
            loadFriendRequests();
        };
        document.getElementById('createGroupBtn').onclick = showCreateGroupModal;
        document.getElementById('confirmCreateGroup').onclick = createGroup;

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

        ajax('GET', apiUrl('/api/im/friends/list')).then(function (res) {
            if (res.code === 0 && res.data.length) {
                state.myUserId = null;
            }
        });

        Promise.all([loadServers(), loadEmployees(), loadFriends(), loadGroups(), loadFriendRequests()])
            .then(function () {
                renderChatList();
                tryNextServer().then(connectWs);
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
