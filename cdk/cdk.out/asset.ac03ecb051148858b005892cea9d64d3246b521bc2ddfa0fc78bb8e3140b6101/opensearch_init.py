
import os
import json
from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError

# ������ ������������������ ��������� ������
def initialize_opensearch_vector_index():
    """
    OpenSearch��� ������ ������ ��������� ������ ������������ ������������������.
    """
    try:
        # OpenSearch ������ ������
        host = os.environ.get("OPENSEARCH_ENDPOINT", "localhost")
        client = OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=("admin", "admin"),
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False
        )
        
        # ��������� ��������� ��������� ������ ��� (������ 768 ������ ������)
        embedding_dim = 768
        
        # ������ ��������� ��������� ������
        chat_index_name = "chat_messages"
        
        try:
            # ��������� ������ ������ ������
            if client.indices.exists(index=chat_index_name):
                print(f"��������� {chat_index_name}��� ������ ���������������.")
                return True
                
            # ��������� ������ (HNSW ������������ ������)
            index_body = {
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 100
                    }
                },
                "mappings": {
                    "properties": {
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": embedding_dim,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": 128,
                                    "m": 24
                                }
                            }
                        },
                        "content": {"type": "text"},
                        "role": {"type": "keyword"},
                        "timestamp": {"type": "date"},
                        "session_id": {"type": "keyword"},
                        "project_id": {"type": "keyword"},
                        "metadata": {"type": "object", "enabled": True}
                    }
                }
            }
            
            # ��������� ������
            response = client.indices.create(index=chat_index_name, body=index_body)
            print(f"��������� {chat_index_name} ������ ������:", response)
            return True
        
        except Exception as e:
            print(f"OpenSearch ��������� ������ ��� ������ ������: {e}")
            return False
    
    except Exception as e:
        print(f"OpenSearch ������ ��� ������ ������: {e}")
        return False

# ������ ��������� ������ ��������� ������ ������
if __name__ == "__main__":
    initialize_opensearch_vector_index()

