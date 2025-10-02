import os
import re
import json
import logging
from config import *
from synonym_handler import SynonymHandler
from special_circuit_data import SPECIAL_COMPONENT_TO_PAGES, SPECIAL_CIRCUIT_COMPONENTS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "search.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)


class SearchEngine:
    def __init__(self):
        self.synonym_handler = SynonymHandler()
        # 相关度权重配置（按需求定义：标题 > 描述 > 普通文本）
        self.relevance_weights = {
            "component_title": 3,  # 元件标题：权重3（最高）
            "component_desc": 2,  # 元件描述/表格：权重2（中）
            "normal_text": 1  # 普通文本：权重1（低）
        }
        # 额外加分项（精准匹配元器件名称）
        self.exact_match_bonus = 1.5

    def _calculate_relevance(self, text_type, is_exact_component_match):
        """计算相关度分数"""
        base_weight = self.relevance_weights.get(text_type, 1)
        # 精准匹配元器件名称额外加分
        if is_exact_component_match:
            base_weight *= self.exact_match_bonus
        return round(base_weight, 1)

    def _search_special_pdf(self, keyword):
        """搜索特定PDF（陕汽轩德翼3电路图）的处理逻辑"""
        if not keyword:
            return {"results": [], "total": 0, "search_terms": []}

        keyword = keyword.strip()
        search_terms = [keyword] + self.synonym_handler.get_synonyms(keyword)
        search_terms = [term.strip() for term in search_terms if term.strip()]
        search_terms = list(set(search_terms))  # 去重

        results = []
        # 检查每个搜索词是否在特定元器件列表中
        for term in search_terms:
            # 精确匹配
            if term in SPECIAL_COMPONENT_TO_PAGES:
                pages = SPECIAL_COMPONENT_TO_PAGES[term]
                for page_num in pages:
                    # 查找该页上的所有元器件作为上下文
                    page_components = SPECIAL_CIRCUIT_COMPONENTS.get(page_num, [])
                    context = ", ".join(page_components[:5])  # 取前5个作为上下文
                    if len(page_components) > 5:
                        context += ", ..."

                    results.append({
                        "page_num": page_num,
                        "text_type": "component_title",  # 特定PDF全部视为标题级匹配
                        "relevance_score": 4.0,  # 特定PDF匹配分数更高
                        "matched_term": term,
                        "highlighted_text": f"<mark>{term}</mark> - 该页还包含: {context}",
                        "full_text": f"{term} 位于第{page_num}页",
                        "components_in_text": page_components
                    })

            # 模糊匹配（术语包含在元器件名称中）
            else:
                for component, pages in SPECIAL_COMPONENT_TO_PAGES.items():
                    if term in component:
                        for page_num in pages:
                            page_components = SPECIAL_CIRCUIT_COMPONENTS.get(page_num, [])
                            context = ", ".join(page_components[:5])
                            if len(page_components) > 5:
                                context += ", ..."

                            results.append({
                                "page_num": page_num,
                                "text_type": "component_desc",
                                "relevance_score": 3.0,
                                "matched_term": term,
                                "highlighted_text": f"{component}（包含<mark>{term}</mark>） - 该页还包含: {context}",
                                "full_text": f"{component} 位于第{page_num}页",
                                "components_in_text": page_components
                            })

        # 去重（同一页面同一术语的匹配只保留一个）
        seen = set()
        unique_results = []
        for result in results:
            key = (result["page_num"], result["matched_term"], result["full_text"])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)

        # 排序：按相关度降序，再按页码升序
        unique_results.sort(key=lambda x: (-x["relevance_score"], x["page_num"]))

        return {
            "results": unique_results,
            "total": len(unique_results),
            "search_terms": search_terms
        }

    def search_in_pdf(self, pdf_filename, keyword):
        """搜索指定PDF中的关键词（包含特定PDF的特殊处理）"""
        # 检查是否为特定PDF（陕汽轩德翼3电路图）
        if pdf_filename == SPECIAL_PDF_IDENTIFIER:
            return self._search_special_pdf(keyword)

        # 普通PDF的搜索逻辑
        if not keyword or not pdf_filename:
            return {"results": [], "total": 0}

        # 1. 加载PDF索引文件
        index_path = os.path.join(INDEX_DIR, f"{pdf_filename.replace('.pdf', '')}.json")
        if not os.path.exists(index_path):
            logging.warning(f"未找到索引文件：{index_path}")
            return {"results": [], "total": 0}

        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                pdf_index = json.load(f)
        except Exception as e:
            logging.error(f"加载索引失败：{str(e)}")
            return {"results": [], "total": 0}

        # 2. 处理关键词（包含同义词）
        keyword = keyword.strip()
        all_search_terms = [keyword] + self.synonym_handler.get_synonyms(keyword)
        all_search_terms = [term.strip().lower() for term in all_search_terms if term.strip()]
        all_search_terms = list(set(all_search_terms))  # 去重
        logging.info(f"搜索关键词及同义词：{all_search_terms}")

        # 3. 遍历页面元素搜索匹配
        search_results = []
        page_elements = pdf_index.get("page_elements", {})

        for page_num_str, elements in page_elements.items():
            page_num = int(page_num_str)
            for elem in elements:
                elem_text = elem["text"].strip()
                elem_text_lower = elem_text.lower()
                text_type = elem["text_type"]
                elem_components = elem.get("components", [])

                # 检查当前元素是否匹配任意搜索词
                for term in all_search_terms:
                    if term in elem_text_lower:
                        # 判断是否为精准元器件匹配
                        is_exact_component = any(comp["name"].lower() == term for comp in elem_components)
                        # 计算相关度
                        relevance_score = self._calculate_relevance(text_type, is_exact_component)
                        # 提取匹配上下文（高亮关键词）
                        highlighted_text = elem_text.replace(
                            term, f"<mark>{term}</mark>"
                        ) if term in elem_text else elem_text
                        # 处理同义词高亮（如果原文本包含同义词）
                        for syn in all_search_terms:
                            if syn != term and syn in elem_text_lower:
                                highlighted_text = highlighted_text.replace(
                                    syn, f"<mark>{syn}</mark>"
                                )

                        # 添加搜索结果
                        search_results.append({
                            "page_num": page_num,
                            "text_type": text_type,
                            "relevance_score": relevance_score,
                            "matched_term": term,  # 匹配的关键词/同义词
                            "highlighted_text": highlighted_text,  # 高亮后的文本
                            "full_text": elem_text,  # 完整文本
                            "components_in_text": [comp["name"] for comp in elem_components]  # 文本中的元器件列表
                        })
                        break  # 一个元素匹配一个关键词即可，避免重复

        # 4. 排序：先按相关度降序，再按页码升序
        search_results.sort(
            key=lambda x: (-x["relevance_score"], x["page_num"])
        )

        # 5. 结果去重（同一页面同一关键词的重复匹配只保留最高相关度）
        unique_results = []
        seen_page_term = set()
        for result in search_results:
            key = (result["page_num"], result["matched_term"])
            if key not in seen_page_term:
                seen_page_term.add(key)
                unique_results.append(result)

        return {
            "results": unique_results,
            "total": len(unique_results),
            "search_terms": all_search_terms  # 返回使用的搜索词（用于前端显示）
        }

    def search_all_pdfs(self, keyword):
        """搜索所有PDF"""
        if not keyword:
            return {}

        results = {}
        for filename in os.listdir(INDEX_DIR):
            if filename.endswith(".json") and not filename.startswith("."):
                pdf_filename = filename.replace(".json", ".pdf")
                pdf_result = self.search_in_pdf(pdf_filename, keyword)
                if pdf_result["total"] > 0:
                    results[pdf_filename] = pdf_result

        return results


# 全局实例
search_engine = SearchEngine()
