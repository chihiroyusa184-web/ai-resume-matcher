# AI简历-岗位智能匹配系统

上传简历PDF + 粘贴岗位描述 → Agent自动解析、技能语义匹配、加权打分、生成改进建议。

## 功能

- **简历解析**：支持PDF上传（pdfplumber）或文本粘贴
- **岗位分析**：LLM提取JD中的硬技能、软技能、学历、经验要求
- **智能匹配**：三维度加权评分（硬技能60% + 软技能20% + 硬性条件20%），三级判定（matched/partial/missing）
- **多轮补充**：系统根据缺失技能生成引导问题，用户补充后即时重新分析，展示分数变化
- **改进建议**：针对缺失和部分匹配的技能，生成具体可操作的简历优化建议
- **多平台LLM**：支持DeepSeek/OpenAI/智谱/通义千问/月之暗面，API Key在网页中配置

## 技术栈

- **Agent框架**: LangGraph (StateGraph)
- **LLM调用**: LangChain + langchain-openai
- **前端**: Streamlit
- **PDF处理**: pdfplumber, fpdf2
- **评估**: 15条自动化测试用例

## 架构

```
extract_text → parse_resume → parse_jd → match → END
                    ↓
           补充信息 → 重新分析 → 循环
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动应用

```bash
streamlit run app.py
```

或双击 `run.bat`（Windows）。

### 3. 使用

1. 左侧边栏选择LLM平台 → 粘贴API Key → 点击"确认配置"
2. 左侧上传简历PDF（或粘贴文本）
3. 右侧粘贴岗位描述
4. 点击"开始分析"
5. 根据引导问题补充信息，系统会重新计算匹配度

## 运行评估

```bash
python eval.py
```

15条测试用例，覆盖高/中/低匹配及边缘场景。

## 项目结构

```
resume-agent/
├── agent.py          # 核心：LangGraph Agent + 匹配算法
├── app.py            # Streamlit Web界面
├── eval.py           # 自动化评估脚本（15条用例）
├── generate_resume.py # 简历PDF生成工具
├── sample_resume.pdf  # 示例简历
├── sample_resume.txt  # 示例简历文本
├── sample_jd.txt      # 示例岗位描述
├── requirements.txt   # Python依赖
├── run.bat / run.ps1  # 启动脚本
└── .env.example       # API配置模板
```

## License

MIT
