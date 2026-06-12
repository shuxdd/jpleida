"""
华为应用市场采集器测试
======================
"""

import pytest
from unittest.mock import patch, AsyncMock, mock_open
import json
from collector.huawei_collector import HuaweiCollector


class TestHuaweiCollector:
    """华为采集器测试"""

    def test_initialization(self):
        """测试初始化"""
        collector = HuaweiCollector(key_file_path="/fake/path.json")
        assert collector.name == "huawei"
        assert collector.key_file_path == "/fake/path.json"

    def test_initialization_default_path(self):
        """测试默认路径初始化"""
        collector = HuaweiCollector()
        assert collector.name == "huawei"

    def test_parse_review_data(self):
        """测试解析评论数据"""
        collector = HuaweiCollector()

        raw_data = {
            "package_name": "com.alibaba.android.rimet",
            "source": "huawei",
            "reviews": [
                {
                    "reviewId": "r001",
                    "userName": "张三",
                    "reviewContent": "很好用的办公软件",
                    "rating": 5,
                    "lastUpdated": "2026-06-10",
                    "device": "Mate 60 Pro",
                    "reply": "",
                },
                {
                    "reviewId": "r002",
                    "userName": "李四",
                    "reviewContent": "偶尔卡顿",
                    "rating": 3,
                    "lastUpdated": "2026-06-09",
                    "device": "P60",
                    "reply": "",
                },
            ],
            "total_fetched": 2,
        }

        result = collector.parse(raw_data)

        assert result["app_name"] == "com.alibaba.android.rimet"
        assert result["store"] == "huawei"
        assert result["rating"] == 4.0
        assert result["ratings_count"] == 2
        assert len(result["reviews"]) == 2
        assert result["reviews"][0]["user"] == "张三"
        assert result["reviews"][0]["text"] == "很好用的办公软件"
        assert result["reviews"][0]["rating"] == 5

    def test_parse_empty_reviews(self):
        """测试解析空评论"""
        collector = HuaweiCollector()

        raw_data = {
            "package_name": "com.test.app",
            "source": "huawei",
            "reviews": [],
            "total_fetched": 0,
        }

        result = collector.parse(raw_data)
        assert result["rating"] == 0
        assert result["ratings_count"] == 0

    def test_parse_error_data(self):
        """测试解析错误数据"""
        collector = HuaweiCollector()
        raw_data = {"package_name": "test", "error": "auth failed", "status": "error"}
        result = collector.parse(raw_data)
        assert result["status"] == "error"

    def test_parse_review(self):
        """测试解析单条评论"""
        collector = HuaweiCollector()

        raw_review = {
            "reviewId": "r001",
            "userName": "测试用户",
            "reviewContent": "测试内容",
            "rating": 4,
            "lastUpdated": "2026-06-10",
            "device": "Mate 60",
            "reply": "感谢反馈",
        }

        result = collector._parse_review(raw_review)

        assert result["review_id"] == "r001"
        assert result["user"] == "测试用户"
        assert result["text"] == "测试内容"
        assert result["rating"] == 4
        assert result["device"] == "Mate 60"
        assert result["reply"] == "感谢反馈"

    def test_clean_removes_empty(self):
        """测试清洗去除空值"""
        collector = HuaweiCollector()
        data = {
            "app_name": "test",
            "rating": 4.0,
            "developer": None,
            "reviews": [
                {"text": "好", "rating": 5},
                {"text": "", "rating": 0},
                {"text": "一般", "rating": 3},
            ],
        }
        cleaned = collector.clean(data)
        assert cleaned["app_name"] == "test"
        assert "developer" not in cleaned
        assert len(cleaned["reviews"]) == 2

    def test_load_key_file_not_found(self):
        """测试密钥文件不存在"""
        collector = HuaweiCollector(key_file_path="/nonexistent/path.json")
        with pytest.raises(FileNotFoundError):
            collector._load_key_file()
