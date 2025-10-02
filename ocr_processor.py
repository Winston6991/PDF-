import os
import json
import re
import logging
import time
import pdfplumber
from config import *

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# 汽车电气系统元器件词典（扩展版）
VEHICLE_COMPONENTS = [
    # 分线器/接线类
    "接小灯分线器", "小灯分线器", "分线器", "接线器", "分线盒", "接T15分线器", "ACC分线器",

    # 雨刮类
    "雨刮间歇", "雨刮间歇控制器", "雨刮电机", "雨刮开关", "洗涤电机", "雨刮间歇继电器",

    # 仪表类
    "仪表电源", "仪表盘电源", "仪表供电", "仪表负", "组合仪表",
    "开关符号指示", "档位指示", "0档指示", "小灯指示灯", "大灯指示灯",
    "前雾指示灯", "后雾指示灯", "充电指示灯", "驻车制动指示", "高档指示灯开关",
    "分动器高档指示", "分动器低档指示", "行车取力指示",

    # 开关类
    "大灯开关", "后雾灯开关", "前雾灯开关", "自动灯光继电器", "近光灯开关",
    "倒车灯开关", "制动灯开关", "集成制动开关限压总阀开关", "接左车门开关",
    "接右车门开关", "蹄片磨损开关", "驻车制动开关", "副驾安全带报警开关",
    "主驾安全带报警开关", "轴间差速锁开关（后桥）", "轮间差速锁开关（中桥）",
    "轮间差速锁开关（后桥）", "取力器开关", "危险报警开关", "喇叭按钮",
    "多功能方向盘", "右侧多功能方向盘开关", "转换开关", "并联油箱开关",
    "作业形式转换开关", "离合器开关", "前照灯高度调节开关", "驾驶室翻转开关",
    "工作灯开关", "右组合开关", "左组合开关", "顶灯翘板开关", "左转向开关",
    "右转向开关", "轴差闭锁开关", "轮差闭锁开关", "取力器选择开关", "ESC关断开关",
    "ESC关断开关 自复位", "坡起开关 自复位", "独立手刹开关（自复位）", "远程油门开关",
    "多功率省油开关", "车下熄火开关", "车下起动开关", "紧急呼叫按钮", "按制动灯开关",

    # 继电器类
    "ACC继电器", "ON继电器", "ADR继电器", "防盗喇叭继电器", "电喇叭继电器",
    "日间行车灯控制输出", "制动灯继电器驱动", "倒车灯继电器驱动", "离合信号抓换继电器",
    "空调请求继电器", "起动继电器", "制动继电器", "左低音扬声器继电器",
    "右低音扬声器继电器", "举升过渡继电器", "举升继电器", "主副油箱切换继电器",
    "近光灯继电器", "远光灯继电器", "前雾灯继电器", "雾灯继电器", "后雾灯继电器",
    "自动灯光继电器", "后视镜加热继电器", "空调请求开关继电器", "电磁式电源总开关继电器",
    "起动锁止继电器", "低速档继电器", "高速档继电器", "驾驶室翻转继电器", "工作灯继电器",

    # 传感器类
    "气压传感器", "里程表传感器", "燃油传感器", "油量传感器", "车速传感器",
    "环境温度传感器", "油温传感器", "水温传感器", "阳光传感器", "室内温度传感器",
    "室外温度传感器", "蒸发器温度传感器", "毫米波雷达", "AEBS（摄像头）",
    "ADAS前视摄像头", "左侧摄像头", "右侧摄像头", "四方位主机", "前照摄像头",
    "后照摄像头", "倒车摄像头", "面部摄像头", "一体式摄像头", "前向监控摄像头",
    "雨量光线传感器", "轮速传感器", "前桥轮速传感器（左）", "前桥轮速传感器（右）",
    "后桥轮速传感", "后桥轮速传感器", "高度传感器左", "高度传感器右",
    "高度传感器后轴左", "高度传感器后轴右", "前桥压力传感器", "三态压力开关",
    "压力传感器", "转角传感器", "横摆率传感器", "挂车气压开关", "制动信号传输器（BST）",
    "左前轮速传感器", "右前轮速传感器", "左后轮速传感器", "右后轮速传感器",
    "里程表传感器", "变速线里程表传感器", "分动器里程表传感器", "主油箱传感器",
    "副油箱传感器", "LNG变送器", "燃气泄漏报警器", "燃气泄露警报器",

    # 执行器类
    "起动机", "自励发电机", "蓄电池一", "蓄电池二", "气喇叭", "电喇叭",
    "左低音扬声器", "右低音扬声器", "左前扬声器", "右前扬声器", "左后扬声器",
    "右后扬声器", "鼓风机电机", "驾驶室翻转继电器", "工作灯继电器",
    "右前组合灯调光电机", "左前组合灯调光电机", "电动翻转电机", "门窗控制单元",
    "中控锁执行电机左", "中控锁执行电机右", "主驾侧玻璃升降机", "副驾侧玻璃升降机",
    "后视镜加热丝", "燃气泄露警报器", "LNG变送器", "燃气泄漏报警器", "加热器总成",
    "电磁泵", "油泵", "独立暖风加热器", "排气制动电磁阀", "电子油门踏板",
    "远程油门控制器总成", "RCU缓速器", "比例阀", "紧急呼叫系统（格洛纳斯/GLONASS）",
    "天行健（IVT）", "收放机总成", "逆变电源", "电压变换器", "DC-DC变换器",
    "交流输出 220V插座", "12V接口", "USB接口（卧铺）", "USB接口（仪表合）",
    "电源车载插座", "点烟器", "220V车载电源插座", "驾驶室气囊断气电磁阀",
    "喇叭继电器", "气电喇叭转换开关", "司机侧门锁电机", "乘客侧门锁电机",
    "中控门锁执行器-司机侧", "中控门锁执行器-乘客侧", "举升电机", "举升电机温控开关",
    "主副油箱转换阀", "干燥器", "轴间差速电磁阀", "轮间差速电磁阀", "取力器电磁阀",
    "取力器选择电磁阀", "ECAS电磁阀", "电磁阀后轴左", "电磁阀后轴右", "电磁阀中心",
    "左前ABS阀", "前右ABS阀", "左前轴电磁阀", "右前轴电磁阀", "左后桥电磁阀",
    "右后桥电磁阀", "前桥AEBS继动阀", "后桥AEBS继动阀", "ASR后桥电磁阀", "ASR前桥电磁阀",
    "挂车控制模块", "挂车控制模块（TCM）", "国产WABCO ABS+ESC控制器", "国产KNORR ABS+ESC控制器",
    "ABS控制器", "DCM(集成RKE)", "ECAS控制器", "变速箱控制器", "OEM换挡控制器",
    "玉柴国六天然气ECI-CFV ECU", "4G车载终端（IVT）", "远程排放终端", "诊断接口",
    "鼓风机调速模块", "内外循环电机", "模式风门电机", "水阀电机", "模式电机",
    "空调压缩机离合器", "供油箱换向阀总成", "左踏步灯", "右踏步灯", "室内顶灯左",
    "室内顶灯右", "左阀读灯", "右阀读灯", "倒车灯", "制动灯", "主车左转向灯",
    "主车右转向灯", "挂车左转向灯", "挂车右转向灯", "侧转向", "左日间行车灯",
    "右日间行车灯", "接T15分线器", "ADR紧急电源故障指示灯", "ADR工作指示灯",

    # 控制单元/模块类
    "集成式ADR控制单元", "ADR集成式室内开关", "ADR集成式室外开关", "空调控制器",
    "电源模块", "中控屏", "四方位主机", "外置功放", "前桥模块", "后桥模块",
    "挂车控制模块", "前桥模块（EPM）", "后桥模块（EPM）", "智能中控屏", "ECAS控制器",

    # 电源/保险类
    "100A慢熔", "50A慢熔", "150A慢熔", "15A快熔", "On 10 A保险", "5A快熔",
    "7.5A快熔", "20A快熔", "10A", "30A", "200A", "快熔", "慢熔", "保险", "电源模块",
    "12V电源", "5V电源", "传感器地", "电源地", "司机侧地", "乘客侧地", "GND",
    "接0501A", "接ON档", "接ACC档", "接0N档继电器2", "司机侧供电", "乘客侧供电",
    "B-CANL", "B-CAN_H", "CAN L", "CAN H", "D+/励磁", "ACC电源", "蓄电池电源",

    # 线束/接插件类
    "线束2端子接插件", "48针插接件", "接插器AM244", "接插器AM245", "接插器AM246",
    "接插器AM215", "接插器AM255", "接插器AM256", "2孔 AT 过渡插接件", "pin 5",
    "SD卡接口", "MIC接口", "收音天线", "定位天线", "4G天线", "遥控闪灯输出",
    "挂车ABS电磁阀电源", "挂车控制器电源", "挂车ABS指示", "电磁阀电源", "系统电源",
    "点火开关输入", "时钟弹簧", "X1线束端", "X2线束端", "X3线束端", "X4线束端"
]

