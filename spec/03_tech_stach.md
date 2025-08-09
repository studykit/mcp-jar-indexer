# 기술 스택

## 언어 및 프레임워크
- **Python 3.12+**: 메인 구현 언어
- **MCP SDK**: Claude와의 통신 프로토콜
- **Tree-sitter**: Java/Kotlin 소스 코드 파싱

## 주요 라이브러리
```python
# 필수 의존성
mcp                    # MCP 서버 SDK
requests              # HTTP 요청 (JAR 다운로드)
aiohttp              # 비동기 HTTP 요청

# 보조 라이브러리  
zipfile              # JAR 파일 처리 (내장)
json                 # 메타데이터 저장 (내장)
os, shutil           # 파일 시스템 작업 (내장)
logging              # 로깅 (내장)
```

## 지원 환경
- **운영체제**: macOS
- **빌드 도구**: Maven, Gradle 캐시 지원
