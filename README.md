# 智能会议室助手（基于 DeepSeek 云端 API）运行手册

本项目是一个全托管的智能会议室助手，支持通过自然语言对话完成会议室的查询、预订与取消操作，并提供 AI 自动生成会议纪要的功能。所有 AI 能力均由 DeepSeek 云端大模型提供，设计极为轻量，方便直接部署到公网或内网环境。

---

## 一、前置环境准备

在运行本项目之前，请确保您的计算机满足以下基本要求：

1. **Python 环境**：已安装 Python 3.8 或更高版本，并配置到系统环境变量。
2. **DeepSeek 账号**：前往 [DeepSeek 开放平台](https://platform.deepseek.com/) 注册账号并获取 API Key。
3. **现代浏览器**：推荐使用最新版 Chrome 或 Edge，以保证完整的前端功能（特别是录音 API 的支持）。

---

## 二、项目配置

在项目根目录下创建一个名为 `.env` 的文件，填入以下配置信息。你可以直接复制下面的模板并替换为你自己的 Key：

```env
# 核心大模型配置
DEEPSEEK_API_KEY=换成你申请好的_DeepSeek_API_Key
DEEPSEEK_API_URL=https://api.deepseek.com/chat/completions
DEEPSEEK_MODEL=deepseek-chat

# 安全配置（填写任意不易被猜破的随机字符串即可）
JWT_SECRET_KEY=your_super_secret_key_here
```

---

## 三、环境安装与启动

为了避免第三方库冲突，**强烈建议使用 Python 虚拟环境**来运行本项目。请按以下顺序在终端中依次执行：

### 1. 创建并激活虚拟环境

打开终端（如 VS Code 终端或 PowerShell），并确认当前正处于项目根目录（`meeting-assistant - web`）：

**Windows 用户：**

```powershell
# 1. 创建虚拟环境 (名为 .venv)
python -m venv .venv

# 2. 赋予当前终端执行脚本的权限（若提示“禁用了运行脚本”引发红字报错，请拔除限制）
Set-ExecutionPolicy Unrestricted -Scope Process -Force

# 3. 激活虚拟环境 (激活成功后，命令行左侧会出现 `(.venv)` 前缀)
.\.venv\Scripts\Activate.ps1
```

**Mac / Linux 用户：**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装项目依赖库

确保虚拟环境已激活（即前面带有 `(.venv)` 标志），执行以下命令安装运行所需的核心库：

```bash
pip install flask flask-cors requests python-dotenv flask-jwt-extended werkzeug
```

### 3. 一键启动后端服务

依赖安装完成后，直接运行主程序即可启动服务：

```bash
python app.py
```

_启动成功后，终端会提示 `Running on http://127.0.0.1:5000`。系统此刻将会自动在本地生成必要的空白数据库并完成初始化工作。_

---

## 四、核心功能使用指南

服务正常启动后，打开浏览器访问 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**，即可体验完整功能：

1. 🗓️ **智能预约与取消**
   - **预定**：在首页聊天框直接发送自然语言：“帮我预约明天下午 2 点到 3 点的会议室A，我是张三，开需求评审会。”
   - **取消**：发送“帮我取消会议室A明天下午的预约。” AI 会自动操作数据库，完成后页面中的会议室占位将会自动刷新。

2. 📝 **AI 会议纪要生成**
   - 点击聊天面板顶部的「会议纪要」按钮打开纪要工作台。
   - 您可以选择开启**持续录音模式**来记录整场会议，或直接手动粘贴会议聊天群组的聊天记录。
   - 点击“生成”后，AI 将自动归纳提取：**核心议题**、**主要决定**和**待办事项**。

3. ⚙️ **个性化外观及模型配置**
   - 点击页面大标题右侧的半透明**齿轮按钮**，您可以更换网页背景图片以适应自身喜好，也可以随时查看当前连接的 AI 模型状态。

---

## 五、停止服务与生产环境部署

### 1. 本地停止运行

当你想关闭服务时，选中正在运行后端的终端窗口，按下键盘上的 `Ctrl + C` 终止进程，服务即会安全停止。

### 2. 生产环境部署建议

如果您打算将本项目部署至公网服务器，基于安全性与性能考量，请采纳以下建议：

- **Web 服务器**：请勿在生产环境使用 Flask 自带的开发服务器，推荐采用 `Gunicorn` 或 `uWSGI` 搭配 `Nginx` 进行反向代理。
- **环境安全**：部署部署到公网前务必修改 `.env` 中的 `JWT_SECRET_KEY` 为高强度密钥。
- **HTTPS 强制启用**：现代安全规范要求 Web Speech API (麦克风录制) 必须在 HTTPS 协议（或 localhost）下才能受权调用。建议为公网域名配置 SSL 证书。
