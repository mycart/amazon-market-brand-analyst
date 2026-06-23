# 🛡️ 亚马逊多国市场品牌智能分析与 PDF 报告生成系统

这是一个基于 **Python + Streamlit + SQLite + Gemini 1.5 Pro (带 Google Search Grounding 谷歌实时搜索接地功能) + ReportLab (中文字体支持)** 构建的跨国电商智能分析系统。

本应用旨在帮助跨境电商卖家与供应链企业，通过输入任意产品中文名称，自动实时调用谷歌搜索抓取最新的亚马逊市场（美、德、日等多站点）畅销排行、真实品牌、环保政策及审美偏好，并一键编译输出格式精美的出版级 PDF 报告。

---

## 📂 项目文件结构
- `app.py`: Streamlit 网页前后台、SQLite 数据库归档以及 ReportLab PDF 报告高精编译的核心引擎。
- `requirements.txt`: 项目所必需的 Python 第三方依赖。
- `README.md`: 本使用与云端一键自动部署说明手册。

---

## 🚀 部署指南

### 方案一：Streamlit Community Cloud 自动化部署（完全免费，推荐）
1. **新建 GitHub 仓库**：在 GitHub 上新建一个私有或公开仓库，例如叫 `amazon-market-analyst`。
2. **上传文件**：将本项目文件（`app.py`、`requirements.txt`、`README.md`）直接拖拽上传到仓库的 `main` 分支。
3. **绑定 Streamlit 账号**：访问 [Streamlit Share](https://share.streamlit.io/)，点击用 GitHub 账号登录并完成授权绑定。
4. **一键部署 (Deploy)**：
   - 点击 **"New app"**。
   - 选中您刚才建立的 GitHub 仓库，Branch 选择 `main`，Main file path 填入 `app.py`。
   - 点击下方 **"Deploy!"** 部署。
5. **配置 API Key 环境变量**：
   - 应用启动后，在网页右下角点击 **"Settings"** -> **"Secrets"**。
   - 填入您的 Google AI Studio API Key：
     ```toml
     GEMINI_API_KEY = "您的谷歌Gemini_API_Key"
     ```
   - 保存后，应用将自动重启，即刻获取强大的实时谷歌数据分析能力！

### 方案二：利用 Build App 一键发布
1. **绑定或推入您的云应用管理控制台**。
2. **设置环境变量**：在 App Settings / Environment Variables 下新增 `GEMINI_API_KEY`。
3. **点击 Build App**，系统会自动拉取此代码包、读取 `requirements.txt` 并执行。部署成功后会为您自动分配并暴露一个安全的公网 URL。

---

## 💻 本地运行指南
1. **安装环境依赖**：
   ```bash
   pip install -r requirements.txt
   ```
2. **设置本地 API Key 环境变量**：
   - **Windows**：
     ```cmd
     set GEMINI_API_KEY=您的API_Key
     ```
   - **macOS / Linux**：
     ```bash
     export GEMINI_API_KEY="您的API_Key"
     ```
3. **启动应用**：
   ```bash
   streamlit run app.py
   ```
   启动成功后，浏览器将自动弹出 `http://localhost:8501`。您即可在本地直接进行查询、生成报告并归档。

---

## 🛠️ 技术亮点说明
1. **Google Search Grounding (谷歌检索接地)**：本应用内置原生 API 检索配置，能够有效克服传统大语言模型的“幻觉”和“时效断层”问题。即使在 2026 年或更晚运行，系统也会去前台搜索实时市场信息，确保报告里出现的品牌和市场对比具有最高真实度。
2. **BLOB 数据库流化存储**：每次生成的 PDF 报告会连同分析的关键词、国家和时间，直接转化成二进制字节流（BLOB）存入 SQLite 数据库。这意味着系统不占用服务器磁盘物理文件，在多次部署和多用户使用中极为稳定，随时支持二次下载。
