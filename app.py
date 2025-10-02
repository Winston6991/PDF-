import os
import json
import time
from flask import Flask, render_template, request, send_from_directory, redirect, url_for
from ocr_processor import process_single_pdf
from search_engine import search_engine
from config import *
from special_circuit_data import SPECIAL_CIRCUIT_COMPONENTS

# 初始化Flask应用
app = Flask(__name__)

# 确保目录存在
for dir_path in [PDF_DIR, INDEX_DIR, LOG_DIR]:
    os.makedirs(dir_path, exist_ok=True)


def get_pdf_list():
    """获取所有PDF文件及其状态信息（扩展元器件统计）"""
    pdf_files = []
    for filename in os.listdir(PDF_DIR):
        if filename.lower().endswith(".pdf") and not filename.startswith("."):
            # 基础信息
            pdf_path = os.path.join(PDF_DIR, filename)
            pdf_size = round(os.path.getsize(pdf_path) / (1024 * 1024), 2)

            # 索引信息
            index_path = os.path.join(INDEX_DIR, f"{filename.replace('.pdf', '')}.json")
            status = "未处理"
            total_pages = 0
            success_pages = 0
            total_components = 0  # 总元器件数
            processed_time = "未处理"

            # 对于特定PDF，直接使用预定义的元器件数据
            if filename == SPECIAL_PDF_IDENTIFIER:
                status = "已处理"
                total_pages = len(SPECIAL_CIRCUIT_COMPONENTS)
                success_pages = total_pages
                total_components = sum(len(components) for components in SPECIAL_CIRCUIT_COMPONENTS.values())
                processed_time = "系统内置"
            elif os.path.exists(index_path):
                try:
                    with open(index_path, 'r', encoding='utf-8') as f:
                        index_data = json.load(f)

                    # 状态映射
                    status_map = {
                        "processing": "已处理",
                        "success": "已处理",
                        "failed": "处理异常"
                    }
                    status = status_map.get(index_data.get("pdf_info", {}).get("status"), "未处理")
                    total_pages = index_data.get("total_pages", 0)
                    success_pages = index_data.get("success_pages", 0)
                    total_components = index_data.get("total_components", 0)
                    # 获取文件修改时间（作为处理时间）
                    processed_time = time.strftime(
                        "%Y-%m-%d %H:%M",
                        time.localtime(os.path.getmtime(index_path))
                    )
                except Exception as e:
                    app.logger.warning(f"读取索引失败 {filename}：{str(e)}")

            pdf_files.append({
                "filename": filename,
                "short_filename": filename[:30] + "..." if len(filename) > 30 else filename,  # 短文件名（适配前端显示）
                "size_mb": pdf_size,
                "status": status,
                "total_pages": total_pages,
                "success_pages": success_pages,
                "total_components": total_components,
                "processed_time": processed_time,
                "is_special": filename == SPECIAL_PDF_IDENTIFIER  # 标记是否为特定PDF
            })

    # 按处理时间降序排序（已处理的在前）
    pdf_files.sort(
        key=lambda x: (x["status"] != "已处理" and x["status"] != "已处理（预定义）", x["processed_time"]),
        reverse=True
    )
    return pdf_files


@app.route('/')
def index():
    """首页：展示所有PDF文件（显示元器件统计）"""
    pdf_list = get_pdf_list()
    return render_template('index.html', pdf_list=pdf_list)


@app.route('/upload', methods=['POST'])
def upload_pdf():
    """上传PDF文件并自动处理"""
    if 'pdf_file' not in request.files:
        return redirect(url_for('index'))

    file = request.files['pdf_file']
    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return redirect(url_for('index'))

    # 保存文件（避免文件名重复）
    filename = file.filename
    base_name, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(os.path.join(PDF_DIR, filename)):
        filename = f"{base_name}_{counter}{ext}"
        counter += 1

    file.save(os.path.join(PDF_DIR, filename))
    # 自动处理PDF（特定PDF不需要处理）
    if filename != SPECIAL_PDF_IDENTIFIER:
        process_single_pdf(filename)
    return redirect(url_for('index'))


@app.route('/process/<pdf_filename>')
def process_pdf(pdf_filename):
    """手动处理指定PDF文件（特定PDF不需要处理）"""
    if pdf_filename == SPECIAL_PDF_IDENTIFIER:
        return redirect(url_for('index'))

    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    if not os.path.exists(pdf_path) or not pdf_filename.lower().endswith(".pdf"):
        return "无效的PDF文件", 404

    # 执行处理
    process_single_pdf(pdf_filename)
    return redirect(url_for('index'))


@app.route('/view/<pdf_filename>')
def view_pdf(pdf_filename):
    """查看PDF并提供搜索功能（适配特定PDF的新搜索结果结构）"""
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    if not os.path.exists(pdf_path) and pdf_filename != SPECIAL_PDF_IDENTIFIER:
        return "无效的PDF文件", 404

    # 获取索引数据
    total_pages = 0
    total_components = 0

    # 处理特定PDF
    is_special_pdf = (pdf_filename == SPECIAL_PDF_IDENTIFIER)
    if is_special_pdf:
        total_pages = len(SPECIAL_CIRCUIT_COMPONENTS)
        total_components = sum(len(components) for components in SPECIAL_CIRCUIT_COMPONENTS.values())
    else:
        index_path = os.path.join(INDEX_DIR, f"{pdf_filename.replace('.pdf', '')}.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                total_pages = index_data.get("total_pages", 0)
                total_components = index_data.get("total_components", 0)
            except Exception as e:
                app.logger.warning(f"读取索引失败 {pdf_filename}：{str(e)}")

    # 处理搜索
    keyword = request.args.get('keyword', '').strip()
    search_result = None
    if keyword:
        search_result = search_engine.search_in_pdf(pdf_filename, keyword)

    return render_template(
        'view_pdf.html',
        pdf_filename=pdf_filename,
        short_filename=pdf_filename[:30] + "..." if len(pdf_filename) > 30 else pdf_filename,
        keyword=keyword,
        search_result=search_result,
        total_pages=total_pages,
        total_components=total_components,
        is_special_pdf=is_special_pdf
    )


@app.route('/pdfs/<pdf_filename>')
def serve_pdf(pdf_filename):
    """提供PDF文件下载/预览（支持中文文件名）"""
    return send_from_directory(PDF_DIR, pdf_filename, as_attachment=False)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
