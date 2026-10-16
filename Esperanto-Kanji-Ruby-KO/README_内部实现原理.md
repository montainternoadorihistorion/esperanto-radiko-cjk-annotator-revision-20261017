> **旧版の参考資料 / Historical reference**
> この文書には旧画面・旧構成の説明が含まれます。現在の操作と配備方法は [リポジトリ直下の README](../README.md) を参照してください。

# Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Korean

아래 내용은, 앞서 주어진 **4개 파이썬 코드(`main.py`, `에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py`, `esp_text_replacement_module.py`, `esp_replacement_json_make_module.py`)**를 중심으로, 이 스트림릿(Streamlit) 기반 앱이 **어떻게 내부적으로 동작**하는지를 (이미 GUI 위주의 사용법은 어느 정도 숙지하고 있는) **한국의 중급 프로그래머**분들을 위해 풀어서 설명한 자료입니다.

---

# 전체 개요

이 앱은 크게 두 가지 메인 기능을 담당합니다.

1. **에스페란토 문장을 (한자/한국어 번역 등)으로 치환**하고, 필요한 경우 **HTML 루비 형태**로 출력하도록 하는 **메인 애플리케이션**(`main.py`).  
2. 사용자가 원하는 **CSV / JSON 파일**을 조합하여, 최종적으로 `main.py`에서 사용하는 **“치환 규칙(3개 리스트가 합쳐진 JSON)”**을 생성할 수 있게 하는 페이지(`에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py`).

그리고 내부적으로, **치환 로직**(에스페란토 문자열 변환, safe_replace, 멀티프로세싱 병렬화, 접두·접미·활용 어근 처리 등)을 구현한 두 개의 모듈:
- `esp_text_replacement_module.py`
- `esp_replacement_json_make_module.py`

이렇게 4개가 서로 유기적으로 연결되어 구동되는 구조입니다.  

이제 각각의 **코드 구조**와 핵심 메커니즘(플레이스홀더, 병렬처리, 치환 로직, JSON 생성 로직 등)을 순차적으로 살펴보겠습니다.

---

# 1. `main.py` (메인 스트림릿 앱)

## 1.1 전반적 구성

- **Streamlit**의 `st.radio`, `st.file_uploader`, `st.selectbox`, `st.text_area`, `st.form` 등을 이용해 **GUI**를 제공합니다.
- **“기본값 사용”** / **“업로드하기”** 옵션으로,  
  - **치환용 JSON**을 불러오고,  
  - 에스페란토 문장을 직접 입력 혹은 텍스트 파일 업로드하여,  
  - 마지막으로 여러 **출력 형식(HTML루비, 괄호 형식 등)** 중 하나를 선택해 치환을 진행합니다.
- **결과**는 **미리보기** 탭으로 보여주고, `.html` 형태로 다운로드할 수 있게 합니다.

## 1.2 코드 구조 특징

### (A) `multiprocessing.set_start_method("spawn")`
- 코드 초반에 `multiprocessing.set_start_method("spawn")`를 호출합니다.  
  - 이는 윈도우 환경 등에서 **스트림릿과 멀티프로세싱을 함께 사용할 때** 발생할 수 있는 PicklingError 등을 피하기 위함입니다.  
  - 이미 설정되었다면 `RuntimeError`가 뜰 수 있으므로 `try-except`를 통해 한 번만 설정하게 처리합니다.

### (B) 외부 모듈 임포트
```python
from esp_text_replacement_module import (
    x_to_circumflex,
    x_to_hat,
    ...
    parallel_process,
    apply_ruby_html_header_and_footer
)
```
- **`esp_text_replacement_module.py`**에서 치환에 필요한 함수들을 전부 불러와 씁니다.  
  - 예: `orchestrate_comprehensive_esperanto_text_replacement()`가 핵심 치환 함수.

### (C) `@st.cache_data`를 활용한 JSON 로드
```python
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    ...
```
- 커다란 JSON 파일(최대 50MB~수십MB)을 자주 읽어들이면 느려질 수 있으니, **스트림릿의 캐싱 데코레이터**를 통해 한번 로드한 결과를 메모리에 보관합니다.
- JSON에는 다음 3개 리스트가 들어 있습니다:
  1. `replacements_final_list` (전역 치환)
  2. `replacements_list_for_localized_string` (국소 치환, `@...@`)
  3. `replacements_list_for_2char` (2글자 어근 처리)

### (D) JSON 읽기 (기본값 / 업로드)

