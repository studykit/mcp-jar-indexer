# JAR Indexer MCP Tools - Product Requirements Document

## 개요
Java/Kotlin JAR 파일의 소스 코드를 인덱싱하고 Claude Code가 외부 라이브러리 소스를 효율적으로 탐색할 수 있게 하는 MCP 서버입니다.

## MCP Tools 목록

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

**Response:**
```json
{
  "success": true,
  "indexed_classes": 247,
  "indexed_files": {
    "java": 230,
    "kotlin": 17
  },
  "cache_location": "~/.jar-indexer/cache/org.springframework_spring-core_5.3.21",
  "processing_time": "2.3s"
}
```

### 2. list_packages
패키지 구조 탐색

**Request:**
```python
list_packages(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    parent_package: None  # 선택사항: 특정 패키지 하위만
)
```

**Response:**
```json
{
  "success": true,
  "packages": [
    {
      "name": "org.springframework.core",
      "class_count": 45,
      "description": "Spring's core conversion system...",
      "subpackages": [
        "org.springframework.core.annotation",
        "org.springframework.core.convert"
      ]
    },
    {
      "name": "org.springframework.util",
      "class_count": 78,
      "subpackages": [
        "org.springframework.util.concurrent"
      ]
    }
  ]
}
```

### 3. list_classes
패키지별 클래스 목록 조회

**Request:**
```python
list_classes(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    package_filter: "org.springframework.core"  # 선택사항
)
```

**Response:**
```json
{
  "success": true,
  "classes": [
    {
      "name": "org.springframework.core.SpringVersion",
      "type": "class",
      "language": "java"
    },
    {
      "name": "org.springframework.core.NestedIOException", 
      "type": "class",
      "language": "java"
    }
  ],
  "total_count": 247
}
```

### 4. get_class_source
클래스 전체 소스 조회 (nested class 통합 조회 방식)

**Request:**
```python
get_class_source(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    class_name: "org.springframework.core.SpringVersion"
)
```

**Response:**
```json
{
  "success": true,
  "class_info": {
    "name": "org.springframework.core.SpringVersion",
    "language": "java",
    "line_range": {"start": 25, "end": 95},
    "source_code": "package org.springframework.core;\n\n/**\n * Class that exposes...\n */\npublic class SpringVersion {\n    public static String getVersion() { ... }\n}",
    "methods": [
      {
        "signature": "public static String getVersion()",
        "line_range": {"start": 45, "end": 48}
      }
    ],
    "fields": [
      {
        "name": "VERSION",
        "type": "String",
        "line_range": {"start": 30, "end": 30}
      }
    ],
    "nested_classes": [
      {
        "name": "StaticNestedClass",
        "full_name": "org.springframework.core.SpringVersion.StaticNestedClass",
        "type": "static_nested",
        "line_range": {"start": 50, "end": 60}
      }
    ]
  }
}
```

### 5. get_method_javadoc
메서드 문서만 조회 (API 참조용)

**Request:**
```python
get_method_javadoc(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    class_name: "org.springframework.util.StringUtils",
    method_name: "hasText",
    method_signature: "(String)"  # 선택사항 (오버로드 구분)
)
```

**Response:**
```json
{
  "success": true,
  "method_docs": [
    {
      "signature": "public static boolean hasText(String str)",
      "line_range": {"start": 150, "end": 155},
      "javadoc": {
        "summary": "Check whether the given String contains actual text.",
        "description": "More detailed description...",
        "params": {"str": "the String to check"},
        "returns": "true if the String is not null and contains at least one non-whitespace character",
        "since": "3.0",
        "see": ["#hasLength(String)"]
      }
    }
  ]
}
```

### 6. get_method_source
메서드 구현 소스만 조회 (코드 분석용)

**Request:**
```python
get_method_source(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    class_name: "org.springframework.util.StringUtils",
    method_name: "hasText",
    method_signature: "(String)"  # 선택사항
)
```

**Response:**
```json
{
  "success": true,
  "method_source": [
    {
      "signature": "public static boolean hasText(String str)",
      "line_range": {"start": 156, "end": 159},
      "source_code": "public static boolean hasText(String str) {\n    return (str != null && !str.trim().isEmpty());\n}"
    }
  ]
}
```

### 7. list_folders
JAR 내부 폴더 구조 조회

**Request:**
```python
list_folders(
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
  "success": true,
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
  "success": true,
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

### 8. search_files
파일명 패턴 검색 (glob/regex 지원)

**Request:**
```python
search_files(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    pattern: "StringUtils*.java",  # glob 또는 regex 패턴
    pattern_type: "glob",  # "glob" | "regex"
    start_path: "org/springframework/util",  # 선택사항, 기본값: 루트
    max_depth: 2  # 선택사항, 기본값: 무제한(-1)
)
```

**Response:**
```json
{
  "success": true,
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

### 9. search_content
파일 내용 기반 검색 (컨텍스트 라인 지원)

**Request:**
```python
search_content(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    pattern: "hasText",  # 검색할 패턴
    pattern_type: "string",  # "string" | "regex"
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
  "success": true,
  "search_config": {
    "pattern": "hasText",
    "pattern_type": "string",
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

### 10. get_file
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
  "success": true,
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

## 핵심 특징

### 소스 JAR 발견 전략 (하이브리드 접근)
1. Maven 로컬 저장소 확인 (`~/.m2/repository`)
2. Gradle 캐시 확인 (`~/.gradle/caches/modules-2/files-2.1`)
3. 자체 캐시 확인
4. Maven Central/Nexus에서 다운로드

### 인덱싱 전략
- **전체 소스 캐싱**: JAR에서 모든 소스 파일 추출 및 저장
- **라인 번호 정보**: 모든 클래스, 메서드, 필드의 정확한 라인 범위 제공
- **Nested Class 지원**: 통합 조회 방식으로 outer class와 함께 제공
- **패키지 정보**: package-info.java 활용한 풍부한 패키지 문서 제공

### 캐시 구조
```
~/.jar-indexer/cache/
└── org.springframework_spring-core_5.3.21/
    ├── metadata.json          # 아티팩트 메타데이터
    ├── index.json            # 클래스 인덱스
    ├── packages.json         # 패키지 정보
    └── sources/              # 추출된 소스 파일들
        └── org/springframework/core/
            └── SpringVersion.java
```

## Claude Code 통합 워크플로

### 탐색적 검색
1. `list_packages` → 패키지 구조 파악
2. `list_classes` → 특정 패키지의 클래스들 확인
3. `get_class_source` → 전체 클래스 소스 조회

### 메서드 중심 분석
1. `search_content` → 메서드명으로 사용처 검색
2. `get_method_javadoc` → API 문서 확인
3. `get_method_source` → 구현 코드 분석

### 파일 기반 탐색
1. `list_folders` → 디렉토리 구조 파악
2. `search_files` → 파일명 패턴 검색
3. `get_file` → 특정 파일의 일부 또는 전체 조회

모든 도구는 Maven 좌표 (group_id, artifact_id, version) 기반으로 동작하며, Claude Code가 라이브러리 소스를 효율적으로 탐색하고 분석할 수 있도록 설계되었습니다.