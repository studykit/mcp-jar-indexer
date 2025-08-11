# index_artifact 1단계 Core 함수 명세

## 개요

`index_artifact` 1단계 구현에 필요한 core 함수들의 상세 명세입니다. 각 함수는 순수한 비즈니스 로직을 담당하며, MCP tool들이 이 함수들을 조합하여 사용합니다.

## 타입 정의

```python
from typing import TypedDict

class SearchMatch(TypedDict):
  """단일 검색 매치 정보"""
  content: str           # 매치된 내용 (컨텍스트 라인 포함)
  content_range: str     # 내용 범위 (예: "10-15")
  match_lines: str       # 실제 매치된 라인 번호들 (예: "12,14")

class SearchConfig(TypedDict):
  """검색 설정 정보"""
  query: str
  query_type: str        # "string" | "regex"
  start_path: str
  context_before: int
  context_after: int

class SearchFileContentsResult(TypedDict):
  """search_file_contents 반환 타입"""
  search_config: SearchConfig
  matches: dict[str, list[SearchMatch]]

class RegisteredSourceInfo(TypedDict):
  """등록된 아티팩트 소스 정보"""
  group_id: str              # Maven group ID
  artifact_id: str           # Maven artifact ID
  version: str               # Maven version
  source_uri: str            # 등록 시 원본 URI (참고용)
  git_ref: str | None        # Git reference (Git 소스인 경우)
  source_type: str           # "jar", "directory", "git"
  local_path: str            # 중간 저장소 상대 경로 (base directory 기준)

class FileInfo(TypedDict):
  """파일 메타데이터 정보"""
  name: str                  # 파일명
  size: str                  # 파일 크기 (예: "1KB", "2.5MB")
  line_count: int            # 텍스트 파일의 라인 수

class IndexArtifactResult(TypedDict):
  """index_artifact MCP tool 응답"""
  status: str                # "success" 또는 에러 코드
  cache_location: str        # 소스 코드 위치 (성공 시)
  processing_time: str       # 처리 시간 (성공 시)

class SearchFileContentMcpResult(TypedDict):
  """search_file_content MCP tool 응답"""
  status: str                         # "success" 또는 에러 코드
  search_config: SearchConfig         # 검색 설정 (성공 시)
  matches: dict[str, list[SearchMatch]] # 검색 결과 (성공 시)

class FolderInfo(TypedDict):
  """폴더 정보"""
  name: str                    # 폴더명
  file_count: int             # 파일 개수
  files: list[FileInfo]       # 파일 목록 (include_files=True일 때)
  folders: list['FolderInfo'] # 하위 폴더 목록

class ListFolderTreeResult(TypedDict):
  """list_folder_tree MCP tool 응답"""
  status: str                 # "success" 또는 에러 코드
  path: str                   # 탐색된 경로
  max_depth: int              # 적용된 최대 깊이
  folders: list[FolderInfo]   # 하위 디렉토리 목록
  files: list[FileInfo]       # 파일 목록 (include_files=True일 때)

class FileSearchResult(TypedDict):
  """파일 검색 결과"""
  name: str                   # 파일명
  path: str                   # 파일 경로
  size: str                   # 파일 크기 (예: "1KB")
  line_count: int             # 라인 수

class FileSearchConfig(TypedDict):
  """파일 검색 설정 정보"""
  start_path: str             # 검색 시작 경로
  max_depth: int              # 최대 검색 깊이
  pattern: str                # 검색 패턴

class SearchFileNamesResult(TypedDict):
  """search_file_names MCP tool 응답"""
  status: str                 # "success" 또는 에러 코드
  search_config: FileSearchConfig # 검색 설정
  files: list[FileSearchResult] # 검색된 파일 목록

class FileContent(TypedDict):
  """파일 내용 정보"""
  start_line: int             # 시작 라인
  end_line: int               # 종료 라인
  source_code: str            # 파일 내용

class GetFileResult(TypedDict):
  """get_file MCP tool 응답"""
  status: str                 # "success" 또는 에러 코드
  file_info: FileInfo         # 파일 정보
  content: FileContent        # 파일 내용

class ListDirectoryTreeResult(TypedDict):
  """list_directory_tree 반환 타입"""
  path: str                   # 탐색된 경로
  max_depth: int              # 적용된 최대 깊이
  folders: list[FolderInfo]   # 하위 디렉토리 목록
  files: list[FileInfo]       # 파일 목록

class GetFileContentResult(TypedDict):
  """get_file_content 반환 타입"""
  file_info: FileInfo         # 파일 정보
  content: FileContent        # 파일 내용

class SearchFilesByPatternResult(TypedDict):
  """search_files_by_pattern 반환 타입"""
  files: list[FileSearchResult] # 매칭된 파일 정보 리스트
```