```python
selected_option = st.radio(..., ("기본값 사용", "업로드하기"))
if selected_option == "기본값 사용":
   ...
else:
   uploaded_file = st.file_uploader(...)
   ...
```
- **기본값** 경로:  
  `./Appの运行に使用する各类文件/최종적 치환용 JSON.json`  
- **업로드** 로직: 업로드된 파일을 `json.load()`하여, `replacements_final_list`, `replacements_list_for_localized_string`, `replacements_list_for_2char` 3개로 나눠서 가져옵니다.

### (E) 플레이스홀더(placeholder) 로드
```python
placeholders_for_skipping_replacements = import_placeholders('./...skip用.txt')
...
```
- `%...%` 스킵, `@...@` 국소치환을 처리할 때 내부에서 쓰이는 문자열 목록.
- `import_placeholders()`는 줄단위 텍스트 파일을 읽어온 뒤 리스트로 반환.

### (F) “고급 설정(병렬 처리)”
- `st.checkbox("병렬 처리를 사용하기", value=False)`  
- `num_processes = st.number_input("동시 프로세스 수", ...)`
- 이 값을 인자로 **치환 함수**(`parallel_process`)를 호출할 때 넘겨줍니다.
  - 병렬화 시, 텍스트를 **행 단위**로 잘라서 여러 프로세스에서 동시에 치환합니다.

### (G) 출력 형식 선택(`format_type`)
```python
options = {
    'HTML형식_Ruby문자_크기조정': 'HTML格式_Ruby文字_大小调整',
    ...
}
selected_display = st.selectbox(...)
format_type = options[selected_display]
```
- **한국어 라벨**을 키, 내부적 문자열을 값으로 두고 맵핑합니다.  
- ‘괄호 형식’, ‘HTML 루비 형식’, ‘한자 치환’ 유무 등 총 7~8가지.

### (H) 에스페란토 문장 입력 소스
- **직접 입력**(TextArea) vs **파일 업로드**(`st.file_uploader`)
- 최종적으로 `text0`에 에스페란토 문장을 얻음.

### (I) 전송 버튼 처리
```python
submit_btn = st.form_submit_button('전송')
if submit_btn:
    if use_parallel:
        processed_text = parallel_process(...)
    else:
        processed_text = orchestrate_comprehensive_esperanto_text_replacement(...)
    ...
```
- “전송” 버튼 클릭 시,  
  - **병렬 처리 여부**에 따라 `parallel_process` 또는 `orchestrate_comprehensive_esperanto_text_replacement` 직접 호출.  
- 치환된 결과를 `processed_text` 변수에 저장.

### (J) 에스페란토 특수문자 최종 변환 (라디오버튼으로 `상단 첨자`, `x 형식`, `^ 형식` 등)
- `replace_esperanto_chars(...)`를 통해 `x_to_circumflex`, `x_to_hat`, 등등을 적용.

### (K) 결과 표시 및 다운로드
- **HTML** 형태면 `st.tabs(["HTML 미리보기", "치환 결과(HTML 소스 코드)"])`  
- **그 외**(괄호, 단순 치환 등)면 텍스트 형태.  
- **파일 다운로드**: `st.download_button(label="치환 결과 다운로드", data=download_data, file_name="치환결과.html", mime="text/html")`

---

# 2. `에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py`

이 페이지는 **Streamlit의 `pages/` 폴더** 안에 넣어두어, “부가 페이지” 역할을 합니다.

## 2.1 주요 목적

- **에스페란토 단어 어근** + **한자(혹은 번역)** 정보가 들어 있는 CSV 파일과,
- **사용자 정의 JSON**(어근 분해법, 우선순위, 접미어 처리 등)을 **종합**하여,
- 최종적으로 `main.py`에서 사용할 **“합쳐진 치환용 JSON”**(3개 리스트가 들어 있는) 파일을 생성하도록 합니다.

## 2.2 코드 흐름

### (A) 상단 설정
- `st.set_page_config(...)`로 레이아웃, 페이지 제목 지정.  
- 상단에 “사용 방법 설명” expander (Streamlit용).

### (B) 샘플 파일 다운로드 버튼
- `st.download_button(...)` 으로 CSV, JSON, Excel 등 예제들을 내려받도록 제공.

### (C) 출력 형식 선택(동일)
- `format_type`을 `HTML格式_Ruby문자_大小调整`, `괄호 형식` 등으로 정해둠.

### (D) “단계 1: CSV 파일 준비”
```python
csv_choice = st.radio("CSV 파일을 어떻게 하시겠습니까?", ("업로드하기", "기본값 사용"))
...
CSV_data_imported = pd.read_csv(...)
```
- CSV는 `pandas`로 읽어오며, 에스페란토 어근과 번역/한자 한 쌍을 가정(2열).

