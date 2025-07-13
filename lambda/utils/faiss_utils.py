import json
import boto3
import numpy as np
import faiss
import tempfile
import os
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class FAISSManager:
    """FAISS 인덱스 관리 클래스"""
    
    def __init__(self, s3_bucket: str, region: str = 'us-east-1'):
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3', region_name=region)
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        self.embed_model_id = os.environ.get('BEDROCK_EMBED_MODEL_ID', 'amazon.titan-embed-text-v1')
        
    def get_embedding(self, text: str) -> np.ndarray:
        """텍스트를 임베딩 벡터로 변환"""
        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.embed_model_id,
                body=json.dumps({
                    "inputText": text
                }),
                contentType="application/json"
            )
            
            result = json.loads(response['body'].read())
            embedding = np.array(result['embedding'], dtype=np.float32)
            return embedding
            
        except Exception as e:
            logger.error(f"임베딩 생성 오류: {str(e)}")
            raise
    
    def get_batch_embeddings(self, texts: List[str]) -> np.ndarray:
        """여러 텍스트를 배치로 임베딩"""
        embeddings = []
        for text in texts:
            embedding = self.get_embedding(text)
            embeddings.append(embedding)
        return np.array(embeddings, dtype=np.float32)
    
    def create_index(self, embeddings: np.ndarray) -> faiss.IndexFlatIP:
        """FAISS 인덱스 생성 (Inner Product 사용)"""
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        
        # 정규화 (cosine similarity를 위해)
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        
        return index
    
    def save_index_to_s3(self, project_id: str, index: faiss.IndexFlatIP, metadata: List[Dict]) -> bool:
        """FAISS 인덱스와 메타데이터를 S3에 저장"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # 인덱스 파일 저장
                index_path = os.path.join(temp_dir, 'index.faiss')
                faiss.write_index(index, index_path)
                
                # 메타데이터 파일 저장
                metadata_path = os.path.join(temp_dir, 'metadata.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                # S3에 업로드
                index_key = f"faiss-indices/{project_id}/index.faiss"
                metadata_key = f"faiss-indices/{project_id}/metadata.json"
                
                self.s3_client.upload_file(index_path, self.s3_bucket, index_key)
                self.s3_client.upload_file(metadata_path, self.s3_bucket, metadata_key)
                
                logger.info(f"FAISS 인덱스 저장 완료: {project_id}")
                return True
                
        except Exception as e:
            logger.error(f"FAISS 인덱스 저장 오류: {str(e)}")
            return False
    
    def load_index_from_s3(self, project_id: str) -> Tuple[Optional[faiss.IndexFlatIP], Optional[List[Dict]]]:
        """S3에서 FAISS 인덱스와 메타데이터 로드"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                index_key = f"faiss-indices/{project_id}/index.faiss"
                metadata_key = f"faiss-indices/{project_id}/metadata.json"
                
                index_path = os.path.join(temp_dir, 'index.faiss')
                metadata_path = os.path.join(temp_dir, 'metadata.json')
                
                # S3에서 다운로드
                self.s3_client.download_file(self.s3_bucket, index_key, index_path)
                self.s3_client.download_file(self.s3_bucket, metadata_key, metadata_path)
                
                # 인덱스 로드
                index = faiss.read_index(index_path)
                
                # 메타데이터 로드
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                return index, metadata
                
        except Exception as e:
            logger.error(f"FAISS 인덱스 로드 오류: {str(e)}")
            return None, None
    
    def search_similar(self, project_id: str, query_text: str, top_k: int = 5) -> List[Dict]:
        """유사한 프롬프트 검색"""
        try:
            # 인덱스 로드
            index, metadata = self.load_index_from_s3(project_id)
            if index is None or metadata is None:
                logger.warning(f"프로젝트 {project_id}의 FAISS 인덱스를 찾을 수 없습니다.")
                return []
            
            # 쿼리 임베딩
            query_embedding = self.get_embedding(query_text)
            query_embedding = query_embedding.reshape(1, -1)
            faiss.normalize_L2(query_embedding)
            
            # 검색 수행
            scores, indices = index.search(query_embedding, min(top_k, index.ntotal))
            
            # 결과 구성
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx >= 0 and idx < len(metadata):  # 유효한 인덱스인지 확인
                    result = metadata[idx].copy()
                    result['similarity_score'] = float(score)
                    result['rank'] = i + 1
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"유사도 검색 오류: {str(e)}")
            return []
    
    def update_index(self, project_id: str, new_texts: List[str], new_metadata: List[Dict]) -> bool:
        """기존 인덱스에 새로운 데이터 추가"""
        try:
            # 기존 인덱스 로드
            existing_index, existing_metadata = self.load_index_from_s3(project_id)
            
            # 새로운 임베딩 생성
            new_embeddings = self.get_batch_embeddings(new_texts)
            
            if existing_index is None:
                # 새 인덱스 생성
                index = self.create_index(new_embeddings)
                metadata = new_metadata
            else:
                # 기존 인덱스에 추가
                faiss.normalize_L2(new_embeddings)
                existing_index.add(new_embeddings)
                index = existing_index
                metadata = existing_metadata + new_metadata
            
            # S3에 저장
            return self.save_index_to_s3(project_id, index, metadata)
            
        except Exception as e:
            logger.error(f"인덱스 업데이트 오류: {str(e)}")
            return False
    
    def rebuild_index(self, project_id: str, all_texts: List[str], all_metadata: List[Dict]) -> bool:
        """인덱스 전체 재구축"""
        try:
            if not all_texts:
                logger.warning(f"프로젝트 {project_id}에 텍스트 데이터가 없습니다.")
                return False
            
            # 모든 텍스트 임베딩
            embeddings = self.get_batch_embeddings(all_texts)
            
            # 새 인덱스 생성
            index = self.create_index(embeddings)
            
            # S3에 저장
            return self.save_index_to_s3(project_id, index, all_metadata)
            
        except Exception as e:
            logger.error(f"인덱스 재구축 오류: {str(e)}")
            return False
    
    def delete_index(self, project_id: str) -> bool:
        """프로젝트의 FAISS 인덱스 삭제"""
        try:
            index_key = f"faiss-indices/{project_id}/index.faiss"
            metadata_key = f"faiss-indices/{project_id}/metadata.json"
            
            # S3에서 삭제
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=index_key)
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=metadata_key)
            
            logger.info(f"FAISS 인덱스 삭제 완료: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"FAISS 인덱스 삭제 오류: {str(e)}")
            return False 