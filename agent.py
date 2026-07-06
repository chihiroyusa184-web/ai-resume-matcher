"""
AI简历-JD智能匹配Agent
基于LangGraph的单Agent + 工具调用架构
"""

import json
import os
from typing import TypedDict, Optional
from dotenv import load_dotenv

import pdfplumber
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

# ============================================================
# 配置
# ============================================================

_llm = None
_llm_config = {}


def _set_user_config(api_key: str, base_url: str, model: str):
    """设置用户API配置(每次run_match调用前设置)"""
    global _llm, _llm_config
    key = api_key or os.getenv("OPENAI_API_KEY", "")
    url = base_url or os.getenv("OPENAI_BASE_URL", "")
    mdl = model or os.getenv("MODEL_NAME", "gpt-4o-mini")
    new_config = {"api_key": key, "base_url": url, "model": mdl}
    if _llm_config != new_config:
        _llm = None  # 强制重建
        _llm_config = new_config


def _get_llm():
    """懒加载LLM实例"""
    global _llm, _llm_config
    if _llm is None:
        _llm = ChatOpenAI(
            model=_llm_config.get("model", "gpt-4o-mini"),
            api_key=_llm_config.get("api_key", ""),
            base_url=_llm_config.get("base_url") or None,
            temperature=0.1,
        )
    return _llm


# ============================================================
# 1. 状态定义 (LangGraph State)
# ============================================================

class MatchState(TypedDict):
    """Agent的全局状态"""
    # 输入
    resume_source: str          # PDF文件路径 或 纯文本
    jd_text: str                # 岗位描述文本

    # 中间结果
    resume_text: str            # 从PDF提取的原始文本
    resume_skills: list[str]    # 简历中的技能列表
    resume_experience: str      # 简历中的经历摘要
    resume_education: str       # 简历中的学历

    jd_hard_skills: list[str]   # JD硬性技能要求
    jd_soft_skills: list[str]   # JD软性技能要求
    jd_education: str           # JD学历要求
    jd_exp_years: float         # JD经验年限要求

    # 输出
    matched: list[dict]         # 匹配上的技能 [{skill, method, evidence}]
    partial: list[dict]         # 部分匹配的技能
    missing: list[dict]         # 缺失的技能 [{skill, importance, suggestion}]
    hard_score: float           # 硬技能得分
    soft_score: float           # 软技能得分
    condition_score: float      # 硬性条件得分
    final_score: float          # 加权总分
    suggestions: list[str]      # 简历修改建议
    error: str                  # 错误信息


# ============================================================
# 2. 工具函数 (Tools)
# ============================================================

def parse_pdf(file_path: str) -> str:
    """工具: 从PDF文件提取文本"""
    try:
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        raise RuntimeError(f"PDF解析失败: {e}")


def extract_resume(resume_text: str) -> dict:
    """
    工具: 用LLM从简历文本中提取结构化信息
    返回 {skills: [], experience: str, education: str}
    """
    prompt = f"""你是一个简历解析专家。从以下简历文本中提取关键信息。

简历文本:
---
{resume_text}
---

请严格按以下JSON格式返回(不要输出其他内容):
{{
    "skills": ["技能1", "技能2", ...],          // 所有技术技能、工具、语言
    "experience": "工作/项目经历摘要(一句话)",
    "education": "学历和专业(如: 本科-计算机科学)"
}}

注意:
1. skills列表要尽量完整,包括编程语言、框架、数据库、工具等
2. 如果某项信息找不到,填空字符串"""""

    response = _get_llm().invoke([HumanMessage(content=prompt)])
    return _parse_json(response.content)


def extract_jd(jd_text: str) -> dict:
    """
    工具: 用LLM从JD中提取关键要求
    返回 {hard_skills: [], soft_skills: [], education: str, exp_years: float}
    """
    prompt = f"""你是一个招聘需求分析专家。从以下岗位描述(JD)中提取关键要求。

岗位描述:
---
{jd_text}
---

请严格按以下JSON格式返回(不要输出其他内容):
{{
    "hard_skills": ["技能1", "技能2", ...],       // 硬性技术要求: 编程语言、框架、工具、数据库等
    "soft_skills": ["沟通能力", "团队协作", ...],  // 软性要求: 沟通、协作、学习能力等
    "education": "学历要求(如: 本科及以上)",
    "exp_years": 0.0                              // 要求的工作经验年数,无明确要求填0
}}

注意:
1. JD中提到的每个技术点都要提取,包括同义词归类(如"熟悉Web框架"→提取"Django/Flask等")
2. 区分"必备"和"加分项"——都提取出来,在importance字段标注
3. 软技能从"任职要求"中的非技术描述里提取"""

    response = _get_llm().invoke([HumanMessage(content=prompt)])
    return _parse_json(response.content)