### (E) “단계 2: JSON 파일(어근 분해법 등) 준비”
```python
json_choice = st.radio("...", ("업로드하기", "기본값 사용"))
...
custom_stemming_setting_list = json.load(...)
```
- 첫 번째 JSON: **어근 분해법(어근 + 품사/활용 + 우선순위)**  
- 두 번째 JSON: **치환 후 문자열 추가 설정**  
- 사용자가 이 JSON들을 직접 업로드하거나, 기본값을 사용할 수 있음.

### (F) “단계 3: 병렬 처리”
- CSV → (임시 치환) → Python dict 만들 때 병렬화 가능 (`parallel_build_pre_replacements_dict`).

### (G) “치환용 JSON 파일 생성하기” 버튼
- 이 버튼 클릭 시,  
  1) **에스페란토 전체 단어 목록**(예: `E_stem_with_Part_Of_Speech_list`)을 로드  
  2) CSV에서 읽은 `(어근, 번역)` 매핑을 토대로 **임시 치환용 dict** 생성  
  3) `safe_replace`를 통해 실제 치환(HTML루비/괄호/단순)을 적용  
  4) “동사활용(as, is, os 등)” / “접두·접미(2글자)” / `AN`, `ON` 등 특수 규칙을 통해 **파생 단어**도 일괄 등록  
  5) “사용자 정의 JSON”에서 추가 규칙 or -1(제외) 적용  
  6) 최종적으로 정렬·우선순위 매긴 뒤 3개 리스트(`replacements_final_list`, `replacements_list_for_2char`, `replacements_list_for_localized_string`)로 만들고, **합쳐서 JSON**으로 dump.

- 마지막에 `st.download_button(..., file_name="합쳐진JSON.json")` 으로 다운로드.

## 2.3 내부 로직의 핵심 포인트

1. **CSV → 임시 치환**  
   - CSV에 적힌 `(에스페란토 어근, 한자/번역)` 쌍을 읽어, `output_format(어근, 한자, format_type, char_widths_dict)`를 호출해 `<ruby>...</ruby>` 또는 `(... )` 형태를 생성.  
   - 이렇게 만든 매핑을 `(old, new, placeholder)` 형태로 만든 뒤 `safe_replace`로 “에스페란토 원형”을 치환해냄.

2. **우선순위(문자열 길이 * 10000 등)**  
   - 긴 단어가 짧은 단어보다 먼저 치환되도록 **우선순위(=정렬용 int)**를 부여합니다.  
   - “동사 어미(as, is, os...)” 등을 붙인 형태는 더 길어질 수 있으므로 우선순위를 크게 주어, 치환 충돌을 방지.

3. **접미어 an, on, 2글자 어근**(suffix_2char_roots, prefix_2char_roots)  
   - 에스페란토에는 2글자짜리 접두/접미가 많아, 이를 어떻게 처리하느냐가 중요.  
   - 예: `an`(단체 구성원), `on`(분수·소립자 개념) 등.  
   - `AN` 리스트, `ON` 리스트, `suffix_2char_roots`, `prefix_2char_roots`, `standalone_2char_roots`를 이용해 **파생 단어**를 대량 생성하고, 치환 규칙에 추가.

4. **사용자 정의 JSON**으로 더 세부적인 규칙을 추가하거나 -1 우선순위로 제외시킬 수 있음.

5. **“국소 치환”**은, `@...@` 안에만 적용하고 싶은 (에스페란토→한자) 매핑을 별도로 만들기 위해, `replacements_list_for_localized_string`를 따로 생성.

결과적으로, **전역 치환**(에스페란토 문장 전체), **국소 치환**(`@...@` 안), **2글자 어근 치환** 전용 리스트 총 3가지를 JSON에 담게 됩니다.

---

# 3. `esp_text_replacement_module.py`

이 모듈은 **“메인 치환 로직 + 멀티프로세싱”**의 핵심 함수들을 제공합니다.

## 3.1 주요 함수/변수

1. **에스페란토 문자 변환 딕셔너리**  
   - `x_to_circumflex`, `circumflex_to_x`, `x_to_hat`, `hat_to_circumflex` 등.  
   - (예) `'cx' -> 'ĉ'`, `'c^' -> 'ĉ'` 등의 매핑.

2. `replace_esperanto_chars(text, char_dict)`
   - 텍스트 내 모든 키워드를 단순 `str.replace`로 치환.

3. `convert_to_circumflex(text: str)`
   - “hat 표기(c^)” 및 “x 표기(cx)”를 전부 “동그라미표기(ĉ)”로 변환.

