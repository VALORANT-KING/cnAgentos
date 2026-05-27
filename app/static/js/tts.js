
/**
 * 语音播报模块 - Web Speech API
 * 用于新消息提醒、采集完成通知等场景
 */

(function() {
    // 模块配置
    var config = {
        enableTTS: true,  // 是否启用语音播报
        lang: 'zh-CN',   // 语音语言
        rate: 0.9,       // 语速（0.1 - 2）
        volume: 1,       // 音量（0 - 1）
        pitch: 1         // 音调（0 - 2）
    };

    // 语音合成对象
    var synth = window.speechSynthesis;
    var voices = [];

    // 加载可用语音列表
    function loadVoices() {
        voices = synth.getVoices();
    }

    // 初始化
    function init() {
        if (!('speechSynthesis' in window)) {
            console.warn('当前浏览器不支持 Web Speech API');
            config.enableTTS = false;
            return;
        }
        loadVoices();
        if (speechSynthesis.onvoiceschanged !== undefined) {
            speechSynthesis.onvoiceschanged = loadVoices;
        }
    }

    /**
     * 播放指定文本
     * @param {string} text 要播放的文本
     */
    function speak(text) {
        if (!config.enableTTS || !text) {
            return;
        }

        // 取消之前正在播放的内容
        synth.cancel();

        var utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = config.lang;
        utterance.rate = config.rate;
        utterance.volume = config.volume;
        utterance.pitch = config.pitch;

        // 尝试找到中文语音
        for (var i = 0; i < voices.length; i++) {
            if (voices[i].lang.indexOf('zh') >= 0) {
                utterance.voice = voices[i];
                break;
            }
        }

        synth.speak(utterance);
    }

    /**
     * 新消息提醒格式
     * @param {string} sender 发送者名称
     * @param {string} message 消息内容
     */
    function notifyNewMessage(sender, message) {
        // 截取消息内容，避免过长
        var shortMessage = message.length > 30 ? message.substring(0, 30) + '...' : message;
        var text = sender + '发来了一条新消息，说' + shortMessage;
        speak(text);
    }

    /**
     * 采集完成通知
     * @param {string} taskName 任务名称
     * @param {number} count 采集数量
     */
    function notifyCollectComplete(taskName, count) {
        var text = '任务' + taskName + '执行完成，采集到' + count + '条数据';
        speak(text);
    }

    /**
     * 系统通知
     * @param {string} content 通知内容
     */
    function notifySystem(content) {
        speak(content);
    }

    // 暴露 API
    window.TTS = {
        init: init,
        speak: speak,
        notifyNewMessage: notifyNewMessage,
        notifyCollectComplete: notifyCollectComplete,
        notifySystem: notifySystem
    };

    // 页面加载时初始化
    document.addEventListener('DOMContentLoaded', init);
})();
