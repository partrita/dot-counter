# 세포 이미지에서 붉은 형광 측정하기

## 설치법

`uv`를 사용해 파이썬 라이브러리를 관리했다. repository를 clone해서 `uv sync` 명령어를 설치할 수 있다.

## 사용법

1. 세포 이미지를 tiff 포멧으로 저장해서 폴더에 넣는다.
2. 루트폴더에서 다음 명령어를 실행해서 붉은 형광의 값을 숫자로 측정해 csv파일로 저장한다.

```bash
!uv run src/red_dot_count.py --input /path/to/tiff/folder
```

- csv파일은 이미지가 있는 폴더에 자동 저장된다.

3. csv 파일을 읽어서 데이터 분석을 진행한다.
    - ipynb 폴더에 시각화를 진행한 내용이 저장되어 있다.

## 도움말

```bash
!uv run src/red_dot_count.py --help
```
