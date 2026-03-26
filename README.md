# Rodi Agent

Rodi Agent의 주요 기능(실행, 평가, 대시보드)을 사용하는 간략한 방법입니다.

## 1. 에이전트 실행 (`main.py`)

에이전트는 두 가지 방식으로 실행할 수 있습니다.

- **대화형 모드 (Interactive Mode)**
  터미널에서 사용자와 직접 상호작용하며 명령(Instruction)을 입력받아 코드를 단건으로 생성합니다.
  ```bash
  python main.py
  ```

- **배치 모드 (Batch Mode)**
  사전에 정의된 여러 개의 명령과 코드가 담긴 테스트 파일(`.json`)을 바탕으로 일괄 처리합니다.
  ```bash
  python main.py --test [테스트_파일_경로]
  # (예시) python main.py --test data/test.json
  ```

## 2. 생성된 코드 평가 (`evaluate.py`)

생성된 코드가 포함된 결과물(Result directory)을 정답(Ground truth)과 비교하여 평가합니다. 모델의 생성물과 정답의 논리적 API 파라미터가 동일한지 판단합니다.

```bash
python evaluate.py [결과_디렉토리_경로] --config [설정_파일_경로]
# (예시) python evaluate.py result/MiniMaxAI --config configs/openai_config.json
```

평가 완료 후, 결과 디렉토리에는 `evaluation_summary.json` 파일이 추가로 생성됩니다.

## 3. 대시보드 확인 (`dashboard.py`)

Streamlit을 바탕으로 제공되는 웹 UI를 통해 평가 결과를 시각적으로 확인하고 에이전트 명령을 사용할 수 있습니다.

```bash
streamlit run dashboard.py
```

- **Results Viewer**: 각 모델별 정확도 측정, 통과 여부 및 내부(agent tools 등) 실행 내역(Trace) 확인 기능
- **Interactive Generation**: 웹 형태의 UI를 통해 명령 하달 후 코드 생성 과정을 실시간으로 확인하는 기능
