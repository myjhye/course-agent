"""
knowledge_base/ 폴더의 md 파일을 읽어서
청킹 → 임베딩 → knowledge_chunks 테이블에 저장하는 스크립트.
"""

import asyncio
import sys
import re
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text, select, func  # type: ignore

from app.database import AsyncSessionLocal
from app.models.knowledge import KnowledgeChunk
from app.services.ai.embedding_service import create_embedding


KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[1] / "knowledge_base"


def parse_md_file(file_path: Path) -> list[dict]:
    """
    md 파일을 ## 헤더 기준으로 청킹한다.

    Returns:
        [{"title": "섹션 제목", "content": "본문", "source_type": "..."}]
    """
    content = file_path.read_text(encoding="utf-8")

    # 메타데이터 추출
    source_type = "general"
    meta_match = re.search(r"<!--\s*source_type:\s*([\w_]+)\s*-->", content)
    if meta_match:
        source_type = meta_match.group(1)

    sections = re.split(r"\n(?=## )", content)

    chunks: list[dict] = []

    for idx, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        lines = section.split("\n")

        # 첫 섹션이 최상위 # 제목만 포함하는 경우 건너뛰기
        if idx == 0 and lines[0].startswith("# "):
            body = "\n".join(lines[1:]).strip()
            if body and "<!--" not in body:
                chunks.append(
                    {
                        "title": lines[0].replace("# ", "").strip(),
                        "content": body,
                        "source_type": source_type,
                    }
                )
            continue

        # 일반적인 ## 섹션
        title_line = lines[0]
        if title_line.startswith("## "):
            title = title_line.replace("## ", "").strip()
        else:
            title = title_line.strip()

        body = "\n".join(lines[1:]).strip()

        if body and len(body) > 20:
            chunks.append(
                {
                    "title": title,
                    "content": body,
                    "source_type": source_type,
                }
            )

    return chunks


async def load_all() -> None:
    """전체 knowledge_base를 로딩."""

    if not KNOWLEDGE_BASE_DIR.exists():
        print(f"❌ knowledge_base 폴더가 없습니다: {KNOWLEDGE_BASE_DIR}")
        return

    md_files = sorted(KNOWLEDGE_BASE_DIR.rglob("*.md"))
    print(f"📂 {len(md_files)}개 md 파일 발견\n")

    all_chunks: list[dict] = []
    for md_file in md_files:
        relative = md_file.relative_to(KNOWLEDGE_BASE_DIR)
        chunks = parse_md_file(md_file)
        for chunk in chunks:
            chunk["source_file"] = str(relative)
        all_chunks.extend(chunks)
        print(f"  📄 {relative}: {len(chunks)}개 청크")

    if not all_chunks:
        print("⚠️  생성된 청크가 없습니다. md 파일 내용을 확인하세요.")
        return

    print(f"\n총 {len(all_chunks)}개 청크")

    async with AsyncSessionLocal() as db:
        # 기존 데이터 삭제
        await db.execute(text("DELETE FROM knowledge_chunks"))
        await db.commit()
        print("🗑️  기존 knowledge_chunks 삭제 완료")

        print(f"\n🔄 임베딩 생성 시작 ({len(all_chunks)}건)...")
        start_time = time.time()

        for i, chunk in enumerate(all_chunks):
            embed_text = f"{chunk['title']}\n{chunk['content']}"
            try:
                embedding = await create_embedding(embed_text)
            except Exception as e:
                print(f"  ⚠️  임베딩 실패: {chunk['title'][:30]}... → {e}")
                embedding = None

            record = KnowledgeChunk(
                source_file=chunk["source_file"],
                source_type=chunk["source_type"],
                title=chunk["title"],
                content=chunk["content"],
                embedding=embedding,
            )
            db.add(record)

            if (i + 1) % 10 == 0 or i == len(all_chunks) - 1:
                print(f"  [{i+1}/{len(all_chunks)}] 완료")

            # OpenAI rate limit 여유
            await asyncio.sleep(0.1)

        await db.commit()

        elapsed = time.time() - start_time
        print(f"\n✅ {len(all_chunks)}개 청크 로딩 완료 ({elapsed:.1f}초)")

        # 요약
        result = await db.execute(
            select(  # type: ignore[name-defined]
                KnowledgeChunk.source_type,
                func.count(KnowledgeChunk.id),  # type: ignore[name-defined]
            ).group_by(KnowledgeChunk.source_type)
        )
        print("\n📊 source_type별 청크 수:")
        for row in result:
            print(f"  {row[0]:20s}: {row[1]}개")


if __name__ == "__main__":
    asyncio.run(load_all())

