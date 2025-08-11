# register_source mcp_tool 상세 구현 설계

## 아키텍처 분석 요약
- **스토리지 구조**: base directory 하위에 `code/`, `source-jar/`, `git-bare/` 디렉토리
- **Git 저장소 지원**: bare clone → worktree 생성 → 인덱싱 흐름

## 개발 단계별 계획

### Phase 1: 프로젝트 구조 및 기본 인프라
1. **의존성 설정** (`pyproject.toml` 업데이트)
   - MCP 서버 프레임워크 
   - Git 조작 라이브러리 (`GitPython`)
   - 파일 처리 라이브러리
   - HTTP 다운로드 라이브러리 (`requests`)

2. **기본 모듈 구조 생성**
   ```
   src/
   ├── main.py (MCP 서버 엔트리포인트)
   ├── tools/
   │   └── register_source.py
   ├── core/
   │   ├── storage.py (스토리지 관리)
   │   ├── git_handler.py (Git 저장소 처리)
   │   └── source_processor.py (소스 처리)
   └── utils/
       ├── file_utils.py
       └── validation.py
   ```

### Phase 2: 코어 기능 구현
1. **스토리지 관리자** (`core/storage.py`)
   - 디렉토리 구조 생성 및 관리
   - `{code,source-jar,git-bare}` 경로 관리
   - Maven 좌표 기반 경로 생성

2. **소스 URI 처리기** (`core/source_processor.py`)
   - URI 파싱 및 검증
   - 지원 URI 형태:
     - `file://` (로컬 JAR/디렉토리)
     - `https://` (원격 JAR 또는 Git 저장소 - suffix로 구분)
     - `git@host:user/repo` (SSH Git 저장소)

### Phase 3: Git 저장소 처리
1. **Git 핸들러** (`core/git_handler.py`)
   - Bare clone 생성 (`git-bare/{group_id}/{artifact_id}/`)
   - Worktree 생성 (`code/{group_id}/{artifact_id}/{version}/`)
   - git_ref (브랜치/태그/커밋) 처리
   - Git 인증 처리 (SSH key, 토큰)

### Phase 4: register_source MCP Tool
1. **파라미터 검증**
   - `group_id`, `artifact_id`, `version` 필수값 검증
   - `source_uri` 형식 검증
   - Git URI인 경우 `git_ref` 필수 검증

2. **소스 타입별 처리 로직**;
   - **JAR 파일**: 다운로드 → `source-jar/` 저장
   - **로컬 디렉토리**: 심볼릭 링크 또는 복사
   - **Git 저장소**: bare clone → worktree 생성

3. **자동 인덱싱 기능** (`auto_index=True`)
   - 등록 완료 후 자동으로 인덱싱 수행
   - 실패 시 롤백 메커니즘

### Phase 5: 에러 처리 및 응답
1. **에러 시나리오 처리**
   - `resource_not_found`: 파일/디렉토리 없음
   - `download_failed`: 원격 다운로드 실패  
   - `git_clone_failed`: Git clone 실패
   - `git_ref_not_found`: 브랜치/태그 없음
   - `invalid_source`: 손상된 파일
   - `unsupported_source_type`: 지원하지 않는 형식

2. **응답 형식 구현**
   - 성공: `registered_and_indexed` / `registered_only`
   - 실패: 상세 에러 메시지 및 해결 방법

### Phase 6: 통합 및 테스트
1. **MCP 서버 통합**
   - `main.py`에서 MCP tool 등록
   - 프로토콜 호환성 확인

2. **테스트 시나리오**
   - 로컬 JAR 파일 등록
   - 원격 JAR 다운로드
   - GitHub 공개 저장소 clone
   - 에러 케이스 검증

## 기술적 고려사항
- **동시성**: Git clone 등 시간 소요 작업의 비동기 처리
- **보안**: Git 인증 정보 안전한 관리
- **성능**: 중복 다운로드 방지를 위한 캐싱
- **복구**: 실패한 작업의 부분 상태 정리

## Git 저장소 처리 예시

**Git 저장소인 경우 (자동 처리):**
- `git-bare/{group_id}/{artifact_id}/` 폴더에 bare clone 생성
- `code/{group_id}/{artifact_id}/{version}/` 아래에 해당 버전의 worktree 생성
- worktree에서 소스 코드 인덱싱

```python
register_source(
    group_id="org.springframework",
    artifact_id="spring-framework",
    version="main",
    source_uri="file:///Users/dev/projects/spring-framework",
    git_ref="v5.3.21",  # 선택적
    auto_index=True
)
```

