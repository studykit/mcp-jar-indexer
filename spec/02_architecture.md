# 아키텍처 개요

## 구성 요소

```
┌─────────────────────────────────────────────────────┐
│                Claude Code                          │
└─────────────────┬───────────────────────────────────┘
                  │ MCP Protocol
┌─────────────────▼───────────────────────────────────┐
│               JAR Indexer MCP Server                │
├─────────────────────────────────────────────────────┤
│  MCP Tools (14개)                                   │
│  ├─ register_source        ├─ get_import_section    │
│  ├─ index_artifact         ├─ get_method_source     │
│  ├─ list_artifacts         ├─ list_folder_tree      │
│  ├─ search_cached_artifact ├─ search_file_names     │
│  ├─ list_packages          ├─ search_file_content   │
│  ├─ list_types             ├─ get_file              │
│  ├─ get_type_source        │                        │
│  ├─ list_methods           │                        │
│  └─ list_fields            │                        │
├─────────────────────────────────────────────────────┤
│  Core Services                                      │
│  ├─ Source JAR Finder   ├─ Java/Kotlin Parser       │
│  ├─ JAR Indexer         ├─ Cache Manager            │
│  ├─ Maven/Gradle Cache  └─ Metadata Extractor       │
│  │  Scanner                                         │
├─────────────────────────────────────────────────────┤
│  Storage Layer                                      │
│  ├─ ~/.jar-indexer/code/{artifact}/                 │
│  │  ├─ metadata.json    ├─ packages.json            │
│  │  ├─ index.json       └─ sources/                 │
│  └─ ~/.jar-indexer/source-jar/*.jar                │
└─────────────────────────────────────────────────────┘
```

## Sotrage Layer Directory 구조

```
~/.jar-indexer/
├── code/                            # 인덱싱된 데이터
│   ├── org.springframework/
│   │   └── spring-core/
│   │       └── 5.3.21/
│   │           ├── metadata.json    # 아티팩트 메타정보
│   │           ├── index.json       # 타입 인덱스
│   │           ├── packages.json    # 패키지 정보
│   │           └── sources/         # 추출된 소스 파일들
│   │               └── org/springframework/core/
│   │                   └── SpringVersion.java
│   └── com.fasterxml.jackson.core/
│       └── jackson-core/
│           └── 2.13.3/
│               ├── metadata.json
│               ├── index.json
│               ├── packages.json
│               └── sources/
├── source-jar/                      # 소스 JAR 파일들
│   ├── org.springframework/
│   │   └── spring-core/
│   │       └── 5.3.21/
│   │           └── spring-core-5.3.21-sources.jar
│   └── com.fasterxml.jackson.core/
│       └── jackson-core/
│           └── 2.13.3/
│               └── jackson-core-2.13.3-sources.jar
├── git-bare/                        # Git bare 저장소들
│   ├── org.springframework/
│   │   └── spring-framework/
│   │       └── .git/                # bare clone
│   └── com.company/
│       └── my-library/
│           └── .git/                # bare clone
└── config.json                     # 서버 설정
```

## 데이터 흐름

```
1. Claude Code 요청
   ↓
2. MCP Tool 호출 (예: get_type_source)
   ↓
3. JAR 인덱싱 상태 확인
   ├─ 인덱싱 완료: 5단계로 진행
   └─ 인덱싱 없음: 에러 반환
   ↓
4. [에러 시] 에러 유형별 처리
   ├─ 소스 없음 (source_jar_not_found):
   │  ├─ search_cached_artifact 도구로 로컬 캐시 확인
   │  └─ register_source 도구 호출
   │     ├─ Claude Code가 Maven/Gradle 다운로드 후 URI 전달
   │     ├─ search_cached_artifact로 발견한 소스 JAR 등록
   │     ├─ 사용자가 직접 소스 등록 (JAR/디렉토리/Git)
   │     └─ 등록 후 자동 인덱싱 (auto_index=True)
   └─ 인덱싱 필요 (indexing_required):
      ├─ index_artifact 도구 호출 (소스는 있지만 미인덱싱)
      ├─ JAR 인덱싱 수행
      │  ├─ 소스 파일 추출
      │  ├─ Java/Kotlin 파싱
      │  ├─ 메타데이터 생성
      │  └─ 캐시에 저장
      └─ 원래 요청 재수행
   ↓
5. 요청된 데이터 조회 및 반환
   ↓
6. Claude Code에 응답
```

## 캐시 검색 워크플로우

```
1. search_cached_artifact 요청
   ├─ group_id: "org.springframework"
   ├─ artifact_id: "spring-core"
   ├─ version_filter: "5.3.21" (선택사항)
   └─ cache: "maven,gradle" (기본값)
   ↓
2. 로컬 캐시 경로 검색
   ├─ Maven 저장소: ~/.m2/repository/
   └─ Gradle 캐시: ~/.gradle/caches/
   ↓
3. 소스 JAR 검색
   ├─ version_filter 있음: 특정 버전만 검색
   └─ version_filter 없음: 모든 버전 검색
   ↓
4. 검색 결과 반환
   ├─ 성공: paths 배열에 모든 발견된 소스 JAR 경로
   └─ 실패: 빈 paths 배열과 오류 메시지
   ↓
5. Claude Code가 소스 JAR 경로로 register_source 호출 가능
```
