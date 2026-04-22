# 🔬 ResearchAgent — 多 Agent 协作的自动化科研助手

> 输入一个研究问题，多个 Agent 分工协作，自动完成 **文献检索 → 论文精读 → 对比分析 → 生成报告** 全流程。

---

## ✨ 项目亮点

- **5 个专职 Agent 流水线协作**，每个 Agent 只干自己最擅长的事
- **全自动检索 arXiv 论文**，无需手动找文献
- **结构化综述报告**，包含摘要、方法对比、趋势洞察、结论等完整章节
- **可视化 Web 界面**，实时查看每一步进度
- **国际平台：** OpenAI、Anthropic Claude、Google Gemini、Groq、Mistral
- **国内平台：** DeepSeek、通义千问、智谱AI、月之暗面 Kimi、字节豆包、MiniMax

---

## 🤖 Agent 分工设计

```
用户输入研究问题
      │
      ▼
  📋 Planner       拆解研究任务，规划执行计划
      │
      ▼
  🔍 Searcher      调用 arXiv API，检索相关论文
      │
      ▼
  📖 Reader        精读每篇论文，提取核心贡献与相关度评分
      │
      ▼
  🔬 Analyst       横向对比多篇论文，提炼洞察与发展趋势
      │
      ▼
  📝 Writer        汇总所有结果，输出结构化综述报告
```

---

## 🛠 技术栈

| 类别 | 技术 |
|------|------|
| 多 Agent 编排 | LangGraph |
| LLM 调用 | LangChain + LangChain-OpenAI / Anthropic |
| 学术检索 | arXiv API |
| PDF 解析 | pypdf |
| Web 界面 | Gradio |
| 报告导出 | python-docx |

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/ResearchAgent.git
cd ResearchAgent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API 密钥

复制配置模板，然后填入你的 API 密钥：

```bash
cp .env.example .env
```

打开 `.env` 文件，填入你的 API 密钥和模型名称：

```env
# 填入你用的模型的 API 密钥（四选一）
OPENAI_API_KEY=your_api_key
# ANTHROPIC_API_KEY=your_api_key
# DEEPSEEK_API_KEY=your_api_key
# ALIYUN_API_KEY=your_api_key

# 填入对应的模型名称
DEFAULT_MODEL=gpt-4o
```

支持 GPT-4o、Claude、DeepSeek、通义千问，详见 `.env.example`。

### 4. 运行

**方式一：Web 可视化界面（推荐）**

```bash
python web/app.py
```

启动后浏览器打开 `http://127.0.0.1:7860`，填入研究问题，点击「开始研究」即可。

**方式二：命令行**

```bash
python main.py "LLM reasoning最新进展"

# 指定阅读论文数（默认10篇）
python main.py "RAG检索增强生成技术综述" -n 5

# 保存报告到文件
python main.py "多模态大模型研究现状" -o my_report.md
```

---

## 📁 项目结构

```
ResearchAgent/
├── agents/          # 5 个 Agent 的具体实现
│   ├── planner.py   # 任务规划 Agent
│   ├── searcher.py  # 文献检索 Agent
│   ├── reader.py    # 论文阅读 Agent
│   ├── analyst.py   # 对比分析 Agent
│   └── writer.py    # 报告撰写 Agent
├── workflow/        # LangGraph 工作流编排
├── tools/           # arXiv 搜索工具
├── prompts/         # 各 Agent 的提示词模板
├── web/             # Gradio Web 界面
├── utils/           # 日志、状态管理、报告导出等工具
├── config/          # 配置读取
├── tests/           # 单元测试
├── .env.example     # 环境变量配置模板
├── requirements.txt # 项目依赖
└── main.py          # 命令行入口
```

---

## 💡 使用示例

在 Web 界面或命令行中，可以尝试以下研究问题：

- `LLM reasoning 最新进展`
- `RAG 检索增强生成技术综述`
- `Chain-of-Thought prompting 方法对比`
- `多模态大模型研究现状`
- `AI Agent 自主决策能力分析`

---

