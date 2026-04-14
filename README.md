# 智能会议室助手（基于 DeepSeek 云端 API）运行手册

本项目是一个全托管的智能会议室助手，支持通过自然语言进行会议室查询、预订、取消，以及 AI 自动总结会议纪要的特性。所有的 AI 能力均由 DeepSeek 云端大模型提供，方便直接部署到公网环境。

## 一、前置环境与下载准备

### 1. 工具与环境依赖

- **DeepSeek API Key**：前往 [DeepSeek 开放平台](https://platform.deepseek.com/) 注册并获取 API Key。
- **Python**：请确保系统已安装 Python 3.8 或以上版本，并已配置到系统环境变量中。
- **现代浏览器**：建议使用最新版的 Chrome 或 Edge 浏览器，以支持现代前端特效。

### 2. 项目配置文件准备

在项目根目录下找到（或新建） `.env` 文件。该文件定义了系统启动时的默认 AI 模型配置。

```env
# 获取到的 DeepSeek API Key
DEEPSEEK_API_KEY=sk-xxxxxxxxx

# DeepSeek 接口地址
DEEPSEEK_API_URL=https://api.deepseek.com/chat/completions

# 默认模型名称（仅支持 deepseek-chat）
DEEPSEEK_MODEL=deepseek-chat

# JWT 密钥 (随意填写随机字符串)
JWT_SECRET_KEY=yoursecretkey
```

## 二、服务启动流程（务必按顺序执行）

### 步骤一：环境配置与项目依赖安装

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
   pip install flask flask-cors requests python-dotenv flask-jwt-extended werkzeug
   ```

### 步骤二：启动 Flask 后端主程序

在项目目录下执行：

```powershell
python app.py
```

当终端输出 `Running on http://127.0.0.1:5000` 时，说明后端服务启动完毕系统会自动生成空白数据库并初始化。

---

## 三、核心功能与使用指南

用浏览器访问 `http://127.0.0.1:5000` 即可开始使用：

1. 🗓️ **智能预约与取消**
   - 您可以直接在聊天框告诉 AI：“帮我预约明天下午2点到3点的会议室A，我是张三，开需求评审会。”
   - 也可以随时撤销：“帮我取消会议室A明天下午的预约。” AI 会自动操作数据库，并让界面自动刷新。
2. 📝 **AI 自动会议纪要**
   - 点击聊天面板顶部的「会议纪要」按钮。
   - 在弹窗中您可以开启**持续录音模式**记录会议全过程，或者直接粘贴会议聊天记录。点击生成后，系统会让 AI 自动帮您提取：**核心议题、主要决定、待办事项**。
4. ⚙️ **配置界面**
   - 点击大标题右上角的半透明 **配置齿轮** 按钮，您可以自定义网页背景图片，同时也提供模型当前对接信息的提示。

---

## 四、服务停止与部署指南

### 1. 正常关闭

停止 Flask 服务：在运行 `app.py` 的终端窗口，按下 `Ctrl + C`，服务即优雅停止。

### 2. 生产环境部署建议

部署到外网时由于涉及到安全与性能：

- 请勿使用 Flask 自带的开发服务器，推荐使用 Gunicorn 或 uWSGI + Nginx。
- 配置好 `JWT_SECRET_KEY` 环境变量。
- 采用 HTTPS 协议，尤其是前端包含录音 (Web Speech API) 时浏览器要求必须处于安全上下文 (localhost 或 HTTPS) 才能调取麦克风。
