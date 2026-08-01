# blog_agent 이관 안내 (2026-08-01)

이 브랜치(`blog-agent-migration`)는 다른 계정에서 blog_agent 파이프라인을
이어서 쓰기 위해 원본 로컬 저장소에서 필요한 파일만 복사해 올린 것입니다.

## 포함된 것
- `blog_agent/` — 파이프라인 패키지 전체(테스트 포함)
- `.claude/commands/blog-agent.md` — `/blog-agent` 오케스트레이션 커맨드
  (이 저장소를 pull한 뒤 그대로 `.claude/commands/`에 있으면 커맨드로 인식됨)
- `kiwi/naver_searchad_keyword_tool.py`, `kiwi/blue_ocean_finder.py` —
  트렌드/자격증 후보 검색량 조회에 필요한 의존 모듈만
- `skills/blog-post-writer/` — **이 저장소 안의 스테이징 위치일 뿐**,
  실제로는 `~/.claude/skills/blog-post-writer/`로 복사해 넣어야
  스킬로 인식됩니다(홈 디렉터리는 git으로 옮길 수 없어서 여기 임시로 담아둠).

## 설치
```
pip install -r blog_agent/requirements.txt
pip install requests python-dotenv   # kiwi 모듈 의존성
```

`.env`에 다음 3개 필요(searchad.naver.com에서 개인 발급 가능, 무료):
```
NAVER_ADS_API_KEY=...
NAVER_ADS_SECRET_KEY=...
NAVER_ADS_CUSTOMER_ID=...
```

헤드리스 도표 캡처용 Chrome/Edge(또는 Playwright Chromium) 필요.

## 확인
```
pytest blog_agent/tests/ -q   # 76 passed 나와야 정상
```

## 원본
`C:\Users\notebook\Desktop\Apps` (Windows 로컬, git 원격 없음)에서 2026-08-01
스냅샷. 원본 저장소는 이 저장소(`spoug02-glitch/yo`)와 무관한 별개 프로젝트라
`main`을 건드리지 않고 별도 브랜치로만 올렸습니다.
