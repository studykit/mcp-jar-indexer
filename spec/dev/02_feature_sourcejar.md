# 소스 등록 및 발견 전략

## 개요

Java/Kotlin 라이브러리의 소스 코드를 효율적으로 등록하고 찾아내는 전략입니다. JAR 파일, 로컬 디렉토리, Git 저장소 등 다양한 소스 형태를 지원하며, Claude Code의 능동적인 다운로드와 MCP 등록을 중심으로 단순하고 효과적인 접근 방식을 제공합니다.

## 전략 개요

### 단순화된 전략

1. **자체 캐시** (가장 빠름, 이미 인덱싱된 파일)
2. **register_source MCP 도구** (JAR 파일, 로컬 디렉토리, Git 저장소 지원)

## 상세 전략

### 1. 자체 캐시

![[02_architecture#캐시 구조]]

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

### 2. register_source MCP 도구

`register_source` MCP 도구가 다양한 소스 형태를 지원하여 모든 소스 등록 시나리오를 처리

**지원하는 source_uri 형태:**

#### JAR 파일

- **로컬 JAR (절대 경로)**: `file:///Users/user/.m2/repository/org/springframework/spring-core/5.3.21/spring-core-5.3.21-sources.jar`
- **로컬 JAR (상대 경로)**: `file://./lib/spring-core-5.3.21-sources.jar`
- **원격 JAR (Maven Central)**: `https://repo1.maven.org/maven2/org/springframework/spring-core/5.3.21/spring-core-5.3.21-sources.jar`
- **원격 JAR (사내 저장소)**: `https://nexus.company.com/repository/maven-public/org/springframework/spring-core/5.3.21/spring-core-5.3.21-sources.jar`

#### 로컬 디렉토리

- **소스 디렉토리**: `file:///Users/user/projects/spring-framework/spring-core/src/main/java`
- **프로젝트 루트**: `file:///Users/user/projects/my-library/src`
- **압축 해제된 소스**: `file:///tmp/spring-core-5.3.21-sources`

#### Git 저장소

- **GitHub 공개 저장소**: `git+https://github.com/spring-projects/spring-framework.git`
- **GitHub 사설 저장소**: `git+https://github.com/company/private-lib.git`
- **GitLab**: `git+https://gitlab.com/user/project.git`
- **사내 Git 서버**: `git+https://git.company.com/team/library.git`
- **SSH 접근**: `git+ssh://git@github.com/user/repo.git`

**워크플로 예시:**

**시나리오 1: 로컬 JAR 다운로드 후 등록**

1. JAR Indexer MCP가 아티팩트 부재 응답
2. Claude Code가 Maven/Gradle 명령 실행
   mvn dependency:sources -Dartifact=org.springframework:spring-core:5.3.21
3. 로컬 경로로 MCP 등록
   register_source(
   group_id="org.springframework",
   artifact_id="spring-core",
   version="5.3.21",
   source_uri="file:///Users/user/.m2/repository/org/springframework/spring-core/5.3.21/spring-core-5.3.21-sources.jar",
   auto_index=True
   )

**시나리오 2: 원격 JAR URL 직접 등록**

1. Claude Code가 Maven Central URL 직접 구성
2. URL로 MCP 등록 (다운로드 자동 처리)
   register_source(
   group_id="org.springframework",
   artifact_id="spring-core",
   version="5.3.21",
   source_uri="https://repo1.maven.org/maven2/org/springframework/spring-core/5.3.21/spring-core-5.3.21-sources.jar",
   auto_index=True
   )

**시나리오 3: Git 저장소 등록**

1. Claude Code가 GitHub 저장소 직접 등록
2. Git 저장소로 MCP 등록 (복제 및 특정 태그 체크아웃 자동 처리)
   register_source(
   group_id="org.springframework",
   artifact_id="spring-core",
   version="5.3.21",
   source_uri="git+https://github.com/spring-projects/spring-framework.git",
   git_ref="v5.3.21",
   auto_index=True
   )

**시나리오 4: 로컬 소스 디렉토리 등록**

1. 개발자가 로컬에서 작업 중인 라이브러리 등록
2. 소스 디렉토리로 MCP 등록
   ```python
   register_source(
       group_id="com.company",
       artifact_id="my-library",
       version="1.0.0-SNAPSHOT",
       source_uri="file:///Users/dev/projects/my-library/src/main/java",
       auto_index=True
   )
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
1. Claude Code에서 Maven/Gradle로 소스 JAR 다운로드:
   mvn dependency:sources -Dartifact={group_id}:{artifact_id}:{version}

2. register_source MCP 도구로 경로 등록:
   register_source(group_id, artifact_id, version, source_uri)

자세한 정보: https://docs.jar-indexer.com/troubleshooting
"""
```

이 전략으로 대부분의 개발 환경에서 소스 JAR을 효율적으로 찾을 수 있을 것입니다.