## 1. 소스 추출/복사 함수들

### extract_jar_source

```python
def extract_jar_source(jar_path: str, target_dir: str) -> None
```

**기능**: JAR 파일을 지정된 디렉토리에 압축 해제합니다.

**파라미터**:
- `jar_path`: 압축 해제할 JAR 파일의 절대 경로
- `target_dir`: 압축 해제될 대상 디렉토리 경로

**리턴값**: None (성공 시), 실패 시 적절한 예외 발생

**예외**:
- `FileNotFoundError`: JAR 파일이 존재하지 않을 때
- `PermissionError`: 대상 디렉토리 쓰기 권한이 없을 때
- `zipfile.BadZipFile`: 잘못된 JAR 파일 형식일 때

---

### copy_directory_source

```python
def copy_directory_source(source_dir: str, target_dir: str) -> None
```

**기능**: 소스 디렉토리의 내용을 대상 디렉토리로 재귀적으로 복사합니다.

**파라미터**:
- `source_dir`: 복사할 소스 디렉토리의 절대 경로
- `target_dir`: 복사될 대상 디렉토리 경로

**리턴값**: None (성공 시), 실패 시 적절한 예외 발생

**예외**:
- `FileNotFoundError`: 소스 디렉토리가 존재하지 않을 때
- `PermissionError`: 소스 읽기 또는 대상 쓰기 권한이 없을 때

---

### compress_directory_to_7z

```python
def compress_directory_to_7z(source_dir: str, target_7z_path: str) -> None
```

**기능**: 디렉토리를 7z 형식으로 압축하여 저장합니다.

**파라미터**:
- `source_dir`: 압축할 소스 디렉토리의 절대 경로
- `target_7z_path`: 생성될 7z 파일의 절대 경로

**리턴값**: None (성공 시), 실패 시 적절한 예외 발생

**예외**:
- `FileNotFoundError`: 소스 디렉토리가 존재하지 않을 때
- `PermissionError`: 소스 읽기 또는 대상 쓰기 권한이 없을 때
- `RuntimeError`: 7z 압축 프로세스 실행 실패 시

---

### extract_7z_source

```python
def extract_7z_source(archive_path: str, target_dir: str) -> None
```

**기능**: 7z 압축 파일을 지정된 디렉토리에 압축 해제합니다.

**파라미터**:
- `archive_path`: 압축 해제할 7z 파일의 절대 경로
- `target_dir`: 압축 해제될 대상 디렉토리 경로

**리턴값**: None (성공 시), 실패 시 적절한 예외 발생

**예외**:
- `FileNotFoundError`: 7z 파일이 존재하지 않을 때
- `PermissionError`: 대상 디렉토리 쓰기 권한이 없을 때
- `RuntimeError`: 7z 압축 해제 프로세스 실행 실패 시

---

### create_git_worktree

```python
def create_git_worktree(bare_repo_path: str, target_dir: str, git_ref: str) -> None
```

**기능**: 기존 Git bare clone에서 특정 버전의 worktree를 생성합니다.

**파라미터**:
- `bare_repo_path`: Git bare clone 디렉토리 경로 (예: `git-bare/{group_id}/{artifact_id}/bare-repo/`)
- `target_dir`: worktree가 생성될 대상 디렉토리 경로 (예: `code/{group_id}/{artifact_id}/{version}/`)
- `git_ref`: 체크아웃할 브랜치/태그/커밋 (필수)

