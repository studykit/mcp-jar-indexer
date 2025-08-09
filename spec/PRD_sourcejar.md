# 소스 JAR 위치 발견 전략 - Product Requirements Document

## 개요
Java/Kotlin 라이브러리의 소스 코드가 포함된 `-sources.jar` 파일을 효율적으로 찾아내는 전략입니다. 로컬 캐시부터 원격 저장소까지 단계적으로 탐색하여 최적의 성능을 제공합니다.

## 전략 개요

### Waterfall Pattern (폭포수 방식)
1. **자체 캐시** (가장 빠름, 검증된 파일)
2. **Maven 로컬 저장소** (빠름)
3. **Gradle 캐시** (빠름)
4. **원격 저장소 다운로드** (느림, 네트워크 필요)
5. **사용자 직접 제공** (수동, 마지막 수단)

## 상세 전략

### 1. 자체 캐시

**위치:** `~/.jar-indexer/downloads`

**구조:**
```
~/.jar-indexer/downloads/
├── org.springframework/
│   └── spring-core/
│       └── 5.3.21/
│           └── spring-core-5.3.21-sources.jar
├── com.fasterxml.jackson.core/
│   └── jackson-core/
│       └── 2.13.3/
│           └── jackson-core-2.13.3-sources.jar
└── ...
```

**구현:**
```python
def check_own_cache(group_id, artifact_id, version):
    cache_dir = os.path.expanduser("~/.jar-indexer/downloads")
    jar_filename = f"{artifact_id}-{version}-sources.jar"
    sources_jar = f"{cache_dir}/{group_id}/{artifact_id}/{version}/{jar_filename}"
    
    if os.path.exists(sources_jar):
        # 파일 무결성 검증 (선택사항)
        if is_valid_jar_file(sources_jar):
            return sources_jar
        else:
            # 손상된 파일 제거
            os.remove(sources_jar)
    return None
```

### 2. Maven 로컬 저장소 ($M2_REPO)

**위치:** `~/.m2/repository`

**구조:**
```
~/.m2/repository/
└── {group_id_path}/
    └── {artifact_id}/
        └── {version}/
            ├── {artifact_id}-{version}.jar
            ├── {artifact_id}-{version}-sources.jar  ← 목표
            └── {artifact_id}-{version}.pom
```

**예시:**
```
~/.m2/repository/org/springframework/spring-core/5.3.21/
├── spring-core-5.3.21.jar
├── spring-core-5.3.21-sources.jar
└── spring-core-5.3.21.pom
```

**구현:**
```python
def check_maven_local_repo(group_id, artifact_id, version):
    m2_home = os.path.expanduser("~/.m2/repository")
    group_path = group_id.replace('.', '/')
    artifact_path = f"{m2_home}/{group_path}/{artifact_id}/{version}"
    sources_jar = f"{artifact_path}/{artifact_id}-{version}-sources.jar"
    
    if os.path.exists(sources_jar):
        # 자체 캐시에 복사하여 저장
        return copy_to_own_cache(sources_jar, group_id, artifact_id, version)
    return None
```

### 3. Gradle 캐시

**위치:** `~/.gradle/caches/modules-2/files-2.1`

**구조:**
```
~/.gradle/caches/modules-2/files-2.1/
└── {group_id}/
    └── {artifact_id}/
        └── {version}/
            ├── {hash1}/
            │   └── {artifact_id}-{version}.jar
            ├── {hash2}/
            │   └── {artifact_id}-{version}-sources.jar  ← 목표
            └── {hash3}/
                └── {artifact_id}-{version}.pom
```

**예시:**
```
~/.gradle/caches/modules-2/files-2.1/org.springframework/spring-core/5.3.21/
├── a1b2c3d4e5f6.../spring-core-5.3.21.jar
├── f6e5d4c3b2a1.../spring-core-5.3.21-sources.jar
└── 9z8y7x6w5v4u.../spring-core-5.3.21.pom
```

**구현:**
```python
def check_gradle_cache(group_id, artifact_id, version):
    gradle_home = os.path.expanduser("~/.gradle/caches/modules-2/files-2.1")
    artifact_dir = f"{gradle_home}/{group_id}/{artifact_id}/{version}"
    
    if not os.path.exists(artifact_dir):
        return None
        
    # 해시 디렉토리들을 스캔
    for hash_dir in os.listdir(artifact_dir):
        hash_path = f"{artifact_dir}/{hash_dir}"
        if os.path.isdir(hash_path):
            sources_jar = f"{hash_path}/{artifact_id}-{version}-sources.jar"
            if os.path.exists(sources_jar):
                # 자체 캐시에 복사하여 저장
                return copy_to_own_cache(sources_jar, group_id, artifact_id, version)
    return None
```

