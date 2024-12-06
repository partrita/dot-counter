import os
import cv2
import numpy as np
import pandas as pd
import argparse

def read_tiff_images(tiff_path):
    images = []
    success, images = cv2.imreadmulti(tiff_path, [], cv2.IMREAD_UNCHANGED)
    if not success:
        print(f'오류: {tiff_path} 파일을 읽을 수 없습니다.')
    return images

def count_red_dots(image):
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv_image, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv_image, lower_red2, upper_red2)
    red_mask = mask1 | mask2
    return cv2.countNonZero(red_mask)

def process_tiff_file(tiff_path):
    print(f"\n처리 중인 파일: {tiff_path}")
    
    images = read_tiff_images(tiff_path)
    
    print(f'로드된 이미지 수: {len(images)}')
    total_red_dots = 0
    for idx, img in enumerate(images):
        print(f'이미지 {idx + 1}: 크기 {img.shape}, 데이터 타입 {img.dtype}')
        red_dots = count_red_dots(img)
        total_red_dots += red_dots
        print(f'이미지 {idx + 1}의 붉은 점 개수: {red_dots}')
    
    print(f'{os.path.basename(tiff_path)}의 총 붉은 점 개수: {total_red_dots}')
    return total_red_dots

def process_tiff_files_recursively(root_folder):
    for root, dirs, files in os.walk(root_folder):
        tiff_files = [f for f in files if f.lower().endswith(('.tif', '.tiff'))]
        
        if tiff_files:
            red_dot_counts = {}
            for tiff_file in tiff_files:
                full_path = os.path.join(root, tiff_file)
                red_dot_counts[tiff_file] = process_tiff_file(full_path)
            
            if red_dot_counts:
                df = pd.DataFrame(red_dot_counts.items(), columns=['TIFF File', 'Red Dot Count'])
                
                # 'TIFF File' 열에서 '.tiff' 부분 제거
                df['TIFF File'] = df['TIFF File'].str.replace('.tiff', '', regex=False)

                try:
                    # 언더스코어를 기준으로 값을 분리하고 새로운 열 생성
                    split_result = df['TIFF File'].str.split('_', expand=True)
                    if split_result.shape[1] >= 3:
                        df['Number'] = split_result[0]
                        df['Date'] = split_result[1]
                        df['Time'] = split_result[2]
                    else:
                        print(f"경고: {root}의 일부 파일 이름이 예상 형식과 다릅니다.")
                        df['Number'] = df['TIFF File']
                        df['Date'] = pd.NaT
                        df['Time'] = pd.NaT

                    # Date와 Time을 결합하여 datetime 형식으로 변환
                    df['Datetime'] = pd.to_datetime(df['Date'] + df['Time'], format='%Y%m%d%H%M%S', errors='coerce')

                    # Number 열을 정수형으로 변환
                    df['Number'] = pd.to_numeric(df['Number'], errors='coerce')

                    # 필요한 열만 선택
                    df = df[['Datetime', 'Number', 'Red Dot Count']]

                    # Datetime과 Number로 정렬
                    sorted_df = df.sort_values(by=['Datetime', 'Number'])

                    # 인덱스 재설정
                    sorted_df = sorted_df.reset_index(drop=True)

                    # 시작 시간 계산
                    start_time = sorted_df['Datetime'].min()

                    # incubation hour 열 추가
                    sorted_df['incubation hour'] = (sorted_df['Datetime'] - start_time).dt.total_seconds() / 3600

                    csv_path = os.path.join(root, 'red_dot_counts_sorted.csv')
                    sorted_df.to_csv(csv_path, index=False)
                    print(f"\nCSV 파일이 저장되었습니다: {csv_path}")
                except Exception as e:
                    print(f"오류 발생: {root}에서 데이터 처리 중 문제가 발생했습니다.")
                    print(f"오류 메시지: {str(e)}")
                    print("이 폴더의 처리를 건너뛰고 다음 폴더로 진행합니다.")
                    
def main():
    parser = argparse.ArgumentParser(description='TIFF 파일의 붉은 점 개수를 계산하는 스크립트입니다.')
    parser.add_argument('--input', type=str, required=True, help='TIFF 파일이 있는 루트 폴더의 경로')
    args = parser.parse_args()

    print("현재 작업 디렉토리:", os.getcwd())
    print("대상 루트 폴더 경로:", args.input)

    process_tiff_files_recursively(args.input)

if __name__ == "__main__":
    main()