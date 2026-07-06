"""
评估脚本: 使用构造的简历+JD数据集,量化匹配准确率
"""

import json
import os
from agent import run_match

# ============================================================
# 评估数据集 (15条, 覆盖高/中/低匹配 + 边缘场景)
# ============================================================

EVAL_SET = [
    # ==================== 高匹配 (>70%) ====================
    {
        "id": "high_01_python_backend",
        "resume": """
张三
教育: 本科-计算机科学, 2024年毕业
技能: Python, Django, MySQL, Redis, Git, Docker, Linux
经历: 在某互联网公司担任后端开发实习生1年,参与电商系统开发,使用Django+MySQL搭建API服务,使用Redis做缓存,用Docker部署
""",
        "jd": """
【岗位】Python后端开发工程师
【要求】1. 精通Python和Django框架 2. 熟悉MySQL数据库 3. 了解Redis缓存 4. 熟悉Linux基本操作 5. 有团队协作精神
""",
        "expected_min_score": 70,
    },
    {
        "id": "high_02_java_senior",
        "resume": """
李四
教育: 硕士-软件工程
技能: Java, Spring Boot, Python, MySQL, Oracle, Git, Maven, Jenkins
经历: 3年Java后端开发经验,主导过3个微服务项目,熟悉CI/CD流程
""",
        "jd": """
【岗位】Java开发工程师
【要求】1. 精通Java,熟悉Spring Boot/Spring Cloud 2. 熟悉MySQL或Oracle 3. 了解DevOps工具如Jenkins 4. 3年以上开发经验
""",
        "expected_min_score": 75,
    },
    {
        "id": "high_03_frontend_react",
        "resume": """
王小明
教育: 本科-软件工程, 2023年毕业
技能: JavaScript, TypeScript, React, Vue, HTML5, CSS3, Webpack, Git, Node.js
经历: 2年前端开发经验,主导过公司中后台管理系统重构(React+TypeScript),参与移动端H5项目(Vue)
""",
        "jd": """
【岗位】高级前端开发工程师
【要求】1. 精通JavaScript/TypeScript 2. 熟练掌握React或Vue框架 3. 熟悉Webpack等构建工具 4. 了解Node.js 5. 2年以上前端经验
""",
        "expected_min_score": 80,
    },
    {
        "id": "high_04_data_analyst",
        "resume": """
陈芳
教育: 硕士-统计学
技能: Python, SQL, R, Tableau, PowerBI, Excel, Pandas, NumPy, 数据可视化
经历: 2年数据分析师经验,负责业务数据分析报告,使用Python(Pandas)做数据处理,SQL做数据提取,Tableau做可视化看板
""",
        "jd": """
【岗位】数据分析师
【要求】1. 熟练使用SQL进行数据查询 2. 掌握Python数据分析工具(Pandas/NumPy) 3. 能使用Tableau或类似BI工具 4. 统计学或数学相关专业 5. 良好的数据敏感度
""",
        "expected_min_score": 80,
    },

    # ==================== 中等匹配 (40-70%) ====================
    {
        "id": "mid_01_math_to_data",
        "resume": """
王五
教育: 本科-数学,辅修计算机
技能: Python, SQL, Excel, Tableau
经历: 数据分析实习6个月,用Python做过爬虫和数据处理项目
""",
        "jd": """
【岗位】数据分析师
【要求】1. 熟练使用Python进行数据分析 2. 精通SQL 3. 掌握至少一种BI工具(Tableau/PowerBI/FineBI) 4. 了解统计学基础
""",
        "expected_min_score": 50,
    },
    {
        "id": "mid_02_comms_to_embedded",
        "resume": """
赵六
教育: 本科-通信工程
技能: C, Python, 通信协议, MATLAB
经历: 参与5G基站测试项目,用Python写自动化测试脚本,实习6个月
""",
        "jd": """
【岗位】嵌入式软件开发工程师
【要求】1. 精通C/C++ 2. 了解嵌入式Linux 3. 熟悉通信协议 4. 有Python自动化测试经验优先
""",
        "expected_min_score": 50,
    },
    {
        "id": "mid_03_java_to_python",
        "resume": """
周磊
教育: 本科-计算机科学
技能: Java, Spring Boot, MySQL, Git, 基础Python
经历: 1年Java后端开发,做过Spring Boot项目,自学过Python写脚本
""",
        "jd": """
【岗位】Python后端开发工程师
【要求】1. 精通Python和FastAPI/Django 2. 熟悉MySQL/PostgreSQL 3. 了解Redis 4. 熟悉Docker部署
""",
        "expected_min_score": 40,
    },
    {
        "id": "mid_04_intern_to_fulltime",
        "resume": """
吴小丽
教育: 本科-计算机科学, 大三在读
技能: Python, HTML, CSS, JavaScript, SQL, Git
经历: 校级网站开发项目负责人,暑期参加过编程训练营,无正式实习经验
""",
        "jd": """
【岗位】全栈开发工程师
【要求】1. 精通Python或Node.js后端开发 2. 熟悉前端框架(React/Vue) 3. 有数据库设计经验 4. 2年以上工作经验 5. 本科及以上学历
""",
        "expected_min_score": 35,
    },
    {
        "id": "mid_05_self_taught",
        "resume": """
郑强
教育: 大专-计算机网络
技能: Python, Django, HTML, CSS, MySQL, Linux基础
经历: 自学Python半年,在GitHub上有2个Django练手项目(博客系统、Todo应用),在培训班做过模拟电商项目
""",
        "jd": """
【岗位】Python后端开发工程师
【要求】1. 精通Python和Django框架 2. 熟悉MySQL数据库设计和优化 3. 了解Redis、Docker 4. 本科及以上学历 5. 1年以上开发经验
""",
        "expected_min_score": 35,
    },

    # ==================== 低匹配 (<40%) ====================
    {
        "id": "low_01_admin_to_ml",
        "resume": """
钱七
教育: 大专-电子商务
技能: Excel, Word, 基础Python
经历: 某公司行政助理1年,负责数据录入和报表整理
""",
        "jd": """
【岗位】机器学习工程师
【要求】1. 精通Python,熟悉PyTorch/TensorFlow 2. 扎实的数学基础(线性代数、概率论) 3. 有模型训练和调优经验 4. 硕士及以上学历
""",
        "expected_min_score": 25,
    },
    {
        "id": "low_02_designer_to_devops",
        "resume": """
孙美美
教育: 本科-视觉传达设计
技能: Photoshop, Illustrator, Figma, Sketch, 基础HTML/CSS
经历: 2年UI设计师经验,做过APP和网页界面设计
""",
        "jd": """
【岗位】DevOps/SRE工程师
【要求】1. 精通Linux系统管理 2. 熟悉Docker/Kubernetes 3. 掌握CI/CD工具(Jenkins/GitLab CI) 4. 至少掌握一种脚本语言(Python/Shell/Go) 5. 了解云服务(AWS/阿里云)
""",
        "expected_min_score": 20,
    },
    {
        "id": "low_03_fresh_grad_to_architect",
        "resume": """
刘新
教育: 本科-计算机科学, 2024年应届
技能: Python, Java, C, 数据结构, 计算机网络, MySQL基础
经历: 课程项目:学生管理系统(Java),毕业设计:基于深度学习的图像分类(Python)
""",
        "jd": """
【岗位】系统架构师
【要求】1. 8年以上软件开发经验 2. 精通微服务架构设计 3. 有大规模分布式系统经验 4. 精通至少两种编程语言生态 5. 有团队管理和技术规划能力 6. 硕士及以上学历优先
""",
        "expected_min_score": 15,
    },

    # ==================== 边缘场景 ====================
    {
        "id": "edge_01_minimal_jd",
        "resume": """
陈工
教育: 本科-计算机科学
技能: Python, Django, MySQL, Git, Docker
经历: 2年后端开发经验,负责API开发和数据库优化
""",
        "jd": """招聘Python开发,会Django就行""",
        "expected_min_score": 60,  # JD简略时,匹配度取决于简历覆盖度
    },
    {
        "id": "edge_02_all_required_plus_extras",
        "resume": """
林大牛
教育: 博士-人工智能
技能: Python, PyTorch, TensorFlow, CUDA, C++, Linux, Docker, Kubernetes, MLflow, Kafka, Spark
经历: 5年AI研究经验,在顶会发表10篇论文,主导过千万级用户推荐系统,有团队管理经验
""",
        "jd": """
【岗位】初级算法工程师
【要求】1. 熟悉Python和至少一种深度学习框架 2. 了解推荐系统基本原理 3. 本科及以上学历
""",
        "expected_min_score": 85,  # 简历远超JD要求,应得高分
    },
    {
        "id": "edge_03_empty_skills",
        "resume": """
无名
教育: 高中毕业
经历: 暂无工作经验
""",
        "jd": """
【岗位】Python开发工程师
【要求】1. 精通Python 2. 熟悉Django框架 3. 了解MySQL
""",
        "expected_min_score": 10,  # 几乎空白简历
    },
]