# 文本类型判断正则（适配汽车电气原理图特点）
TEXT_TYPE_PATTERNS = {
    "component_title": [
        # 标题特征：包含"系统"、"原理"、"图"等关键词，或格式如"XXX 14-1"
        r'[电电气气系系统统|电路系统|电气系统].*[原理理图图|原理图]',
        r'^[A-Za-z0-9\-_]+[\s]*\d+-\d+$',  # 如"14-1"、"3700001-94001"
        r'^[电电气气|电气|电路|控制|电源|信号|执行|传感].*[系统|模块|单元|装置]$'
    ],
    "component_desc": [
        # 描述/表格特征：包含"控制"、"连接"、"输入"、"输出"、"参数"等，或带冒号/箭头
        r'[控制|连接|输入|输出|参数|说明|功能|状态|信号].*[:：→→]',
        r'^[A-Za-z0-9]+[\s]*→[\s]*[A-Za-z0-9]+',  # 如"A3→A2"、"C11→C12"
        r'^[左|右|前|后|上|下|主|副|司机|乘客].*[开关|电机|传感器|继电器|指示灯]$',
        r'^[0-9A-Za-z]+[\s]*[V|A|Ω|W|Hz]',  # 带单位的参数，如"12V"、"15A"
        r'^[短接|接地|供电|接线|插接|端子|pin].*'
    ]
}


