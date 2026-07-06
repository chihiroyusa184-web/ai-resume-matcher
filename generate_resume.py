"""生成个人简历PDF"""
from fpdf import FPDF

class ResumePDF(FPDF):
    def __init__(self):
        super().__init__("P", "mm", "A4")
        # 注册中文字体
        self.add_font("SimHei", "", "C:/Windows/Fonts/simhei.ttf", uni=True)
        self.add_font("SimHei", "B", "C:/Windows/Fonts/simhei.ttf", uni=True)
        self.set_auto_page_break(True, 15)

    def header(self):
        pass  # 不用默认页眉

    def footer(self):
        self.set_y(-15)
        self.set_font("SimHei", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"第{self.page_no()}页", align="C")

    def section_title(self, title: str):
        """带下划线的章节标题"""
        self.set_font("SimHei", "B", 14)
        self.set_text_color(30, 30, 30)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        # 下划线
        self.set_draw_color(0, 102, 204)
        self.set_line_width(0.6)
        x = self.get_x()
        y = self.get_y()
        self.line(x, y, x + 190, y)
        self.ln(4)

    def body_text(self, text: str, indent: bool = False):
        """正文"""
        self.set_font("SimHei", "", 10.5)
        self.set_text_color(60, 60, 60)
        x = self.get_x()
        if indent:
            self.set_x(x + 5)
        self.multi_cell(0, 6.5, text, new_x="LMARGIN", new_y="NEXT")

    def key_value(self, key: str, value: str):
        """键值对: 加粗key + 普通value"""
        self.set_font("SimHei", "B", 10.5)
        self.set_text_color(30, 30, 30)
        self.cell(self.get_string_width(key) + 2, 6.5, key)
        self.set_font("SimHei", "", 10.5)
        self.set_text_color(60, 60, 60)
        self.cell(0, 6.5, value, new_x="LMARGIN", new_y="NEXT")

    def bullet(self, text: str):
        """带圆点标记的列表项"""
        self.set_font("SimHei", "", 10.5)
        self.set_text_color(60, 60, 60)
        x0 = self.get_x()
        self.cell(8, 6.5, "—")
        self.multi_cell(0, 6.5, text, new_x="LMARGIN", new_y="NEXT")


pdf = ResumePDF()

# ==================== 第一页 ====================
pdf.add_page()

# --- 姓名 ---
pdf.set_font("SimHei", "B", 28)
pdf.set_text_color(0, 51, 102)
pdf.cell(0, 12, "柴清会", new_x="LMARGIN", new_y="NEXT")
pdf.ln(2)

# --- 联系方式 ---
pdf.set_font("SimHei", "", 10)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 7, "电话: 18019210419  |  上海理工大学  |  计算机科学与技术  |  2024级 准大三", new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)

# ==================== 教育背景 ====================
pdf.section_title("教育背景")
pdf.key_value("上海理工大学", "计算机科学与技术  |  2024级  |  GPA: 3.3/4.5")
pdf.body_text("大一期间获得校级二等奖学金，专业排名前15%。主修课程包括数据结构、算法设计、数据库原理、计算机网络、操作系统等。")

pdf.ln(3)

# ==================== 技能 ====================
pdf.section_title("专业技能")
skills = [
    ("编程语言", "C（大一系统学习）, Java（课程学习）, Python（近期自学）, SQL（数据库课程）"),
    ("AI协作开发", "熟练使用Claude等AI编程助手，能够通过AI辅助完成项目架构设计、代码实现与Bug排查"),
    ("目前在学习", "LangGraph Agent开发, LangChain框架, Prompt Engineering, Streamlit Web开发, Django"),
    ("数据库与工具", "MySQL基础, Redis基础了解, Git版本控制, Linux基本操作"),
]
for key, value in skills:
    pdf.key_value(f"{key}：", value)

pdf.ln(3)

# ==================== 项目经历 ====================
pdf.section_title("项目经历")

pdf.set_font("SimHei", "B", 12)
pdf.set_text_color(30, 30, 30)
pdf.cell(0, 7, "AI简历-岗位智能匹配系统", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("SimHei", "", 10)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 6, "个人项目  |  Python, LangGraph, Streamlit, LLM API, Claude辅助开发  |  2025.06 - 至今", new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)

items = [
    "独立完成项目需求分析与架构设计，借助Claude等AI编程助手实现代码开发，两周内从零交付完整系统",
    "设计三维度加权打分算法（硬技能60%、软技能20%、硬性条件20%），支持matched/partial/missing三级技能判定",
    "基于LangGraph+LangChain搭建Agent流程，调用LLM API实现简历解析、技能语义匹配、改进建议生成等功能",
    "使用Streamlit构建Web交互界面，支持多平台LLM切换，实现API Key网页配置、多轮补充信息交互等特性",
    "设计15条覆盖高/中/低匹配及边缘场景的测试用例，验证匹配算法准确率",
]
for item in items:
    pdf.bullet(item)

pdf.ln(4)

# ==================== 荣誉奖项 ====================
pdf.section_title("荣誉奖项")
pdf.bullet("校级二等奖学金（大一学年，专业排名前15%）")

pdf.ln(4)

# ==================== 自我评价 ====================
pdf.section_title("自我评价")
pdf.body_text("大二升大三计算机专业学生，具备扎实的编程基础（Java/Python/C/SQL），对AI应用开发有浓厚兴趣。"
              "擅长利用AI工具（Claude等）辅助学习和开发，通过边学边做的方式，两周内独立完成AI简历匹配系统的全流程开发。"
              "在项目过程中学习了LangGraph Agent架构、LLM API调用、Streamlit Web开发等技术，具备快速上手新技术的能力。"
              "希望在后端开发或AI应用方向获得实习机会，将所学技能应用于实际业务场景。")

# ==================== 保存 ====================
output_path = "c:/Users/16720/OneDrive/Desktop/python/resume-agent/my_resume.pdf"
pdf.output(output_path)
print(f"简历已生成: {output_path}")