4. `safe_replace(text, replacements: List[Tuple[str, str, str]])`
   - (old, new, placeholder) 기반 **2단계 치환**(old→placeholder→new) 방식을 사용.  
   - 한 번에 `text.replace(old, new)` 하면 충돌/중복치환 위험이 있어서,  
   - **placeholder**로 일시 치환한 뒤 마지막에 placeholder를 최종 변환합니다.

5. **`orchestrate_comprehensive_esperanto_text_replacement(...)`**:  
   이 모듈의 **가장 핵심**이 되는 함수로서,
   1) 공백 정규화(`unify_halfwidth_spaces`) + 에스페란토 특수문자 변환  
   2) `%...%`로 감싸인 부분은 치환에서 스킵  
   3) `@...@`로 감싸인 부분은 국소 치환 전용 리스트로 치환  
   4) 전역 치환 + 2글자 치환(2번 반복)  
   5) placeholder 복원  
   6) HTML형식이면 `<br>`, `&nbsp;` 같은 후처리

6. **병렬 처리** 관련: `parallel_process(...)`
   - `text`를 **줄 단위**로 나눈 뒤,  
   - `process_segment(...)` 함수를 여러 프로세스에서 병렬로 돌립니다.  
   - 각 프로세스가 `orchestrate_comprehensive_esperanto_text_replacement(...)`를 호출해 부분 텍스트를 치환하고, 결과를 합침.

---

# 4. `esp_replacement_json_make_module.py`

이 모듈은 **“JSON 생성 과정에서 대량 어근 치환, 우선순위 부여, 접두·접미 파생 처리”** 등을 담당합니다.

## 4.1 주요 함수/변수

1. 에스페란토 문자 변환 딕셔너리 (동일)
2. `output_format(main_text, ruby_content, format_type, char_widths_dict)`
   - **에스페란토 단어(원문)와 한자(또는 번역) 문자열**을,  
     - HTML 루비(`HTML格式_Ruby문자_크기조정`, 등)  
     - 괄호 표기  
     - 단순치환  
     ... 등으로 **합쳐**서 하나의 문자열로 만듭니다.
   - HTML 루비일 때, **글자폭 비율**(`measure_text_width_Arial16`)을 고려해 `<rt class="...">`에 사이즈 클래스를 달리 부여.

3. `process_chunk_for_pre_replacements(...)` / `parallel_build_pre_replacements_dict(...)`
   - CSV나 사전 형태의 (에스페란토어근, 품사) 목록을 나누어 `safe_replace`를 병렬로 돌리는 로직.  
   - (대규모 데이터 처리 시) 성능 향상을 위해 멀티프로세싱 사용.

4. `remove_redundant_ruby_if_identical(text: str)`
   - **루비 부모와 루비 내용이 동일**할 경우, `<ruby>...</ruby>` 태그를 제거.  
   - 예: `<ruby>xxx<rt>xxx</rt></ruby>` → `xxx`

5. **접두·접미어 관련 리스트**: `suffix_2char_roots`, `prefix_2char_roots`, `standalone_2char_roots`  
   - 예: `suffix_2char_roots = ['ad','ag','am','ar',...]`  
   - 어근에 접미를 붙여서 파생어를 만들어내고, 이를 치환 규칙에 추가하기 위해 사용.

6. `AN`, `ON` 리스트  
   - 예: `AN = [ ['dietan','/diet/an/', ...], ... ]`  
   - `on`도 마찬가지.  
   - 이들은 **에스페란토에서 “an”으로 끝나는 단어(회員, 속해 있는 사람)”** 등을 체계적으로 분류하여, 그 뒤에 ‘o’, ‘a’, ‘e’ 등 품사 어미를 붙인 다양한 형태를 생성할 수 있게 돕습니다.

---

# 정리 및 핵심 이해 포인트

1. **치환 구조**  
   - **전역 치환**: (old → new) 매핑을 순서대로 안전치환(`safe_replace`), placeholder 사용 → 충돌 방지.  
   - **국소 치환**(`@...@`): 전역 치환과 별개로, “@안”에 들어가는 텍스트만 따로 리스트를 적용.  
   - **스킵**(`%...%`): 치환 제외.  
   - **2글자 치환**: 에스페란토의 접두/접미(2글자)가 굉장히 많으므로, 전역 치환과 별도로 2차 치환 과정을 추가로 거침.

2. **JSON 생성**(`에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py`)  
   - CSV + 사용자 정의 JSON → 파생어(동사활용, 접미어, an/on)까지 전부 포함 → (전역/국소/2글자 치환) 3리스트를 최종 JSON에 담아서 export.  
   - **이 JSON을 `main.py`에서 불러와** 치환할 원문에 적용.

