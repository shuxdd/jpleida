import json
from datetime import datetime
from utils.json_utils import json_serialize, json_dumps_pretty


class TestJsonSerialize:
    """json_serialize 函数测试"""

    def test_serialize_dict(self):
        """测试序列化字典"""
        data = {"name": "测试", "value": 123}
        result = json_serialize(data)
        assert json.loads(result) == data

    def test_serialize_chinese(self):
        """测试中文不转义"""
        data = {"key": "中文内容"}
        result = json_serialize(data)
        assert "中文内容" in result

    def test_serialize_custom_indent(self):
        """测试自定义缩进"""
        data = {"a": 1}
        result = json_serialize(data, indent=4)
        assert "    " in result

    def test_serialize_datetime(self):
        """测试 datetime 序列化"""
        data = {"time": datetime(2026, 1, 1)}
        result = json_serialize(data)
        assert "2026" in result


class TestJsonDumpsPretty:
    """json_dumps_pretty 函数测试"""

    def test_pretty_output(self):
        """测试美化输出"""
        data = {"name": "test", "items": [1, 2, 3]}
        result = json_dumps_pretty(data)
        assert "\n" in result
        assert "test" in result

    def test_pretty_chinese(self):
        """测试中文美化"""
        data = {"key": "中文"}
        result = json_dumps_pretty(data)
        assert "中文" in result
