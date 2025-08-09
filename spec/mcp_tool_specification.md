# JAR Indexer MCP Tools - Product Requirements Document

## 개요
Java/Kotlin JAR 파일의 소스 코드를 인덱싱하고 Claude Code가 외부 라이브러리 소스를 효율적으로 탐색할 수 있게 하는 MCP 서버입니다.

## MCP Tools 목록 (14개)

### 0. register_source
사용자가 직접 제공한 소스 JAR 파일 또는 소스 디렉토리를 시스템에 등록

**사용 시나리오:**
- Claude Code가 Maven/Gradle로 소스 JAR을 다운로드한 후 URI 전달
- IDE에서 다운로드한 소스 JAR 파일 직접 등록
- 수동으로 다운로드한 소스 JAR 파일 등록
- 로컬에 압축 해제된 소스 디렉토리 등록
- 개발 중인 라이브러리의 src 디렉토리 등록
- GitHub/GitLab의 오픈소스 라이브러리 특정 버전 등록
- 사내 Git 저장소의 특정 브랜치/태그 등록

**Request:**
```python
register_source(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    source_uri: "git+https://github.com/spring-projects/spring-framework.git",
    auto_index: True,  # 선택사항, 기본값: True (등록 후 자동 인덱싱 여부)
    git_ref: "v5.3.21"  # 선택사항, Git URI인 경우 태그/브랜치/커밋 SHA 지정
)
```

**source_uri 형태:**

### JAR 파일
- **로컬 JAR (절대 경로)**: `file:///Users/user/.m2/repository/org/springframework/spring-core/5.3.21/spring-core-5.3.21-sources.jar`
- **로컬 JAR (상대 경로)**: `file://./lib/spring-core-5.3.21-sources.jar`
- **원격 JAR (Maven Central)**: `https://repo1.maven.org/maven2/org/springframework/spring-core/5.3.21/spring-core-5.3.21-sources.jar`
- **원격 JAR (사내 저장소)**: `https://nexus.company.com/repository/maven-public/org/springframework/spring-core/5.3.21/spring-core-5.3.21-sources.jar`

### 로컬 디렉토리
- **소스 디렉토리**: `file:///Users/user/projects/spring-framework/spring-core/src/main/java`
- **프로젝트 루트**: `file:///Users/user/projects/my-library/src`
- **압축 해제된 소스**: `file:///tmp/spring-core-5.3.21-sources`

### Git 저장소
- **GitHub 공개 저장소**: `git+https://github.com/spring-projects/spring-framework.git`
- **GitHub 사설 저장소**: `git+https://github.com/company/private-lib.git`
- **GitLab**: `git+https://gitlab.com/user/project.git`
- **사내 Git 서버**: `git+https://git.company.com/team/library.git`
- **SSH 접근**: `git+ssh://git@github.com/user/repo.git`

**git_ref 파라미터 (Git URI인 경우):**
- **태그**: `"v5.3.21"`, `"1.0.0"`, `"release-2023.12"`
- **브랜치**: `"main"`, `"develop"`, `"feature/new-api"`  
- **커밋 SHA**: `"a1b2c3d4e5f6"`
- **생략시 기본값**: `"main"` 또는 저장소 기본 브랜치

**Response (auto_index=True, 기본값):**
```json
{
  "group_id": "org.springframework",
  "artifact_id": "spring-core", 
  "version": "5.3.21",
  "status": "registered_and_indexed",
  "indexed": true
}
```

**Response (auto_index=False):**
```json
{
  "group_id": "org.springframework",
  "artifact_id": "spring-core",
  "version": "5.3.21",
  "status": "registered_only",
  "indexed": false,
  "message": "소스가 등록되었습니다. index_artifact 도구로 인덱싱을 수행하세요."
}
```

**Error Response:**
```json
{
  "error": {
    "type": "ResourceNotFound", 
    "message": "소스를 찾을 수 없습니다: file:///invalid/path/spring-core-5.3.21-sources.jar"
  }
}
```

```json
{
  "error": {
    "type": "DownloadFailed",
    "message": "원격 소스 다운로드 실패: https://invalid-url.com/spring-core-5.3.21-sources.jar"
  }
}
```

```json
{
  "error": {
    "type": "InvalidSource",
    "message": "유효하지 않은 소스입니다: file:///path/to/corrupted.jar"
  }
}
```

