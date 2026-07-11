"""
static/images/ 폴더의 시설 이미지 3장을 읽어
GPT-4o Vision API로 요약문을 생성한 뒤,
임베딩을 거쳐 knowledge_chunks 테이블에 source_type="image"로 시딩하는 스크립트.
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path

# 프로젝트 루트 경로를 Python PATH에 주입
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Windows 콘솔 표준 출력 UTF-8 강제 지정
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from sqlalchemy import text  # type: ignore
from app.database import AsyncSessionLocal
from app.models.knowledge import KnowledgeChunk
from app.services.ai.openai_vision_client import analyze_image_with_vision
from app.services.ai.embedding_service import create_embedding
from app.services.ai.langfuse_client import get_langfuse, flush_langfuse

IMAGE_DIR = Path(__file__).resolve().parents[1] / "static" / "images"

IMAGES_TO_SEED = [
    {
        "filename": "swimming_pool_facility.png",
        "title": "수영장 프리미엄 스포츠센터 시설 전경",
    },
    {
        "filename": "tennis_court_facility.png",
        "title": "실내 테니스장 테니스 코트 스포츠센터 시설 전경",
    },
    {
        "filename": "pilates_studio_facility.png",
        "title": "기구 필라테스 스튜디오 웰빙 센터 시설 전경",
    }
]


async def _execute_seeding(db) -> None:
    # 기존에 시딩된 이미지 레코드만 정돈
    await db.execute(text("DELETE FROM knowledge_chunks WHERE source_type = 'image'"))
    await db.commit()
    print("[Delete] 기존에 등록된 RAG 이미지 지식 데이터(source_type='image') 삭제 완료.")

    for i, img_meta in enumerate(IMAGES_TO_SEED):
        img_path = IMAGE_DIR / img_meta["filename"]
        img_url = f"/static/images/{img_meta['filename']}"
        title = img_meta["title"]
        
        print(f"\n[ {i+1} / {len(IMAGES_TO_SEED)} ] '{img_meta['filename']}' 처리 중...")
        
        # 1. GPT-4o Vision API 분석 진행
        start_vision = time.time()
        summary = await analyze_image_with_vision(str(img_path))
        
        if not summary:
            print(f"  [Error] '{img_meta['filename']}' Vision 분석에 실패하여 건너뜁니다.")
            continue

        elapsed_vision = time.time() - start_vision
        print(f"  [Vision] 요약 완료 ({elapsed_vision:.1f}초)")
        print(f"  [Summary] 요약 요약문 (30자): {summary[:30]}...")

        # 2. 요약 텍스트 임베딩화 진행
        embed_text = f"{title}\n{summary}"
        start_embed = time.time()
        
        try:
            embedding = await create_embedding(embed_text)
        except Exception as e:
            print(f"  [Error] 임베딩 실패: {title[:20]}... → {e}")
            embedding = None

        elapsed_embed = time.time() - start_embed
        print(f"  [Embedding] 텍스트 임베딩화 완료 ({elapsed_embed:.1f}초)")

        # 3. DB 적재
        record = KnowledgeChunk(
            source_file=img_meta["filename"],
            source_type="image",
            title=title,
            content=summary,
            metadata_json=json.dumps({"image_url": img_url}),
            embedding=embedding
        )
        db.add(record)
        print(f"  [DB] DB 스테이징 등록 완료 (URL: {img_url})")

        # API 호출 쿨다운
        await asyncio.sleep(0.2)

    await db.commit()
    print("\n[Success] 이미지 RAG 지식 데이터베이스 커밋 완료!")


async def seed_images() -> None:
    if not IMAGE_DIR.exists():
        print(f"[Error] static/images/ 폴더가 없습니다: {IMAGE_DIR}")
        return

    print(f"[Start] static/images/ 에서 {len(IMAGES_TO_SEED)}개의 대표 이미지 시딩을 시작합니다.\n")

    langfuse = get_langfuse()
    
    async with AsyncSessionLocal() as db:
        if langfuse:
            print("[Langfuse] 관측 Span 계측이 활성화되었습니다.")
            try:
                # 최상위 Span을 띄워 하위 Vision 및 Embedding 호출을 하나로 바인딩
                with langfuse.start_as_current_observation(
                    as_type="span",
                    name="seed_image_rag",
                    input={"images_count": len(IMAGES_TO_SEED)}
                ):
                    await _execute_seeding(db)
            except Exception as e:
                print(f"[Langfuse Warning] Langfuse 관측 연동 중 실패했으나 시딩은 계속 진행합니다: {e}")
                await _execute_seeding(db)
        else:
            await _execute_seeding(db)

        # Langfuse 버퍼 비우기
        if langfuse:
            try:
                flush_langfuse()
                print("[Langfuse] 버퍼 전송 완료.")
            except:
                pass


if __name__ == "__main__":
    asyncio.run(seed_images())