def get_text_type(text):
    """判断文本类型（适配汽车电气系统文本特点）
    返回：component_title(元件标题) > component_desc(元件描述/表格) > normal_text(普通文本)
    """
    text = text.strip()
    if not text:
        return "normal_text"

    # 1. 判断是否为元件标题（最高优先级）
    for pattern in TEXT_TYPE_PATTERNS["component_title"]:
        if re.search(pattern, text, re.IGNORECASE):
            return "component_title"
    # 额外判断：是否为明确的元器件名称（从VEHICLE_COMPONENTS匹配）
    for comp in VEHICLE_COMPONENTS:
        if comp in text and len(comp) > 2:  # 避免太短的匹配（如"开关"）
            return "component_title"

    # 2. 判断是否为元件描述/表格（中优先级）
    for pattern in TEXT_TYPE_PATTERNS["component_desc"]:
        if re.search(pattern, text, re.IGNORECASE):
            return "component_desc"
    # 额外判断：包含元器件名称且带描述性内容
    for comp in VEHICLE_COMPONENTS:
        if comp in text and (":" in text or "→" in text or "=" in text):
            return "component_desc"

    # 3. 普通文本（低优先级）
    return "normal_text"


def extract_components_from_text(text):
    """从文本中提取元器件（基于VEHICLE_COMPONENTS精准匹配）"""
    components = []
    text_lower = text.lower()
    for comp in VEHICLE_COMPONENTS:
        comp_lower = comp.lower()
        if comp_lower in text_lower:
            # 记录元器件在文本中的位置和上下文
            start_idx = text_lower.index(comp_lower)
            end_idx = start_idx + len(comp_lower)
            # 取前后10个字符作为上下文
            context_start = max(0, start_idx - 10)
            context_end = min(len(text), end_idx + 10)
            context = text[context_start:context_end].replace("\n", " ")
            components.append({
                "name": comp,
                "context": context,
                "position": (start_idx, end_idx)
            })
    # 去重（同一文本中同一元器件多次出现只保留一次）
    unique_components = []
    seen_comps = set()
    for comp in components:
        if comp["name"] not in seen_comps:
            seen_comps.add(comp["name"])
            unique_components.append(comp)
    return unique_components