**리턴값**: None (성공 시), 실패 시 적절한 예외 발생

**동작 과정**:
1. bare repository에서 지정된 git_ref 존재 여부 확인
2. target_dir에 worktree 생성
3. 지정된 git_ref로 체크아웃

**예외**:
- `git.exc.GitCommandError`: Git worktree 생성 실패 시
- `git.exc.InvalidGitRepositoryError`: 잘못된 bare repository 경로일 때
- `GitRefNotFoundError`: 지정된 git_ref가 존재하지 않을 때
- `PermissionError`: 대상 디렉토리 쓰기 권한이 없을 때

---

### get_artifact_code_path

```python
def get_artifact_code_path(group_id: str, artifact_id: str, version: str) -> str
```

**기능**: Maven 좌표를 기반으로 아티팩트의 소스 코드 디렉토리 상대 경로를 생성합니다.

**파라미터**:
- `group_id`: Maven group ID
- `artifact_id`: Maven artifact ID  
- `version`: Maven version

**리턴값**: 아티팩트 소스 코드 디렉토리의 상대 경로 (str)

**예시**:
```python
path = get_artifact_code_path("org.springframework", "spring-core", "5.3.21")
# 리턴: "code/org.springframework/spring-core/5.3.21"
```

**참고**: 실제 절대 경로는 설정 가능한 base directory와 조합하여 사용됩니다.

---

## 2. 파일 시스템 탐색 함수들

### list_directory_tree

```python
def list_directory_tree(
  base_path: str, 
  start_path: str = "", 
  max_depth: int = 1, 
  include_files: bool = True
) -> ListDirectoryTreeResult
```

**기능**: 지정된 경로부터 디렉토리 트리 구조를 탐색하여 계층적 정보를 반환합니다.

**파라미터**:
- `base_path`: 아티팩트의 루트 디렉토리 절대 경로
- `start_path`: 탐색 시작 경로 (base_path 기준 상대 경로)
- `max_depth`: 탐색할 최대 깊이
- `include_files`: 파일 정보 포함 여부

**리턴값**: `ListDirectoryTreeResult` (상단 타입 정의 참조)

---

### get_file_content

```python
def get_file_content(
  base_path: str, 
  file_path: str, 
  start_line: int | None = None, 
  end_line: int | None = None
) -> GetFileContentResult
```

**기능**: 지정된 파일의 내용을 읽어 반환합니다. 선택적으로 라인 범위를 지정할 수 있습니다.

**파라미터**:
- `base_path`: 아티팩트의 루트 디렉토리 절대 경로
- `file_path`: 읽을 파일의 경로 (base_path 기준 상대 경로)
- `start_line`: 시작 라인 번호 (1-based, 선택적)
- `end_line`: 종료 라인 번호 (1-based, 선택적)

**리턴값**: `GetFileContentResult` (상단 타입 정의 참조)

**예외**:
- `FileNotFoundError`: 파일이 존재하지 않을 때
- `PermissionError`: 파일 읽기 권한이 없을 때

---

### search_files_by_pattern

```python
def search_files_by_pattern(
  base_path: str, 
  pattern: str, 
  pattern_type: str, 
  start_path: str = "", 
  max_depth: int | None = None
) -> SearchFilesByPatternResult
```

**기능**: 지정된 패턴으로 파일명을 검색합니다.

**파라미터**:
- `base_path`: 아티팩트의 루트 디렉토리 절대 경로
- `pattern`: 검색 패턴
- `pattern_type`: 패턴 타입 ("glob" 또는 "regex")
- `start_path`: 검색 시작 경로 (base_path 기준 상대 경로)
- `max_depth`: 검색할 최대 깊이 (None이면 무제한)

**리턴값**: `SearchFilesByPatternResult` (상단 타입 정의 참조)

---

### search_file_contents

```python
def search_file_contents(
  base_path: str, 
  query: str, 
  query_type: str, 
  start_path: str = "", 
  max_depth: int | None = None,
  context_before: int = 0, 
  context_after: int = 0, 
  max_results: int | None = None
) -> SearchFileContentsResult
```

