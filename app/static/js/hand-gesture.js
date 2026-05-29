/**
 * MediaPipe 视觉手势识别系统
 * 基于摄像头实现手势识别并控制大屏功能
 */

(function() {
    'use strict';

    // 状态管理
    var state = {
        isInitialized: false,
        isRunning: false,
        stream: null,
        videoEl: null,
        canvasEl: null,
        canvasCtx: null,
        hands: null,
        lastGesture: null,
        gestureTimer: null,
        callbacks: {}
    };

    /**
     * 手势类型定义
     */
    var GESTURES = {
        OPEN_PALM: 'open_palm',
        CLOSED_FIST: 'closed_fist',
        POINT_UP: 'point_up',
        THREE_FINGERS: 'three_fingers',
        PEACE: 'peace',
        THUMBS_UP: 'thumbs_up',
        THUMBS_DOWN: 'thumbs_down',
        UNKNOWN: 'unknown'
    };

    // 手势历史记录，用于稳定性检查
    var gestureHistory = [];
    var holdHistory = [];
    var GESTURE_HISTORY_LENGTH = 5;
    var GESTURE_HOLD_LENGTH = 14;
    var COOLDOWN_MS = 2000;
    var RELEASE_FRAMES_REQUIRED = 10;

    var cooldownUntil = 0;
    var waitingForRelease = false;
    var noGestureFrames = 0;
    var commandModeEnabled = false;

    /**
     * 初始化手势识别系统
     */
    function init(options) {
        if (state.isInitialized) {
            return Promise.resolve();
        }

        options = options || {};

        // 创建 DOM 元素
        state.videoEl = document.createElement('video');
        state.videoEl.setAttribute('playsinline', 'true');
        state.videoEl.style.display = 'none';
        state.videoEl.width = 640;
        state.videoEl.height = 480;
        
        state.canvasEl = document.createElement('canvas');
        state.canvasEl.style.display = 'none';
        state.canvasEl.width = 640;
        state.canvasEl.height = 480;
        state.canvasCtx = state.canvasEl.getContext('2d');

        document.body.appendChild(state.videoEl);
        document.body.appendChild(state.canvasEl);

        // MediaPipe 脚本已在 HTML 中加载，直接初始化
        return new Promise(function(resolve, reject) {
            initMediaPipeHands(resolve, reject, options);
        });
    }

    /**
     * 初始化 MediaPipe Hands
     */
    function initMediaPipeHands(resolve, reject, options) {
        try {
            if (typeof Hands === 'undefined') {
                reject(new Error('Hands is not defined'));
                return;
            }

            state.hands = new Hands({
                locateFile: function(file) {
                    return 'https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1646424915/' + file;
                }
            });

            state.hands.setOptions({
                maxNumHands: 1,
                modelComplexity: 1,
                minDetectionConfidence: 0.7,
                minTrackingConfidence: 0.7
            });

            state.hands.onResults(onHandsResults);
            state.isInitialized = true;
            resolve();
        } catch (e) {
            reject(e);
        }
    }

    /**
     * 启动摄像头和手势识别
     */
    function start() {
        if (!state.isInitialized) {
            return Promise.reject(new Error('请先调用 init() 初始化'));
        }

        if (state.isRunning) {
            return Promise.resolve();
        }

        return navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: 640, height: 480 }
        }).then(function(stream) {
            state.stream = stream;
            state.videoEl.srcObject = stream;
            
            return new Promise(function(resolve, reject) {
                state.videoEl.onloadedmetadata = function() {
                    try {
                        state.videoEl.play();
                        state.canvasEl.width = state.videoEl.videoWidth || 640;
                        state.canvasEl.height = state.videoEl.videoHeight || 480;
                        
                        if (typeof Camera !== 'undefined') {
                            var camera = new Camera(state.videoEl, {
                                onFrame: async function() {
                                    if (state.isRunning) {
                                        await state.hands.send({ image: state.videoEl });
                                    }
                                },
                                width: 640,
                                height: 480
                            });
                            camera.start();
                        } else {
                            startManualDetection();
                        }
                        
                        state.isRunning = true;
                        triggerCallback('started');
                        resolve();
                    } catch (e) {
                        reject(e);
                    }
                };
                
                state.videoEl.onerror = function(e) {
                    reject(e);
                };
            });
        });
    }

    /**
     * 手动检测模式（备用）
     */
    function startManualDetection() {
        function detectLoop() {
            if (!state.isRunning) return;
            
            if (state.videoEl.videoWidth > 0) {
                state.canvasCtx.drawImage(state.videoEl, 0, 0, 
                    state.canvasEl.width, state.canvasEl.height);
                state.hands.send({ image: state.canvasEl });
            }
            
            requestAnimationFrame(detectLoop);
        }
        detectLoop();
    }

    /**
     * 停止手势识别
     */
    function stop() {
        state.isRunning = false;
        
        if (state.stream) {
            var tracks = state.stream.getTracks();
            tracks.forEach(function(track) {
                track.stop();
            });
            state.stream = null;
        }
        
        gestureHistory = [];
        holdHistory = [];
        cooldownUntil = 0;
        waitingForRelease = false;
        noGestureFrames = 0;
        triggerCallback('stopped');
    }

    function setCommandModeEnabled(enabled) {
        commandModeEnabled = !!enabled;
        gestureHistory = [];
        holdHistory = [];
        waitingForRelease = false;
        noGestureFrames = 0;
    }

    function isCommandModeEnabled() {
        return commandModeEnabled;
    }

    function updateReleaseState(hasGesture) {
        if (hasGesture) {
            noGestureFrames = 0;
            return;
        }
        noGestureFrames++;
        if (noGestureFrames >= RELEASE_FRAMES_REQUIRED) {
            waitingForRelease = false;
        }
    }

    function isAllSameGesture(history, gesture) {
        for (var i = 0; i < history.length; i++) {
            if (history[i] !== gesture) {
                return false;
            }
        }
        return history.length > 0;
    }

    function enterGestureCooldown() {
        cooldownUntil = Date.now() + COOLDOWN_MS;
        waitingForRelease = true;
        gestureHistory = [];
        holdHistory = [];
        state.lastGesture = null;
    }

    function canTriggerGesture() {
        if (waitingForRelease) {
            return false;
        }
        if (Date.now() < cooldownUntil) {
            return false;
        }
        return true;
    }

    /**
     * 处理手势检测结果
     */
    function onHandsResults(results) {
        if (!state.isRunning) return;

        drawCanvas(results);
        var gesture = detectGesture(results);
        updateReleaseState(!!gesture);

        if (!gesture) {
            gestureHistory = [];
            holdHistory = [];
            return;
        }

        if (!canTriggerGesture()) {
            return;
        }

        gestureHistory.push(gesture);
        if (gestureHistory.length > GESTURE_HISTORY_LENGTH) {
            gestureHistory.shift();
        }

        var stableGesture = getStableGesture();
        if (!stableGesture) {
            return;
        }

        if (!commandModeEnabled) {
            holdHistory.push(stableGesture);
            if (holdHistory.length > GESTURE_HOLD_LENGTH) {
                holdHistory.shift();
            }
            if (holdHistory.length === GESTURE_HOLD_LENGTH && isAllSameGesture(holdHistory, stableGesture)) {
                enterGestureCooldown();
                triggerCallback('gesture_hold', stableGesture);
            }
            return;
        }

        if (stableGesture !== state.lastGesture) {
            state.lastGesture = stableGesture;
            enterGestureCooldown();
            triggerCallback('gesture', stableGesture);
        }
    }
    
    /**
     * 从历史记录中获取稳定的手势
     */
    function getStableGesture() {
        if (gestureHistory.length < GESTURE_HISTORY_LENGTH) {
            return null;
        }
        
        // 检查是否所有记录都是相同手势
        var firstGesture = gestureHistory[0];
        for (var i = 1; i < gestureHistory.length; i++) {
            if (gestureHistory[i] !== firstGesture) {
                return null;
            }
        }
        
        return firstGesture;
    }

    /**
     * 在画布上绘制手部骨架
     */
    function drawCanvas(results) {
        state.canvasCtx.save();
        state.canvasCtx.clearRect(0, 0, state.canvasEl.width, state.canvasEl.height);
        
        if (results && results.image) {
            // 绘制并镜像画面
            state.canvasCtx.save();
            state.canvasCtx.translate(state.canvasEl.width, 0);
            state.canvasCtx.scale(-1, 1);
            state.canvasCtx.drawImage(results.image, 0, 0, state.canvasEl.width, state.canvasEl.height);
            state.canvasCtx.restore();
        }
        
        if (results && results.multiHandLandmarks && typeof drawConnectors !== 'undefined' && typeof drawLandmarks !== 'undefined') {
            for (var i = 0; i < results.multiHandLandmarks.length; i++) {
                var landmarks = results.multiHandLandmarks[i];
                // 镜像地标点以匹配镜像后的画面
                var mirroredLandmarks = landmarks.map(function(lm) {
                    return {
                        x: 1 - lm.x,
                        y: lm.y,
                        z: lm.z
                    };
                });
                
                drawConnectors(state.canvasCtx, mirroredLandmarks, [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[0,9],[9,10],[10,11],[11,12],[0,13],[13,14],[14,15],[15,16],[0,17],[17,18],[18,19],[19,20]], { color: '#00FF00', lineWidth: 3 });
                drawLandmarks(state.canvasCtx, mirroredLandmarks, { color: '#FF4444', lineWidth: 2, radius: 5 });
            }
        }
        
        state.canvasCtx.restore();
    }

    /**
     * 检测手势
     */
    function detectGesture(results) {
        if (!results || !results.multiHandLandmarks || results.multiHandLandmarks.length === 0) {
            return null;
        }
        
        var landmarks = results.multiHandLandmarks[0];
        var fingers = getFingersState(landmarks);
        return classifyGesture(fingers, landmarks);
    }

    /**
     * 获取手指状态（伸直/弯曲）
     * 使用更精确的方法判断每个手指
     */
    function getFingersState(landmarks) {
        var fingers = {
            thumb: false,
            index: false,
            middle: false,
            ring: false,
            pinky: false
        };
        
        try {
            // 大拇指：比较指尖和掌骨的位置关系
            if (landmarks[3] && landmarks[4]) {
                var thumbTip = landmarks[4];
                var thumbIP = landmarks[3];
                var thumbMCP = landmarks[2];
                
                // 计算距离来判断是否伸直
                var ipToTipDist = Math.sqrt(
                    Math.pow(thumbTip.x - thumbIP.x, 2) + 
                    Math.pow(thumbTip.y - thumbIP.y, 2)
                );
                
                var mcpToIPDist = Math.sqrt(
                    Math.pow(thumbIP.x - thumbMCP.x, 2) + 
                    Math.pow(thumbIP.y - thumbMCP.y, 2)
                );
                
                // 如果指尖到IP的距离大于IP到MCP距离的0.8倍，说明大拇指伸直
                fingers.thumb = ipToTipDist > mcpToIPDist * 0.7;
            }
            
            // 食指：比较指尖和PIP的Y坐标
            if (landmarks[6] && landmarks[8]) {
                var indexPIP = landmarks[6];
                var indexTip = landmarks[8];
                fingers.index = (indexPIP.y - indexTip.y) > 0.02;
            }
            
            // 中指
            if (landmarks[10] && landmarks[12]) {
                var middlePIP = landmarks[10];
                var middleTip = landmarks[12];
                fingers.middle = (middlePIP.y - middleTip.y) > 0.02;
            }
            
            // 无名指
            if (landmarks[14] && landmarks[16]) {
                var ringPIP = landmarks[14];
                var ringTip = landmarks[16];
                fingers.ring = (ringPIP.y - ringTip.y) > 0.02;
            }
            
            // 小指
            if (landmarks[18] && landmarks[20]) {
                var pinkyPIP = landmarks[18];
                var pinkyTip = landmarks[20];
                fingers.pinky = (pinkyPIP.y - pinkyTip.y) > 0.02;
            }
        } catch (e) {
            console.warn('Finger state detection error:', e);
        }
        
        return fingers;
    }

    /**
     * 分类手势 - 重新设计优先级和判断逻辑
     */
    function classifyGesture(fingers, landmarks) {
        try {
            // 优先级1：张开手掌 - 所有手指都伸直
            if (fingers.thumb && fingers.index && fingers.middle && fingers.ring && fingers.pinky) {
                return GESTURES.OPEN_PALM;
            }
            
            // 优先级2：剪刀手 - 食指和中指伸直，其他弯曲
            if (fingers.index && fingers.middle && !fingers.ring && !fingers.pinky) {
                // 验证食指和中指是否分开足够远
                var indexTip = landmarks[8];
                var middleTip = landmarks[12];
                var distance = Math.sqrt(
                    Math.pow(indexTip.x - middleTip.x, 2) + 
                    Math.pow(indexTip.y - middleTip.y, 2)
                );
                if (distance > 0.05) {
                    return GESTURES.PEACE;
                }
            }
            
            // 优先级3：食指向上 - 只有食指伸直向上，大拇指和其他手指都弯曲
            if (!fingers.thumb && fingers.index && !fingers.middle && !fingers.ring && !fingers.pinky) {
                // 使用食指指尖到食指MCP的方向
                var angle = getFingerDirection(landmarks[8], landmarks[5]);
                // 判断是否向上
                if (angle > -60 && angle < 60) {
                    return GESTURES.POINT_UP;
                }
            }
            
            // 优先级4：三指伸直 - 食指、中指、无名指伸直，小指和大拇指弯曲
            if (fingers.index && fingers.middle && fingers.ring && !fingers.pinky) {
                return GESTURES.THREE_FINGERS;
            }
            
            // 优先级5：点赞/向下 - 只有大拇指伸直
            if (fingers.thumb && !fingers.index && !fingers.middle && !fingers.ring && !fingers.pinky) {
                if (landmarks[4] && landmarks[9]) {
                    var thumbTip = landmarks[4];
                    var middleMCP = landmarks[9];
                    
                    if (thumbTip.y < middleMCP.y) {
                        return GESTURES.THUMBS_UP;
                    } else {
                        return GESTURES.THUMBS_DOWN;
                    }
                }
            }
            
            // 优先级6：握拳 - 所有手指都弯曲
            if (!fingers.thumb && !fingers.index && !fingers.middle && !fingers.ring && !fingers.pinky) {
                var wrist = landmarks[0];
                var indexTip = landmarks[8];
                var middleTip = landmarks[12];
                
                var indexDist = Math.sqrt(
                    Math.pow(indexTip.x - wrist.x, 2) + 
                    Math.pow(indexTip.y - wrist.y, 2)
                );
                
                var middleDist = Math.sqrt(
                    Math.pow(middleTip.x - wrist.x, 2) + 
                    Math.pow(middleTip.y - wrist.y, 2)
                );
                
                if (indexDist < 0.4 && middleDist < 0.4) {
                    return GESTURES.CLOSED_FIST;
                }
            }
            
        } catch (e) {
            console.warn('Gesture classification error:', e);
        }
        
        return null;
    }

    /**
     * 获取手指方向角度 - 以竖直向上为0度
     */
    function getFingerDirection(tip, base) {
        if (!tip || !base) return 0;
        // 计算从base指向tip的向量
        var dx = tip.x - base.x;
        var dy = tip.y - base.y;
        // 计算相对于竖直向上的角度（Y轴向下为正，所以dy为负表示向上）
        // 使用 atan2(dx, -dy) 来获得以竖直向上为0度的角度
        var angle = Math.atan2(dx, -dy) * (180 / Math.PI);
        return angle;
    }

    /**
     * 事件回调系统
     */
    function on(eventName, callback) {
        state.callbacks[eventName] = callback;
    }

    function triggerCallback(eventName, data) {
        var callback = state.callbacks[eventName];
        if (typeof callback === 'function') {
            try {
                callback(data);
            } catch (e) {
                console.error('Gesture callback error:', e);
            }
        }
    }

    /**
     * 获取视频流画布（用于预览）
     */
    function getCanvas() {
        return state.canvasEl;
    }

    /**
     * 暴露接口
     */
    window.HandGesture = {
        GESTURES: GESTURES,
        init: init,
        start: start,
        stop: stop,
        on: on,
        getCanvas: getCanvas,
        setCommandModeEnabled: setCommandModeEnabled,
        isCommandModeEnabled: isCommandModeEnabled,
        isRunning: function() { return state.isRunning; },
        isInitialized: function() { return state.isInitialized; }
    };
})();
