"""
种子数据脚本
============
启动 API 后运行，自动写入竞品到数据库。
前端开箱即用。

用法:
    python seed.py              # 默认写入全部竞品
    python seed.py --clear      # 清空后重新写入
    python seed.py --dry-run    # 仅预览，不写入
"""

import sys
import asyncio
import argparse

try:
    import httpx
except ImportError:
    print("请先安装 httpx: pip install httpx")
    sys.exit(1)

API_BASE = "http://localhost:8000"
SEED_USER = {"username": "admin", "password": "admin123"}

# ==================== 竞品数据 ====================

COMPETITORS = [
    # --- 企业办公/协同 ---
    {
        "name": "Notion",
        "website": "https://notion.so",
        "industry": "知识管理",
        "tags": ["生产力", "知识管理", "协作", "SaaS"],
        "notes": "All-in-one工作空间，集文档、知识库、项目管理于一体。公司Notion Labs成立于2013年，总部旧金山，估值100亿美元。",
    },
    {
        "name": "Obsidian",
        "website": "https://obsidian.md",
        "industry": "知识管理",
        "tags": ["知识管理", "笔记", "Markdown", "本地优先"],
        "notes": "基于本地Markdown文件的知识管理工具，支持双向链接和图谱视图。Dynalist Inc.出品，自筹资金，团队10-50人。",
    },
    {
        "name": "飞书文档",
        "website": "https://feishu.cn",
        "industry": "企业办公",
        "tags": ["企业协作", "办公套件", "视频会议", "即时通讯", "移动端"],
        "notes": "字节跳动出品的企业级协作办公套件，集文档、表格、视频会议、IM于一体。面向中大型企业。",
        "google_play_id": "com.ss.android.lark",
    },
    {
        "name": "钉钉",
        "website": "https://dingtalk.com",
        "industry": "企业办公",
        "tags": ["企业办公", "IM", "视频会议", "OA审批", "移动端"],
        "notes": "阿里巴巴出品的企业协同办公平台。覆盖IM、视频会议、OA审批、考勤打卡、低代码应用等。用户超6亿，企业组织超2300万。",
        "google_play_id": "com.alibaba.android.rimet",
    },
    {
        "name": "企业微信",
        "website": "https://work.weixin.qq.com",
        "industry": "企业办公",
        "tags": ["企业办公", "IM", "客户管理", "微信生态", "移动端"],
        "notes": "腾讯出品，与微信互通的企业通讯与办公工具。优势在于连接微信生态的12亿用户，客户联系和私域运营能力突出。",
        "google_play_id": "com.tencent.wework",
    },
    {
        "name": "语雀",
        "website": "https://yuque.com",
        "industry": "知识管理",
        "tags": ["知识库", "文档协作", "团队笔记", "蚂蚁集团"],
        "notes": "蚂蚁集团出品的专业知识库与文档协作平台。支持富文本、Markdown、表格、画板等，适合团队知识沉淀。",
    },
    # --- AI大模型/对话 ---
    {
        "name": "文心一言",
        "website": "https://yiyan.baidu.com",
        "industry": "AI大模型",
        "tags": ["AI大模型", "对话", "生成式AI", "百度"],
        "notes": "百度推出的大语言模型，基于文心大模型4.0。支持多模态（文本、图片、代码），深度整合百度搜索和知识图谱。",
    },
    {
        "name": "通义千问",
        "website": "https://tongyi.aliyun.com",
        "industry": "AI大模型",
        "tags": ["AI大模型", "对话", "多模态", "阿里云"],
        "notes": "阿里云出品的大语言模型，Qwen系列。支持文本、图像、音频多模态，开源了多个参数规模的模型版本。",
    },
    {
        "name": "Kimi",
        "website": "https://kimi.moonshot.cn",
        "industry": "AI大模型",
        "tags": ["AI大模型", "长文本", "对话", "月之暗面"],
        "notes": "月之暗面（Moonshot AI）出品，主打超长上下文窗口（200万字）。擅长长文档理解、多轮对话和信息检索。",
    },
    {
        "name": "智谱清言",
        "website": "https://chatglm.cn",
        "industry": "AI大模型",
        "tags": ["AI大模型", "对话", "GLM", "清华"],
        "notes": "智谱AI出品，基于GLM大模型。源自清华大学，支持对话、代码生成、知识问答，开源了ChatGLM系列。",
    },
    # --- 内容/社交平台 ---
    {
        "name": "小红书",
        "website": "https://xiaohongshu.com",
        "industry": "内容社交",
        "tags": ["社交", "内容", "种草", "生活方式"],
        "notes": "生活方式分享平台，以图文和短视频种草内容为主。月活超3亿，用户以年轻女性为主，商业化以品牌广告和电商为主。",
    },
    {
        "name": "知乎",
        "website": "https://zhihu.com",
        "industry": "内容社区",
        "tags": ["问答", "知识社区", "内容平台", "长内容"],
        "notes": "中文互联网最大的问答式知识社区。月活超1亿，以深度长内容见长。商业化包括广告、盐选会员、知+等。",
    },
    {
        "name": "B站",
        "website": "https://bilibili.com",
        "industry": "内容社区",
        "tags": ["视频", "内容社区", "二次元", "PUGC"],
        "notes": "以PUGC视频为核心的内容社区，月活超3.4亿。用户以Z世代为主，内容涵盖游戏、动画、科技、生活等。商业化包括广告、游戏、直播、电商。",
    },
    # --- 电商/SaaS工具 ---
    {
        "name": "有赞",
        "website": "https://youzan.com",
        "industry": "电商SaaS",
        "tags": ["电商SaaS", "小程序", "私域运营", "商家服务"],
        "notes": "为商家提供全渠道经营SaaS系统，支持小程序商城、会员管理、营销工具等。服务超600万商家，以私域电商为核心。",
    },
    {
        "name": "微盟",
        "website": "https://weimob.com",
        "industry": "电商SaaS",
        "tags": ["电商SaaS", "智慧零售", "营销", "企微助手"],
        "notes": "为商家提供智慧商业解决方案，覆盖电商、零售、餐饮等场景。以WOS新商业操作系统为核心，服务超300万商家。",
    },
]


