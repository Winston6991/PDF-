import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# PDF文件存放目录
PDF_DIR = os.path.join(BASE_DIR, "static", "pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

# 索引文件存放目录
INDEX_DIR = os.path.join(BASE_DIR, "static", "indexes")
os.makedirs(INDEX_DIR, exist_ok=True)

# 日志目录
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 日志文件路径
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# 陕汽轩德翼3电路图特定PDF文件名标识
SPECIAL_PDF_IDENTIFIER = "陕汽_轩德翼3_整车电路图【玉柴ECI-CFV天然气系统_Econtrol120针ECU】【国六】分页版_可搜索.pdf"
