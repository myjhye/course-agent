import os
import base64
import httpx
from typing import Optional

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


async def analyze_image_with_vision(image_path: str) -> Optional[str]:
    """
    OpenAI GPT-4o Vision API를 사용하여 이미지 시설 전경 및 텍스트(OCR) 정보를 상세히 분석합니다.
    분석된 텍스트 요약은 2차 Reranking 시 어휘 정합성에 잘 매칭되도록 풍부한 키워드를 포함합니다.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[OpenAI Vision] OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        return None

    if not os.path.exists(image_path):
        print(f"[OpenAI Vision] 이미지 파일을 찾을 수 없습니다: {image_path}")
        return None

    try:
        # 이미지 파일을 읽어 base64 데이터로 인코딩
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")

        # 확장자에 따른 mime type 감지
        ext = os.path.splitext(image_path)[1].lower()
        mime_type = "image/png" if ext == ".png" else "image/jpeg"

        # Cohere Reranker와 1차 벡터 임베딩이 질문과의 관계를 정확히 계산할 수 있게 상세 요약 지침 지시
        system_instruction = (
            "당신은 스포츠 센터의 시설, 인테리어 및 스포츠 장비 이미지를 정밀 분석하는 AI 어시스턴트입니다.\n"
            "제공된 스포츠 센터 전경 이미지(수영장, 테니스장, 필라테스실 등)를 분석하여 상세한 한국어 요약 설명문을 작성해 주세요.\n"
            "설명문은 RAG(검색 증강 생성) 및 리랭킹 시스템에서 검색 정확도를 극대화할 수 있도록 아래 지침을 엄격히 따라 작성해야 합니다:\n\n"
            "1. 해당 시설의 이름과 분류를 첫 줄에 명확히 기재하세요 (예: [수영장 시설 전경 및 안내]).\n"
            "2. 이미지에서 관측되는 핵심 키워드를 모두 기재하세요 (예: 50m 레인, 유리 통창, 우든 바닥, 리포머 기구, 테니스 네트, 라인 등).\n"
            "3. 시설의 인테리어 무드와 조명, 분위기 및 색상(예: 깔끔한 화이트톤, 따뜻한 나무 인테리어, 청량한 블루톤 물빛 등)을 구체적으로 설명하세요.\n"
            "4. 이 이미지는 어떤 수강생이 어떤 질문(예: '수영장 시설 사진 보여줘', '필라테스 기구 어때요?', '테니스 코트 실내인가요?')을 할 때 적합한지 매칭 가이드를 텍스트로 자연스럽게 포함하세요.\n"
            "5. 부차적인 미사여구는 빼고, 정보 가치가 높은 명사형 키워드와 설명적인 문장으로 정형화해 작성하세요."
        )

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": system_instruction
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "이 스포츠 센터 이미지를 RAG 검색 최적화용 가이드라인에 맞추어 한국어 요약 설명문으로 분석해줘."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                OPENAI_CHAT_URL,
                headers=headers,
                json=payload,
                timeout=30.0  # Vision 분석 시간을 감안한 타임아웃
            )

            if response.status_code != 200:
                print(f"[OpenAI Vision] API 호출 실패 (상태코드 {response.status_code}): {response.text}")
                return None

            result = response.json()
            analysis_text = result["choices"][0]["message"]["content"].strip()
            return analysis_text

    except Exception as e:
        print(f"[OpenAI Vision] 이미지 분석 중 예외 발생: {e}")
        return None