### 4. 원격 저장소 다운로드

**지원 저장소:**
1. **Maven Central** - `https://repo1.maven.org/maven2`
2. **사내 Nexus** - 설정에서 URL 지정
3. **기타 공개 저장소** - Apache, Spring 등

**URL 패턴:**
```
{repository_base_url}/{group_path}/{artifact_id}/{version}/{artifact_id}-{version}-sources.jar
```

**예시:**
```
https://repo1.maven.org/maven2/org/springframework/spring-core/5.3.21/spring-core-5.3.21-sources.jar
```

**구현:**
```python
def download_from_remote(group_id, artifact_id, version):
    repositories = get_configured_repositories()
    
    group_path = group_id.replace('.', '/')
    jar_name = f"{artifact_id}-{version}-sources.jar"
    
    for repo_config in repositories:
        url = f"{repo_config['url']}/{group_path}/{artifact_id}/{version}/{jar_name}"
        
        try:
            response = requests.get(
                url, 
                timeout=30,
                headers=repo_config.get('headers', {}),
                auth=repo_config.get('auth', None)
            )
            
            if response.status_code == 200:
                return save_to_own_cache(response.content, group_id, artifact_id, version)
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to download from {url}: {e}")
            continue
    
    return None
```

### 5. 사용자 직접 제공

자동 발견이 모두 실패한 경우, 사용자에게 소스 JAR 경로를 직접 요청하는 인터랙티브 방식

**시나리오:**
- 사내 사설 저장소에만 있는 라이브러리
- 로컬에 수동으로 다운로드한 소스 JAR
- 커스텀 빌드된 라이브러리

**구현:**
```python
def prompt_user_for_sources_jar(group_id, artifact_id, version):
    """사용자에게 소스 JAR 경로를 요청"""
    print(f"\n소스 JAR을 찾을 수 없습니다: {group_id}:{artifact_id}:{version}")
    print("다음 위치에서 소스 JAR 파일을 찾아보세요:")
    print(f"  - IDE Downloads 폴더")
    print(f"  - {group_id.replace('.', '/')}/{artifact_id}/{version}/ 경로")
    print(f"  - {artifact_id}-{version}-sources.jar 파일명")
    
    while True:
        user_path = input("\n소스 JAR 파일 경로를 입력하세요 (취소: q): ").strip()
        
        if user_path.lower() == 'q':
            return None
            
        if not user_path:
            print("경로를 입력해주세요.")
            continue
            
        # 경로 확장 (~ 등)
        expanded_path = os.path.expanduser(user_path)
        
        if not os.path.exists(expanded_path):
            print(f"파일을 찾을 수 없습니다: {expanded_path}")
            continue
            
        if not expanded_path.endswith('-sources.jar'):
            print("소스 JAR 파일이어야 합니다 (파일명이 -sources.jar로 끝나야 함)")
            continue
            
        if not is_valid_jar_file(expanded_path):
            print("유효하지 않은 JAR 파일입니다.")
            continue
            
        # 유효한 파일이므로 자체 캐시에 복사
        try:
            cached_path = copy_to_own_cache(expanded_path, group_id, artifact_id, version)
            print(f"✓ 소스 JAR이 캐시에 저장되었습니다: {cached_path}")
            return cached_path
        except Exception as e:
            print(f"캐시 저장 실패: {e}")
            continue

def prompt_user_for_sources_jar_non_interactive(group_id, artifact_id, version):
    """비대화형 환경을 위한 사용자 가이드 메시지"""
    guidance = f"""
소스 JAR을 찾을 수 없습니다: {group_id}:{artifact_id}:{version}

해결 방법:
1. IDE에서 해당 라이브러리의 소스를 다운로드
2. Maven/Gradle에서 sources classifier 추가:
   Maven: <classifier>sources</classifier>
   Gradle: implementation '{group_id}:{artifact_id}:{version}:sources'
3. 수동으로 소스 JAR 다운로드 후 설정 파일에 경로 추가:
   ~/.jar-indexer/user-provided.json

설정 파일 예시:
{{
  "user_provided_jars": {{
    "{group_id}:{artifact_id}:{version}": "/path/to/{artifact_id}-{version}-sources.jar"
  }}
}}
"""
    print(guidance)
    return None

def get_configured_repositories():
    return [
        {
            "name": "Maven Central",
            "url": "https://repo1.maven.org/maven2",
            "priority": 1
        },
        {
            "name": "Company Nexus",
            "url": get_nexus_url_from_config(),
            "headers": get_nexus_headers(),
            "auth": get_nexus_auth(),
            "priority": 0  # 높은 우선순위
        }
    ]
```

