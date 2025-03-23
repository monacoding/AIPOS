from docx import Document
from docx.shared import RGBColor
from database import POS_FOLDER
import os
from openai import OpenAI
import re
import unicodedata

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "download")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def reflect_changes_with_llm(std_text, proj_text):
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
        return revised
    except Exception as e:
        print(f"❌ GPT 호출 실패: {e}")
        return proj_text

def normalize_text(text):
    """텍스트 정규화: 공백, 특수 문자, 대소문자, 유니코드 정규화"""
    text = re.sub(r'\s+', ' ', text)  # 모든 공백 문자 제거
    text = unicodedata.normalize('NFKC', text)  # 유니코드 정규화
    text = re.sub(r'[^\w\s]', '', text)  # 특수 문자 제거 (선택 사항)
    return text.strip().lower() # 공백 제거, 특수문자 제거, 소문자 변환

def update_pos_word_with_differences(ship_type, differences, project_number, pos_filename):
    source_path = os.path.join(POS_FOLDER, ship_type, pos_filename)
    if not os.path.exists(source_path):
        print(f"❌ POS Word 파일이 존재하지 않음: {source_path}")
        return None, []

    doc = Document(source_path)
    change_log = []

    # 1. 전체 텍스트 추출
    full_text = "\n".join([para.text for para in doc.paragraphs])

    # 2. 프롬프트 작성
    prompt = f"다음은 {ship_type} 선박의 표준 POS(선박 인도 사양서) 문서입니다.\n{full_text}\n\n다음 변경 사항을 반영하여 프로젝트 사양에 맞게 수정해주세요.\n"
    for diff in differences:
        prompt += f"- {diff['표준 사양서']}  => {diff['프로젝트 사양서']}\n"
    prompt += "\n수정된 POS 문서를 완전한 형태로 제공해주세요."

    # 3. LLM 호출
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 최고의 선박 POS 문서 작성 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4, # You can adjust the temperature for more creative or conservative responses
        )
        llm_generated_text = response.choices[0].message.content.strip()
        print("✅ LLM이 생성한 텍스트:", llm_generated_text)

    except Exception as e:
        print(f"❌ LLM 호출 실패: {e}")
        return None, []

    # 4. Word 문서 업데이트 (전체 내용 교체)
    for para in doc.paragraphs:
        para.clear()  # 기존 내용 모두 삭제
    
    # 문단 단위로 분리하여 추가 (개행 유지)
    for paragraph_text in llm_generated_text.split("\n"):
        doc.add_paragraph(paragraph_text)

    # 5. 결과 저장
    result_filename = pos_filename.replace("STD", project_number)
    result_path = os.path.join(DOWNLOAD_FOLDER, result_filename)
    doc.save(result_path)
    print(f"✅ Word 문서 저장 완료: {result_path}")
    return result_path, change_log