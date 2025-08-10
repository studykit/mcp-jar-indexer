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

1. **소스 JAR 자동 발견**: Claude Code가 Maven/Gradle 캐시, 원격 저장소에서 `-sources.jar` 파일 위치를 찾아 제공
2. **전체 소스 인덱싱**: 소스 코드를 추출하여 패키지, 클래스, 메서드 단위로 체계적으로 인덱싱
3. **MCP Tools 제공**: Claude Code가 라이브러리 소스를 효율적으로 탐색할 수 있는 13가지 도구 제공
4. **스마트 캐싱**: 한 번 인덱싱한 라이브러리는 로컬 캐시에서 빠르게 재사용

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

--- 


### 3. MCP Tools (14개)

![[01_mcp_tool_specification#용도에 따른 분류]]


이 프로젝트를 통해 Claude Code는 Java/Kotlin 생태계의 방대한 오픈소스 라이브러리 소스코드에 직접 접근하여 더욱 정확하고 깊이 있는 코드 분석을 제공할 수 있게 됩니다.