# ============================================================
# 评估函数
# ============================================================

def run_eval(api_key: str = "", base_url: str = "", model: str = ""):
    """跑评估,输出准确率统计"""
    results = []
    total = len(EVAL_SET)
    passed = 0
    errors = 0

    print(f"📊 开始评估,共 {total} 条测试数据")
    print(f"   高匹配: {sum(1 for c in EVAL_SET if c['expected_min_score'] >= 70)} 条")
    print(f"   中等匹配: {sum(1 for c in EVAL_SET if 40 <= c['expected_min_score'] < 70)} 条")
    print(f"   低匹配: {sum(1 for c in EVAL_SET if c['expected_min_score'] < 40)} 条")
    print("=" * 70)

    for i, case in enumerate(EVAL_SET, 1):
        print(f"\n[{i}/{total}] {case['id']}")

        try:
            result = run_match(
                case["resume"],
                case["jd"],
                api_key=api_key,
                base_url=base_url,
                model=model,
            )

            if result.get("error"):
                print(f"  ❌ Agent执行错误: {result['error']}")
                errors += 1
                results.append({
                    "id": case["id"], "expected_min": case["expected_min_score"],
                    "actual": 0, "passed": False, "error": result["error"],
                })
                continue

            actual_score = round(result["final_score"] * 100)
            expected = case["expected_min_score"]
            is_pass = actual_score >= expected

            if is_pass:
                passed += 1
                status = "✅"
            else:
                status = f"❌ (差{expected - actual_score}%)"

            print(f"  期望 ≥{expected}% | 实际 {actual_score}% | {status}")
            print(f"  ───")
            print(f"  硬技能: {round(result['hard_score']*100)}% | 软技能: {round(result['soft_score']*100)}% | 硬性条件: {round(result['condition_score']*100)}%")
            print(f"  匹配: {len(result['matched'])} | 部分: {len(result['partial'])} | 缺失: {len(result['missing'])}")

            results.append({
                "id": case["id"],
                "expected_min": expected,
                "actual": actual_score,
                "passed": is_pass,
                "error": "",
            })

        except Exception as e:
            print(f"  ❌ 执行异常: {e}")
            errors += 1
            results.append({
                "id": case["id"],
                "expected_min": case["expected_min_score"],
                "actual": 0,
                "passed": False,
                "error": str(e),
            })

    # ---- 汇总 ----
    print("\n" + "=" * 70)
    print("\n📊 评估汇总\n")

    valid = [r for r in results if not r["error"]]
    if valid:
        avg_score = sum(r["actual"] for r in valid) / len(valid)
        print(f"  通过率: {passed}/{total} ({round(passed/total*100)}%)")
        print(f"  平均得分: {round(avg_score)}%")
        print(f"  执行异常: {errors} 条")
    else:
        print("  ⚠️ 所有用例均失败,请检查API配置")

    print(f"\n  各用例结果:")
    for r in results:
        status = "✅" if r["passed"] else ("⚠️" if r["error"] else "❌")
        print(f"    {status} {r['id']}: 期望≥{r['expected_min']}% | 实际{r['actual']}%")

    # 输出JSON
    print(f"\n📄 详细结果(JSON):")
    print(json.dumps(results, ensure_ascii=False, indent=2))

    return results


if __name__ == "__main__":
    # 从.env或环境变量读取API配置
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "")
    model = os.getenv("MODEL_NAME", "")
    run_eval(api_key=api_key, base_url=base_url, model=model)