```json
{
  "error": {
    "type": "UnsupportedSourceType", 
    "message": "지원하지 않는 소스 형태입니다. JAR 파일, Java/Kotlin 소스 디렉토리, 또는 Git 저장소만 지원됩니다."
  }
}
```

```json
{
  "error": {
    "type": "GitCloneFailed",
    "message": "Git 저장소 복제 실패: git+https://github.com/user/repo.git (권한 없음 또는 저장소 없음)"
  }
}
```

```json
{
  "error": {
    "type": "GitRefNotFound",
    "message": "Git 참조를 찾을 수 없습니다: v1.0.0 (태그/브랜치/커밋이 존재하지 않음)"
  }
}
```

### 1. index_artifact
아티팩트 전체 인덱싱 (사전 준비용)

**Request:**
```python
index_artifact(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21"
)
```

**Response (성공):**
```json
{
  "status": "success",
  "indexed_classes": 247,
  "indexed_files": {
    "java": 230,
    "kotlin": 17
  },
  "cache_location": "~/.jar-indexer/cache/org.springframework/spring-core/5.3.21",
  "processing_time": "2.3s"
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

### 2. list_indexed_artifacts
인덱싱된 아티팩트 목록 조회

**Request:**
```python
list_indexed_artifacts(
    page: 1,  # 선택사항, 기본값: 1
    page_size: 50,  # 선택사항, 기본값: 50
    group_filter: "org.springframework",  # 선택사항, 그룹별 필터링
    artifact_filter: "spring-core",  # 선택사항, 아티팩트별 필터링
    version_filter: ">=5.3.0"  # 선택사항, 버전 비교 필터링
)
```

**Version Filter 지원 연산자:**
- `"5.3.21"` - 정확히 해당 버전
- `">=5.3.0"` - 5.3.0 이상
- `">5.2.0"` - 5.2.0 초과
- `"<=5.3.21"` - 5.3.21 이하
- `"<6.0.0"` - 6.0.0 미만
- `">=5.0.0,<6.0.0"` - 범위 지정 (5.0.0 이상 6.0.0 미만)

**Response (성공):**
```json
{
  "status": "success",
  "pagination": {
    "page": 1,
    "total_count": 23,
    "total_pages": 1,
  },
  "artifacts": [
    {
      "group_id": "org.springframework",
      "artifact_id": "spring-core",
      "version": "5.3.21",
      "status": "indexed"
    },
    {
      "group_id": "org.springframework", 
      "artifact_id": "spring-context",
      "version": "5.3.21",
      "status": "indexed"
    },
    {
      "group_id": "com.fasterxml.jackson.core",
      "artifact_id": "jackson-core", 
      "version": "2.13.3",
      "status": "indexed"
    },
    {
      "group_id": "io.netty",
      "artifact_id": "netty-common",
      "version": "4.1.79.Final",
      "status": "failed"
    }
  ]
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

### 3. list_packages
패키지 구조 탐색

**Request:**
```python
list_packages(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    parent_package: "org.springframework.core",  # 선택사항: 시작점 패키지 경로
    max_depth: 2,  # 선택사항, 기본값: 1 (현재 레벨만)
    include_description: True  # 선택사항, 기본값: False (패키지 설명 포함 여부)
)
```

**parent_package 파라미터:**
- `None` 또는 생략: 루트부터 모든 패키지 조회
- `"org.springframework"`: 해당 패키지부터 시작하여 하위 패키지만 조회
- `"org.springframework.core"`: core 패키지 하위의 서브패키지들만 조회

**예시:**
- `parent_package=None` → `org.springframework`, `org.springframework.core`, `org.springframework.util` 등 전체
- `parent_package="org.springframework.core"` → `annotation`, `convert`, `io` 등 core 하위만

**Response (include_description=True):**
```json
{
  "status": "success",
  "max_depth": 2,
  "packages": [
    {
      "name": "org.springframework.core",
      "description": "Spring's core conversion system...",
      "packages": [
        {
          "name": "annotation",
          "description": "Annotation support utilities and meta-annotations for Spring components",
          "packages": [
            {
              "name": "meta",
              "description": "Meta-annotation support for creating composed annotations"
            }
          ]
        },
        {
          "name": "convert",
          "description": "Type conversion system for Spring framework",
          "packages": [
            {
              "name": "converter",
              "description": "Built-in converter implementations"
            }
          ]
        }
      ]
    }
  ]
}
```

**Response (include_description=False, 기본값):**
```json
{
  "status": "success",
  "max_depth": 2,
  "packages": [
    {
      "name": "org.springframework.core",
      "packages": [
        {
          "name": "annotation",
          "packages": [
            {
              "name": "meta"
            }
          ]
        },
        {
          "name": "convert",
          "packages": [
            {
              "name": "converter"
            }
          ]
        }
      ]
    }
  ]
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

### 4. list_types
패키지별 타입 목록 조회 (클래스, 인터페이스, 열거형, 어노테이션 등)

**Request:**
```python
list_types(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    package_filter: "org.springframework.core",  # 선택사항
    name_filter: "*Utils",  # 선택사항, 타입 이름 패턴 필터링
    name_filter_type: "glob",  # 선택사항, "glob" | "regex", 기본값: "glob"
    page: 1,  # 선택사항, 기본값: 1
    page_size: 50,  # 선택사항, 기본값: 50
    include_description: True  # 선택사항, 기본값: False (타입 설명 포함 여부)
)
```

**name_filter 예시:**
- **glob 패턴**:
  - `"*Utils"` - Utils로 끝나는 모든 타입
  - `"String*"` - String으로 시작하는 모든 타입
  - `"*Exception*"` - Exception이 포함된 모든 타입
- **regex 패턴**:
  - `"^[A-Z][a-z]+Utils$"` - 대문자로 시작하고 Utils로 끝나는 타입
  - `".*Annotation.*"` - Annotation이 포함된 타입

**Response (include_description=True):**
```json
{
  "status": "success",
  "package": "org.springframework.core",
  "pagination": {
    "page": 1,
    "total_count": 247,
    "total_pages": 5,
  },
  "types": [
    {
      "name": "AttributeAccessor",
      "kind": "interface",
      "language": "java",
      "description": "Interface defining a generic contract for attaching and accessing metadata to/from arbitrary objects."
    },
    {
      "name": "AttributeAccessorSupport",
      "kind": "class", 
      "language": "java",
      "description": "Support class for AttributeAccessor implementations, providing a base implementation of all methods."
    },
    {
      "name": "NestedIOException", 
      "kind": "class",
      "language": "java",
      "description": "Subclass of IOException that properly handles a root cause, exposing the root cause just like NestedCheckedException does."
    }
  ]
}
```

**Response (성공, include_description=False, 기본값):**
```json
{
  "status": "success",
  "package": "org.springframework.core",
  "pagination": {
    "page": 1,
    "total_count": 247,
    "total_pages": 5,
  },
  "types": [
    {
      "name": "AttributeAccessor",
      "kind": "interface",
      "language": "java"
    },
    {
      "name": "AttributeAccessorSupport",
      "kind": "class", 
      "language": "java"
    },
    {
      "name": "NestedIOException", 
      "kind": "class",
      "language": "java"
    }
  ]
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

### 5. get_type_source
타입 전체 소스 조회

**Request:**
```python
get_type_source(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    type_name: "org.springframework.core.SpringVersion"
)
```

**Response (성공):**
```json
{
  "status": "success",
  "type_info": {
    "name": "org.springframework.core.SpringVersion",
    "kind": "class",
    "language": "java",
    "line_range": {"start": 25, "end": 95},
    "source_code": "package org.springframework.core;\n\n/**\n * Class that exposes the Spring version. Fetches the Implementation-Version manifest attribute from the jar file.\n */\npublic class SpringVersion {\n\n    private static final String VERSION = getImplementationVersion();\n\n    public static String getVersion() {\n        return VERSION;\n    }\n\n    static class StaticNestedClass {\n        // nested class implementation\n    }\n\n    private static String getImplementationVersion() {\n        // implementation details\n    }\n}"
  }
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

### 6. list_methods
클래스/인터페이스의 모든 메서드 목록 조회

**Request:**
```python
list_methods(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    type_name: "org.springframework.util.StringUtils",
    include_inherited: False,  # 선택사항, 상속된 메서드 포함 여부
    name_filter: "has*",  # 선택사항, 메서드 이름 패턴 필터링
    name_filter_type: "glob",  # 선택사항, "glob" | "regex", 기본값: "glob"
    page: 1,  # 선택사항, 기본값: 1
    page_size: 50,  # 선택사항, 기본값: 50
    include_description: True  # 선택사항, 기본값: False (메서드 설명 포함 여부)
)
```

**name_filter 예시:**
- **glob 패턴**:
  - `"get*"` - get으로 시작하는 모든 메서드 (getter 메서드)
  - `"set*"` - set으로 시작하는 모든 메서드 (setter 메서드)
  - `"*Test"` - Test로 끝나는 모든 메서드 (테스트 메서드)
  - `"is*"` - is로 시작하는 모든 메서드 (boolean 반환 메서드)
- **regex 패턴**:
  - `"^(get|set)[A-Z].*"` - getter/setter 메서드만
  - `".*Builder$"` - Builder로 끝나는 메서드

**Response (include_description=True):**
```json
{
  "status": "success",
  "type_name": "org.springframework.util.StringUtils",
  "type_kind": "class",
  "language": "java",
  "pagination": {
    "page": 1,
    "total_count": 45,
    "total_pages": 1
  },
  "methods": [
    {
      "signature": "public static boolean hasText(String str)",
      "line_range": {"start": 156, "end": 159},
      "description": "Check whether the given String contains actual text."
    },
    {
      "signature": "public static boolean hasText(CharSequence str)",
      "line_range": {"start": 171, "end": 174},
      "description": "Check whether the given CharSequence contains actual text."
    },
    {
      "signature": "public static boolean hasLength(String str)",
      "line_range": {"start": 189, "end": 192},
      "description": "Check whether the given String has actual length."
    }
  ]
}
```

**Response (include_description=False, 기본값):**
```json
{
  "type_name": "org.springframework.util.StringUtils",
  "type_kind": "class",
  "language": "java",
  "pagination": {
    "page": 1,
    "total_count": 45,
    "total_pages": 1
  },
  "methods": [
    {
      "signature": "public static boolean hasText(String str)",
      "line_range": {"start": 156, "end": 159}
    },
    {
      "signature": "public static boolean hasText(CharSequence str)",
      "line_range": {"start": 171, "end": 174}
    },
    {
      "signature": "public static boolean hasLength(String str)",
      "line_range": {"start": 189, "end": 192}
    }
  ]
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

### 7. list_fields
클래스/인터페이스의 모든 필드 목록 조회

**Request:**
```python
list_fields(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    type_name: "org.springframework.core.SpringVersion",
    include_inherited: False,  # 선택사항, 상속된 필드 포함 여부
    name_filter: "*VERSION*",  # 선택사항, 필드 이름 패턴 필터링
    name_filter_type: "glob",  # 선택사항, "glob" | "regex", 기본값: "glob"
    page: 1,  # 선택사항, 기본값: 1
    page_size: 50,  # 선택사항, 기본값: 50
    include_description: True  # 선택사항, 기본값: False (필드 설명 포함 여부)
)
```

**name_filter 예시:**
- **상수 필드**: `"*VERSION*"`, `"*CONSTANT*"`
- **설정 필드**: `"*CONFIG*"`, `"*SETTING*"`
- **캐시 필드**: `"*CACHE*"`, `"cache*"`
- **로거 필드**: `"*LOG*"`, `"logger"`

**Response (include_description=True):**
```json
{
  "status": "success",
  "type_name": "org.springframework.core.SpringVersion",
  "type_kind": "class",
  "pagination": {
    "page": 1,
    "total_count": 5,
    "total_pages": 1
  },
  "fields": [
    {
      "signature": "private static final String VERSION",
      "line_range": {"start": 28, "end": 28},
      "description": "The Spring version string cached at class loading time."
    },
    {
      "signature": "private static final Logger logger",
      "line_range": {"start": 32, "end": 32},
      "description": "Logger for SpringVersion class."
    },
    {
      "signature": "public static final int MAJOR_VERSION",
      "line_range": {"start": 35, "end": 35},
      "description": "The major version number of Spring framework."
    }
  ]
}
```

**Response (include_description=False, 기본값):**
```json
{
  "type_name": "org.springframework.core.SpringVersion",
  "type_kind": "class",
  "pagination": {
    "page": 1,
    "total_count": 5,
    "total_pages": 1
  },
  "fields": [
    {
      "signature": "private static final String VERSION",
      "line_range": {"start": 28, "end": 28}
    },
    {
      "signature": "private static final Logger logger",
      "line_range": {"start": 32, "end": 32}
    },
    {
      "signature": "public static final int MAJOR_VERSION",
      "line_range": {"start": 35, "end": 35}
    }
  ]
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

### 8. get_import_section
타입의 import 구문 소스 조회

**Request:**
```python
get_import_section(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    type_name: "org.springframework.core.SpringVersion"
)
```

**Response:**
```json
{
  "status": "success",
  "type_name": "org.springframework.core.SpringVersion",
  "import_section": {
    "line_range": {"start": 23, "end": 31},
    "source_code": "import java.util.Properties;\nimport java.util.jar.Attributes;\nimport java.util.jar.Manifest;\nimport org.springframework.util.StringUtils;\nimport org.springframework.core.io.ClassPathResource;\nimport org.springframework.lang.Nullable;\n\nimport static org.springframework.util.Assert.notNull;\nimport static java.util.Objects.requireNonNull;"
  }
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

### 9. get_method_source
메서드 구현 소스만 조회 (코드 분석용)

**Request:**
```python
get_method_source(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    type_name: "org.springframework.util.StringUtils",
    method_name: "hasText",
    method_signature: "(String)"  # 선택사항
)
```

**Response:**
```json
{
  "status": "success",
  "method_source": [
    {
      "line_range": {"start": 156, "end": 159},
      "source_code": "public static boolean hasText(String str) {\n    return (str != null && !str.trim().isEmpty());\n}"
    }
  ]
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

### 10. list_folder_tree
JAR 내부 폴더 구조 조회

**Request:**
```python
list_folder_tree(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    path: "org/springframework/core",  # 선택사항, 없으면 루트
    include_files: True,  # True: 폴더+파일, False: 폴더만
    max_depth: 3  # 선택사항, 기본값: 1 (현재 폴더만)
)
```

**Response (include_files=True):**
```json
{
  "status": "success",
  "path": "org/springframework/core",
  "max_depth": 3,
  "folders": [
    {
      "name": "annotation",
      "file_count": 8,
      "files": [
        {
          "name": "AnnotationUtils.java",
          "size": "12.5KB",
          "line_count": 345
        }
      ],
      "folders": [
        {
          "name": "meta",
          "file_count": 5,
          "files": [
            {
              "name": "AnnotationMetadata.java",
              "size": "3.1KB",
              "line_count": 89
            }
          ],
          "folders": [
            {
              "name": "impl",
              "file_count": 3,
              "files": [
                {
                  "name": "StandardAnnotationMetadata.java",
                  "size": "4.7KB",
                  "line_count": 134
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  "files": [
    {
      "name": "SpringVersion.java",
      "size": "2.1KB",
      "line_count": 67
    }
  ]
}
```

**Response (include_files=False):**
```json
{
  "status": "success",
  "path": "org/springframework/core",
  "max_depth": 3,
  "folders": [
    {
      "name": "annotation",
      "file_count": 8,
      "folders": [
        {
          "name": "meta",
          "file_count": 5,
          "folders": [
            {
              "name": "impl",
              "file_count": 3
            }
          ]
        }
      ]
    }
  ]
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

### 11. search_file_names
파일명 패턴 검색 (glob/regex 지원)

**Request:**
```python
search_file_names(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    pattern: "StringUtils*.java",  # glob 또는 regex 패턴
    pattern_type: "glob",  # "glob" | "regex"
    start_path: "org/springframework/util",  # 선택사항, 기본값: 루트
    max_depth: 2  # 선택사항, 기본값: 무제한(-1)
)
```

**Response (성공):**
```json
{
  "status": "success",
  "search_config": {
    "start_path": "org/springframework/util",
    "max_depth": 2,
    "pattern": "StringUtils*.java"
  },
  "files": [
    {
      "name": "StringUtils.java",
      "path": "org/springframework/util/StringUtils.java",
      "size": "15.2KB",
      "line_count": 456,
      "depth": 0
    },
    {
      "name": "StringUtilsHelper.java",
      "path": "org/springframework/util/concurrent/StringUtilsHelper.java", 
      "size": "3.1KB",
      "line_count": 89,
      "depth": 1
    }
  ]
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

### 12. search_file_content
파일 내용 기반 검색 (컨텍스트 라인 지원)

**Request:**
```python
search_file_content(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    query: "hasText",  # 검색 쿼리
    query_type: "string",  # "string" | "regex"
    start_path: "org/springframework/util",  # 선택사항, 기본값: 루트
    max_depth: 2,  # 선택사항, 기본값: 무제한(-1)
    context_before: 2,  # 선택사항, 매칭 라인 위로 N줄
    context_after: 3,   # 선택사항, 매칭 라인 아래로 N줄
    max_results: 20  # 선택사항
)
```

**Response:**
```json
{
  "status": "success",
  "search_config": {
    "query": "hasText",
    "query_type": "string",
    "start_path": "org/springframework/util",
    "context_before": 2,
    "context_after": 3
  },
  "matches": {
    "StringUtils.java": [
      {
        "content": "    /**\n     * Check whether the given String contains actual text.\n     */\n    public static boolean hasText(String str) {\n        return (str != null && !str.trim().isEmpty());\n    }\n",
        "content_range": "154-159",
        "match_lines": "156"
      },
      {
        "content": "    /**\n     * Another method documentation.\n     * @see #hasText(String)\n     */\n    public static boolean hasLength(String str) {\n        return (str != null && !str.isEmpty());\n    }",
        "content_range": "201-207",
        "match_lines": "203"
      }
    ],
    "concurrent/ConcurrentStringUtils.java": [
      {
        "content": "    // Uses StringUtils.hasText internally\n    public void process() {\n        if (hasText(input)) { ... }\n    }",
        "content_range": "45-49",
        "match_lines": "47"
      }
    ]
  }
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

### 13. get_file
파일 내용 조회 (라인 범위 지원)

**Request:**
```python
get_file(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    file_path: "org/springframework/util/StringUtils.java",
    start_line: 150,  # 선택사항
    end_line: 200     # 선택사항
)
```

**Response:**
```json
{
  "status": "success",
  "file_info": {
    "name": "StringUtils.java",
    "path": "org/springframework/util/StringUtils.java"
  },
  "content": {
    "start_line": 150,
    "end_line": 200,
    "source_code": "    /**\n     * Check whether the given String contains actual text.\n     */\n    public static boolean hasText(String str) {\n        return (str != null && !str.trim().isEmpty());\n    }\n\n    /**\n     * Check whether the given String has length.\n     */\n    public static boolean hasLength(String str) {\n        return (str != null && !str.isEmpty());\n    }"
  }
}
```

**에러 응답:** 하단 "공통 에러 응답" 섹션 참조

## Claude Code 통합 워크플로

### 탐색적 검색
1. `list_packages` → 패키지 구조 파악
2. `list_types` → 특정 패키지의 타입들 확인
3. `get_type_source` → 전체 타입 소스 조회

### 메서드/필드 중심 분석
1. `list_methods` → 메서드 목록 및 시그니처 확인
2. `list_fields` → 필드 목록 및 시그니처 확인
3. `get_method_source` → 메서드 구현 코드 분석
4. `get_import_section` → import 의존성 분석

### 파일 기반 탐색
1. `list_folder_tree` → 디렉토리 구조 파악
2. `search_file_names` → 파일명 패턴 검색
3. `search_file_content` → 파일 내용 문자열 검색
4. `get_file` → 특정 파일의 일부 또는 전체 조회

모든 도구는 Maven 좌표 (group_id, artifact_id, version) 기반으로 동작하며, Claude Code가 라이브러리 소스를 효율적으로 탐색하고 분석할 수 있도록 설계되었습니다.

---

## 공통 응답 형식

### Status 필드
모든 MCP Tool 응답은 `status` 필드를 포함합니다:

#### 탐색적 검색 및 메서드/필드 중심 분석 도구
- `"success"`: 정상적으로 데이터를 반환했습니다
- `"source_jar_not_found"`: 소스 JAR 파일을 찾을 수 없습니다
- `"indexing_required"`: 소스 JAR은 있지만 인덱싱이 필요합니다

#### 파일 기반 탐색 도구
- `"success"`: 정상적으로 데이터를 반환했습니다  
- `"source_jar_not_found"`: 소스 JAR 파일을 찾을 수 없습니다

### 공통 에러 응답

각 MCP Tool에서 발생할 수 있는 공통 에러 응답들입니다.

#### 소스 JAR 없음
```json
{
  "status": "source_jar_not_found",
  "message": "해당 아티팩트의 소스를 찾을 수 없습니다. register_source 도구를 사용하여 소스를 등록해주세요.",
  "suggested_action": "register_source"
}
```

#### 인덱싱 필요 (탐색적 검색 및 메서드/필드 중심 분석 도구만)
```json
{
  "status": "indexing_required", 
  "message": "해당 아티팩트가 아직 인덱싱되지 않았습니다. index_artifact 도구를 사용하여 인덱싱을 수행해주세요.",
  "suggested_action": "index_artifact"
}
```

#### 내부 서버 에러
```json
{
  "status": "internal_error",
  "message": "내부 서버 에러가 발생했습니다: [상세 에러 메시지]"
}
```