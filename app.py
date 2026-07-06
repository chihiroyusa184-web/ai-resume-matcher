"""
AI简历-JD智能匹配系统 — Streamlit前端
"""

import importlib
import os
import sys
import tempfile
import streamlit as st

# --- 强制重载 agent 模块, 防止 Streamlit 热重载时使用缓存的旧代码 ---
if "agent" in sys.modules:
    importlib.reload(sys.modules["agent"])
from agent import run_match, generate_supplement_questions, run_match_with_supplement

st.set_page_config(
    page_title="AI简历-岗位智能匹配",
    page_icon="📊",
    layout="wide",
)

# ============================================================
# 样式
# ============================================================

st.markdown("""
<style>
    .score-big { font-size: 72px; font-weight: bold; text-align: center; }
    .score-high { color: #22c55e; }
    .score-mid { color: #f59e0b; }
    .score-low { color: #ef4444; }
    .skill-tag { display: inline-block; padding: 4px 12px; border-radius: 16px;
                  margin: 3px; font-size: 14px; }
    .skill-matched { background: #dcfce7; color: #166534; }
    .skill-partial { background: #fef3c7; color: #92400e; }
    .skill-missing { background: #fee2e2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 标题
# ============================================================

st.title("📊 AI简历 × 岗位智能匹配")
st.caption("上传简历 + 输入岗位描述 → Agent自动解析、对比、打分、给建议")

# ============================================================
# 侧边栏: API配置
# ============================================================

with st.sidebar:
    st.header("🔑 API 配置")

    # 预设平台选择
    PLATFORMS = {
        "": {"url": "", "model": "", "desc": "手动输入"},
        "DeepSeek": {"url": "https://api.deepseek.com/v1", "model": "deepseek-chat", "desc": "便宜,注册送额度"},
        "OpenAI": {"url": "https://api.openai.com/v1", "model": "gpt-4o-mini", "desc": "官方,稳定"},
        "智谱GLM": {"url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash", "desc": "国产,免费额度"},
        "通义千问": {"url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-turbo", "desc": "阿里云"},
        "月之暗面": {"url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k", "desc": "长文本"},
    }

    platform = st.selectbox(
        "选择平台",
        list(PLATFORMS.keys()),
        format_func=lambda x: f"{x} — {PLATFORMS[x]['desc']}" if x else "手动输入以下内容",
    )

    preset_url = PLATFORMS[platform]["url"]
    preset_model = PLATFORMS[platform]["model"]

    api_key_input = st.text_input(
        "API Key",
        type="password",
        placeholder="sk-xxxxxxxx",
    )

    base_url_input = st.text_input(
        "Base URL (API地址)",
        value=preset_url,
        placeholder="https://api.deepseek.com/v1",
    )
    model_input = st.text_input(
        "Model (模型名)",
        value=preset_model,
        placeholder="deepseek-chat",
    )

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        confirm_clicked = st.button("✅ 确认配置", use_container_width=True)
    with col_btn2:
        if "api_configured" in st.session_state and st.session_state.api_configured:
            st.success("已配置 ✓")

    if confirm_clicked:
        if api_key_input.strip():
            st.session_state.api_key = api_key_input.strip()
            st.session_state.base_url = base_url_input.strip()
            st.session_state.model = model_input.strip()
            st.session_state.api_configured = True
            st.success("配置已保存!")
        else:
            st.error("请先输入API Key")

    st.divider()
    st.caption("💡 推荐 DeepSeek: platform.deepseek.com 注册送免费额度")


# ============================================================
# 结果展示函数
# ============================================================

def display_results(result: dict, previous_score: float | None = None):
    """展示匹配结果，可选择显示与上一轮分数的变化"""
    if result.get("error"):
        st.error(f"❌ 分析失败: {result['error']}")
        return

    final_score_pct = round(result["final_score"] * 100)

    # --- 分数变化指示 ---
    delta_html = ""
    if previous_score is not None:
        prev_pct = round(previous_score * 100)
        delta = final_score_pct - prev_pct
        if delta > 0:
            delta_html = f'<div style="font-size:16px;color:#22c55e;">↑ +{delta}%</div>'
        elif delta < 0:
            delta_html = f'<div style="font-size:16px;color:#ef4444;">↓ {delta}%</div>'
        else:
            delta_html = '<div style="font-size:16px;color:#64748b;">无变化</div>'

    # --- 总分 ---
    if final_score_pct >= 70:
        color_class = "score-high"
        verdict = "匹配度较高,可以投递 👆"
    elif final_score_pct >= 40:
        color_class = "score-mid"
        verdict = "有差距,建议针对性优化后投递 ✋"
    else:
        color_class = "score-low"
        verdict = "差距较大,需要大幅调整简历 ⚠️"

    if previous_score is not None:
        prev_pct = round(previous_score * 100)
        verdict = f"{prev_pct}% → {final_score_pct}%  {verdict}"

    st.markdown(f"""
    <div style="text-align:center; padding:20px 0;">
        <div class="score-big {color_class}">{final_score_pct}%</div>
        {delta_html}
        <div style="font-size:18px;color:#64748b;">综合匹配度 — {verdict}</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- 三维度得分 ---
    col_hard, col_soft, col_cond = st.columns(3)
    col_hard.metric("硬技能匹配", f"{round(result['hard_score']*100)}%",
                    help="编程语言、框架、工具等的匹配情况")
    col_soft.metric("软技能匹配", f"{round(result['soft_score']*100)}%",
                    help="沟通、协作、学习能力等的匹配情况")
    col_cond.metric("硬性条件", f"{round(result['condition_score']*100)}%",
                    help="学历、经验年限等的匹配情况")

    st.divider()

    # --- 技能详情 ---
    st.subheader("📋 技能逐项分析")

    tab_matched, tab_partial, tab_missing = st.tabs([
        f"✅ 匹配技能 ({len(result['matched'])})",
        f"⚠️ 部分匹配 ({len(result['partial'])})",
        f"❌ 缺失技能 ({len(result['missing'])})",
    ])

    with tab_matched:
        if result["matched"]:
            for item in result["matched"]:
                st.success(f"**{item['required_skill']}** — {item.get('reason', '')}")
        else:
            st.write("无完全匹配的技能")

    with tab_partial:
        if result["partial"]:
            for item in result["partial"]:
                st.warning(f"**{item['required_skill']}** — {item.get('reason', '')}")
        else:
            st.write("无部分匹配的技能")

    with tab_missing:
        if result["missing"]:
            for item in result["missing"]:
                st.error(f"**{item['required_skill']}** — {item.get('reason', '')}")
        else:
            st.write("无缺失技能 🎉")

    # --- 改进建议 ---
    if result.get("suggestions"):
        st.divider()
        st.subheader("💡 简历修改建议")
        for i, suggestion in enumerate(result["suggestions"], 1):
            st.info(f"**{i}.** {suggestion}")

    # --- 调试信息 ---
    with st.expander("🔧 调试信息 (Agent提取的原始数据)"):
        col_debug_1, col_debug_2 = st.columns(2)
        with col_debug_1:
            st.write("**简历解析结果**")
            st.json({
                "skills": result["resume_skills"],
                "experience": result["resume_experience"],
                "education": result["resume_education"],
            })
        with col_debug_2:
            st.write("**岗位解析结果**")
            st.json({
                "hard_skills": result["jd_hard_skills"],
                "soft_skills": result["jd_soft_skills"],
                "education": result["jd_education"],
                "exp_years": result["jd_exp_years"],
            })


# ============================================================
# 输入区: 左右两栏
# ============================================================

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📄 简历")
    upload_mode = st.radio("选择输入方式", ["上传PDF", "粘贴文本"], horizontal=True)

    resume_source = None
    if upload_mode == "上传PDF":
        uploaded = st.file_uploader("上传简历PDF", type=["pdf"])
        if uploaded:
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded.read())
                resume_source = tmp.name
            st.success(f"已上传: {uploaded.name}")
    else:
        resume_source = st.text_area(
            "粘贴简历文本",
            height=300,
            placeholder="张三\n教育背景: ...\n技能: Python, SQL, ...\n工作经历: ...",
        )

