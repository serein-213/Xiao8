from langchain_chroma import Chroma
from typing import List
from langchain_core.documents import Document
from datetime import datetime
from memory.recent import CompressedRecentHistoryManager
from config import SEMANTIC_STORE, SEMANTIC_MODEL, OPENROUTER_API_KEY, OPENROUTER_URL, RERANKER_MODEL, NAME_MAPPING
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from config.prompts_sys import semantic_manager_prompt
import json

class SemanticMemory:
    def __init__(self, recent_history_manager: CompressedRecentHistoryManager, persist_directory = SEMANTIC_STORE):
        self.original_memory = {}
        self.compressed_memory = {}
        for i in persist_directory:
            self.original_memory[i] = SemanticMemoryOriginal(persist_directory, i)
            self.compressed_memory[i] = SemanticMemoryCompressed(persist_directory, i, recent_history_manager)
        self.reranker = ChatOpenAI(model=RERANKER_MODEL, base_url=OPENROUTER_URL, api_key=OPENROUTER_API_KEY, temperature=0.1)

    def store_conversation(self, event_id, messages, lanlan_name):
        self.original_memory[lanlan_name].store_conversation(event_id, messages)
        self.compressed_memory[lanlan_name].store_compressed_summary(event_id, messages)

    def hybrid_search(self, query, lanlan_name, with_rerank=True, k=10):
        # 从原始和压缩记忆中获取结果
        original_results = self.original_memory[lanlan_name].retrieve_by_query(query, k)
        compressed_results = self.compressed_memory[lanlan_name].retrieve_by_query(query, k)
        combined = original_results + compressed_results

        if with_rerank:
            return self.rerank_results(query, combined)
        else:
            return combined

    def query(self, query, lanlan_name):
        results_text = "\n".join([
            f"记忆片段{i} | \n{doc.page_content}\n"
            for i, doc in enumerate(self.hybrid_search(query, lanlan_name))
        ])
        return f"""======{lanlan_name}尝试回忆=====\n{query}\n\n====={lanlan_name}的相关记忆=====\n{results_text}"""

    def rerank_results(self, query, results: List[Document], k=5) -> List[Document]:
        # 使用LLM重新排序结果
        results_text = "\n\n".join([
            f"记忆片段 {i + 1}:\n{doc.page_content}"
            for i, doc in enumerate(results)
        ])

        prompt = semantic_manager_prompt % (query, results_text, k)
        retries = 0
        while retries < 3:
            try:
                response = self.reranker.invoke(prompt)
            except Exception as e:
                retries += 1
                print('Rerank query失败', e)
                continue

            try:
                # 解析排序后的文档编号
                reranked_indices = json.loads(response.content)
                # 按新顺序排序结果
                reranked_results = [results[idx] for idx in reranked_indices[:k] if 0 <= idx < len(results)]
                return reranked_results
            except Exception as e:
                retries += 1
                print('Rerank结果解析失败', e)
        return []


class SemanticMemoryOriginal:
    def __init__(self, persist_directory, lanlan_name):
        self.embeddings = OpenAIEmbeddings(base_url=OPENROUTER_URL, model=SEMANTIC_MODEL, api_key=OPENROUTER_API_KEY)
        self.vectorstore = Chroma(
            collection_name="Origin",
            persist_directory=persist_directory[lanlan_name],
            embedding_function=self.embeddings
        )
        self.lanlan_name = lanlan_name

    def store_conversation(self, event_id, messages):
        # 将对话转换为文本
        texts = []
        metadatas = []
        name_mapping = NAME_MAPPING.copy()
        name_mapping['ai'] = self.lanlan_name

        for message in messages:
            texts.append(f'{name_mapping[message.type]} | {"\n".join(i.get("text", "|" +i["type"]+ "|") for i in message.content)}\n')
            metadatas.append({
                "event_id": event_id,
                "role": message.type,
                "year": str(datetime.now().year),
                "month": "%02d" % (datetime.now().month),
                "day": "%02d" % (datetime.now().day),
                "weekday": "%02d" % (datetime.now().weekday()),
                "hour": "%02d" % (datetime.now().hour),
                "minute": "%02d" % (datetime.now().minute),
                "timestamp": datetime.now().isoformat()
            })

        # 存储到向量数据库
        self.vectorstore.add_texts(texts=texts, metadatas=metadatas)

    def retrieve_by_query(self, query, k=10):
        # 在原始对话上进行精确语义搜索
        return self.vectorstore.similarity_search(query, k=k)


class SemanticMemoryCompressed:
    def __init__(self, persist_directory, lanlan_name, recent_history_manager: CompressedRecentHistoryManager):
        self.lanlan_name = lanlan_name
        self.embeddings = OpenAIEmbeddings(base_url=OPENROUTER_URL, model=SEMANTIC_MODEL, api_key=OPENROUTER_API_KEY)
        self.vectorstore = Chroma(
            collection_name="Compressed",
            persist_directory=persist_directory[lanlan_name],
            embedding_function=self.embeddings
        )
        self.recent_history_manager = recent_history_manager

    def store_compressed_summary(self, event_id, messages):
        # 存储压缩摘要的嵌入
        _, summary = self.recent_history_manager.compress_history(messages, self.lanlan_name)
        if not summary:
            return
        self.vectorstore.add_texts(
            texts=[summary],
            metadatas=[{
                "event_id": event_id,
                "role": "SYSTEM_SUMMARY",
                "year": str(datetime.now().year),
                "month": "%02d" % (datetime.now().month),
                "day": "%02d" % (datetime.now().day),
                "weekday": "%02d" % (datetime.now().weekday()),
                "hour": "%02d" % (datetime.now().hour),
                "minute": "%02d" % (datetime.now().minute),
                "timestamp": datetime.now().isoformat()
            }]
        )

    def retrieve_by_query(self, query, k=10):
        # 在压缩摘要上进行语义搜索
        return self.vectorstore.similarity_search(query, k=k)