**기능**: 파일 내용에서 지정된 쿼리를 검색하고 컨텍스트와 함께 반환합니다.

**파라미터**:
- `base_path`: 아티팩트의 루트 디렉토리 절대 경로
- `query`: 검색 쿼리
- `query_type`: 쿼리 타입 ("string" 또는 "regex")
- `start_path`: 검색 시작 경로 (base_path 기준 상대 경로)
- `max_depth`: 검색할 최대 깊이 (None이면 무제한)
- `context_before`: 매칭 라인 이전 컨텍스트 라인 수
- `context_after`: 매칭 라인 이후 컨텍스트 라인 수
- `max_results`: 최대 결과 수 (None이면 무제한)

**리턴값**: `SearchFileContentsResult` (상단 타입 정의 참조)

---

## 3. 유틸리티 함수들

### get_registered_source_info

```python
def get_registered_source_info(group_id: str, artifact_id: str, version: str) -> RegisteredSourceInfo | None
```

**기능**: 등록된 아티팩트의 소스 정보를 조회합니다.

**파라미터**:
- `group_id`: Maven group ID
- `artifact_id`: Maven artifact ID
- `version`: Maven version

**리턴값**: `RegisteredSourceInfo | None` (상단 타입 정의 참조)

**저장소 구조와의 관계**:
```
<base-directory>/
├── source-jar/             # JAR 파일들이 다운로드되어 저장되는 곳
│   └── org.springframework/spring-core/5.3.21/
│       └── spring-core-5.3.21-sources.jar
├── source-dir/             # 일반 디렉토리들이 7z 압축되어 저장되는 곳
│   └── org.springframework/spring-core/5.3.21/
│       └── sources.7z      # 원본 디렉토리를 7z로 압축
├── git-bare/               # Git bare clone들이 저장되는 곳  
│   └── org.springframework/spring-framework/
│       └── bare-repo/
└── code/                   # 실제 소스 코드가 풀려있는 곳 (index_artifact 결과)
    └── org.springframework/spring-core/5.3.21/
        └── org/springframework/...
```

**`source_type`별 `local_path` 예시**:
- `"jar"`: `source-jar/{group_id}/{artifact_id}/{version}/xxx.jar`
- `"directory"`: `source-dir/{group_id}/{artifact_id}/{version}/sources.7z`
- `"git"`: `git-bare/{group_id}/{artifact_id}/bare-repo/`

**참고**: 실제 절대 경로는 설정 가능한 base directory와 조합하여 사용됩니다.

---


### validate_maven_coordinates

```python
def validate_maven_coordinates(group_id: str, artifact_id: str, version: str) -> bool
```

**기능**: Maven 좌표가 안전한 파일 시스템 경로 생성이 가능한지 검증합니다.

**핵심 목적**: 모든 Maven 좌표 사용 함수들이 다음 패턴으로 파일 시스템 경로를 생성하므로 보안과 호환성을 보장해야 합니다:
```
code/{group_id}/{artifact_id}/{version}/
source-jar/{group_id}/{artifact_id}/{version}/
git-bare/{group_id}/{artifact_id}/
```

**검증 항목**:
1. **디렉토리 탐색 공격 방지**: `../`, `./`, `~` 등 경로 탐색 문자 차단
2. **파일 시스템 호환성**: Windows/Linux/macOS에서 유효하지 않은 문자 차단 (`/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|` 등)
3. **경로 길이 제한**: 너무 긴 좌표로 인한 파일 시스템 오류 방지
4. **빈 값 및 공백 처리**: 빈 문자열, null, 공백만 있는 값 거부

**사용하는 함수들**:
- `get_artifact_code_path` - 경로 생성 전 안전성 검증
- `get_registered_source_info` - 파일 시스템 조회 전 검증  
- `is_artifact_code_available` - 디렉토리 존재 확인 전 검증
- `is_artifact_code_indexed` - 인덱스 파일 확인 전 검증
- 모든 MCP Tool 함수들 - 입력값 검증 단계에서 사용

