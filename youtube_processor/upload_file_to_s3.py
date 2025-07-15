import boto3
from botocore.exceptions import NoCredentialsError

def upload_file_to_s3(local_path, bucket_name, s3_key, region="ap-northeast-2"):
    """
    S3에 파일을 업로드하는 함수
    :param local_path: 로컬 파일 경로
    :param bucket_name: S3 버킷 이름
    :param s3_key: S3에 저장될 경로 (폴더/파일명 포함)
    """
    s3 = boto3.client('s3')

    try:
        s3.upload_file(local_path, bucket_name, s3_key)
        url = f"{s3_key}"
        print(f"✅ 업로드 성공: s3://{bucket_name}/{s3_key}")
        return url

    except FileNotFoundError as e:
          print(f"❌ 로컬 파일을 찾을 수 없습니다: {e.filename}")
    except NoCredentialsError as e:
        print("❌ AWS 자격 증명 오류 (credentials not found).")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

    return None

  
