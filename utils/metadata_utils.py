import json


def sanitize_metadata(metadata: dict) -> dict:
    """
    清洗单个元数据，确保 ChromaDB 兼容。

    处理：
    1. list -> 逗号分隔字符串
    2. dict -> JSON 字符串
    3. None -> 空字符串
    4. 其他类型保持不变

    Args:
        metadata: 原始元数据字典

    Returns:
        清洗后的元数据字典
    """
    cleaned = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            cleaned[key] = ", ".join(str(item) for item in value)
        elif isinstance(value, dict):
            cleaned[key] = json.dumps(value, ensure_ascii=False)
        elif value is None:
            cleaned[key] = ""
        else:
            cleaned[key] = value
    return cleaned


def sanitize_metadatas(metadatas: list[dict]) -> list[dict]:
    """
    批量清洗元数据。

    Args:
        metadatas: 元数据字典列表

    Returns:
        清洗后的元数据字典列表
    """
    return [sanitize_metadata(meta) for meta in metadatas]
