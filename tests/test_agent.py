"""
Agent模块测试
=============

测试Agent核心功能。
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from agent.graph_state import AgentState
from agent.graph import create_analysis_graph


class TestAgentState:
    """Agent状态测试"""

    def test_state_creation(self):
        """测试状态创建"""
        state = {
            "competitors": ["Notion", "Obsidian"],
            "analysis_type": "standard",
            "dimensions": ["features", "pricing"],
            "my_product": None,
            "collection_plan": {},
            "raw_data": [],
            "extracted_info": [],
            "analysis_results": {},
            "report": "",
            "evaluation": {},
            "status": "pending",
            "errors": []
        }

        assert state["competitors"] == ["Notion", "Obsidian"]
        assert state["analysis_type"] == "standard"
        assert state["status"] == "pending"

    def test_state_raw_data_append(self):
        """测试raw_data追加语义"""
        import operator

        # 模拟LangGraph的Annotated[List[dict], operator.add]行为
        data1 = [{"competitor": "A", "data": {}}]
        data2 = [{"competitor": "B", "data": {}}]

        result = operator.add(data1, data2)
        assert len(result) == 2


class TestGraphAssembly:
    """状态图组装测试"""

    def test_graph_creation(self):
        """测试状态图创建"""
        graph = create_analysis_graph()
        assert graph is not None

    def test_graph_has_all_nodes(self):
        """测试状态图包含所有节点"""
        graph = create_analysis_graph()

        # 获取图的节点列表
        nodes = list(graph.get_graph().nodes)
        expected_nodes = {"planner", "searcher", "scraper", "extractor", "analyzer", "reporter", "evaluator", "__start__", "__end__"}

        for node in expected_nodes:
            assert node in nodes, f"缺少节点: {node}"


class TestPlannerNode:
    """规划节点测试"""

    @pytest.mark.asyncio
    async def test_default_plan_generation(self):
        """测试默认计划生成"""
        from agent.nodes.planner import _generate_default_plan

        plan = _generate_default_plan(["Notion", "Obsidian"], ["features", "pricing"])

        assert len(plan["competitors"]) == 2
        assert plan["competitors"][0]["name"] == "Notion"
        assert len(plan["competitors"][0]["search_keywords"]) > 0
        assert plan["analysis_dimensions"] == ["features", "pricing"]

    @pytest.mark.asyncio
    async def test_plan_analysis_with_mock_llm(self):
        """测试规划节点（mock LLM）"""
        from agent.nodes.planner import plan_analysis

        mock_response = Mock()
        mock_response.content = '''
        {
            "competitors": [
                {
                    "name": "Notion",
                    "search_keywords": ["Notion 官网", "Notion 定价"],
                    "target_urls": [],
                    "info_types": ["products", "pricing"]
                }
            ],
            "analysis_dimensions": ["features"]
        }
        '''

        with patch("agent.nodes.planner.create_llm") as mock_create:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = mock_response
            mock_create.return_value = mock_llm

            state = {
                "competitors": ["Notion"],
                "analysis_type": "standard",
                "dimensions": ["features"],
                "my_product": None,
                "errors": []
            }

            result = await plan_analysis(state)

            assert "collection_plan" in result
            assert result["status"] == "planning"


class TestAnalyzerNode:
    """分析节点测试"""

    def test_feature_matrix_building(self):
        """测试功能矩阵构建"""
        from agent.nodes.analyzer import _build_feature_matrix

        merged_data = {
            "Notion": {"features": ["文档管理", "知识库", "项目管理"]},
            "Obsidian": {"features": ["文档管理", "知识库", "双向链接"]}
        }

        matrix = _build_feature_matrix(merged_data)

        assert "文档管理" in matrix["features"]
        assert "双向链接" in matrix["features"]
        assert matrix["competitors"]["Notion"]["文档管理"] is True
        assert matrix["competitors"]["Obsidian"]["双向链接"] is True
        assert matrix["competitors"]["Notion"]["双向链接"] is False

    def test_pricing_comparison(self):
        """测试定价对比构建"""
        from agent.nodes.analyzer import _build_pricing_comparison

        merged_data = {
            "Notion": {"prices": [{"price": 8, "currency": "USD"}, {"price": 15, "currency": "USD"}]},
            "Obsidian": {"prices": [{"price": 50, "currency": "USD"}]}
        }

        comparison = _build_pricing_comparison(merged_data)

        assert comparison["competitors"]["Notion"]["min_price"] == 8
        assert comparison["competitors"]["Notion"]["max_price"] == 15
        assert comparison["competitors"]["Obsidian"]["min_price"] == 50

    def test_group_by_competitor(self):
        """测试按竞品分组"""
        from agent.nodes.analyzer import _group_by_competitor

        extracted = [
            {"competitor": "Notion", "extracted_info": {"company_name": "Notion"}},
            {"competitor": "Obsidian", "extracted_info": {"company_name": "Obsidian"}},
            {"competitor": "Notion", "extracted_info": {"products": []}}
        ]

        grouped = _group_by_competitor(extracted)

        assert len(grouped["Notion"]) == 2
        assert len(grouped["Obsidian"]) == 1


class TestReporterNode:
    """报告节点测试"""

    def test_header_generation(self):
        """测试报告头部生成"""
        from agent.nodes.reporter import _generate_header

        header = _generate_header(["Notion", "Obsidian"])

        assert "竞品分析报告" in header
        assert "Notion" in header
        assert "Obsidian" in header
        assert "标准" in header

    def test_simple_report_generation(self):
        """测试简化报告生成"""
        from agent.nodes.reporter import _generate_simple_report

        analysis_results = {
            "summary": "测试摘要",
            "feature_matrix": {
                "features": ["功能A", "功能B"],
                "competitors": {"Notion": {"功能A": True}}
            },
            "pricing_comparison": {
                "competitors": {
                    "Notion": {"prices": [{"price": 8, "currency": "USD"}]}
                }
            },
            "swot_analysis": {}
        }

        report = _generate_simple_report(analysis_results, ["Notion"])

        assert "竞品分析报告" in report
        assert "测试摘要" in report
        assert "功能A" in report



class TestEvaluatorNode:
    """评估节点测试"""

    def test_empty_result(self):
        """测试空评估结果"""
        from agent.nodes.evaluator import _empty_result

        result = _empty_result("test error")
        assert result["overall_score"] == 0
        assert len(result["key_improvements"]) == 0
        assert result["coverage"]["score"] == 0

    def test_generate_diagnosis(self):
        """测试诊断生成"""
        from agent.nodes.evaluator import _generate_diagnosis

        # 全低分
        poor_eval = {
            "coverage": {"score": 2, "reasoning": "low"},
            "depth": {"score": 2, "reasoning": "low"},
            "structure": {"score": 2, "reasoning": "low"},
            "actionability": {"score": 2, "reasoning": "low"},
        }
        diag = _generate_diagnosis(poor_eval)
        assert len(diag) == 4  # 4个维度都低于3
        assert all(d.startswith("[") for d in diag)

        # 全高分 — 不生成诊断
        good_eval = {
            "coverage": {"score": 5, "reasoning": "good"},
            "depth": {"score": 4, "reasoning": "good"},
            "structure": {"score": 5, "reasoning": "good"},
            "actionability": {"score": 4, "reasoning": "good"},
        }
        diag = _generate_diagnosis(good_eval)
        assert len(diag) == 0  # 全部 >= 4，不生成诊断


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