## 통합 구현

### 메인 함수
```python
def find_sources_jar(group_id, artifact_id, version):
    """
    소스 JAR 파일을 찾는 메인 함수
    
    Args:
        group_id: Maven group ID (e.g., "org.springframework")
        artifact_id: Maven artifact ID (e.g., "spring-core")
        version: 버전 (e.g., "5.3.21")
    
    Returns:
        str: 소스 JAR 파일의 절대 경로
        
    Raises:
        SourcesJarNotFound: 소스 JAR을 찾을 수 없는 경우
    """
    
    logger.info(f"Looking for sources JAR: {group_id}:{artifact_id}:{version}")
    
    # 1순위: 자체 캐시
    logger.debug("Checking own cache...")
    sources_jar = check_own_cache(group_id, artifact_id, version)
    if sources_jar:
        logger.info(f"Found in own cache: {sources_jar}")
        return sources_jar
    
    # 2순위: Maven 로컬 저장소
    logger.debug("Checking Maven local repository...")
    sources_jar = check_maven_local_repo(group_id, artifact_id, version)
    if sources_jar:
        logger.info(f"Found in Maven local repo: {sources_jar}")
        return sources_jar
    
    # 3순위: Gradle 캐시
    logger.debug("Checking Gradle cache...")
    sources_jar = check_gradle_cache(group_id, artifact_id, version)
    if sources_jar:
        logger.info(f"Found in Gradle cache: {sources_jar}")
        return sources_jar
    
    # 4순위: 원격 다운로드
    logger.debug("Downloading from remote repositories...")
    sources_jar = download_from_remote(group_id, artifact_id, version)
    if sources_jar:
        logger.info(f"Downloaded and cached: {sources_jar}")
        return sources_jar
    
    # 5순위: 사용자 직접 제공 (대화형 환경에서만)
    logger.debug("Prompting user for sources JAR...")
    if is_interactive_environment():
        sources_jar = prompt_user_for_sources_jar(group_id, artifact_id, version)
        if sources_jar:
            logger.info(f"User provided sources JAR: {sources_jar}")
            return sources_jar
    else:
        # 비대화형 환경에서는 가이드 메시지만 출력
        prompt_user_for_sources_jar_non_interactive(group_id, artifact_id, version)
    
    # 완전 실패
    error_msg = f"No sources JAR found for {group_id}:{artifact_id}:{version}"
    logger.error(error_msg)
    raise SourcesJarNotFound(error_msg)
```

### 보조 함수들
```python
def save_to_own_cache(jar_content, group_id, artifact_id, version):
    """다운로드한 JAR을 자체 캐시에 저장"""
    cache_dir = os.path.expanduser("~/.jar-indexer/downloads")
    cache_path = f"{cache_dir}/{group_id}/{artifact_id}/{version}"
    os.makedirs(cache_path, exist_ok=True)
    
    jar_filename = f"{artifact_id}-{version}-sources.jar"
    full_path = f"{cache_path}/{jar_filename}"
    
    with open(full_path, 'wb') as f:
        f.write(jar_content)
    
    logger.info(f"Cached sources JAR: {full_path}")
    return full_path

def copy_to_own_cache(source_jar_path, group_id, artifact_id, version):
    """기존 JAR 파일을 자체 캐시에 복사"""
    import shutil
    
    cache_dir = os.path.expanduser("~/.jar-indexer/downloads")
    cache_path = f"{cache_dir}/{group_id}/{artifact_id}/{version}"
    os.makedirs(cache_path, exist_ok=True)
    
    jar_filename = f"{artifact_id}-{version}-sources.jar"
    full_path = f"{cache_path}/{jar_filename}"
    
    # 파일 복사
    shutil.copy2(source_jar_path, full_path)
    
    logger.info(f"Copied to cache: {source_jar_path} -> {full_path}")
    return full_path

def is_valid_jar_file(jar_path):
    """JAR 파일의 유효성 검증"""
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            # 기본적인 ZIP 구조 검증
            jar.testzip()
            return True
    except (zipfile.BadZipFile, FileNotFoundError):
        return False

def is_interactive_environment():
    """대화형 환경 여부 확인"""
    import sys
    return sys.stdin.isatty()

class SourcesJarNotFound(Exception):
    """소스 JAR을 찾을 수 없을 때 발생하는 예외"""
    pass
```

