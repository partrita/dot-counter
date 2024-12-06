use std::fs;
use std::path::{Path, PathBuf};
use std::error::Error;
use opencv::{core, imgcodecs, imgproc, prelude::*};
use chrono::{NaiveDateTime, Duration};
use polars::prelude::*;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(name = "tiff_processor", about = "TIFF 파일의 붉은 점 개수를 계산하는 스크립트입니다.")]
struct Opt {
    #[structopt(short, long, parse(from_os_str))]
    input: PathBuf,
}

fn read_tiff_images(tiff_path: &Path) -> Result<Vec<Mat>, Box<dyn Error>> {
    let mut images = Vec::new();
    let mut success = false;
    imgcodecs::imreadmulti(tiff_path.to_str().unwrap(), &mut images, imgcodecs::IMREAD_UNCHANGED)?;
    if images.is_empty() {
        println!("오류: {} 파일을 읽을 수 없습니다.", tiff_path.display());
        success = false;
    } else {
        success = true;
    }
    if !success {
        Err("Failed to read TIFF file".into())
    } else {
        Ok(images)
    }
}

fn count_red_dots(image: &Mat) -> Result<i32, Box<dyn Error>> {
    let mut hsv_image = Mat::default();
    imgproc::cvt_color(&image, &mut hsv_image, imgproc::COLOR_BGR2HSV, 0)?;

    let lower_red1 = core::Scalar::new(0.0, 100.0, 100.0, 0.0);
    let upper_red1 = core::Scalar::new(10.0, 255.0, 255.0, 0.0);
    let lower_red2 = core::Scalar::new(160.0, 100.0, 100.0, 0.0);
    let upper_red2 = core::Scalar::new(180.0, 255.0, 255.0, 0.0);

    let mut mask1 = Mat::default();
    let mut mask2 = Mat::default();
    core::in_range(&hsv_image, &lower_red1, &upper_red1, &mut mask1)?;
    core::in_range(&hsv_image, &lower_red2, &upper_red2, &mut mask2)?;

    let mut red_mask = Mat::default();
    core::bitwise_or(&mask1, &mask2, &mut red_mask, &Mat::default())?;

    Ok(core::count_non_zero(&red_mask)?)
}

fn process_tiff_file(tiff_path: &Path) -> Result<i32, Box<dyn Error>> {
    println!("\n처리 중인 파일: {}", tiff_path.display());

    let images = read_tiff_images(tiff_path)?;

    println!("로드된 이미지 수: {}", images.len());
    let mut total_red_dots = 0;
    for (idx, img) in images.iter().enumerate() {
        println!("이미지 {}: 크기 {:?}, 데이터 타입 {:?}", idx + 1, img.size()?, img.typ());
        let red_dots = count_red_dots(img)?;
        total_red_dots += red_dots;
        println!("이미지 {}의 붉은 점 개수: {}", idx + 1, red_dots);
    }

    println!("{}의 총 붉은 점 개수: {}", tiff_path.file_name().unwrap().to_str().unwrap(), total_red_dots);
    Ok(total_red_dots)
}

fn process_tiff_files_recursively(root_folder: &Path) -> Result<(), Box<dyn Error>> {
    for entry in fs::read_dir(root_folder)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            process_tiff_files_recursively(&path)?;
        } else if let Some(extension) = path.extension() {
            if extension.to_str().map(|s| s.to_lowercase()) == Some("tif".to_string())
                || extension.to_str().map(|s| s.to_lowercase()) == Some("tiff".to_string())
            {
                let mut red_dot_counts = Vec::new();
                let red_dot_count = process_tiff_file(&path)?;
                red_dot_counts.push((path.file_name().unwrap().to_str().unwrap().to_string(), red_dot_count));

                if !red_dot_counts.is_empty() {
                    let mut df = DataFrame::new(vec![
                        Series::new("TIFF File", red_dot_counts.iter().map(|(name, _)| name.clone()).collect::<Vec<String>>()),
                        Series::new("Red Dot Count", red_dot_counts.iter().map(|(_, count)| *count).collect::<Vec<i32>>()),
                    ])?;

                    df.apply("TIFF File", |s| s.str()?.replace(".tiff", ""))?;

                    let split_result: Vec<Vec<&str>> = df.column("TIFF File")?
                        .utf8()?
                        .into_iter()
                        .map(|opt_s| opt_s.map(|s| s.split('_').collect()).unwrap_or_default())
                        .collect();

                    if split_result.iter().all(|v| v.len() >= 3) {
                        df.with_column(Series::new("Number", split_result.iter().map(|v| v[0]).collect::<Vec<&str>>()))?;
                        df.with_column(Series::new("Date", split_result.iter().map(|v| v[1]).collect::<Vec<&str>>()))?;
                        df.with_column(Series::new("Time", split_result.iter().map(|v| v[2]).collect::<Vec<&str>>()))?;
                    } else {
                        println!("경고: {}의 일부 파일 이름이 예상 형식과 다릅니다.", path.display());
                        df.with_column(Series::new("Number", df.column("TIFF File")?.clone()))?;
                        df.with_column(Series::new("Date", vec![None; df.height()]))?;
                        df.with_column(Series::new("Time", vec![None; df.height()]))?;
                    }

                    df.with_column(
                        df.column("Date")?
                            .utf8()?
                            .into_iter()
                            .zip(df.column("Time")?.utf8()?.into_iter())
                            .map(|(date, time)| {
                                date.and_then(|d| time.map(|t| format!("{}{}", d, t)))
                                    .and_then(|dt| NaiveDateTime::parse_from_str(&dt, "%Y%m%d%H%M%S").ok())
                            })
                            .collect::<Series>()
                            .rename("Datetime"),
                    )?;

                    df.with_column(
                        df.column("Number")?
                            .cast(&DataType::Int64)
                            .unwrap_or_else(|_| Series::new("Number", vec![None; df.height()])),
                    )?;

                    df = df.select(["Datetime", "Number", "Red Dot Count"])?;

                    df = df.sort(["Datetime", "Number"], vec![false, false])?;

                    let start_time = df.column("Datetime")?.datetime()?.min()?;

                    df.with_column(
                        df.column("Datetime")?
                            .datetime()?
                            .into_iter()
                            .map(|opt_dt| {
                                opt_dt.map(|dt| {
                                    (dt - start_time).num_seconds() as f64 / 3600.0
                                })
                            })
                            .collect::<Series>()
                            .rename("incubation hour"),
                    )?;

                    let csv_path = path.with_file_name("red_dot_counts_sorted.csv");
                    CsvWriter::new(fs::File::create(csv_path)?).finish(&df)?;
                    println!("\nCSV 파일이 저장되었습니다: {}", csv_path.display());
                }
            }
        }
    }
    Ok(())
}

fn main() -> Result<(), Box<dyn Error>> {
    let opt = Opt::from_args();

    println!("현재 작업 디렉토리: {}", std::env::current_dir()?.display());
    println!("대상 루트 폴더 경로: {}", opt.input.display());

    process_tiff_files_recursively(&opt.input)?;

    Ok(())
}