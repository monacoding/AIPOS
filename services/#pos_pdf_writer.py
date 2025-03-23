import os
import fitz  # PyMuPDF
from openai import OpenAI
from database import POS_FOLDER
from dotenv import load_dotenv

# ✅ 환경 변수 불러오기
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ✅ 다운로드 폴더 설정
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "download")

# ✅ 텍스트 정규화 함수
def normalize_text(text):
    return ' '.join(text.strip().split())

# ✅ LLM을 이용한 문단 리라이트 함수
def rewrite_paragraph_with_llm(para, std_text, proj_text):
    prompt = f"""
다음은 LNG선 POS 문서의 문단입니다. 표준 사양서 문장을 새로운 프로젝트 사양서 내용으로 반영하여 문장을 자연스럽게 수정해줘. 전체 문단 구조는 유지하되, 지정된 문장만 부드럽게 바꿔줘.

[문단 원문]
{para}

[바꿀 부분 - 표준 문장]
{std_text}

[대체할 부분 - 프로젝트 문장]
{proj_text}

[요청사항]
- 문단 구조를 유지하며
- 표준 문장을 프로젝트 문장으로 자연스럽게 대체
- 다른 부분은 절대 변경하지 말 것
- 한글 스타일 유지
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "너는 LNG선 POS 문서를 전문적으로 작성하는 AI 어시스턴트야."},
                {"role": "user", "content": prompt.strip()}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ LLM 호출 실패: {e}")
        return para  # 실패 시 원문 그대로 반환

def apply_differences_to_pos_pdf(ship_type, differences, project_number, pos_filename):
    source_pdf_path = os.path.join(POS_FOLDER, ship_type, pos_filename)
    if not os.path.exists(source_pdf_path):
        print(f"❌ 원본 POS 파일 없음: {source_pdf_path}")
        return None, []

    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    result_filename = pos_filename.replace("STD", project_number)
    result_pdf_path = os.path.join(DOWNLOAD_FOLDER, result_filename)

    change_log = []

    try:
        doc = fitz.open(source_pdf_path)
        for diff in differences:
            std_text = diff["표준 사양서"].strip()
            proj_text = diff["프로젝트 사양서"].strip()

            found = False
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                paragraphs = page_text.split("\n\n")
                for para in paragraphs:
                    if std_text in para:
                        print(f"🔍 문단 매칭됨 (p.{page_num+1}): {para[:50]}...")

                        # ✅ LLM을 통해 자연스럽게 문단 수정
                        rewritten_para = rewrite_paragraph_with_llm(para, std_text, proj_text)

                        # 페이지 클리어 후 새로운 문단 삽입
                        page.clean_contents()
                        page.insert_text(
                            (72, 72),  # 좌측 상단 기준 위치
                            rewritten_para,
                            fontsize=11,
                            color=(1, 0, 0),
                            render_mode=3
                        )

                        change_log.append({
                            "기존": std_text,
                            "수정": proj_text
                        })
                        found = True
                        break
                if found:
                    break

            if not found:
                print(f"⚠️ '{std_text[:30]}...' 문구를 POS PDF에서 찾을 수 없음")
                print("📄 페이지 텍스트:")
                print(page.get_text())

        doc.save(result_pdf_path)
        doc.close()
        print(f"✅ 저장 완료: {result_pdf_path}")
        return result_pdf_path, change_log

    except Exception as e:
        print(f"❌ PDF 반영 중 오류: {e}")
        return None, []