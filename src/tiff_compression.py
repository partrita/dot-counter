import os
import tifffile

# 데이터 및 결과 폴더 경로 설정
Data_folder = "../input/demo"  # 입력 폴더 경로
Result_folder = "../output/demo"  # 출력 폴더 경로

# 결과 폴더가 존재하지 않으면 생성
if not os.path.exists(Result_folder):
    os.makedirs(Result_folder)

# 입력 폴더 내의 모든 TIFF 파일 처리
for image in os.listdir(Data_folder):
    if image.lower().endswith(('.tiff', '.tif')):  # TIFF 파일 필터링
        # TIFF 파일 읽기
        file_path = os.path.join(Data_folder, image)
        prediction_stack_16 = tifffile.imread(file_path)
        
        # 파일 이름에서 확장자 제거
        name, _ = os.path.splitext(image)
        
        # 압축된 TIFF 파일로 저장
        output_file_path = os.path.join(Result_folder, f"{name}_compressed.tif")
        # 무손실
        # tifffile.imwrite(output_file_path, prediction_stack_16, metadata={'axes': 'XYZC'}, compression='lzw')
        tifffile.imwrite(output_file_path, prediction_stack_16, metadata={'axes': 'XYZC'}, compression='zlib')

print("모든 TIFF 파일이 성공적으로 압축되었습니다.")