## 설정 관리

### 설정 파일 예시 (config.json)
```json
{
  "repositories": [
    {
      "name": "Company Nexus",
      "url": "https://nexus.company.com/repository/maven-public",
      "priority": 0,
      "auth": {
        "username": "${NEXUS_USERNAME}",
        "password": "${NEXUS_PASSWORD}"
      }
    },
    {
      "name": "Maven Central",
      "url": "https://repo1.maven.org/maven2",
      "priority": 1
    }
  ],
  "cache": {
    "directory": "~/.jar-indexer/downloads",
    "max_size_mb": 1000,
    "cleanup_after_days": 30
  },
  "download": {
    "timeout_seconds": 30,
    "max_retries": 3,
    "concurrent_downloads": 3
  }
}
```

## 성능 최적화

### 1. 병렬 다운로드
```python
import asyncio
import aiohttp

async def download_from_multiple_repos(group_id, artifact_id, version):
    """여러 저장소에서 동시에 다운로드 시도"""
    repositories = get_configured_repositories()
    
    async def try_download(session, repo_config):
        url = build_download_url(repo_config, group_id, artifact_id, version)
        try:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    content = await response.read()
                    return save_to_own_cache(content, group_id, artifact_id, version)
        except Exception:
            return None
    
    async with aiohttp.ClientSession() as session:
        tasks = [try_download(session, repo) for repo in repositories]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 첫 번째 성공한 결과 반환
        for result in results:
            if result and not isinstance(result, Exception):
                return result
    
    return None
```

### 2. 캐시 무효화
```python
def is_cache_valid(cache_path, max_age_days=30):
    """캐시 파일의 유효성 검사"""
    if not os.path.exists(cache_path):
        return False
    
    file_age = time.time() - os.path.getmtime(cache_path)
    max_age = max_age_days * 24 * 60 * 60  # 초 단위
    
    return file_age < max_age and is_valid_jar_file(cache_path)
```

## 에러 처리 및 로깅

### 예외 클래스
```python
class SourcesJarError(Exception):
    """소스 JAR 관련 기본 예외"""
    pass

class SourcesJarNotFound(SourcesJarError):
    """소스 JAR을 찾을 수 없는 경우"""
    pass

class SourcesJarCorrupted(SourcesJarError):
    """소스 JAR 파일이 손상된 경우"""
    pass

class DownloadFailure(SourcesJarError):
    """다운로드 실패"""
    pass
```

### 사용자 친화적 메시지
```python
def get_user_friendly_error_message(group_id, artifact_id, version):
    return f"""
소스 코드를 찾을 수 없습니다: {group_id}:{artifact_id}:{version}

다음 방법을 시도해보세요:
1. IDE에서 해당 라이브러리의 소스를 다운로드했는지 확인
2. Maven/Gradle에서 sources classifier를 명시적으로 의존성에 추가
3. 사내 저장소 설정이 올바른지 확인

자세한 정보: https://docs.jar-indexer.com/troubleshooting
"""
```

## 테스트 전략

### 단위 테스트 예시
```python
import pytest
from unittest.mock import patch, MagicMock

class TestSourcesJarFinder:
    
    def test_maven_local_repo_found(self):
        with patch('os.path.exists', return_value=True):
            result = check_maven_local_repo("org.example", "test-lib", "1.0.0")
            expected = os.path.expanduser("~/.m2/repository/org/example/test-lib/1.0.0/test-lib-1.0.0-sources.jar")
            assert result == expected
    
    def test_maven_local_repo_not_found(self):
        with patch('os.path.exists', return_value=False):
            result = check_maven_local_repo("org.example", "test-lib", "1.0.0")
            assert result is None
    
    @patch('requests.get')
    def test_download_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake jar content'
        mock_get.return_value = mock_response
        
        with patch('jar_finder.save_to_own_cache', return_value='/cache/path'):
            result = download_from_remote("org.example", "test-lib", "1.0.0")
            assert result == '/cache/path'
```

이 전략으로 대부분의 개발 환경에서 소스 JAR을 효율적으로 찾을 수 있을 것입니다.