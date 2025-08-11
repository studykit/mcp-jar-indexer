## TODO List

### Phase 1: 프로젝트 구조 및 기본 인프라
- [x] pyproject.toml 의존성 추가
  - [x] MCP 서버 프레임워크 추가
  - [x] GitPython 라이브러리 추가
  - [x] requests 라이브러리 추가
  - [x] 기타 필요한 파일 처리 라이브러리 추가
- [x] 기본 모듈 구조 생성
  - [x] `src/tools/` 디렉토리 생성
  - [x] `src/core/` 디렉토리 생성
  - [x] `src/utils/` 디렉토리 생성
  - [x] `src/tools/__init__.py` 생성
  - [x] `src/core/__init__.py` 생성
  - [x] `src/utils/__init__.py` 생성

### Phase 2: 코어 기능 구현
- [x] `src/core/storage.py` 구현
  - [x] 스토리지 디렉토리 구조 생성 기능
  - [x] base directory 홈 디렉토리 관리
  - [x] Maven 좌표 기반 경로 생성 유틸리티
  - [x] 디렉토리 권한 및 안전성 검증
- [x] `src/core/source_processor.py` 구현
  - [x] URI 파싱 및 검증 로직
  - [x] `file://` URI 처리
  - [x] `https://` URI 처리 (.jar/.git suffix 기반 분류)
  - [x] `git@host:user/repo` SSH URI 처리
  - [x] URI 타입 감지 및 분류
- [x] `src/utils/validation.py` 구현
  - [x] Maven 좌표 검증 (group_id, artifact_id, version)
  - [x] URI 형식 검증
  - [x] 파라미터 타입 검증
- [x] `src/utils/file_utils.py` 구현
  - [x] 파일 다운로드 유틸리티
  - [x] JAR 파일 검증
  - [x] 파일 복사/심볼릭 링크 생성

### Phase 3: Git 저장소 처리
- [x] `src/core/git_handler.py` 구현
  - [x] Git bare clone 생성 기능
  - [x] Worktree 생성 및 관리
  - [x] git_ref (브랜치/태그/커밋) 처리
  - [x] Git 인증 처리 (SSH key, 토큰)
  - [x] Git 작업 에러 핸들링
  - [x] 기존 저장소 업데이트 처리
- [x] `tests/core/test_git_handler.py` 테스트 구현
  - [x] GitHandler 초기화 및 Git 저장소 감지 테스트
  - [x] Bare 저장소 복제 테스트 (성공/실패/인증 에러)
  - [x] Worktree 생성/삭제/목록 조회 테스트
  - [x] Git 참조 검증 및 기본 브랜치 감지 테스트
  - [x] 인증 설정 및 에러 처리 테스트
  - [x] Git 예외 클래스 테스트 (35개 테스트 케이스)

### Phase 4: register_source MCP Tool
- [x] `src/tools/register_source.py` 구현
  - [x] MCP Tool 인터페이스 구현
  - [x] 파라미터 검증 로직
  - [x] 소스 타입별 처리 분기
  - [x] JAR 파일 처리 로직
  - [x] 로컬 디렉토리 처리 로직
  - [x] Git 저장소 처리 로직
  - [x] 롤백 메커니즘 구현

### Phase 5: 에러 처리 및 응답
- [x] Git 관련 에러 클래스 정의 (`src/core/git_handler.py`에 구현됨)
  - [x] `GitError` (기본 Git 에러 클래스)
  - [x] `GitCloneFailedError` 정의
  - [x] `GitRefNotFoundError` 정의
  - [x] `GitAuthenticationError` 정의
  - [x] `GitWorktreeError` 정의
- [x] 기타 에러 클래스 정의
  - [x] `ResourceNotFoundError` 정의
  - [x] `DownloadFailedError` 정의
  - [x] `InvalidSourceError` 정의
  - [x] `UnsupportedSourceTypeError` 정의
- [x] 응답 형식 구현
  - [x] 성공 응답 (`registered_and_indexed`, `registered_only`)
  - [x] 에러 응답 (상세 메시지 및 해결 방법)
  - [x] JSON 스키마 검증

### Phase 6: 통합 및 테스트
- [ ] MCP 서버 통합
  - [ ] `src/main.py` MCP 서버 설정
  - [ ] register_source tool 등록
  - [ ] MCP 프로토콜 호환성 확인
- [ ] 테스트 시나리오 구현
  - [ ] 로컬 JAR 파일 등록 테스트
  - [ ] 원격 JAR 다운로드 테스트
  - [ ] GitHub 공개 저장소 clone 테스트
  - [ ] 에러 케이스 검증 테스트
  - [ ] 통합 테스트 작성
- [ ] 문서화
  - [ ] API 문서 업데이트
  - [ ] 사용법 예시 추가
  - [ ] 에러 코드 문서화