def match_skills(resume_skills: list[str], jd_hard_skills: list[str]) -> dict:
    """
    工具: 用LLM做语义匹配 + Python代码做精确比对
    返回 {matched: [], partial: [], missing: []}
    """
    prompt = f"""你是技能匹配专家。对比简历中的技能和JD要求,判断匹配程度。

简历技能: {json.dumps(resume_skills, ensure_ascii=False)}

JD要求技能: {json.dumps(jd_hard_skills, ensure_ascii=False)}

对JD中每个技能,判断与简历技能的匹配关系,严格按JSON返回:

{{
    "results": [
        {{
            "required_skill": "Python",
            "status": "matched",           // matched | partial | missing
            "resume_evidence": "Python 2年项目经验",  // 简历中的证据
            "reason": "简历明确列出Python"
        }}
    ]
}}

判断规则:
- "matched": 简历中明确包含该技能或其同义词
- "partial": 简历中有相关但不完全相同的技能(如JD要MySQL,简历有SQL)
- "missing": 简历中完全找不到该技能"""

    response = _get_llm().invoke([HumanMessage(content=prompt)])
    result = _parse_json(response.content)
    results = result.get("results", [])

    matched = [r for r in results if r["status"] == "matched"]
    partial = [r for r in results if r["status"] == "partial"]
    missing = [r for r in results if r["status"] == "missing"]

    return {"matched": matched, "partial": partial, "missing": missing}


def match_soft_skills(resume_text: str, jd_soft_skills: list[str]) -> float:
    """
    工具: 用LLM判断简历中是否有软技能的间接证据
    返回 0~1 的得分
    """
    if not jd_soft_skills:
        return 1.0  # JD没要求软技能,默认满分

    prompt = f"""判断简历中是否有以下软技能的间接证据。

JD要求的软技能: {json.dumps(jd_soft_skills, ensure_ascii=False)}

简历文本:
---
{resume_text}
---

对每项软技能判断是否在简历中有体现,严格按JSON返回:
{{
    "scores": [
        {{"skill": "沟通能力", "found": true, "evidence": "学生会外联部部长"}},
        {{"skill": "团队协作", "found": false, "evidence": ""}}
    ]
}}"""

    response = _get_llm().invoke([HumanMessage(content=prompt)])
    result = _parse_json(response.content)
    scores = result.get("scores", [])

    if not scores:
        return 0.0

    found_count = sum(1 for s in scores if s.get("found"))
    return found_count / len(scores)


def generate_suggestions(
    missing: list[dict],
    partial: list[dict],
    resume_skills: list[str],
    jd_text: str,
) -> list[str]:
    """工具: 用LLM生成具体的简历修改建议"""
    prompt = f"""基于以下差距,给求职者生成3-5条具体的简历修改建议。

简历已有技能: {json.dumps(resume_skills, ensure_ascii=False)}

完全缺失的技能: {json.dumps([m['required_skill'] for m in missing], ensure_ascii=False)}
部分匹配的技能: {json.dumps([p['required_skill'] for p in partial], ensure_ascii=False)}

JD原文:
---
{jd_text}
---

严格按JSON返回:
{{
    "suggestions": [
        "建议1(要具体、可操作,不超过30字)",
        "建议2"
    ]
}}

要求:
1. 每条建议必须具体可操作,不能是空话
2. 优先针对缺失的必备技能
3. 如果技能确实无法短期弥补,建议如何在简历中弱化这个短板"""

    response = _get_llm().invoke([HumanMessage(content=prompt)])
    result = _parse_json(response.content)
    return result.get("suggestions", [])


# ============================================================
# 3. LangGraph节点
# ============================================================

def node_extract_text(state: MatchState) -> MatchState:
    """节点1: 提取文本"""
    source = state["resume_source"]

    if source.endswith(".pdf"):
        state["resume_text"] = parse_pdf(source)
    else:
        # 用户直接粘贴文本
        state["resume_text"] = source

    if not state["resume_text"].strip():
        state["error"] = "简历文本为空,请检查上传的文件"

    return state


def node_parse_resume(state: MatchState) -> MatchState:
    """节点2A: 解析简历"""
    if state.get("error"):
        return state

    try:
        info = extract_resume(state["resume_text"])
        state["resume_skills"] = info.get("skills", [])
        state["resume_experience"] = info.get("experience", "")
        state["resume_education"] = info.get("education", "")
    except Exception as e:
        state["error"] = f"简历解析失败: {e}"

    return state


