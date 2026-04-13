
      let currentUser = localStorage.getItem("meeting_auth_user");

      let isRegisterMode = false;

      function toggleAuthMode() {
        isRegisterMode = !isRegisterMode;
        document.getElementById("authTitle").innerHTML = isRegisterMode
          ? "📝 注册新账户"
          : "🔐 身份验证";
        document.getElementById("authBtn").textContent = isRegisterMode ? "立即注册" : "登录系统";
        document.getElementById("toggleAuthBtn").textContent = isRegisterMode
          ? "已有账号？去登录"
          : "还没有账号？点击注册";
        document.getElementById("confirmPasswordGroup").style.display = isRegisterMode
          ? "block"
          : "none";
        document.getElementById("loginError").style.display = "none";
      }

      async function doAuth() {
        const username = document.getElementById("usernameInput").value.trim();
        const pwd = document.getElementById("passwordInput").value.trim();
        const confirmPwd = document.getElementById("confirmPasswordInput").value.trim();
        const errDiv = document.getElementById("loginError");
        errDiv.style.display = "none";

        if (!username || !pwd) {
          errDiv.textContent = "请完整填写账号和密码。";
          errDiv.style.display = "block";
          return;
        }

        if (isRegisterMode && pwd !== confirmPwd) {
          errDiv.textContent = "两次输入的密码不一致，请重试。";
          errDiv.style.display = "block";
          return;
        }

        const endpoint = isRegisterMode ? "/api/register" : "/api/login";

        try {
          const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: username, password: pwd }),
          });
          const data = await res.json();
          if (data.success) {
            if (isRegisterMode) {
              // 注册成功，切换回登录
              alert(data.msg);
              toggleAuthMode();
              document.getElementById("passwordInput").value = "";
              document.getElementById("confirmPasswordInput").value = "";
            } else {
              // 登录成功
              currentUser = data.username;
              localStorage.setItem("meeting_auth_user", currentUser);
              document.getElementById("currentAccountName").textContent = currentUser;

              // 登录成功动画消失
              const overlay = document.getElementById("loginOverlay");
              overlay.style.opacity = "0";
              setTimeout(() => {
                overlay.style.display = "none";
              }, 500);

              // 初始化背景
              loadBackgroundSetting();
            }
          } else {
            errDiv.textContent = data.msg;
            errDiv.style.display = "block";
          }
        } catch (e) {
          errDiv.textContent = "网络错误，请稍后再试。";
          errDiv.style.display = "block";
        }
      }

      function logout() {
        if (!confirm("确定要退出登录吗？")) return;
        localStorage.removeItem("meeting_auth_user");
        currentUser = null;
        document.getElementById("passwordInput").value = "";

        const overlay = document.getElementById("loginOverlay");
        overlay.style.display = "flex";
        setTimeout(() => {
          overlay.style.opacity = "1";
        }, 10);
        document.body.style.background =
          "url('/static/default_bg.jpg') no-repeat center center fixed";
      }

      // 初始化
      document.addEventListener("DOMContentLoaded", function () {
        // 检查登录状态
        if (currentUser) {
          document.getElementById("loginOverlay").style.display = "none";
          document.getElementById("currentAccountName").textContent = currentUser;
          loadBackgroundSetting();
        } else {
          document.body.style.background =
            "url('/static/default_bg.jpg') no-repeat center center fixed"; // 退回默认给登录用
        }

        // 密码框回车键登录
        document.getElementById("passwordInput").addEventListener("keypress", function (e) {
          if (e.key === "Enter") doAuth();
        });
        document.getElementById("confirmPasswordInput").addEventListener("keypress", function (e) {
          if (e.key === "Enter") doAuth();
        });

        // 设置默认日期
        const today = new Date().toISOString().split("T")[0];
        document.getElementById("queryDate").value = today;

        // 加载会议室状态
        loadRoomStatus();

        // 绑定事件
        document.getElementById("queryDate").addEventListener("change", loadRoomStatus);
        document.getElementById("sendBtn").addEventListener("click", sendMessage);
        document.getElementById("chatInput").addEventListener("keypress", function (e) {
          if (e.key === "Enter") sendMessage();
        });

        // 初始化加载设置
        loadSettings();

        // 会议纪要生成事件
        document.getElementById("generateSummaryBtn").addEventListener("click", generateSummary);

        // 保存设置事件
        document.getElementById("saveSettingsBtn").addEventListener("click", saveSettings);
      });

      // ---------------- 背景图相关逻辑 ----------------
      function applyBackgroundImage(url) {
        if (url && url.trim() !== "") {
          document.body.style.backgroundImage = `url('${url}')`;
        } else {
          document.body.style.backgroundImage = "linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)";
        }
      }

      function loadBackgroundSetting() {
        const savedBg = localStorage.getItem("meeting_assistant_bg");
        if (savedBg) {
          document.getElementById("bgImageInput").value = savedBg;
          applyBackgroundImage(savedBg);
        }
      }

      // 控制界面麦克风图标的是否可用状态
      function updateMicVisibilityByModel(modelName) {
        const isExpert = modelName.includes("35b");
        const micBtn = document.getElementById("micBtn");
        const recordMeetingBtn = document.getElementById("recordMeetingBtn");
        const micTitle = isExpert
          ? "语音输入"
          : "当前模型(4b)不支持语音，请切换至专家思考模型(35b)";

        if (micBtn) {
          micBtn.disabled = !isExpert;
          micBtn.title = micTitle;
          if (!isExpert) {
            micBtn.style.opacity = "0.5";
            micBtn.style.cursor = "not-allowed";
          } else {
            micBtn.style.opacity = "1";
            micBtn.style.cursor = "pointer";
          }
        }

        if (recordMeetingBtn) {
          recordMeetingBtn.disabled = !isExpert;
          recordMeetingBtn.title = micTitle;
        }
      }

      let currentModel = ""; // 记录当前选择的模型，避免不必要的提示

      // ---------------- 接口设置相关逻辑 ----------------
      async function loadSettings() {
        try {
          const res = await fetch("/api/settings");
          const data = await res.json();
          if (data.model) {
            currentModel = data.model;
            const select = document.getElementById("modelSelectInput");
            if ([...select.options].some((opt) => opt.value === data.model)) {
              select.value = data.model;
            }
            updateMicVisibilityByModel(data.model);
          }
        } catch (e) {
          console.error("加载设置失败", e);
        }
      }

      async function saveSettings() {
        const btn = document.getElementById("saveSettingsBtn");
        const model = document.getElementById("modelSelectInput").value;
        let bgImageUrl = document.getElementById("bgImageInput").value.trim();

        // 移除多余的引号
        bgImageUrl = bgImageUrl.replace(/^['"]+|['"]+$/g, "");

        // 拦截本地绝对路径输入并提示
        if (/^[a-zA-Z]:/.test(bgImageUrl)) {
          alert(
            "检测到似乎是本地磁盘路径（如 E:\\...）。请将网页背景图片放入 static 文件夹内，并使用 /static/图片名 格式进行配置。",
          );
          return;
        }

        btn.disabled = true;
        btn.innerHTML =
          '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 保存中...';

        // 1. 本地存储更新背景图
        localStorage.setItem("meeting_assistant_bg", bgImageUrl);
        document.getElementById("bgImageInput").value = bgImageUrl;
        applyBackgroundImage(bgImageUrl);

        // 2. 接口提交更新模型
        try {
          const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model: model }),
          });
          const data = await res.json();
          if (data.success) {
            // 关闭模态框
            const modalEl = document.getElementById("settingsModal");
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal.hide();

            // 更新麦克风按钮状态
            updateMicVisibilityByModel(model);

            // 在对话框里悄悄提示一句（只有模型真正改变时才提示）
            if (model !== currentModel) {
              const chatBox = document.getElementById("chatBox");
              chatBox.innerHTML += `
                <div class="message ai-message">
                    <div class="message-content text-success">
                        <i class="bi bi-check-circle"></i> 模型接口已切换至：${model.includes("35b") ? "专家思考模型" : "快速响应模型"}
                    </div>
                    <div class="message-time">系统提示</div>
                </div>
              `;
              chatBox.scrollTop = chatBox.scrollHeight;
              currentModel = model;
            }
          } else {
            alert(data.msg || "保存失败");
          }
        } catch (e) {
          alert("请求失败，请检查网络！");
        } finally {
          btn.disabled = false;
          btn.innerHTML = "保存并生效";
        }
      }

      // ---------------- 语音识别相关逻辑 ----------------
      let voiceRecognition = null;
      let meetingRecognition = null;
      let isRecordingChat = false;
      let isRecordingMeeting = false;

      function initSpeechRecognition() {
        if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
          console.warn("当前浏览器不支持语音识别 API");
          document.getElementById("micBtn").style.display = "none";
          document.getElementById("recordMeetingBtn").style.display = "none";
          return;
        }

        const SpeechRecognize = window.SpeechRecognition || window.webkitSpeechRecognition;

        // 1. 聊天语音录入
        voiceRecognition = new SpeechRecognize();
        voiceRecognition.lang = "zh-CN";
        voiceRecognition.continuous = false;
        voiceRecognition.interimResults = true;

        voiceRecognition.onresult = function (event) {
          let interimTranscript = "";
          let finalTranscript = "";

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript;
            } else {
              interimTranscript += event.results[i][0].transcript;
            }
          }

          let input = document.getElementById("chatInput");
          if (finalTranscript) {
            input.value = finalTranscript;
            // 收到最终结果，自动发送
            sendMessage();
          } else {
            input.value = interimTranscript;
          }
        };

        voiceRecognition.onend = function () {
          isRecordingChat = false;
          const micBtn = document.getElementById("micBtn");
          micBtn.classList.remove("btn-danger");
          micBtn.classList.add("btn-outline-secondary");
          micBtn.innerHTML = '<i class="bi bi-mic"></i>';
        };

        document.getElementById("micBtn").addEventListener("click", function () {
          if (isRecordingChat) {
            voiceRecognition.stop();
          } else {
            document.getElementById("chatInput").value = "";
            voiceRecognition.start();
            isRecordingChat = true;
            this.classList.remove("btn-outline-secondary");
            this.classList.add("btn-danger");
            this.innerHTML = '<i class="bi bi-stop-circle"></i>';
          }
        });

        // 2. 会议纪要持续录音
        meetingRecognition = new SpeechRecognize();
        meetingRecognition.lang = "zh-CN";
        meetingRecognition.continuous = true;
        meetingRecognition.interimResults = true;

        meetingRecognition.onresult = function (event) {
          let interimTranscript = "";
          let finalTranscript = "";

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript + "。";
            } else {
              interimTranscript += event.results[i][0].transcript;
            }
          }

          let textArea = document.getElementById("meetingText");
          // 追加最终结果到原有文本
          if (finalTranscript) {
            textArea.value += finalTranscript + "\n";
          }
        };

        meetingRecognition.onend = function () {
          if (isRecordingMeeting) {
            // 如果意外中断，尝试重启
            try {
              meetingRecognition.start();
            } catch (e) {}
          }
        };

        document.getElementById("recordMeetingBtn").addEventListener("click", function () {
          if (isRecordingMeeting) {
            isRecordingMeeting = false;
            meetingRecognition.stop();
            this.classList.remove("btn-danger");
            this.classList.add("btn-outline-danger");
            document.getElementById("recordMeetingText").innerText = "继续录音";
            this.innerHTML =
              '<i class="bi bi-record-circle"></i> <span id="recordMeetingText">继续录音</span>';
          } else {
            isRecordingMeeting = true;
            try {
              meetingRecognition.start();
            } catch (e) {}
            this.classList.remove("btn-outline-danger");
            this.classList.add("btn-danger");
            this.innerHTML =
              '<i class="bi bi-stop-circle"></i> <span id="recordMeetingText">停止录音</span>';
          }
        });
      }
      // ----------------------------------------------------

      // 加载会议室状态
      async function loadRoomStatus() {
        const date = document.getElementById("queryDate").value;
        try {
          const response = await fetch(`/api/room_status?date=${date}`);
          const rooms = await response.json();
          const statusList = document.getElementById("roomStatusList");

          let html = "";
          rooms.forEach((room) => {
            html += `
                    <div class="room-card">
                        <h3>
                            ${room.name}
                            <span class="badge bg-primary">${room.capacity}人</span>
                        </h3>
                        <div class="room-info">
                            <span><i class="bi bi-gear"></i> ${room.equipment}</span>
                        </div>
                        <div class="reservations">
                    `;

            if (room.reservations.length === 0) {
              html += `<div class="no-reservation"><i class="bi bi-check-circle"></i> 当日暂无预约</div>`;
            } else {
              room.reservations.forEach((res) => {
                // 格式化时间显示
                const startTime = res.start_time.replace(" ", " ").slice(0, 16);
                const endTime = res.end_time.replace(" ", " ").slice(0, 16);
                html += `
                            <div class="time-slot">
                                <div class="time">${startTime} - ${endTime}</div>
                                <div class="details">
                                    <span><i class="bi bi-person"></i> ${res.user_name}</span>
                                    <span><i class="bi bi-tag"></i> ${res.meeting_topic}</span>
                                </div>
                            </div>
                            `;
              });
            }

            html += `
                        </div>
                    </div>
                    `;
          });

          statusList.innerHTML = html;
        } catch (error) {
          console.error("加载状态失败：", error);
          document.getElementById("roomStatusList").innerHTML = `
                    <div class="alert alert-danger">加载失败：${error.message}</div>
                `;
        }
      }

      let chatHistory = []; // 用于保存上下文记忆

      // 发送消息
      async function sendMessage() {
        const input = document.getElementById("chatInput");
        const message = input.value.trim();
        if (!message) return;

        // 向上下文加入用户消息
        chatHistory.push({ role: "user", content: message });
        // 保持上下文不要太长，最多保留最近的8条（即4轮对话），避免占用太多token
        if (chatHistory.length > 8) {
          chatHistory = chatHistory.slice(chatHistory.length - 8);
        }

        // 如果在语音识别期间发送，需要停止识别
        if (voiceRecognition && isRecordingChat) {
          voiceRecognition.stop();
        }

        // 添加用户消息
        const chatBox = document.getElementById("chatBox");
        const now = new Date().toLocaleTimeString();
        chatBox.innerHTML += `
                <div class="message user-message">
                    <div class="message-content">${message}</div>
                    <div class="message-time">${now}</div>
                </div>
            `;
        input.value = "";
        chatBox.scrollTop = chatBox.scrollHeight;

        // 添加本地思考中动画
        const thinkingId = "thinking-" + Date.now();
        chatBox.innerHTML += `
            <div class="message ai-message" id="${thinkingId}">
                <div class="message-content">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
                <div class="message-time">思考中...</div>
            </div>
        `;
        chatBox.scrollTop = chatBox.scrollHeight;

        // 调用AI接口 (SSE流式)
        try {
          // 由于我们将发送的 message 是当次的新提问，history 传送前面截取的数组（不包括此次问题本身），这样后端就不会重复
          const historyToSend = chatHistory.slice(0, chatHistory.length - 1);

          const response = await fetch("/api/ai_chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              prompt: message,
              history: historyToSend,
              username: currentUser,
            }),
          });

          // 移除思考中动画
          const thinkingNode = document.getElementById(thinkingId);
          if (thinkingNode) thinkingNode.remove();

          const reader = response.body.getReader();
          const decoder = new TextDecoder();

          // 创建一个新的AI聊天框接收流
          const aiMessageId = "aimsg-" + Date.now();
          chatBox.innerHTML += `
                    <div class="message ai-message" id="${aiMessageId}">
                        <div class="message-content"></div>
                        <div class="message-time">${now}</div>
                    </div>
                `;
          const msgContent = document.querySelector(`#${aiMessageId} .message-content`);

          let fullAiResponse = "";
          let sseBuffer = "";
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            sseBuffer += decoder.decode(value, { stream: true });
            const lines = sseBuffer.split("\n\n");

            // 保留最后一个不完整的块（或者正好是空字符串）
            sseBuffer = lines.pop();

            for (let line of lines) {
              if (line.startsWith("data: ")) {
                let data;
                try {
                  data = JSON.parse(line.substring(6));
                } catch (e) {
                  continue;
                }

                if (data.type === "think") {
                  msgContent.innerHTML =
                    "<span class='text-muted'><i>" + data.content + "</i></span><br>";
                  chatBox.scrollTop = chatBox.scrollHeight;
                } else if (data.type === "chunk") {
                  // 移除之前的思考提示
                  if (msgContent.innerHTML.includes("text-muted")) {
                    msgContent.innerHTML = "";
                  }
                  msgContent.innerHTML += data.content.replace(/\n/g, "<br>");
                  fullAiResponse += data.content;
                  chatBox.scrollTop = chatBox.scrollHeight;
                } else if (data.type === "action") {
                  msgContent.innerHTML = data.content.replace(/\n/g, "<br>");
                  fullAiResponse = data.content; // 如果是动作，记录动作提示作为AI回复上下文
                  chatBox.scrollTop = chatBox.scrollHeight;
                  if (data.refresh) {
                    setTimeout(loadRoomStatus, 1000);
                  }
                } else if (data.type === "error") {
                  msgContent.innerHTML += `<div class="text-danger mt-2"><i class="bi bi-exclamation-triangle"></i> ${data.content}</div>`;
                  chatBox.scrollTop = chatBox.scrollHeight;
                }
              }
            }
          }

          // 流结束，将AI最终回复存入上下文
          if (fullAiResponse.trim() !== "") {
            chatHistory.push({ role: "assistant", content: fullAiResponse });
          }
        } catch (error) {
          // 移除思考中动画
          const thinkingNode = document.getElementById(thinkingId);
          if (thinkingNode) thinkingNode.remove();

          chatBox.innerHTML += `
                    <div class="message ai-message">
                        <div class="message-content text-danger">
                            <i class="bi bi-exclamation-triangle"></i> 服务异常：${error.message}
                        </div>
                        <div class="message-time">${now}</div>
                    </div>
                `;
          chatBox.scrollTop = chatBox.scrollHeight;
        }
      }

      // 生成会议纪要
      async function generateSummary() {
        const text = document.getElementById("meetingText").value.trim();
        const resultDiv = document.getElementById("summaryResult");
        const btn = document.getElementById("generateSummaryBtn");

        if (!text) {
          alert("请先输入或录入会议内容！");
          return;
        }

        // 修改UI状态为生成中
        btn.disabled = true;
        btn.innerHTML =
          '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 生成中...';
        resultDiv.innerHTML = `
          <div class="d-flex align-items-center text-primary">
            <div class="spinner-border ms-auto" role="status" aria-hidden="true"></div>
            <strong>AI 正在努力阅读并总结纪要，请稍候...</strong>
          </div>
        `;

        try {
          const response = await fetch("/api/meeting_summary", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text }),
          });

          const result = await response.json();
          resultDiv.innerHTML = result.content.replace(/\n/g, "<br>");
        } catch (error) {
          resultDiv.innerHTML = `<div class="text-danger"><i class="bi bi-exclamation-triangle"></i> 生成失败：${error.message}</div>`;
        } finally {
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-magic"></i> 生成纪要';
        }
      }
    