with col_right:
    st.subheader("💼 岗位描述")
    jd_text = st.text_area(
        "粘贴岗位描述",
        height=300,
        placeholder="【岗位】Python后端开发实习生\n【任职要求】\n1. 熟练掌握Python...\n2. 熟悉MySQL...",
    )


# ============================================================
# 开始分析按钮 + 补充信息交互
# ============================================================

st.divider()

can_run = (
    resume_source is not None
    and jd_text.strip()
    and st.session_state.get("api_configured", False)
)

# --- 按钮：首次分析 / 清空重来 ---
col_btn1, col_btn2 = st.columns([3, 1])
with col_btn1:
    run_clicked = st.button(
        "🚀 开始分析", type="primary",
        disabled=not can_run,
        use_container_width=True,
    )
with col_btn2:
    has_result = st.session_state.get("latest_result") is not None
    if has_result:
        reset_clicked = st.button("🔄 重来", use_container_width=True)
        if reset_clicked:
            for key in ["latest_result", "original_resume_text", "original_jd_text",
                        "supplements", "supplement_questions", "score_history",
                        "supplement_active"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

if not st.session_state.get("api_configured", False) and resume_source is not None and jd_text.strip():
    st.warning("⚠️ 请先在左侧边栏配置API并点击「确认配置」")


# ============================================================
# 执行首次分析
# ============================================================

if run_clicked:
    with st.spinner("Agent正在工作中..."):
        result = run_match(
            resume_source,
            jd_text,
            st.session_state.get("api_key", ""),
            st.session_state.get("base_url", ""),
            st.session_state.get("model", ""),
        )

        if result.get("error"):
            st.error(f"❌ 分析失败: {result['error']}")
        else:
            # 保存到 session_state
            st.session_state.latest_result = result
            st.session_state.original_resume_text = result["resume_text"]
            st.session_state.original_jd_text = jd_text
            st.session_state.supplements = []
            st.session_state.score_history = [result["final_score"]]
            st.session_state.supplement_active = True

            # 生成引导问题
            if result["missing"] or result["partial"]:
                with st.spinner("正在生成引导问题..."):
                    questions = generate_supplement_questions(
                        result["missing"], result["partial"]
                    )
            else:
                questions = ["你还有其他与岗位相关的技能或经验需要补充吗？"]
            st.session_state.supplement_questions = questions

            st.rerun()


# ============================================================
# 展示结果 (从 session_state 恢复)
# ============================================================

def get_api_config():
    return (
        st.session_state.get("api_key", ""),
        st.session_state.get("base_url", ""),
        st.session_state.get("model", ""),
    )


if st.session_state.get("latest_result") and st.session_state.get("supplement_active"):
    result = st.session_state.latest_result
    score_history = st.session_state.get("score_history", [result["final_score"]])
    supplements = st.session_state.get("supplements", [])

    # 如果有历史分数，显示上一次的
    previous_score = score_history[-2] if len(score_history) > 1 else None
    display_results(result, previous_score)

    # ==================== 补充信息交互区 ====================
    st.divider()
    st.subheader("💬 补充信息")

    rounds = len(supplements)
    if rounds > 0:
        st.caption(f"已进行 {rounds} 轮补充，当前分数基于原始简历 + {rounds} 次补充")

    # 显示引导问题
    questions = st.session_state.get("supplement_questions", [])
    if questions:
        with st.expander("💡 思考以下问题（点击展开）", expanded=(rounds == 0)):
            for i, q in enumerate(questions, 1):
                st.markdown(f"**{i}.** {q}")

    # 补充输入
    supplement_text = st.text_area(
        "补充你的技能、项目经验或其他能力（简历中未体现的部分）",
        height=100,
        placeholder="例如：\n- 我在学校里用Kotlin写过Android课设\n- 我自学过Swift，做了简单的iOS App\n- 我参加过ACM竞赛，算法能力不错",
        key=f"supplement_input_{rounds}",
    )

    col_supp1, col_supp2 = st.columns([1, 2])
    with col_supp1:
        supplement_clicked = st.button(
            "🔄 补充并重新分析",
            type="primary",
            disabled=not supplement_text.strip(),
            use_container_width=True,
        )
    with col_supp2:
        if rounds > 0:
            st.caption("补充后系统会将新信息合并到简历中，重新计算匹配度")

    if supplement_clicked and supplement_text.strip():
        with st.spinner("正在重新分析..."):
            # 累积补充文本
            supplements.append(supplement_text.strip())
            st.session_state.supplements = supplements

            # 重新匹配
            api_key, base_url, model = get_api_config()
            new_result = run_match_with_supplement(
                st.session_state.original_resume_text,
                st.session_state.original_jd_text,
                supplements,
                api_key, base_url, model,
            )

            if new_result.get("error"):
                st.error(f"❌ 重新分析失败: {new_result['error']}")
            else:
                # 更新状态
                old_score = st.session_state.latest_result["final_score"]
                st.session_state.latest_result = new_result
                st.session_state.score_history.append(new_result["final_score"])

                # 重新生成引导问题
                if new_result["missing"] or new_result["partial"]:
                    with st.spinner("更新引导问题..."):
                        questions = generate_supplement_questions(
                            new_result["missing"], new_result["partial"]
                        )
                else:
                    questions = ["还有其他需要补充的吗？"]
                st.session_state.supplement_questions = questions

                st.rerun()

    # 完成按钮
    if rounds > 0:
        st.divider()
        done_clicked = st.button("✅ 完成分析，不再补充", use_container_width=True)
        if done_clicked:
            st.session_state.supplement_active = False
            st.rerun()

    # 补充历史
    if supplements:
        with st.expander(f"📝 补充记录 ({len(supplements)}轮)"):
            for i, supp in enumerate(supplements, 1):
                st.caption(f"第{i}轮补充:")
                st.text(supp)
            st.divider()
            st.caption(f"分数变化: {' → '.join(f'{round(s*100)}%' for s in score_history)}")


# ============================================================
# 初始状态提示
# ============================================================

if not run_clicked and not st.session_state.get("latest_result"):
    st.info("👆 上传简历并输入岗位描述后，点击「开始分析」按钮")