def node_parse_jd(state: MatchState) -> MatchState:
    """节点2B: 解析JD"""
    if state.get("error"):
        return state

    try:
        info = extract_jd(state["jd_text"])
        state["jd_hard_skills"] = info.get("hard_skills", [])
        state["jd_soft_skills"] = info.get("soft_skills", [])
        state["jd_education"] = info.get("education", "")
        state["jd_exp_years"] = float(info.get("exp_years", 0))
    except Exception as e:
        state["error"] = f"JD解析失败: {e}"

    return state


def node_match(state: MatchState) -> MatchState:
    """节点3: 执行匹配打分"""
    if state.get("error"):
        return state

    try:
        # 3a. 硬技能匹配
        match_result = match_skills(
            state["resume_skills"], state["jd_hard_skills"]
        )
        state["matched"] = match_result["matched"]
        state["partial"] = match_result["partial"]
        state["missing"] = match_result["missing"]

        total_hard = len(state["jd_hard_skills"])
        if total_hard > 0:
            # 完全匹配得1分,部分匹配得0.5分
            hard_score = (
                len(state["matched"]) * 1.0 + len(state["partial"]) * 0.5
            ) / total_hard
        else:
            hard_score = 1.0
        state["hard_score"] = round(hard_score, 2)

        # 3b. 软技能匹配
        state["soft_score"] = round(
            match_soft_skills(state["resume_text"], state["jd_soft_skills"]), 2
        )

        # 3c. 硬性条件
        condition_score = _match_conditions(state)
        state["condition_score"] = round(condition_score, 2)

        # 3d. 加权汇总
        state["final_score"] = round(
            state["hard_score"] * 0.6
            + state["soft_score"] * 0.2
            + state["condition_score"] * 0.2,
            2,
        )

        # 3e. 生成建议
        state["suggestions"] = generate_suggestions(
            state["missing"],
            state["partial"],
            state["resume_skills"],
            state["jd_text"],
        )
    except Exception as e:
        state["error"] = f"匹配过程出错: {e}"

    return state


# ============================================================
# 4. 辅助函数
# ============================================================

def _match_conditions(state: MatchState) -> float:
    """硬性条件匹配: 学历 + 经验年限"""
    score = 0.0
    count = 0

    # 学历匹配(简单关键词匹配,不需要LLM)
    if state["jd_education"]:
        count += 1
        edu_keywords = ["本科", "硕士", "博士", "大专"]
        jd_edu = state["jd_education"]
        resume_edu = state.get("resume_education", "")

        # 检查学历层级
        jd_level = _edu_level(jd_edu)
        resume_level = _edu_level(resume_edu)

        if resume_level >= jd_level:
            score += 1.0
        elif resume_level > 0:
            score += 0.5

    # 经验匹配
    if state["jd_exp_years"] > 0:
        count += 1
        # 从简历中估算经验年数(简化: 用LLM提取过,这里用关键词)
        resume_years = _estimate_exp_years(state.get("resume_experience", ""))
        if resume_years >= state["jd_exp_years"]:
            score += 1.0
        elif resume_years > 0:
            ratio = resume_years / state["jd_exp_years"]
            score += min(ratio, 1.0) * 0.8  # 有一定经验但不是

    if count == 0:
        return 1.0  # JD没要求学历和经验,默认满分
    return score / count


def _edu_level(edu_text: str) -> int:
    """学历文本 → 等级数字"""
    if "博士" in edu_text:
        return 4
    if "硕士" in edu_text or "研究生" in edu_text:
        return 3
    if "本科" in edu_text:
        return 2
    if "大专" in edu_text or "专科" in edu_text:
        return 1
    return 0


def _estimate_exp_years(exp_text: str) -> float:
    """从经历文本中估算经验年数(简化版)"""
    # 简单策略: 数"X年"的出现
    import re
    years = re.findall(r"(\d+)\s*年", exp_text)
    if years:
        return float(max(int(y) for y in years))
    # fallback: 有实习/工作经历至少算0.5年
    if any(w in exp_text for w in ["实习", "工作", "项目"]):
        return 0.5
    return 0.0


def _parse_json(text: str) -> dict:
    """安全解析LLM返回的JSON,处理```json```包裹的情况"""
    text = text.strip()
    # 去掉```json ... ```包裹
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


# ============================================================
# 5. 构建图 + 公共入口
# ============================================================

