import os
from typing import List, Dict, Optional
from datetime import datetime
import cv2
import numpy as np
import pandas as pd
import click


def read_tiff_images(tiff_path: str) -> List[np.ndarray]:
    """TIFF 파일에서 모든 이미지를 읽어옵니다."""
    images: List[np.ndarray] = []
    success: bool
    success, images = cv2.imreadmulti(tiff_path, [], cv2.IMREAD_UNCHANGED)
    if not success:
        print(f"오류: {tiff_path} 파일을 읽을 수 없습니다.")
    return images


def count_red_dots(image: np.ndarray) -> int:
    """이미지에서 붉은 점의 개수를 세어 반환합니다."""
    hsv_image: np.ndarray = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 붉은색 범위 정의 (HSV)
    lower_red1: np.ndarray = np.array([0, 100, 100])
    upper_red1: np.ndarray = np.array([10, 255, 255])
    lower_red2: np.ndarray = np.array([160, 100, 100])
    upper_red2: np.ndarray = np.array([180, 255, 255])

    # 마스크 생성
    mask1: np.ndarray = cv2.inRange(hsv_image, lower_red1, upper_red1)
    mask2: np.ndarray = cv2.inRange(hsv_image, lower_red2, upper_red2)
    red_mask: np.ndarray = mask1 | mask2

    return cv2.countNonZero(red_mask)


def process_tiff_file(tiff_path: str) -> int:
    """단일 TIFF 파일을 처리하여 총 붉은 점 개수를 반환합니다."""

    images: List[np.ndarray] = read_tiff_images(tiff_path)
    total_red_dots: int = 0

    for idx, img in enumerate(images):
        red_dots: int = count_red_dots(img)
        total_red_dots += red_dots

    return total_red_dots


def process_tiff_files_recursively(
    root_folder: str, output_path: Optional[str] = None
) -> None:
    """루트 폴더에서 재귀적으로 TIFF 파일들을 찾아 처리합니다."""
    # 실행 시간을 한 번만 계산
    execution_time: str = datetime.now().strftime("%Y%m%d_%H%M%S")

    for root, dirs, files in os.walk(root_folder):
        tiff_files: List[str] = [
            f for f in files if f.lower().endswith((".tif", ".tiff"))
        ]

        if tiff_files:
            red_dot_counts: Dict[str, int] = {}

            for tiff_file in tiff_files:
                full_path: str = os.path.join(root, tiff_file)
                red_dot_counts[tiff_file] = process_tiff_file(full_path)

            if red_dot_counts:
                df: pd.DataFrame = pd.DataFrame(
                    red_dot_counts.items(), columns=["TIFF File", "Red Dot Count"]
                )

                # 'TIFF File' 열에서 '.tiff' 부분 제거
                df["TIFF File"] = df["TIFF File"].str.replace(".tiff", "", regex=False)

                try:
                    # 언더스코어를 기준으로 값을 분리하고 새로운 열 생성
                    split_result: pd.DataFrame = df["TIFF File"].str.split(
                        "_", expand=True
                    )

                    if split_result.shape[1] >= 3:
                        df["Number"] = split_result[0]
                        df["Date"] = split_result[1]
                        df["Time"] = split_result[2]
                    else:
                        print(f"경고: {root}의 일부 파일 이름이 예상 형식과 다릅니다.")
                        df["Number"] = df["TIFF File"]
                        df["Date"] = pd.NaT
                        df["Time"] = pd.NaT

                    # Date와 Time을 결합하여 datetime 형식으로 변환
                    df["Datetime"] = pd.to_datetime(
                        df["Date"] + df["Time"], format="%Y%m%d%H%M%S", errors="coerce"
                    )

                    # Number 열을 정수형으로 변환
                    df["Number"] = pd.to_numeric(df["Number"], errors="coerce")

                    # 필요한 열만 선택
                    df = df[["Datetime", "Number", "Red Dot Count"]]

                    # Datetime과 Number로 정렬
                    sorted_df: pd.DataFrame = df.sort_values(by=["Datetime", "Number"])

                    # 인덱스 재설정
                    sorted_df = sorted_df.reset_index(drop=True)

                    # 시작 시간 계산
                    start_time: pd.Timestamp = sorted_df["Datetime"].min()

                    # incubation hour 열 추가
                    sorted_df["incubation hour"] = (
                        sorted_df["Datetime"] - start_time
                    ).dt.total_seconds() / 3600

                    # 출력 경로 결정
                    if output_path:
                        # 지정된 출력 디렉토리에 저장
                        filename: str = f"count_{execution_time}.csv"
                        csv_path: str = os.path.join(output_path, filename)
                    else:
                        # 원본 폴더에 저장 (기존 방식)
                        csv_path: str = os.path.join(root, "red_dot_counts_sorted.csv")

                    sorted_df.to_csv(csv_path, index=False)
                    print(f"\nCSV 파일이 저장되었습니다: {csv_path}")

                except Exception as e:
                    print(f"오류 발생: {root}에서 데이터 처리 중 문제가 발생했습니다.")
                    print(f"오류 메시지: {str(e)}")
                    print("이 폴더의 처리를 건너뛰고 다음 폴더로 진행합니다.")


@click.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    required=True,
    help="TIFF 파일이 있는 루트 폴더의 경로",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    required=False,
    help="CSV 파일을 저장할 출력 디렉토리 경로 (지정하지 않으면 TIFF 폴더에 저장)",
)
def main(input: str, output: Optional[str]) -> None:
    """TIFF 파일의 붉은 점 개수를 계산하는 스크립트입니다.

    지정된 루트 폴더에서 재귀적으로 TIFF 파일을 찾아 각 파일의 붉은 점을 세고,
    결과를 CSV 파일로 저장합니다.

    출력 파일명: count_YYYYMMDD_HHMMSS.csv (출력 디렉토리 지정 시)
    """
    print("현재 작업 디렉토리:", os.getcwd())
    print("대상 루트 폴더 경로:", input)

    if output:
        # 출력 디렉토리가 존재하지 않으면 생성
        os.makedirs(output, exist_ok=True)
        print("출력 디렉토리:", output)
        execution_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"출력 파일명: count_{execution_time}.csv")

    process_tiff_files_recursively(input, output)


if __name__ == "__main__":
    main()
