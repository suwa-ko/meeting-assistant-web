# 智能会议室助手（基于本地 Qwen + LM Studio）运行手册

本项目是一个全托管的智能会议室助手，支持通过自然语言进行会议室查询、预订、取消，同时提供基于 Web Speech API 的语音录入功能，以及 AI 自动总结会议纪要的特性。所有的 AI 能力均由本地部署的大规模语言模型提供，保障企业数据绝对安全。

## 一、前置环境与下载准备

### 1. 工具与环境依赖

- **LM Studio**：一款能在本地轻松运行大型语言模型的软件。请前往[官网](https://lmstudio.ai/)下载并安装。在软件内搜索并下载对应的 Qwen 模型（**推荐轻量极速版 `qwen/qwen3-4b-2507`，或者高智商思考版 `qwen3.5-35b-a3b`**）。
- **Python**：请确保系统已安装 Python 3.8 或以上版本，并已配置到系统环境变量中。
- **现代浏览器**：建议使用最新版的 Chrome 或 Edge 浏览器，以完美支持语音输入与毛玻璃界面特效。

### 2. 项目配置文件准备

在项目根目录下找到 `.env` 文件。该文件定义了系统启动时的默认 AI 模型指向。当然，**您现在也可以在界面的「齿轮设置」中动态免重启切换模型！**

```env
# LM Studio 本地 API 配置（端口需与 LM Studio 保持一致）
LMSTUDIO_API_URL=http://localhost:3000/v1/chat/completions
# 默认模型名称（需与 LM Studio 中加载的模型名称保持完全一致）
LMSTUDIO_MODEL=qwen/qwen3-4b-2507
```

## 二、服务启动流程（务必按顺序执行）

### 步骤一：启动 LM Studio 本地 API 服务

1. 打开 **管理员权限** 的 PowerShell 或 Terminal。
2. 启动本地大模型推理服务（指定 3000 端口并开启跨域）：
   ```powershell
   lms server start --port 3000 --cors
   ```
3. **验证服务**：浏览器访问 `http://127.0.0.1:3000/v1/models`，若能看到模型信息返回，即说明大模型引擎启动成功。

### 步骤二：环境配置与项目依赖安装

进入您的项目目录，建议使用 Python 虚拟环境以避免依赖冲突。

1. **创建并激活虚拟环境**（在终端中依次执行）：

   ```powershell
   cd /您的项目路径/meeting-assistant
   # 创建虚拟环境
   python -m venv .venv

   # 如果在 Windows PowerShell 中激活时提示“在此系统上禁用了运行脚本”的错误，请先执行以下命令临时解除限制：
   Set-ExecutionPolicy Unrestricted -Scope Process -Force

   # 激活虚拟环境 (执行成功后命令行前会出现 (.venv) 标识)
   .\.venv\Scripts\Activate.ps1
   ```

2. **安装相关运行库**（确保在虚拟环境激活状态下执行，若已安装可跳过）：
   ```powershell
   pip install flask flask-cors requests python-dotenv
   ```

### 步骤三：启动 Flask 后端主程序

在项目目录下执行：

```powershell
python app.py
```

当终端输出 `Running on http://127.0.0.1:5000` 时，说明后端服务启动完毕。

---

## 三、核心功能与使用指南

用浏览器访问 `http://127.0.0.1:5000` 即可开始使用：

1. 🗓️ **智能预约与取消**
   - 您可以直接在聊天框告诉 AI：“帮我预约明天下午2点到3点的会议室A，我是张三，开需求评审会。”
   - 也可以随时撤销：“帮我取消会议室A明天下午的预约。” AI 会自动操作数据库，并让界面自动刷新。
2. 🎤 **语音交互**
   - 点击输入框旁边的「麦克风」按钮，即可通过说话下达指令，支持边说边转文字，极大提升交互效率。
3. 📝 **AI 自动会议纪要**
   - 点击聊天面板顶部的「会议纪要」按钮。
   - 在弹窗中您可以开启**持续录音模式**记录会议全过程，或者直接粘贴会议聊天记录。点击生成后，系统会让 AI 自动帮您提取：**核心议题、主要决定、待办事项**。
4. ⚙️ **动态模型切换**
   - 点击大标题右上角的半透明 **配置齿轮** 按钮，您可以随时把 AI 大脑更换成不同的模型（例如从 `9B` 无缝切换到智能更高的 `35B`），**免切后台、即改即生效**！

---

## 四、服务停止与进程清理指南

### 1. 正常关闭（建议按照以下顺序）

1. **停止 Flask 服务**：在运行 `app.py` 的终端窗口，按下 `Ctrl + C`，服务即优雅停止。
2. **停止模型服务**：在启动了 `lms server` 的终端里执行以下命令，或者直接按 `Ctrl + C`：
   ```powershell
   lms server stop
   ```
3. 关闭 LM Studio 应用以及浏览器窗口。

### 2. 强制关闭（仅用于服务卡死情况）

如果端口被占用或服务失去响应，可通过 PowerShell 强制结束进程：

```powershell
# 强制清理 Python Flask 进程
tasklist | findstr python.exe
taskkill /F /PID [查看到的PID号码]

# 强制清理 3000 端口占用 (LM Studio API)
netstat -ano | findstr :3000
taskkill /F /PID [查看到的PID号码]
```

### 3. 强制关闭注意事项

仅在服务无响应时使用，正常情况下优先用 `Ctrl + C` 或 `lms server stop`，避免进程残留。

### 4. 其他

"请在根目录新建一个 .env 文件，并填入 JWT_SECRET_KEY=你的密钥 以及 LMSTUDIO_API_URL=大模型地址，然后直接运行 python app.py 系统会自动生成空白数据库。"