def build_graph():
    """构建LangGraph状态图"""
    workflow = StateGraph(MatchState)

    # 注册节点
    workflow.add_node("extract_text", node_extract_text)
    workflow.add_node("parse_resume", node_parse_resume)
    workflow.add_node("parse_jd", node_parse_jd)
    workflow.add_node("match", node_match)

    # 连线: extract_text → parse_resume → parse_jd → match → END
    workflow.set_entry_point("extract_text")
    workflow.add_edge("extract_text", "parse_resume")
    workflow.add_edge("parse_resume", "parse_jd")
    workflow.add_edge("parse_jd", "match")
    workflow.add_edge("match", END)

    return workflow.compile()


_graph = None


def get_graph():
    """单例获取编译好的图"""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_match(
    resume_source: str,
    jd_text: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> MatchState:
    """
    公共入口: 执行一次完整的简历-JD匹配

    Args:
        resume_source: PDF文件路径 或 纯文本简历内容
        jd_text: 岗位描述文本
        api_key: API密钥(可选,不传则从.env读取)
        base_url: API地址(可选)
        model: 模型名(可选)

    Returns:
        MatchState: 包含完整匹配结果的状态
    """
    _set_user_config(api_key, base_url, model)

    graph = get_graph()
    initial_state: MatchState = {
        "resume_source": resume_source,
        "jd_text": jd_text,
        "resume_text": "",
        "resume_skills": [],
        "resume_experience": "",
        "resume_education": "",
        "jd_hard_skills": [],
        "jd_soft_skills": [],
        "jd_education": "",
        "jd_exp_years": 0.0,
        "matched": [],
        "partial": [],
        "missing": [],
        "hard_score": 0.0,
        "soft_score": 0.0,
        "condition_score": 0.0,
        "final_score": 0.0,
        "suggestions": [],
        "error": "",
    }
    result = graph.invoke(initial_state)
    return result


# ============================================================
# 6. 补充信息交互功能
# ============================================================

def generate_supplement_questions(
    missing: list[dict],
    partial: list[dict],
) -> list[str]:
    """
    根据缺失和部分匹配的技能，用LLM生成2-3个引导性提问。
    帮助用户回忆简历中未提到但可能具备的技能或经验。
    """
    missing_skills = [m["required_skill"] for m in missing]
    partial_skills = [p["required_skill"] for p in partial]

    if not missing_skills and not partial_skills:
        return ["你还有其他与岗位相关的技能或经验需要补充吗？"]

    prompt = f"""你是一个职业顾问。候选人的简历与岗位要求存在以下差距：

缺失技能（简历中完全没有）: {json.dumps(missing_skills, ensure_ascii=False)}
部分匹配技能（相关但不完全相同）: {json.dumps(partial_skills, ensure_ascii=False)}

请生成2-3个引导性问题，帮助候选人回忆简历中未提及的潜在能力。
问题应该：
1. 针对最重要的缺失技能提问
2. 引导候选人思考是否有相关经验（哪怕是课程项目、自学、比赛等）
3. 语气友好、鼓励性

严格按JSON返回：
{{
    "questions": ["问题1", "问题2", "问题3"]
}}"""

    try:
        response = _get_llm().invoke([HumanMessage(content=prompt)])
        result = _parse_json(response.content)
        return result.get("questions", ["你有哪些简历中未体现的技能或经验？"])
    except Exception:
        # LLM调用失败时返回默认问题
        default = []
        if missing_skills:
            top_missing = missing_skills[:2]
            default.append(f"你是否学习过或使用过 {'、'.join(top_missing)}？即使没有写在简历上")
        if partial_skills:
            default.append(f"你对 {'、'.join(partial_skills[:2])} 的掌握程度如何？有实际项目经验吗？")
        if not default:
            default.append("你还有其他与岗位相关的技能或经验需要补充吗？")
        return default


def run_match_with_supplement(
    original_resume_text: str,
    jd_text: str,
    supplements: list[str],
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> MatchState:
    """
    将原始简历文本与用户补充信息合并后，重新执行匹配分析。

    Args:
        original_resume_text: 首次从PDF提取(或粘贴)的原始简历文本
        jd_text: 岗位描述文本
        supplements: 用户各轮补充的文本列表
        api_key/base_url/model: API配置

    Returns:
        更新后的MatchState
    """
    # 合并原始简历 + 所有补充信息
    combined = original_resume_text
    for i, supp in enumerate(supplements, 1):
        combined += f"\n\n【补充信息 第{i}轮】\n{supp}"

    return run_match(combined, jd_text, api_key, base_url, model)
