import json


def json_serialize(obj: any, indent: int = 2) -> str:
    """
    JSON 序列化，处理中文和特殊类型。

    Args:
        obj: 要序列化的对象
        indent: 缩进空格数

    Returns:
        JSON 字符串
    """
    return json.dumps(obj, ensure_ascii=False, indent=indent, default=str)


def json_dumps_pretty(obj: any) -> str:
    """
    美化 JSON 输出。

    Args:
        obj: 要序列化的对象

    Returns:
        美化后的 JSON 字符串
    """
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