**파라미터**:
- `group_id`: Maven group ID
- `artifact_id`: Maven artifact ID
- `version`: Maven version

**리턴값**: 파일 시스템 경로 생성에 안전한 좌표이면 True, 그렇지 않으면 False

---

### is_artifact_code_available

```python
def is_artifact_code_available(group_id: str, artifact_id: str, version: str) -> bool
```

**기능**: 지정된 아티팩트의 소스 코드가 `code/` 디렉토리에 존재하는지 확인합니다.

**파라미터**:
- `group_id`: Maven group ID
- `artifact_id`: Maven artifact ID
- `version`: Maven version

**리턴값**: 소스 코드가 존재하면 True, 그렇지 않으면 False

**확인 내용**:
- `code/{group_id}/{artifact_id}/{version}/` 디렉토리 존재 여부
- 디렉토리가 비어있지 않은지 확인 (소스 파일 존재 여부)

---

### is_artifact_code_indexed

```python
def is_artifact_code_indexed(group_id: str, artifact_id: str, version: str) -> bool
```

**기능**: 지정된 아티팩트가 완전히 인덱싱되었는지 확인합니다.

**파라미터**:
- `group_id`: Maven group ID
- `artifact_id`: Maven artifact ID
- `version`: Maven version

**리턴값**: 완전 인덱싱되었으면 True, 그렇지 않으면 False

**확인 내용**:
- `code/{group_id}/{artifact_id}/{version}/.jar-indexer/index.json` 존재 여부
- 인덱스 메타데이터 파일의 유효성 검증

**인덱싱 상태별 디렉토리 구조**:
```
# 1. 코드만 있는 상태 (Code-only)
code/org.springframework/spring-core/5.3.21/
├── org/springframework/core/...   # 소스 코드 파일들
├── META-INF/...
└── (인덱스 파일 없음)

# 2. 완전 인덱싱된 상태 (Fully-indexed)  
code/org.springframework/spring-core/5.3.21/
├── org/springframework/core/...   # 소스 코드 파일들
├── META-INF/...
└── .jar-indexer/                  # 인덱스 메타데이터
    ├── index.json                 # 1단계: 기본 인덱스
    ├── ctags.json                 # 2단계: ctags 결과 (향후)
    └── ast.json                   # 3단계: AST 분석 결과 (향후)
```

---

### get_file_info

```python
def get_file_info(file_path: str) -> FileInfo
```

**기능**: 파일의 메타데이터 정보를 반환합니다.

**파라미터**:
- `file_path`: 정보를 가져올 파일의 절대 경로

**리턴값**: `FileInfo` (상단 타입 정의 참조)

---

### normalize_path

```python
def normalize_path(path: str) -> str
```

**기능**: 크로스 플랫폼 호환성을 위해 경로를 정규화합니다.

