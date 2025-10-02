import logging
from config import *


class SynonymHandler:
    def __init__(self):
        # 汽车电气系统专用同义词词典（扩展版）
        self.BASE_SYNONYM_DICT = {
            # 电源类
            "蓄电池电源": ["电瓶电源", "蓄电池供电", "电瓶供电"],
            "ACC电源": ["附件档电源", "ACC供电", "附件电源"],
            "ON电源": ["点火档电源", "ON供电", "点火电源"],

            # 开关类
            "大灯开关": ["前照灯开关", "头灯开关"],
            "雾灯开关": ["前雾灯开关", "后雾灯开关", "雾光灯开关"],
            "制动灯开关": ["刹车灯开关", "制动开关", "刹车开关"],
            "倒车灯开关": ["倒挡灯开关", "倒车开关"],
            "车门开关": ["车门感应开关", "车门状态开关"],
            "ESC关断开关": ["ESC关闭开关", "电子稳定程序关断开关"],

            # 继电器类
            "近光灯继电器": ["近光继电器", "大灯近光继电器"],
            "远光灯继电器": ["远光继电器", "大灯远光继电器"],
            "ACC继电器": ["附件档继电器", "ACC档继电器"],
            "ON继电器": ["点火档继电器", "ON档继电器"],
            "起动继电器": ["启动继电器"],

            # 传感器类
            "气压传感器": ["气压传感装置", "压力传感器（气压）"],
            "燃油传感器": ["油量传感器", "燃油液位传感器", "油量传感装置"],
            "里程表传感器": ["车速传感器", "里程传感器"],
            "轮速传感器": ["车轮速度传感器", "车轮转速传感器"],

            # 执行器类
            "门锁电机": ["中控门锁电机", "车门锁电机"],
            "车窗电机": ["门窗电机", "车窗升降电机"],
            "举升电机": ["驾驶室举升电机", "升降电机"],
            "雨刮电机": ["刮水器电机", "雨刷电机"],

            # 线束/接插件类
            "接插件": ["连接器", "插头", "插座"],
            "线束": ["导线束", "电缆束"],

            # 陕汽轩德翼3特有元器件
            "ADR控制单元": ["ADR控制器", "ADR控制模块"],
            "ECAS控制器": ["电子控制空气悬架控制器", "空气悬架控制单元"],
            "ABS控制器": ["防抱死制动系统控制器", "防抱死系统控制单元"],
            "ESC控制器": ["电子稳定控制系统控制器", "车身稳定控制单元"]
        }
        self.logger = logging.getLogger(__name__)

    def get_synonyms(self, keyword):
        """获取关键词的所有同义词（支持模糊匹配）"""
        if not keyword:
            return []
        # 统一转为小写匹配，返回原始大小写的同义词
        lower_keyword = keyword.strip().lower()
        synonyms = []
        # 精确匹配关键词
        for key, syn_list in self.BASE_SYNONYM_DICT.items():
            if lower_keyword == key.lower():
                synonyms.extend(syn_list)
        # 模糊匹配（关键词包含在词典key中）
        for key, syn_list in self.BASE_SYNONYM_DICT.items():
            if lower_keyword in key.lower() and key not in synonyms:
                synonyms.append(key)
                synonyms.extend(syn_list)
        # 去重并返回
        return list(set(synonyms))

    def find_matched_terms(self, text, keyword):
        """查找文本中与关键词及其同义词匹配的术语"""
        if not text or not keyword:
            return []
        matched_terms = []
        # 检查关键词本身
        if keyword.lower() in text.lower():
            matched_terms.append(keyword)
        # 检查所有同义词
        for synonym in self.get_synonyms(keyword):
            if synonym.lower() in text.lower() and synonym not in matched_terms:
                matched_terms.append(synonym)
        return matched_terms