def process_single_page(pdf_path, page_num, pdf_filename):
    """处理单页（提取汽车元器件和分类文本）"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_num - 1 >= len(pdf.pages):
                raise Exception(f"页码{page_num}超出范围")
            page = pdf.pages[page_num - 1]
            # 提取文本（保留原始格式，包括换行）
            raw_text = page.extract_text() or ""
            # 提取页面中的表格文本（如果有表格，优先按表格处理）
            table_text = ""
            if page.extract_tables():
                for table in page.extract_tables():
                    for row in table:
                        row_text = " ".join([cell.strip() for cell in row if cell and cell.strip()])
                        if row_text:
                            table_text += row_text + "\n"

        # 合并原始文本和表格文本
        full_text = raw_text + "\n" + table_text
        # 保存页面文本（用于调试，保留原始格式）
        page_save_dir = os.path.join(INDEX_DIR, pdf_filename.replace(".pdf", ""))
        os.makedirs(page_save_dir, exist_ok=True)
        with open(os.path.join(page_save_dir, f"page_{page_num}_text.txt"), 'w', encoding='utf-8') as f:
            f.write(f"=== 第{page_num}页 ===\n{full_text}")

        # 逐行分析文本，提取页面元素（包含文本类型和元器件信息）
        page_elements = []
        lines = full_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line or len(line) < 2:  # 过滤空行和过短文本
                continue

            # 1. 判断文本类型
            text_type = get_text_type(line)
            # 2. 提取当前行中的元器件
            components = extract_components_from_text(line)
            # 3. 构建页面元素
            page_element = {
                "text": line,
                "page_num": page_num,
                "text_type": text_type,
                "components": components  # 关联当前行中的元器件
            }
            page_elements.append(page_element)

        return {
            "success": True,
            "page_elements": page_elements,
            "page_num": page_num,
            "component_count": len([c for elem in page_elements for c in elem["components"]])  # 统计当前页元器件数
        }
    except Exception as e:
        logging.error(f"第{page_num}页处理失败：{str(e)}")
        return {"success": False, "error": str(e), "page_num": page_num}


def process_single_pdf(pdf_filename):
    """处理PDF，生成索引（包含元器件关联信息）"""
    start_time = time.time()
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    if not os.path.exists(pdf_path):
        error_msg = f"文件不存在：{pdf_filename}"
        logging.error(error_msg)
        return {"status": "failed", "error": error_msg}

    # 初始化结果结构（扩展元器件统计）
    result = {
        "pdf_info": {"filename": pdf_filename, "status": "processing"},
        "total_pages": 0,
        "success_pages": 0,
        "total_components": 0,  # 总元器件数
        "page_components_count": {},  # 每页元器件数：{页码: 数量}
        "page_elements": {}  # 核心：{页码: 页面元素列表}
    }

    try:
        # 获取PDF总页数
        with pdfplumber.open(pdf_path) as pdf:
            result["total_pages"] = len(pdf.pages)

        # 逐页处理
        for page_num in range(1, result["total_pages"] + 1):
            page_result = process_single_page(pdf_path, page_num, pdf_filename)
            if page_result["success"]:
                result["success_pages"] += 1
                result["page_elements"][str(page_num)] = page_result["page_elements"]
                result["page_components_count"][str(page_num)] = page_result["component_count"]
                result["total_components"] += page_result["component_count"]
                logging.info(f"第{page_num}页处理完成：{page_result['component_count']}个元器件")

        # 保存索引文件
        index_path = os.path.join(INDEX_DIR, f"{pdf_filename.replace('.pdf', '')}.json")
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        result["pdf_info"]["status"] = "success"
        logging.info(
            f"PDF处理完成：{pdf_filename}，共{result['total_pages']}页，成功处理{result['success_pages']}页，提取{result['total_components']}个元器件")
    except Exception as e:
        result["pdf_info"]["status"] = "failed"
        result["pdf_info"]["error"] = str(e)
        logging.error(f"PDF处理失败：{str(e)}")

    return result