async def clear_competitors(client: httpx.AsyncClient):
    """清空所有竞品（需要在调用前设置 client.headers）"""
    resp = await client.get(f"{API_BASE}/api/competitors", params={"page_size": 100})
    data = resp.json()
    competitors = data.get("data", [])
    if not competitors:
        print("  数据库已为空")
        return

    for c in competitors:
        await client.delete(f"{API_BASE}/api/competitors/{c['id']}")
    print(f"  已清空 {len(competitors)} 个竞品")


async def _ensure_user(client: httpx.AsyncClient) -> str:
    """确保默认用户存在，返回 token"""
    # 先尝试注册
    resp = await client.post(f"{API_BASE}/api/auth/register", json=SEED_USER)
    if resp.status_code == 200:
        data = resp.json()
        token = data["data"]["token"]
        print(f"  [OK] 已创建默认用户 admin")
        return token

    # 已存在则登录
    resp = await client.post(f"{API_BASE}/api/auth/login", json=SEED_USER)
    if resp.status_code == 200:
        data = resp.json()
        token = data["data"]["token"]
        print(f"  [OK] 使用已有用户 admin")
        return token

    print(f"[ERROR] 无法创建/登录用户: {resp.text}")
    sys.exit(1)


async def seed(dry_run: bool = False, clear: bool = False):
    """写入种子数据"""
    print(f"\n{'=' * 50}")
    print(f"  竞品种子数据脚本")
    print(f"  共 {len(COMPETITORS)} 个竞品")
    print(f"{'=' * 50}\n")

    if dry_run:
        print("[DRY RUN] 仅预览，不写入:\n")
        for i, c in enumerate(COMPETITORS, 1):
            print(f"  {i:2d}. {c['name']:8s} | {c['industry']:8s} | {', '.join(c['tags'][:3])}")
        return

    async with httpx.AsyncClient(timeout=10) as client:
        # 检查API是否可用
        try:
            resp = await client.get(f"{API_BASE}/health")
            resp.raise_for_status()
        except Exception as e:
            print(f"[ERROR] 无法连接 API ({API_BASE}): {e}")
            print("请先启动API: uvicorn api.app:app --reload --host 0.0.0.0 --port 8000")
            sys.exit(1)

        # 登录/注册
        print("[AUTH] 准备默认用户...")
        token = await _ensure_user(client)
        headers = {"Authorization": f"Bearer {token}"}

        # 清空已有数据
        if clear:
            print("[CLEAR] 清空已有竞品...")
            client.headers.update(headers)
            await clear_competitors(client)
            print()

        # 写入竞品
        success = 0
        skipped = 0
        for c in COMPETITORS:
            try:
                resp = await client.post(f"{API_BASE}/api/competitors", json=c, headers=headers)
                result = resp.json()
                if result.get("code") == 200:
                    print(f"  [OK] {c['name']}")
                    success += 1
                elif "已存在" in result.get("message", ""):
                    print(f"  [SKIP] {c['name']} (已存在)")
                    skipped += 1
                else:
                    print(f"  [FAIL] {c['name']}: {result.get('message', '未知错误')}")
            except Exception as e:
                print(f"  [ERROR] {c['name']}: {e}")

        print(f"\n完成: 成功 {success}, 跳过 {skipped}, 总计 {len(COMPETITORS)}")


def main():
    parser = argparse.ArgumentParser(description="竞品种子数据脚本")
    parser.add_argument("--clear", action="store_true", help="清空已有数据后重新写入")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入")
    args = parser.parse_args()

    asyncio.run(seed(dry_run=args.dry_run, clear=args.clear))


if __name__ == "__main__":
    main()
