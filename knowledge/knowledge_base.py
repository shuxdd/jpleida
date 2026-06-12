"""
知识库管理
==========

整合向量数据库和Embedding服务，提供统一的知识库管理接口。
"""

from typing import List, Dict, Any, Optional
import logging
import json

from .vector_store import VectorStore
from .embeddings import EmbeddingService, create_embedding_service
from utils.text_utils import split_text as utils_split_text

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """知识库管理"""

    def __init__(
        self,
        persist_dir: str = "./data/chroma",
        embedding_service: Optional[EmbeddingService] = None,
        embedding_type: str = "openai",
        **embedding_kwargs
    ):
        """
        初始化知识库

        Args:
            persist_dir: 向量数据库持久化目录
            embedding_service: Embedding服务实例
            embedding_type: Embedding服务类型
            **embedding_kwargs: Embedding服务参数
        """
        self.vector_store = VectorStore(persist_dir=persist_dir)

        if embedding_service:
            self.embedding_service = embedding_service
        else:
            self.embedding_service = create_embedding_service(
                service_type=embedding_type,
                **embedding_kwargs
            )

        logger.info("知识库初始化完成")

    def add_competitor(
        self,
        competitor_id: str,
        competitor_data: Dict[str, Any]
    ):
        """
        添加竞品信息到知识库

        Args:
            competitor_id: 竞品ID
            competitor_data: 竞品数据
        """
        # 构建文档文本
        documents = []
        metadatas = []

        # 公司基本信息
        company_info = competitor_data.get("company_info", {})
        company_text = f"""
公司名称: {company_info.get('company_name', '')}
成立时间: {company_info.get('founded', '')}
所在地: {company_info.get('location', '')}
融资情况: {company_info.get('funding', '')}
员工规模: {company_info.get('employees', '')}
目标市场: {competitor_data.get('target_market', '')}
差异化优势: {', '.join(competitor_data.get('key_differentiators', []))}
""".strip()

        documents.append(company_text)
        metadatas.append({
            "competitor_id": competitor_id,
            "type": "company_info",
            "source": "manual"
        })

        # 产品信息
        for product in competitor_data.get("products", []):
            product_text = f"""
产品名称: {product.get('name', '')}
产品描述: {product.get('description', '')}
功能特性: {', '.join(product.get('features', []))}
""".strip()

            if product.get("pricing"):
                pricing = product["pricing"]
                pricing_text = f"""
定价模式: {pricing.get('model', '')}
定价层级: {json.dumps(pricing.get('tiers', []), ensure_ascii=False)}
""".strip()
                product_text += "\n" + pricing_text

            documents.append(product_text)
            metadatas.append({
                "competitor_id": competitor_id,
                "type": "product",
                "product_name": product.get("name", ""),
                "source": "manual"
            })

        # 添加到向量数据库
        if documents:
            self.vector_store.add_documents(
                collection_name="competitors",
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"添加竞品 {competitor_id} 到知识库，共 {len(documents)} 个文档")

    def add_web_content(
        self,
        competitor_id: str,
        url: str,
        content: str,
        content_type: str = "web_page"
    ):
        """
        添加网页内容到知识库

        Args:
            competitor_id: 竞品ID
            url: 网页URL
            content: 网页内容
            content_type: 内容类型
        """
        # 分割长文本
        chunks = self._split_text(content, max_chunk_size=1000, overlap=100)

        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({
                "competitor_id": competitor_id,
                "type": content_type,
                "url": url,
                "chunk_index": i,
                "source": "web_scrape"
            })

        if documents:
            self.vector_store.add_documents(
                collection_name="competitors",
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"添加网页内容到知识库，URL: {url}, 分块数: {len(documents)}")

    def add_user_review(
        self,
        competitor_id: str,
        review_content: str,
        rating: float,
        source: str,
        review_id: Optional[str] = None
    ):
        """
        添加用户评价到知识库

        Args:
            competitor_id: 竞品ID
            review_content: 评价内容
            rating: 评分
            source: 评价来源
            review_id: 评价ID
        """
        metadata = {
            "competitor_id": competitor_id,
            "type": "user_review",
            "rating": rating,
            "source": source
        }

        if review_id:
            metadata["review_id"] = review_id

        self.vector_store.add_documents(
            collection_name="reviews",
            documents=[review_content],
            metadatas=[metadata]
        )
        logger.info(f"添加用户评价到知识库，竞品: {competitor_id}, 评分: {rating}")

    def search_competitors(
        self,
        query: str,
        competitor_id: Optional[str] = None,
        content_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        搜索竞品信息

        Args:
            query: 查询文本
            competitor_id: 竞品ID过滤
            content_type: 内容类型过滤
            top_k: 返回结果数量

        Returns:
            搜索结果列表
        """
        where = {}
        if competitor_id:
            where["competitor_id"] = competitor_id
        if content_type:
            where["type"] = content_type

        return self.vector_store.search(
            query=query,
            collection_name="competitors",
            top_k=top_k,
            where=where if where else None
        )

    def search_reviews(
        self,
        query: str,
        competitor_id: Optional[str] = None,
        min_rating: Optional[float] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索用户评价

        Args:
            query: 查询文本
            competitor_id: 竞品ID过滤
            min_rating: 最低评分过滤
            top_k: 返回结果数量

        Returns:
            搜索结果列表
        """
        where = {}
        if competitor_id:
            where["competitor_id"] = competitor_id
        if min_rating is not None:
            where["rating"] = {"$gte": min_rating}

        return self.vector_store.search(
            query=query,
            collection_name="reviews",
            top_k=top_k,
            where=where if where else None
        )

    def get_competitor_context(
        self,
        competitor_id: str,
        query: str,
        max_tokens: int = 3000
    ) -> str:
        """
        获取竞品上下文信息（用于RAG）

        Args:
            competitor_id: 竞品ID
            query: 查询文本
            max_tokens: 最大token数

        Returns:
            上下文文本
        """
        results = self.search_competitors(
            query=query,
            competitor_id=competitor_id,
            top_k=10
        )

        # 拼接上下文
        context_parts = []
        current_length = 0

        for result in results:
            doc = result["document"]
            if current_length + len(doc) > max_tokens:
                break
            context_parts.append(doc)
            current_length += len(doc)

        return "\n\n---\n\n".join(context_parts)

    def get_multi_competitor_context(
        self,
        competitor_ids: List[str],
        query: str,
        max_tokens: int = 5000
    ) -> Dict[str, str]:
        """
        获取多个竞品的上下文信息

        Args:
            competitor_ids: 竞品ID列表
            query: 查询文本
            max_tokens: 每个竞品的最大token数

        Returns:
            竞品ID到上下文的映射
        """
        contexts = {}
        for competitor_id in competitor_ids:
            context = self.get_competitor_context(
                competitor_id=competitor_id,
                query=query,
                max_tokens=max_tokens // len(competitor_ids)
            )
            contexts[competitor_id] = context

        return contexts

    def delete_competitor(self, competitor_id: str):
        """
        删除竞品信息

        Args:
            competitor_id: 竞品ID
        """
        # 获取该竞品的所有文档
        results = self.vector_store.search(
            query="",
            collection_name="competitors",
            top_k=1000,
            where={"competitor_id": competitor_id}
        )

        if results:
            ids = [r["id"] for r in results if r.get("id")]
            if ids:
                self.vector_store.delete_documents(
                    collection_name="competitors",
                    ids=ids
                )
                logger.info(f"删除竞品 {competitor_id} 的 {len(ids)} 个文档")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Returns:
            统计信息
        """
        collections = self.vector_store.list_collections()
        stats = {}

        for collection_name in collections:
            stats[collection_name] = self.vector_store.get_collection_stats(collection_name)

        return stats

    def _split_text(
        self,
        text: str,
        max_chunk_size: int = 1000,
        overlap: int = 100
    ) -> List[str]:
        """
        分割文本

        Args:
            text: 原始文本
            max_chunk_size: 最大分块大小
            overlap: 重叠大小

        Returns:
            分块列表
        """
        return utils_split_text(text, chunk_size=max_chunk_size, overlap=overlap)

    def clear(self):
        """清空知识库"""
        for collection_name in self.vector_store.list_collections():
            self.vector_store.clear_collection(collection_name)
        logger.info("知识库已清空")