3. **병렬 처리**  
   - (메인에서) 긴 텍스트(행 단위) 치환, (JSON 생성 페이지) 대규모 어근 목록 치환  
   - 스트림릿과 `multiprocessing` 혼용 시 spawn 모드를 주의해야 함.

4. **루비 사이즈 조정**  
   - `HTML格式_Ruby문자_크기조정` 옵션에서, **에스페란토 단어 대비 번역(한자) 길이가 너무 긴 경우**를 여러 등급으로 나누어 `<rt>` 폰트 크기를 다르게 설정.  
   - `<ruby>...</ruby>`가 길 경우 `<br>`를 자동으로 끼워넣기도 함. (줄바꿈)

---

## 중급 프로그래머에게 유의미한 추가 TIP

1. **커스터마이징**  
   - 만약 “에스페란토 말고 다른 언어 치환”, “특정 프로젝트의 텍스트 치환”에 응용하려면,  
     - `orchestrate_comprehensive_esperanto_text_replacement` 함수의 **정규표현식**(`%...%`, `@...@`), `safe_replace` 구조를 그대로 쓰고,  
     - CSV/JSON 생성 로직(`esp_replacement_json_make_module`)을 수정해, 원하는 (old→new) 매핑을 만들어주면 됩니다.

2. **성능**  
   - 한 번에 긴 텍스트(수백~수천 줄)를 치환할 때, 병렬 처리로 유의미한 속도 향상을 기대할 수 있습니다.  
   - 다만, 실제로 병렬 프로세스간 통신/메모리 문제가 발생할 수도 있으므로, 코어(프로세스) 수는 4나 5 정도가 적절합니다.

3. **에스페란토 특수문자 표기 변환**  
   - 앱 내부에서 “cx → ĉ”, “c^ → ĉ” 모두 대응해주지만, 반대로 **최종 출력을 c^ 형태로** 돌리고 싶다면 UI에서 “^ 형식” 버튼을 누르면 `circumflex_to_hat` 매핑이 적용되어 `ĉ`가 `c^`로 바뀝니다.

4. **HTML 루비 지원 범위**  
   - 최신 브라우저(Chrome, Firefox, Safari 등)에서 문제없이 보이지만, 구형 IE 등에선 `<ruby>`가 깨질 수 있습니다.  
   - 때문에 “괄호 형식” 또는 “단순 치환” 같은 텍스트 기반 출력 옵션도 제공하는 것으로 보입니다.

---

# 결론

- **`main.py`**: 최종 사용자 입장에서 “에스페란토 문장을 입력하고 치환 결과를 확인/다운로드” 하는 **메인 앱**.  
- **`에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py`**: “치환 규칙용 JSON”을 생성하는 **보조 페이지**.  
- **`esp_text_replacement_module.py` / `esp_replacement_json_make_module.py`**:  
  - 치환 로직, 병렬 처리, CSV→(old,new)매핑 변환, 접두/접미 파생 처리, HTML루비 사이즈 조정 등의 **핵심 알고리즘**이 담긴 **모듈**.

이 전체 구조를 이해하면,  
- **GUI적인 접근(어떻게 버튼을 눌러 텍스트를 치환하나?)**뿐 아니라,  
- 내부에서 **에스페란토 단어를 어떤 순서로, 어떤 우선순위로, 어떤 식으로 치환**하는지,  
- 사용자 정의 JSON/CSV를 어떻게 합쳐서 병렬 처리로 대량 변환**하는지까지 한눈에 파악할 수 있습니다.

**즉, 이 앱은 “문자열 치환 + 멀티프로세싱 + 정규표현식 + HTML 루비 처리”가 복합적으로 결합된 사례**이며, Python/Streamlit로 간단히 확장하거나 수정할 수 있게 구성되어 있습니다.  

중급 프로그래머 관점에서는,  
- **placeholder** 기반 “2단계 치환”  
- `%/@` 같은 마커로 국소/스킵 처리  
- 에스페란토 동사 활용/접미 처리  
- 병렬 처리(Spawn 모드) + Streamlit  
등이 재미있는 부분일 것입니다.  

이상으로 **앱 내부 메커니즘**을 정리해 보았습니다.  
추가로 직접 `esp_text_replacement_module.py`와 `esp_replacement_json_make_module.py`를 살펴보시면, “치환 우선순위 부여 로직”, “HTML 루비 크기 계산” 파트가 가장 핵심이라 느껴지실 것입니다.  

감사합니다.
