"""
Distilled TPS/Lean Knowledge - AR (Arabic)

Auto-generated placeholder module.
Contains foundational TPS principles translated to Arabic.
"""

from typing import Dict, List, Any, Optional


class TPSLeanKnowledgeAR:
    """
    TPS/Lean Manufacturing Knowledge for AR language.
    
    This class contains principles distilled from manufacturing and
    management books, encoded directly for fast reasoning without RAG.
    """
    
    LANGUAGE = "ar"
    
    # Foundational TPS principles in Arabic
    PRINCIPLES = [
        {
            "id": "ar_tps_001",
            "principle": "الإفراط في الإنتاج هو أصل كل الهدر - يجب إنتاج ما يحتاجه العميل فقط",
            "domain": "tps_lean",
            "keywords": ["الإفراط", "الإنتاج", "الهدر", "مودا"],
            "waste_categories": ["overproduction"],
            "a3_phases": ["root_cause", "countermeasures"],
            "countermeasures": ["تطبيق نظام كانبان", "تقليل حجم الدفعات"],
            "source_books": ["نظام إنتاج تويوتا - تايتشي أونو"]
        },
        {
            "id": "ar_tps_002",
            "principle": "كايزن: التحسين المستمر من خلال تغييرات صغيرة يومية",
            "domain": "tps_lean",
            "keywords": ["كايزن", "التحسين", "المستمر"],
            "waste_categories": ["general"],
            "a3_phases": ["countermeasures", "follow_up"],
            "countermeasures": ["عقد اجتماعات كايزن يومية", "تشجيع اقتراحات الموظفين"],
            "source_books": ["كايزن - ماساكي إيماي"]
        },
        {
            "id": "ar_tps_003",
            "principle": "جيمبا: الحقيقة موجودة في موقع العمل الفعلي",
            "domain": "tps_lean",
            "keywords": ["جيمبا", "موقع", "العمل"],
            "waste_categories": ["general"],
            "a3_phases": ["current_condition", "root_cause"],
            "countermeasures": ["زيارة الجيمبا يومياً", "مراقبة العمل الفعلي"],
            "source_books": ["جيمبا كايزن - ماساكي إيماي"]
        },
        {
            "id": "ar_tps_004",
            "principle": "العمل المعياري هو الأساس لكل تحسين",
            "domain": "tps_lean",
            "keywords": ["العمل", "المعياري", "التحسين"],
            "waste_categories": ["general"],
            "a3_phases": ["current_condition", "follow_up"],
            "countermeasures": ["توثيق أفضل الممارسات", "تدريب الفريق على الإجراءات المعيارية"],
            "source_books": ["إدارة مكان العمل - تايتشي أونو"]
        },
        {
            "id": "ar_tps_005",
            "principle": "جيدوكا: الجودة في المصدر - توقف عند اكتشاف أي خلل",
            "domain": "quality",
            "keywords": ["جيدوكا", "الجودة", "المصدر"],
            "waste_categories": ["defects"],
            "a3_phases": ["countermeasures"],
            "countermeasures": ["تمكين العمال من إيقاف الخط", "حل المشاكل فوراً"],
            "source_books": ["نظام إنتاج تويوتا"]
        },
        {
            "id": "ar_quality_001",
            "principle": "الجودة ليست فحصاً - بل هي بناء الجودة في العملية",
            "domain": "quality",
            "keywords": ["الجودة", "الفحص", "العملية"],
            "waste_categories": ["defects"],
            "a3_phases": ["countermeasures"],
            "countermeasures": ["تطبيق بوكا يوكي", "الفحص في المصدر"],
            "source_books": ["صفر عيوب - شيجيو شينجو"]
        },
        {
            "id": "ar_mgmt_001",
            "principle": "القيادة تعني تطوير الآخرين وليس إصدار الأوامر",
            "domain": "management",
            "keywords": ["القيادة", "التطوير", "التمكين"],
            "waste_categories": ["skills"],
            "a3_phases": ["countermeasures"],
            "countermeasures": ["التدريب والتوجيه", "تفويض السلطة مع المسؤولية"],
            "source_books": ["طريقة تويوتا - جيفري ليكر"]
        },
        {
            "id": "ar_psych_001",
            "principle": "الدافع الحقيقي يأتي من الاستقلالية والإتقان والهدف",
            "domain": "psychology",
            "keywords": ["الدافع", "الاستقلالية", "الإتقان"],
            "waste_categories": ["skills"],
            "a3_phases": ["countermeasures"],
            "countermeasures": ["منح الموظفين حرية اتخاذ القرار", "توفير فرص التعلم"],
            "source_books": ["الدافع - دانيال بينك"]
        },
        {
            "id": "ar_logistics_001",
            "principle": "المخزون يخفي المشاكل - قلل المخزون لكشف المشاكل الحقيقية",
            "domain": "logistics",
            "keywords": ["المخزون", "المشاكل", "التخفيض"],
            "waste_categories": ["inventory"],
            "a3_phases": ["root_cause"],
            "countermeasures": ["تقليل مستوى المخزون تدريجياً", "حل المشاكل المكتشفة"],
            "source_books": ["الهدف - إلياهو جولدرات"]
        },
        {
            "id": "ar_accounting_001",
            "principle": "التكلفة الحقيقية تشمل جميع أنواع الهدر المخفية",
            "domain": "accounting",
            "keywords": ["التكلفة", "الهدر", "المحاسبة"],
            "waste_categories": ["general"],
            "a3_phases": ["current_condition"],
            "countermeasures": ["حساب تكلفة الهدر", "تتبع مؤشرات الأداء"],
            "source_books": ["محاسبة الإنتاجية"]
        }
    ]
    
    @classmethod
    def get_principles(cls) -> List[Dict[str, Any]]:
        """Get all principles."""
        return cls.PRINCIPLES
    
    @classmethod
    def get_by_domain(cls, domain: str) -> List[Dict[str, Any]]:
        """Get principles for a specific domain."""
        return [p for p in cls.PRINCIPLES if p["domain"] == domain]
    
    @classmethod
    def get_by_keyword(cls, keyword: str) -> List[Dict[str, Any]]:
        """Get principles matching a keyword."""
        keyword_lower = keyword.lower()
        return [
            p for p in cls.PRINCIPLES
            if any(keyword_lower in str(kw).lower() for kw in p["keywords"])  # type: ignore[union-attr]
            or keyword_lower in str(p["principle"]).lower()
        ]
    
    @classmethod
    def get_by_waste_category(cls, waste: str) -> List[Dict[str, Any]]:
        """Get principles related to a waste category."""
        return [p for p in cls.PRINCIPLES if waste in p["waste_categories"]]
    
    @classmethod
    def get_by_a3_phase(cls, phase: str) -> List[Dict[str, Any]]:
        """Get principles relevant to an A3 phase."""
        return [p for p in cls.PRINCIPLES if phase in p["a3_phases"]]
    
    @classmethod
    def reason(cls, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform reasoning on a query.
        
        Returns relevant principles with confidence scores.
        """
        query_words = set(query.lower().split())
        results = []
        
        for principle in cls.PRINCIPLES:
            # Calculate relevance score
            principle_words = set(principle["principle"].lower().split())
            keyword_words = set(str(kw).lower() for kw in principle["keywords"])
            
            # Word overlap with principle
            p_overlap = len(query_words & principle_words) / max(1, len(query_words))
            
            # Keyword match
            k_overlap = len(query_words & keyword_words) / max(1, len(keyword_words))
            
            score = (p_overlap * 0.7) + (k_overlap * 0.3)
            
            if score > 0.1:
                results.append({
                    "principle": principle,
                    "relevance_score": score,
                    "match_type": "semantic" if p_overlap > k_overlap else "keyword"
                })
        
        # Sort by relevance and return top results
        results.sort(key=lambda x: x["relevance_score"], reverse=True)  # type: ignore[arg-type, return-value]
        return results[:max_results]
