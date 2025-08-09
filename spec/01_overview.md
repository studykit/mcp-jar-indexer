# JAR Indexer MCP Server - Project Overview

## 프로젝트 개요

JAR Indexer는 Claude Code가 Java/Kotlin 프로젝트를 분석할 때 외부 라이브러리의 소스 코드에 직접 접근할 수 있게 해주는 MCP (Model Context Protocol) 서버입니다.

### 해결하고자 하는 문제

Claude Code로 Java/Kotlin 코드를 분석하다 보면 외부 라이브러리(Spring Framework, Jackson 등)의 구현 세부사항이나 메서드 시그니처를 확인해야 하는 경우가 많습니다. 하지만 Claude Code는 JAR 파일 내부의 소스 코드에 직접 접근할 수 없어 다음과 같은 제약이 있습니다:

- 외부 라이브러리의 메서드 구현을 볼 수 없음
- 클래스 상속 구조나 인터페이스 구현을 파악하기 어려움  
- 라이브러리의 내부 동작 방식을 이해하기 어려움
- JavaDoc만으로는 부족한 컨텍스트 정보

### 솔루션

JAR Indexer MCP 서버는 다음과 같은 방식으로 이 문제를 해결합니다:

1. **소스 JAR 자동 발견**: Maven/Gradle 캐시, 원격 저장소에서 `-sources.jar` 파일을 자동으로 찾아 다운로드
2. **전체 소스 인덱싱**: 소스 코드를 추출하여 패키지, 클래스, 메서드 단위로 체계적으로 인덱싱
3. **MCP Tools 제공**: Claude Code가 라이브러리 소스를 효율적으로 탐색할 수 있는 13가지 도구 제공
4. **스마트 캐싱**: 한 번 인덱싱한 라이브러리는 로컬 캐시에서 빠르게 재사용

## 아키텍처 개요

### 구성 요소

```
┌─────────────────────────────────────────────────────┐
│                Claude Code                          │
└─────────────────┬───────────────────────────────────┘
                  │ MCP Protocol
┌─────────────────▼───────────────────────────────────┐
│               JAR Indexer MCP Server                │
├─────────────────────────────────────────────────────┤
│  MCP Tools (13개)                                   │
│  ├─ index_artifact         ├─ get_import_section    │
│  ├─ list_indexed_artifacts ├─ get_method_source     │
│  ├─ list_packages          ├─ list_folder_tree      │
│  ├─ list_types             ├─ search_file_names     │
│  ├─ get_type_source        ├─ search_file_content   │
│  ├─ list_methods           ├─ get_file              │
│  └─ list_fields            │                        │
├─────────────────────────────────────────────────────┤
│  Core Services                                      │
│  ├─ Source JAR Finder   ├─ Java/Kotlin Parser       │
│  ├─ JAR Indexer         ├─ Cache Manager            │
│  └─ Metadata Extractor                              │
├─────────────────────────────────────────────────────┤
│  Storage Layer                                      │
│  ├─ ~/.jar-indexer/cache/{artifact}/                │
│  │  ├─ metadata.json    ├─ packages.json            │
│  │  ├─ index.json       └─ sources/                 │
│  └─ ~/.jar-indexer/downloads/*.jar                  │
└─────────────────────────────────────────────────────┘
```

### 데이터 흐름

