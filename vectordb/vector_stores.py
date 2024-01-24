import abc
import chromadb
import os
import weaviate
from llama_index import (
    VectorStoreIndex,
    StorageContext,
    ServiceContext,
    set_global_service_context,
)
from llama_index.llms import (
    OpenAI,
    HuggingFaceLLM
)
from llama_index.embeddings import (
    HuggingFaceEmbedding,
    OpenAIEmbedding
)
from llama_index.vector_stores import (
    WeaviateVectorStore,
    ChromaVectorStore
)

from utils.logging import log, now, get_elapsed
from utils import get_model_config

def set_rag_context():
    rag_llm = get_model_config().rag.llm
    rag_embed_model = get_model_config().get_rag_embed_model()

    if rag_llm.hub == "huggingface":
        llm = HuggingFaceLLM(tokenizer_name=rag_llm.model,model_name=rag_llm.model)
        llm_model_key = "model_name"
    elif rag_llm.hub == "openai":
        llm = OpenAI(tokenizer_name=rag_llm.model, model_name=rag_llm.model)
        llm_model_key = "model"
    else:
        llm = None

    if rag_embed_model.hub == "huggingface":
        embed_model = HuggingFaceEmbedding(model_name=rag_embed_model.model)
    elif rag_embed_model.hub == "openai":
        embed_model = OpenAIEmbedding(model_name=rag_embed_model.model)
    else:
        embed_model = 'local'

    service_context = ServiceContext.from_defaults(llm=llm, embed_model=embed_model)

    # if llm is not None and embed_model is not None:        
    #     service_context = ServiceContext.from_defaults(llm=llm, embed_model=embed_model)
    # else:
    #     service_context = ServiceContext.from_defaults()

    set_global_service_context(service_context)

    service_context_dict = service_context.to_dict()

    llm_desc = f'{service_context_dict["llm"].get("class_name")}:{service_context_dict["llm"].get(llm_model_key)}'
    embedding_desc = f'{service_context_dict["embed_model"].get("class_name")}:{service_context_dict["embed_model"].get("model_name")}'

    log(f'llm: {llm_desc}')
    log(f'embed_model: {embedding_desc}')
    log(f'service context: {service_context_dict}')

class LLamaIndex:

    @staticmethod
    def process_query(prompt):
        set_rag_context()
        start = now()
        vdbs_processed = []
        responses = []
        vdbs = get_model_config().rag.vector_stores
        if 'weaviate' in vdbs:
            response = Weaviate.process_query(prompt)
            vdbs_processed.append('weaviate')
            responses.append(response)
        if 'chromadb' in vdbs:
            response = ChromaDB.process_query(prompt)
            vdbs_processed.append('chromadb')
            responses.append(response)
        elapsed = get_elapsed(start)
        return {
            'prompt': prompt,
            'vdbs_processed': vdbs_processed,
            'responses': responses,
            'elapsed': elapsed,
        }


    @staticmethod
    def vectorize_docs(docs, vdbs):
        set_rag_context()
        log(f'vdbs: {vdbs}')
        vdbs_processed = []
        if 'weaviate' in vdbs:
            Weaviate.vectorize_docs(docs)
            vdbs_processed.append('weaviate')
        if 'chromadb' in vdbs:
            ChromaDB.vectorize_docs(docs)
            vdbs_processed.append('chromadb')
        log(f'vdbs processed: {vdbs_processed}')
        return vdbs_processed


class BaseVectorStore(abc.ABC):
    LFAI_INDEX_NAME = os.environ.get('LFAI_INDEX_NAME')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

    @staticmethod
    def index_from_docs(docs, storage_context):
        index = VectorStoreIndex.from_documents(docs, storage_context=storage_context)
        return index

    def index_from_vector_store(vector_store):
        return VectorStoreIndex.from_vector_store(vector_store=vector_store)

    @staticmethod
    def persist_index(index):
        index.storage_context.persist()

    @staticmethod
    def query_index(index, query):
        query_engine = index.as_query_engine()
        response = query_engine.query(query).response
        return response

    @staticmethod
    @abc.abstractmethod
    def process_query(prompt):
        pass

    @staticmethod
    @abc.abstractmethod
    def get_client():
        pass

    @staticmethod
    @abc.abstractmethod
    def get_storage_context(index_name):
        pass

    @staticmethod
    @abc.abstractmethod
    def get_vector_store(index_name):
        pass

    @staticmethod
    @abc.abstractmethod
    def vectorize_docs(docs, index_name=None):
        pass

class Weaviate(BaseVectorStore):
    HOST = os.environ.get('WEAVIATE_HOST')
    PORT = os.environ.get('WEAVIATE_PORT')

    @staticmethod
    def get_client():
        return weaviate.Client(f'http://{Weaviate.HOST}:{Weaviate.PORT}')

    @staticmethod
    def get_storage_context(index_name):
        vector_store = Weaviate.get_vector_store(index_name)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        return storage_context


    @staticmethod
    def get_vector_store(index_name):
        client = Weaviate.get_client()
        vector_store = WeaviateVectorStore(weaviate_client=client, index_name=index_name)
        return vector_store


    @staticmethod
    def vectorize_docs(docs, index_name=None):
        index_name = Weaviate.LFAI_INDEX_NAME if index_name is None else index_name
        storage_context = Weaviate.get_storage_context(index_name)
        index = Weaviate.index_from_docs(docs, storage_context)
        Weaviate.persist_index(index)


    def process_query(prompt):
        start = now()
        vector_store = Weaviate.get_vector_store(Weaviate.LFAI_INDEX_NAME)
        index = Weaviate.index_from_vector_store(vector_store)
        response = Weaviate.query_index(index, prompt)
        elapsed = get_elapsed(start)
        return {'vector_store': 'weaviate', 'response': response, 'elapsed': elapsed}


class ChromaDB(BaseVectorStore):
    HOST = os.environ.get('CHROMADB_HOST')
    PORT = os.environ.get('CHROMADB_PORT')


    @staticmethod
    def get_client():
        return chromadb.HttpClient(host=ChromaDB.HOST, port=ChromaDB.PORT)

    @staticmethod
    def get_storage_context(index_name):
        vector_store = ChromaDB.get_vector_store(index_name)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        return storage_context

    @staticmethod
    def get_vector_store(index_name):
        client = ChromaDB.get_client()
        chroma_collection = client.get_or_create_collection(index_name)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        return vector_store

    @staticmethod
    def vectorize_docs(docs, index_name=None):
        index_name = ChromaDB.LFAI_INDEX_NAME if index_name is None else index_name
        storage_context = ChromaDB.get_storage_context(index_name)
        index = ChromaDB.index_from_docs(docs, storage_context)
        ChromaDB.persist_index(index)


    def process_query(prompt):
        start = now()
        vector_store = ChromaDB.get_vector_store(Weaviate.LFAI_INDEX_NAME)
        index = ChromaDB.index_from_vector_store(vector_store)
        response = ChromaDB.query_index(index, prompt)
        elapsed = get_elapsed(start)
        return {'vector_store': 'chromadb', 'response': response, 'elapsed': elapsed}
