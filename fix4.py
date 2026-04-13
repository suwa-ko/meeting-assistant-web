import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

s = content.find('// ---------------- 接口设置相关逻辑 ----------------')
e = content.find('// ---------------- 语音识别相关逻辑 ----------------')

new_block = '''// ---------------- 接口设置相关逻辑 ----------------
        async function loadSettings() {
          try {
            const res = await fetch("/api/settings");
            const data = await res.json();
            if (data.model) {
              currentModel = data.model;
              const select = document.getElementById("modelSelectInput");
              if ([...select.options].some((opt) => opt.value === data.model)) {
                select.value = data.model;
                handleModelChange();
              }
              if (data.deepseek_api_key) {
                document.getElementById('deepseekApiKeyInput').value = data.deepseek_api_key;
              }
              updateMicVisibilityByModel(data.model);
            }
          } catch (e) {
            console.error("加载设置失败", e);
          }
        }

        function handleModelChange() {
          const select = document.getElementById("modelSelectInput");
          if (select.value.includes("deepseek")) {
            document.getElementById("deepseekKeyDiv").style.display = "block";
          } else {
            document.getElementById("deepseekKeyDiv").style.display = "none";
          }
        }

        document.getElementById("modelSelectInput").addEventListener("change", handleModelChange);

        async function saveSettings() {
          const btn = document.getElementById("saveSettingsBtn");
          const model = document.getElementById("modelSelectInput").value;
          const dsKey = document.getElementById("deepseekApiKeyInput").value.trim();
          let bgImageUrl = document.getElementById("bgImageInput").value.trim();

          // 移除多余的引号
          bgImageUrl = bgImageUrl.replace(/^['"]+|['"]+$/g, "");

          // 拦截本地绝对路径输入并提示
          if (/^[a-zA-Z]:/.test(bgImageUrl)) {
            alert(
              "检测到似乎是本地磁盘路径（如 E:\\\\...）。请将网页背景图片放入 static 文件夹内，并使用 /static/图片名 格式进行配置。"
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
              body: JSON.stringify({ model: model, api_key: dsKey }),
            });
            const data = await res.json();
            if (data.success) {
              // 关闭模态框
              const modalEl = document.getElementById("settingsModal");
              // Bootstrap 5 可能会报错所以加判断
              if (typeof bootstrap !== 'undefined') {
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();
              } else {
                modalEl.style.display = "none";
                document.querySelector('.modal-backdrop')?.remove();
              }

              // 更新麦克风按钮状态
              updateMicVisibilityByModel(model);

              // 在对话框里悄悄提示一句
              if (model !== currentModel) {
                const chatBox = document.getElementById("chatBox");
                let modelTypeStr = "快速响应模型";
                if (model.includes("35b")) modelTypeStr = "专家思考模型";
                if (model.includes("deepseek-chat")) modelTypeStr = "DeepSeek 在线版 (v3, 官方API)";
                if (model.includes("deepseek-reasoner")) modelTypeStr = "DeepSeek 思考版 (R1, 官方API)";

                chatBox.innerHTML += \<div class="message ai-message"><div class="message-content text-success"><i class="bi bi-check-circle"></i> 模型接口已切换至：\ + modelTypeStr + \</div><div class="message-time">系统提示</div></div>\;
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

        '''

new_content = content[:s] + new_block + content[e:]

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("HTML repaired successfully.")
