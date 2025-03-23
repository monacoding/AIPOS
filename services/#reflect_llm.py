import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def reflect_changes_to_word(differences):
    changes = []

    for diff in differences:
        std_text = diff["표준 사양서"].strip()
        proj_text = diff["프로젝트 사양서"].strip()

        prompt = (
            f"다음은 LNG선 POS 문서의 기존 문장입니다:\n"
            f"{std_text}\n\n"
            f"아래 프로젝트 사양서의 내용을 반영하되, 전체 문장을 새로 쓰지 말고 "
            f"수치, 단어 등 필요한 부분만 최소한으로 수정해줘:\n"
            f"{proj_text}"
        )

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "너는 LNG선 POS 문서를 작성하는 전문가야."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            revised = response.choices[0].message.content.strip()
            changes.append({
                "표준 사양서": std_text,
                "프로젝트 사양서": revised
            })
        except Exception as e:
            print(f"❌ GPT 호출 실패: {e}")
            changes.append({
                "표준 사양서": std_text,
                "프로젝트 사양서": proj_text + " (GPT 실패)"
            })

    return changes