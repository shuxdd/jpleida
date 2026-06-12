import json
from utils.metadata_utils import sanitize_metadata, sanitize_metadatas


class TestSanitizeMetadata:
    """sanitize_metadata 函数测试"""

    def test_list_to_string(self):
        """测试 list 转字符串"""
        meta = {"tags": ["a", "b", "c"]}
        result = sanitize_metadata(meta)
        assert result["tags"] == "a, b, c"

    def test_dict_to_string(self):
        """测试 dict 转 JSON 字符串"""
        meta = {"info": {"key": "value"}}
        result = sanitize_metadata(meta)
        assert json.loads(result["info"]) == {"key": "value"}

    def test_none_to_empty(self):
        """测试 None 转空字符串"""
        meta = {"field": None}
        result = sanitize_metadata(meta)
        assert result["field"] == ""

    def test_string_unchanged(self):
        """测试字符串保持不变"""
        meta = {"name": "test"}
        result = sanitize_metadata(meta)
        assert result["name"] == "test"

    def test_number_unchanged(self):
        """测试数字保持不变"""
        meta = {"count": 42}
        result = sanitize_metadata(meta)
        assert result["count"] == 42


class TestSanitizeMetadatas:
    """sanitize_metadatas 函数测试"""

    def test_multiple_metadatas(self):
        """测试多个元数据"""
        metadatas = [
            {"tags": ["a", "b"]},
            {"info": {"key": "value"}}
        ]
        result = sanitize_metadatas(metadatas)
        assert len(result) == 2
        assert result[0]["tags"] == "a, b"

    def test_empty_list(self):
        """测试空列表"""
        result = sanitize_metadatas([])
        assert result == []