**정규화 처리**:
1. **경로 구분자 통일**: OS에 적합한 구분자로 변환 (Unix/macOS: `/`, Windows: `\`)
2. **절대 경로 변환**: 상대 경로를 절대 경로로 변환
3. **경로 정규화**: 중복 구분자 제거, `.` 및 `..` 구성요소 해결
4. **대소문자 일관성**: 대소문자 구분 (Unix/macOS) 및 비구분 (Windows) 파일 시스템 간 일관된 처리

**파라미터**:
- `path`: 정규화할 경로

**리턴값**: 정규화된 절대 경로 문자열

---

### calculate_directory_depth

```python
def calculate_directory_depth(base_path: str, target_path: str) -> int
```

**기능**: 기준 경로에서 대상 경로까지의 디렉토리 깊이를 계산합니다.

**파라미터**:
- `base_path`: 기준 경로
- `target_path`: 대상 경로

**리턴값**: 디렉토리 깊이 (int)

---

## 4. MCP Tool 함수들

### index_artifact

```python
async def index_artifact(group_id: str, artifact_id: str, version: str) -> IndexArtifactResult
```

**기능**: 등록된 아티팩트를 인덱싱하는 MCP tool입니다.

**처리 로직**:
1. `is_artifact_code_indexed()` → 이미 완전 인덱싱됨 → 성공 응답
2. `is_artifact_code_available()` → 코드만 있음 → 인덱싱 작업만
3. 둘 다 False → `get_registered_source_info()`로 소스 확인 → 소스 추출 + 인덱싱

**소스 추출 단계** (3번 경우):
- `get_registered_source_info()`로 중간 저장소 확인
- 타입별 압축 해제:
  - **JAR**: `extract_jar_source(local_path, code_path)`
  - **Directory**: `extract_7z_source(local_path, code_path)` 
  - **Git**: `create_git_worktree(local_path, code_path, git_ref)`

**인덱싱 단계**:
- 1단계: 기본 인덱스 생성 (`.jar-indexer/index.json`)
- 향후 2-3단계에서 ctags, AST 분석 추가

**파라미터**:
- `group_id`: Maven group ID
- `artifact_id`: Maven artifact ID
- `version`: Maven version

**리턴값**: `IndexArtifactResult` (상단 타입 정의 참조)

---

### list_folder_tree

```python
async def list_folder_tree(
  group_id: str, 
  artifact_id: str, 
  version: str,
  path: str = "", 
  include_files: bool = True, 
  max_depth: int = 1
) -> ListFolderTreeResult
```

**기능**: 디렉토리 구조를 탐색하는 MCP tool입니다.

**파라미터**:
- `group_id`: Maven group ID
- `artifact_id`: Maven artifact ID
- `version`: Maven version
- `path`: 탐색 시작 경로
- `include_files`: 파일 포함 여부
- `max_depth`: 최대 탐색 깊이

**리턴값**: `ListFolderTreeResult` (상단 타입 정의 참조)

---

### get_file

```python
async def get_file(
  group_id: str, 
  artifact_id: str, 
  version: str,
  file_path: str, 
  start_line: int | None = None, 
  end_line: int | None = None
) -> GetFileResult
```

**기능**: 파일 내용을 조회하는 MCP tool입니다.

**파라미터**:
- `group_id`: Maven group ID
- `artifact_id`: Maven artifact ID
- `version`: Maven version
- `file_path`: 파일 경로
- `start_line`: 시작 라인 (선택적)
- `end_line`: 종료 라인 (선택적)

**리턴값**: `GetFileResult` (상단 타입 정의 참조)

---

### search_file_names

```python
async def search_file_names(
  group_id: str, 
  artifact_id: str, 
  version: str,
  pattern: str, 
  pattern_type: str, 
  start_path: str = "", 
  max_depth: int | None = None
) -> SearchFileNamesResult
```

**기능**: 파일명을 패턴으로 검색하는 MCP tool입니다.

**파라미터**:
- `group_id`: Maven group ID
- `artifact_id`: Maven artifact ID
- `version`: Maven version
- `pattern`: 검색 패턴
- `pattern_type`: 패턴 타입 ("glob" 또는 "regex")
- `start_path`: 검색 시작 경로
- `max_depth`: 최대 검색 깊이

**리턴값**: `SearchFileNamesResult` (상단 타입 정의 참조)

---

### search_file_content

```python
async def search_file_content(
  group_id: str, 
  artifact_id: str, 
  version: str,
  query: str, 
  query_type: str, 
  start_path: str = "", 
  max_depth: int | None = None,
  context_before: int = 0, 
  context_after: int = 0, 
  max_results: int | None = None
) -> SearchFileContentMcpResult
```

**기능**: 파일 내용을 검색하는 MCP tool입니다.

**파라미터**:
- `group_id`: Maven group ID
- `artifact_id`: Maven artifact ID
- `version`: Maven version
- `query`: 검색 쿼리
- `query_type`: 쿼리 타입 ("string" 또는 "regex")
- `start_path`: 검색 시작 경로
- `max_depth`: 최대 검색 깊이
- `context_before`: 이전 컨텍스트 라인 수
- `context_after`: 이후 컨텍스트 라인 수
- `max_results`: 최대 결과 수

**리턴값**: `SearchFileContentMcpResult` (상단 타입 정의 참조)