```
1. Claude Code 요청
   ↓
2. MCP Tool 호출 (예: get_type_source)
   ↓
3. JAR 인덱싱 상태 확인
   ├─ 인덱싱 완료: 5단계로 진행
   └─ 인덱싱 없음: 에러 반환
   ↓
4. [에러 시] Claude Code가 소스 등록 후 재시도
   ├─ index_artifact 도구 호출
   ├─ 소스 JAR 발견 (5단계 Waterfall)
   │  ├─ 자체 캐시
   │  ├─ Maven 로컬 저장소  
   │  ├─ Gradle 캐시
   │  ├─ 원격 저장소 다운로드
   │  └─ 사용자 직접 제공
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

## 주요 기능

### 1. 소스 JAR 발견 전략
- **5단계 Waterfall 방식**: 효율성 순서대로 단계적 탐색
- **자동 캐싱**: 발견한 소스 JAR을 자체 캐시에 보관
- **사용자 폴백**: 자동 발견 실패시 수동 경로 입력 지원

### 2. 전체 소스 인덱싱
- **완전한 소스 캐싱**: JAR 내 모든 `.java`, `.kt` 파일 추출
- **라인 번호 추적**: 모든 클래스, 메서드, 필드의 정확한 라인 범위
- **JavaDoc 파싱**: 문서 정보와 소스 코드 통합 제공
- **중첩 클래스 지원**: Inner class, Static nested class 통합 조회

### 3. MCP Tools (13개)

#### 탐색적 검색
- `list_packages`: 패키지 구조 트리 조회
- `list_types`: 패키지별 타입(클래스/인터페이스) 목록
- `get_type_source`: 타입 전체 소스코드 조회

#### 메서드/필드 중심 분석
- `list_methods`: 클래스/인터페이스의 모든 메서드 목록 조회 (필터링 지원)
- `list_fields`: 클래스/인터페이스의 모든 필드 목록 조회 (필터링 지원)
- `get_method_source`: 메서드 구현 소스만 조회 (코드 분석용)
- `get_import_section`: 타입의 import 구문 소스 조회 (의존성 분석용)

#### 파일 기반 탐색
- `list_folder_tree`: JAR 내부 폴더 구조 조회
- `search_file_names`: 파일명 패턴 검색 (glob/regex)
- `search_file_content`: 파일 내용 기반 검색
- `get_file`: 특정 파일의 부분/전체 조회

#### 관리 도구
- `index_artifact`: 아티팩트 사전 인덱싱 (준비 작업용)
- `list_indexed_artifacts`: 인덱싱된 아티팩트 목록 조회

### 4. 성능 최적화
- **스마트 캐싱**: 인덱싱된 데이터의 영구 보관
- **페이지네이션**: 대용량 결과셋의 효율적 처리
- **깊이 제어**: 트리 구조 조회시 성능 조절
- **병렬 다운로드**: 여러 저장소에서 동시 다운로드 시도

## 기술 스택

### 언어 및 프레임워크
- **Python 3.12+**: 메인 구현 언어
- **MCP SDK**: Claude와의 통신 프로토콜
- **Tree-sitter**: Java/Kotlin 소스 코드 파싱

### 주요 라이브러리
```python
# 필수 의존성
mcp                    # MCP 서버 SDK
tree-sitter           # 소스 코드 파싱
tree-sitter-java      # Java 언어 지원
tree-sitter-kotlin    # Kotlin 언어 지원
requests              # HTTP 요청 (JAR 다운로드)
aiohttp              # 비동기 HTTP 요청

# 보조 라이브러리  
zipfile              # JAR 파일 처리 (내장)
json                 # 메타데이터 저장 (내장)
os, shutil           # 파일 시스템 작업 (내장)
logging              # 로깅 (내장)
```

### 지원 환경
- **운영체제**: macOS, Linux, Windows
- **빌드 도구**: Maven, Gradle 캐시 지원
- **저장소**: Maven Central, 사내 Nexus, 커스텀 저장소

## 캐시 구조

```
~/.jar-indexer/
├── cache/                           # 인덱싱된 데이터
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
├── downloads/                       # 소스 JAR 파일들
│   ├── org.springframework/
│   │   └── spring-core/
│   │       └── 5.3.21/
│   │           └── spring-core-5.3.21-sources.jar
│   └── com.fasterxml.jackson.core/
│       └── jackson-core/
│           └── 2.13.3/
│               └── jackson-core-2.13.3-sources.jar
└── config.json                     # 서버 설정
```

## Claude Code 통합 시나리오

### 시나리오 1: Spring Framework 메서드 분석
```
1. Claude Code: "StringUtils.hasText() 메서드가 어떻게 구현되어 있나요?"
2. JAR Indexer: Spring 소스 JAR 발견 및 인덱싱
3. get_method_source 호출로 구현 코드 반환
4. Claude Code: 정확한 구현 로직과 함께 답변 제공
```

### 시나리오 2: 라이브러리 구조 탐색
```
1. Claude Code: "Jackson 라이브러리의 패키지 구조를 보여주세요"
2. list_packages로 전체 패키지 트리 조회
3. list_types로 주요 클래스들 확인
4. get_type_source로 핵심 클래스 소스 분석
5. Claude Code: 체계적인 라이브러리 분석 제공
```

### 시나리오 3: 버그 디버깅 지원
```
1. Claude Code: "이 예외가 왜 발생하는지 라이브러리 소스를 확인해주세요"
2. search_file_content로 예외 관련 코드 검색
3. get_type_source로 관련 클래스 전체 분석  
4. Claude Code: 예외 발생 원인과 해결 방안 제시
```

이 프로젝트를 통해 Claude Code는 Java/Kotlin 생태계의 방대한 오픈소스 라이브러리 소스코드에 직접 접근하여 더욱 정확하고 깊이 있는 코드 분석을 제공할 수 있게 됩니다.