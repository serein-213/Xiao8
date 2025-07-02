function init_app(){
    const micButton = document.getElementById('micButton');
    const muteButton = document.getElementById('muteButton');
    const screenButton = document.getElementById('screenButton');
    const stopButton = document.getElementById('stopButton');
    const resetSessionButton = document.getElementById('resetSessionButton');
    const statusElement = document.getElementById('status');
    const chatContainer = document.getElementById('chatContainer');

    let audioContext;
    let workletNode;
    let stream;
    let isRecording = false;
    let socket;
    let currentGeminiMessage = null;
    let audioPlayerContext = null;
    let videoTrack, videoSenderInterval;
    let audioBufferQueue = [];
    let isPlaying = false;
    let audioStartTime = 0;
    let scheduledSources = [];
    let animationFrameId;
    let seqCounter = 0;
    let globalAnalyser = null;
    let lipSyncActive = false;

    function isMobile() {
      return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
        navigator.userAgent
      );
    }

    // 建立WebSocket连接
    function connectWebSocket() {
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        socket = new WebSocket(`${protocol}://${window.location.host}/ws/${lanlan_config.lanlan_name}`);

        socket.onopen = () => {
            console.log('WebSocket连接已建立');
        };

        socket.onmessage = (event) => {
            if (event.data instanceof Blob) {
                // 处理二进制音频数据
                console.log("收到新的音频块")
                handleAudioBlob(event.data);
                return;
            }

            try {
                const response = JSON.parse(event.data);

                if (response.type === 'gemini_response') {
                    // 检查是否是新消息的开始
                    const isNewMessage = response.isNewMessage || false;
                    appendMessage(response.text, 'gemini', isNewMessage);

                    // 如果是新消息，停止并清空当前音频队列
                    if (isNewMessage) {
                        clearAudioQueue();
                    }
                } else if (response.type === 'user_activity') {
                    clearAudioQueue();
                } if (response.type === 'cozy_audio') {
                    // 处理音频响应
                    console.log("收到新的音频头")
                    const isNewMessage = response.isNewMessage || false;

                    if (isNewMessage) {
                        // 如果是新消息，清空当前音频队列
                        clearAudioQueue();
                    }

                    // 根据数据格式选择处理方法
                    if (response.format === 'base64') {
                        handleBase64Audio(response.audioData, isNewMessage);
                    }
                } else if (response.type === 'status') {
                    statusElement.textContent = response.message;
                    if (response.message === `${lanlan_config.lanlan_name}失联了，请重启！`){
                        statusElement.textContent += " 10秒后自动重启...";
                        stopRecording();
                        if (socket.readyState === WebSocket.OPEN) {
                            socket.send(JSON.stringify({
                                action: 'end_session'
                            }));
                        }
                        hideLive2d();
                        micButton.disabled = true;
                        muteButton.disabled = true;
                        screenButton.disabled = true;
                        stopButton.disabled = true;
                        resetSessionButton.disabled = true;

                        setTimeout(async () => {
                            try {
                                await startMicCapture();
                                statusElement.textContent = `重启完成，${lanlan_config.lanlan_name}回来了！`;
                            } catch (error) {
                                console.error("重启语音捕捉时出错:", error);
                                statusElement.textContent = "重启失败，请手动刷新。";
                            }
                        }, 10000); // 5秒后执行
                    }
                } else if (response.type === 'expression') {
                    window.LanLan1.registered_expressions[response.message]();
                }
            } catch (error) {
                console.error('处理消息失败:', error);
            }
        };

        socket.onclose = () => {
            console.log('WebSocket连接已关闭');
            // 尝试重新连接
            setTimeout(connectWebSocket, 3000);
        };

        socket.onerror = (error) => {
            console.error('WebSocket错误:', error);
        };
    }

    // 初始化连接
    connectWebSocket();

    // 添加消息到聊天界面
    function appendMessage(text, sender, isNewMessage = true) {
        function getCurrentTimeString() {
            return new Date().toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }

        if (sender === 'gemini' && !isNewMessage && currentGeminiMessage) {
            // 追加到现有的Gemini消息
            // currentGeminiMessage.textContent += text;
            currentGeminiMessage.insertAdjacentHTML('beforeend', text.replaceAll('\n', '<br>'));
        } else {
            // 创建新消息
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', sender);
            messageDiv.textContent = "[" + getCurrentTimeString() + "] 🎀 " + text;
            chatContainer.appendChild(messageDiv);

            // 如果是Gemini消息，更新当前消息引用
            if (sender === 'gemini') {
                currentGeminiMessage = messageDiv;
            }
        }
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }


    async function startMicCapture() {  // 开麦，按钮on click
        try {
            if (!audioPlayerContext) {
                audioPlayerContext = new (window.AudioContext || window.webkitAudioContext)();
            }

            if (audioPlayerContext.state === 'suspended') {
                await audioPlayerContext.resume();
            }

            // 获取麦克风流
            stream = await navigator.mediaDevices.getUserMedia({audio: true});

            // 检查音频轨道状态
            const audioTracks = stream.getAudioTracks();
            console.log("音频轨道数量:", audioTracks.length);
            console.log("音频轨道状态:", audioTracks.map(track => ({
                label: track.label,
                enabled: track.enabled,
                muted: track.muted,
                readyState: track.readyState
            })));

            if (audioTracks.length === 0) {
                console.error("没有可用的音频轨道");
                statusElement.textContent = '无法访问麦克风';
                return;
            }

            await startAudioWorklet(stream);

            micButton.disabled = true;
            muteButton.disabled = false;
            screenButton.disabled = false;
            stopButton.disabled = true;
            resetSessionButton.disabled = false;
            statusElement.textContent = '正在语音...';
        } catch (err) {
            console.error('获取麦克风权限失败:', err);
            statusElement.textContent = '无法访问麦克风';
        }
    }

    async function stopMicCapture(){ // 闭麦，按钮on click
        stopRecording();
        micButton.disabled = false;
        muteButton.disabled = true;
        screenButton.disabled = true;
        stopButton.disabled = true;
        resetSessionButton.disabled = false;
        statusElement.textContent = `${lanlan_config.lanlan_name}待机中...`;
    }

    async function getMobileCameraStream() {
      const makeConstraints = (facing) => ({
        video: {
          facingMode: facing,
          frameRate: { ideal: 1, max: 1 },
        },
        audio: false,
      });

      const attempts = [
        { label: 'rear', constraints: makeConstraints({ ideal: 'environment' }) },
        { label: 'front', constraints: makeConstraints('user') },
        { label: 'any', constraints: { video: { frameRate: { ideal: 1, max: 1 } }, audio: false } },
      ];

      let lastError;

      for (const attempt of attempts) {
        try {
          console.log(`Trying ${attempt.label} camera @ ${1}fps…`);
          return await navigator.mediaDevices.getUserMedia(attempt.constraints);
        } catch (err) {
          console.warn(`${attempt.label} failed →`, err);
          statusElement.textContent = err;
          return err;
        }
      }
    }

    async function startScreenSharing(){ // 分享屏幕，按钮on click
        // 检查是否在录音状态
        if (!isRecording) {
            statusElement.textContent = '请先开启麦克风录音！';
            return;
        }
        
        try {
            // 初始化音频播放上下文
            showLive2d();
            if (!audioPlayerContext) {
                audioPlayerContext = new (window.AudioContext || window.webkitAudioContext)();
            }

            // 如果上下文被暂停，则恢复它
            if (audioPlayerContext.state === 'suspended') {
                await audioPlayerContext.resume();
            }
            let captureStream;

            if (isMobile()) {
              // On mobile we capture the *camera* instead of the screen.
              // `environment` is the rear camera (iOS + many Androids). If that's not
              // available the UA will fall back to any camera it has.
              captureStream = await getMobileCameraStream();

            } else {
              // Desktop/laptop: capture the user's chosen screen / window / tab.
              captureStream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                  cursor: 'always',
                  frameRate: 1,
                },
                audio: false,
              });
            }
            startScreenVideoStreaming(captureStream, isMobile() ? 'camera' : 'screen');

            micButton.disabled = true;
            muteButton.disabled = false;
            screenButton.disabled = true;
            stopButton.disabled = false;
            resetSessionButton.disabled = false;

            // 当用户停止共享屏幕时
            captureStream.getVideoTracks()[0].onended = stopScreening;

            // 获取麦克风流
            if (!isRecording) statusElement.textContent = '没开麦啊喂！';
            // const mic_stream = await navigator.mediaDevices.getUserMedia({audio: true});

            // 检查音频轨道状态
            // const audioTracks = mic_stream.getAudioTracks();
            // console.log("音频轨道数量:", audioTracks.length);
            // console.log("音频轨道状态:", audioTracks.map(track => ({
            //     label: track.label,
            //     enabled: track.enabled,
            //     muted: track.muted,
            //     readyState: track.readyState
            // })));
            //
            // if (audioTracks.length === 0) {
            //     console.error("没有可用的音频轨道");
            //     statusElement.textContent = '无法访问麦克风';
            //     return;
            // }

            // await startAudioWorklet(micStream);
            // statusElement.textContent = isMobile() ? '正在使用摄像头...' : '正在共享屏幕...';
          } catch (err) {
            console.error(isMobile() ? '摄像头访问失败:' : '屏幕共享失败:', err);
            console.error('启动失败 →', err);
            let hint = '';
            switch (err.name) {
              case 'NotAllowedError':
                hint = '请检查 iOS 设置 → Safari → 摄像头 权限是否为"允许"';
                break;
              case 'NotFoundError':
                hint = '未检测到摄像头设备';
                break;
              case 'NotReadableError':
              case 'AbortError':
                hint = '摄像头被其它应用占用？关闭扫码/拍照应用后重试';
                break;
            }
            statusElement.textContent = `${err.name}: ${err.message}${hint ? `\n${hint}` : ''}`;
          }
    }

    async function stopScreenSharing(){ // 停止共享，按钮on click
        stopScreening();
        micButton.disabled = true;
        muteButton.disabled = false;
        screenButton.disabled = false;
        stopButton.disabled = true;
        resetSessionButton.disabled = false;
        statusElement.textContent = '正在语音...';
    }

    window.switchMicCapture = async () => {
        if (muteButton.disabled) {
            await startMicCapture();
        } else {
            await stopMicCapture();
        }
    }
    window.switchScreenSharing = async () => {
        if (stopButton.disabled) {
            // 检查是否在录音状态
            if (!isRecording) {
                statusElement.textContent = '请先开启麦克风录音！';
                return;
            }
            await startScreenSharing();
        } else {
            await stopScreenSharing();
        }
    }

    // 开始麦克风录音
    micButton.addEventListener('click', async () => {
        // 立即禁用所有按钮
        micButton.disabled = true;
        muteButton.disabled = true;
        screenButton.disabled = true;
        stopButton.disabled = true;
        resetSessionButton.disabled = true;
        
        // 发送start session事件
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                action: 'start_session',
                input_type: 'audio'
            }));
        }
        
        statusElement.textContent = '正在初始化麦克风...';
        
        // 3秒后执行正常的麦克风启动逻辑
        setTimeout(async () => {
            try {
                // 显示Live2D
                showLive2d();
                await startMicCapture();
            } catch (error) {
                console.error('启动麦克风失败:', error);
                // 如果失败，恢复按钮状态
                micButton.disabled = false;
                muteButton.disabled = true;
                screenButton.disabled = true;
                stopButton.disabled = true;
                resetSessionButton.disabled = false;
                statusElement.textContent = '麦克风启动失败';
            }
        }, 2500);
    });

    // 开始屏幕共享
    screenButton.addEventListener('click', startScreenSharing);

    // 停止屏幕共享
    stopButton.addEventListener('click', stopScreenSharing);

    // 停止对话
    muteButton.addEventListener('click', stopMicCapture);

    resetSessionButton.addEventListener('click', () => {
        hideLive2d()
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                action: 'end_session'
            }));
        }
        stopRecording();
        clearAudioQueue();
        micButton.disabled = false;
        muteButton.disabled = true;
        screenButton.disabled = true;
        stopButton.disabled = true;
        resetSessionButton.disabled = true;
    });

    // 使用AudioWorklet开始音频处理
    async function startAudioWorklet(stream) {
        isRecording = true;

        // 创建音频上下文
        audioContext = new AudioContext();
        console.log("音频上下文采样率:", audioContext.sampleRate);

        // 创建媒体流源
        const source = audioContext.createMediaStreamSource(stream);

        try {
            // 加载AudioWorklet处理器
            await audioContext.audioWorklet.addModule('/static/audio-processor.js');

            // 创建AudioWorkletNode
            workletNode = new AudioWorkletNode(audioContext, 'audio-processor', {
                processorOptions: {
                    originalSampleRate: audioContext.sampleRate,
                    targetSampleRate: 16000
                }
            });

            // 监听处理器发送的消息
            workletNode.port.onmessage = (event) => {
                const audioData = event.data;

                if (isRecording && socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify({
                        action: 'stream_data',
                        data: Array.from(audioData),
                        input_type: 'audio'
                    }));
                }
            };

            // 连接节点
            source.connect(workletNode);
            // 不需要连接到destination，因为我们不需要听到声音
            // workletNode.connect(audioContext.destination);

        } catch (err) {
            console.error('加载AudioWorklet失败:', err);
            statusElement.textContent = 'AudioWorklet加载失败';
        }
    }


    // 停止录屏
    function stopScreening() {
        if (videoSenderInterval) clearInterval(videoSenderInterval);
    }

    // 停止录音
    function stopRecording() {

        stopScreening();
        if (!isRecording) return;

        isRecording = false;
        currentGeminiMessage = null;

        // 停止所有轨道
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }

        // 关闭AudioContext
        if (audioContext) {
            audioContext.close();
        }

        // 通知服务器暂停会话
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                action: 'pause_session'
            }));
        }
        // statusElement.textContent = '录制已停止';
    }

    // 清空音频队列并停止所有播放
    function clearAudioQueue() {
        // 停止所有计划的音频源
        scheduledSources.forEach(source => {
            try {
                source.stop();
            } catch (e) {
                // 忽略已经停止的源
            }
        });

        // 清空队列和计划源列表
        scheduledSources = [];
        audioBufferQueue = [];
        isPlaying = false;
        audioStartTime = 0;
        nextStartTime = 0; // 新增：重置预调度时间
    }


// 处理Base64编码的音频数据
    async function handleBase64Audio(base64AudioData, isNewMessage) {
        try {
            // 确保音频上下文已初始化
            if (!audioPlayerContext) {
                audioPlayerContext = new (window.AudioContext || window.webkitAudioContext)();
            }

            // 如果上下文被暂停，则恢复它
            if (audioPlayerContext.state === 'suspended') {
                await audioPlayerContext.resume();
            }

            // 将Base64转换为ArrayBuffer
            const binaryString = window.atob(base64AudioData);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            // 解码音频数据
            const audioBuffer = await audioPlayerContext.decodeAudioData(bytes.buffer);

            // 将解码后的音频添加到队列
            audioBufferQueue.push(audioBuffer);

            // 如果当前没有播放，开始播放
            if (!isPlaying) {
                playNextInQueue();
            }
        } catch (error) {
            console.error('处理音频失败:', error);
        }
    }


    function scheduleAudioChunks() {
        const scheduleAheadTime = 5;

        initializeGlobalAnalyser();

        // 关键：预调度所有在lookahead时间内的chunk
        while (nextChunkTime < audioPlayerContext.currentTime + scheduleAheadTime) {
            if (audioBufferQueue.length > 0) {
                const { buffer: nextBuffer } = audioBufferQueue.shift();
                console.log('ctx', audioPlayerContext.sampleRate,
                    'buf', nextBuffer.sampleRate);

                const source = audioPlayerContext.createBufferSource();
                source.buffer = nextBuffer;
                // source.connect(audioPlayerContext.destination);


                // 创建analyser节点用于lipSync
                // const analyser = audioPlayerContext.createAnalyser();
                // analyser.fftSize = 2048;
                // source.connect(analyser);
                // analyser.connect(audioPlayerContext.destination);
                // if (window.LanLan1 && window.LanLan1.live2dModel) {
                //     startLipSync(window.LanLan1.live2dModel, analyser);
                // }


                source.connect(globalAnalyser);

                if (!lipSyncActive && window.LanLan1 && window.LanLan1.live2dModel) {
                    startLipSync(window.LanLan1.live2dModel, globalAnalyser);
                    lipSyncActive = true;
                }

                // 精确时间调度
                source.start(nextChunkTime);
                // console.log(`调度chunk在时间: ${nextChunkTime.toFixed(3)}`);

                // 设置结束回调处理lipSync停止
                source.onended = () => {
                    // if (window.LanLan1 && window.LanLan1.live2dModel) {
                    //     stopLipSync(window.LanLan1.live2dModel);
                    // }
                    const index = scheduledSources.indexOf(source);
                    if (index !== -1) {
                        scheduledSources.splice(index, 1);
                    }

                    if (scheduledSources.length === 0 && audioBufferQueue.length === 0) {
                        if (window.LanLan1 && window.LanLan1.live2dModel) {
                            stopLipSync(window.LanLan1.live2dModel);
                        }
                        lipSyncActive = false;
                    }
                };

                // // 更新下一个chunk的时间
                nextChunkTime += nextBuffer.duration;

                scheduledSources.push(source);
            } else {
                break;
            }
        }

        // 继续调度循环
        setTimeout(scheduleAudioChunks, 25); // 25ms间隔检查
    }


    async function handleAudioBlob(blob) {
        // 你现有的PCM处理代码...
        const pcmBytes = await blob.arrayBuffer();
        if (!pcmBytes || pcmBytes.byteLength === 0) {
            console.warn('收到空的PCM数据，跳过处理');
            return;
        }

        if (!audioPlayerContext) {
            audioPlayerContext = new (window.AudioContext || window.webkitAudioContext)();
        }

        if (audioPlayerContext.state === 'suspended') {
            await audioPlayerContext.resume();
        }

        const int16Array = new Int16Array(pcmBytes);
        const audioBuffer = audioPlayerContext.createBuffer(1, int16Array.length, 48000);
        const channelData = audioBuffer.getChannelData(0);
        for (let i = 0; i < int16Array.length; i++) {
            channelData[i] = int16Array[i] / 32768.0;
        }

        const bufferObj = { seq: seqCounter++, buffer: audioBuffer };
        audioBufferQueue.push(bufferObj);

        let i = audioBufferQueue.length - 1;
        while (i > 0 && audioBufferQueue[i].seq < audioBufferQueue[i - 1].seq) {
            [audioBufferQueue[i], audioBufferQueue[i - 1]] =
              [audioBufferQueue[i - 1], audioBufferQueue[i]];
            i--;
        }

        // 如果是第一次，初始化调度
        if (!isPlaying) {
            nextChunkTime = audioPlayerContext.currentTime + 0.1;
            isPlaying = true;
            scheduleAudioChunks(); // 开始调度循环
        }
    }

    // 播放队列中的下一个音频
    function playNextInQueue() {
        if (audioBufferQueue.length === 0) {
            console.warn('缓冲区空了，发生underrun');
                underrunCount++;

                // 如果经常发生underrun，增加缓冲
                if (underrunCount > 2) {
                    adaptiveBufferSize = Math.min(adaptiveBufferSize + 1, 8);
                    // console.log(`增加缓冲大小到: ${adaptiveBufferSize}`);
                    underrunCount = 0;
            }

            isPlaying = false;
            return;
        }

        stablePlayCount++;

        if (stablePlayCount > 50 && adaptiveBufferSize > 2) {
            adaptiveBufferSize--;
            // console.log(`减少缓冲大小到: ${adaptiveBufferSize}`);
            stablePlayCount = 0;
        }

        // 获取队列中的下一个音频缓冲区
        const { buffer: nextBuffer } = audioBufferQueue.shift();

        // 创建音频源节点
        const source = audioPlayerContext.createBufferSource();
        source.buffer = nextBuffer;

        // 连接到音频输出
        source.connect(audioPlayerContext.destination);

        // 假设 audioPlayerContext 已经是你的 AudioContext
        // const analyser = audioPlayerContext.createAnalyser();
        // analyser.fftSize = 2048;
        // source.connect(analyser);
        // analyser.connect(audioPlayerContext.destination);
        // if (window.LanLan1 && window.LanLan1.live2dModel) {
        //     startLipSync(window.LanLan1.live2dModel, analyser)
        // }
        source.connect(audioPlayerContext.destination);

        // 添加到计划源列表
        scheduledSources.push(source);

        // 设置播放结束回调
        source.onended = () => {
            // 从计划源列表中移除
            const index = scheduledSources.indexOf(source);
            if (index !== -1) {
                scheduledSources.splice(index, 1);
            }
            if (window.LanLan1 && window.LanLan1.live2dModel) {
                stopLipSync(window.LanLan1.live2dModel)
            }

            // 继续调度下一个
            playNextInQueue();
        };

        // 关键改动：使用精确时间调度而不是立即播放
        source.start(nextStartTime);

        // 更新下一个音频的开始时间
        nextStartTime += nextBuffer.duration;
    }

    function startScreenVideoStreaming(stream, input_type) {
        const video = document.createElement('video');
        // console.log('Ready for sharing 1')

        video.srcObject = stream;
        video.autoplay = true;
        video.muted = true;
        // console.log('Ready for sharing 2')

        videoTrack = stream.getVideoTracks()[0];
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        // 定时抓取当前帧并编码为jpeg
        video.play().then(() => {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            videoSenderInterval = setInterval(() => {
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                const dataUrl = canvas.toDataURL('image/jpeg', 0.8); // base64 jpeg

                if (socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify({
                        action: 'stream_data',
                        data: dataUrl,
                        input_type: input_type,
                    }));
                }
            }, 1000); } // 每100ms一帧
        )
    }

    function initializeGlobalAnalyser() {
        if (!globalAnalyser && audioPlayerContext) {
            globalAnalyser = audioPlayerContext.createAnalyser();
            globalAnalyser.fftSize = 2048;
            globalAnalyser.connect(audioPlayerContext.destination);
        }
    }

    function startLipSync(model, analyser) {
        const dataArray = new Uint8Array(analyser.fftSize);

        function animate() {
            function trySetParam(model, id, value) {
                // getParameterIndex: 找不到时返回 -1
                if (model.internalModel.coreModel.getParameterIndex(id) !== -1) {
                    model.internalModel.coreModel.setParameterValueById(id, value);
                    return true;
                }
                return false;
              }

              
            analyser.getByteTimeDomainData(dataArray);
            // 简单求音量（RMS 或最大振幅）
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
                const val = (dataArray[i] - 128) / 128; // 归一化到 -1~1
                sum += val * val;
            }
            const rms = Math.sqrt(sum / dataArray.length);
            // 这里可以调整映射关系
            const mouthOpen = Math.min(1, rms * 8); // 放大到 0~1
            // 设置 Live2D 嘴巴参数
            trySetParam(model, "ParamO", mouthOpen);
            trySetParam(model, "ParamMouthOpenY", mouthOpen);

            animationFrameId = requestAnimationFrame(animate);
        }

        animate();
    }

    function stopLipSync(model) {
        cancelAnimationFrame(animationFrameId);
        // 关闭嘴巴
        model.internalModel.coreModel.setParameterValueById("ParamMouthOpenY", 0);
    }

    // 隐藏live2d函数
    function hideLive2d() {
        const container = document.getElementById('live2d-container');
        container.classList.add('minimized');
    }

    // 显示live2d函数
    function showLive2d() {
        const container = document.getElementById('live2d-container');

        // 判断是否已经最小化（通过检查是否有hidden类或检查样式）
        if (!container.classList.contains('minimized') &&
            container.style.visibility !== 'minimized') {
            // 如果已经显示，则不执行任何操作
            return;
        }

        // 先恢复容器尺寸和可见性，但保持透明度为0和位置在屏幕外
        // container.style.height = '1080px';
        // container.style.width = '720px';
        container.style.visibility = 'visible';

        // 强制浏览器重新计算样式，确保过渡效果正常
        void container.offsetWidth;

        // 移除hidden类，触发过渡动画
        container.classList.remove('minimized');
    }
    window.startScreenSharing = startScreenSharing;
    window.stopScreenSharing  = stopScreenSharing;
    window.screen_share       = startScreenSharing; // 兼容老按钮
}

const ready = () => {
    if (ready._called) return;
    ready._called = true;
    init_app();
};

document.addEventListener("DOMContentLoaded", ready);
window.addEventListener("load", ready);

