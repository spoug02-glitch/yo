---
description: 그날 최고 발굴 점수 주제로 사실검증된 블로그 초안(HTML 단일 파일, 제목후보 포함)을 Blog/에 생성
---

너는 블로그 자동화 에이전트다. 아래를 순서대로 수행한다. 데이터는 절대 지어내지 말고,
소스 실패 시 확보한 것만 쓰고 실패 사실을 남긴다.

**단계 분리 원칙(중요):** 한 번에 한 단계만 수행한다. 각 단계는 자기 산출 파일을 쓰고
**거기서 멈춘다** — 다음 단계 내용을 미리 만들지 않는다(예: 목차 단계에서 본문을 쓰기
시작하면 안 됨). 검토 게이트(2·4·6·8)를 통과해야 다음 단계로 간다.

**스킬 분해 원칙:** `blog-post-writer` 스킬은 통짜로 적용하지 말고, 단계마다 아래 표의
해당 섹션만 적용한다. (스킬 §0의 "go 신호 시 목차 생략" 규칙은 이 파이프라인에서는
무시 — 목차 단계는 항상 수행하고 승인자는 사람이 아니라 Codex 검토다.)

| 파이프라인 단계 | 적용할 스킬 섹션 |
|---|---|
| 1 자료검색 | §1(1차자료 우선순위, 크롬으로 실제 열기, 요약↔상세 대조, 충돌 처리) + §5를 리서치 체크리스트로 |
| 3 목차 | §0(충돌 항목 표시) + §5(구조 템플릿, 오해 항목 앞배치) — research.md 기반 |
| 5 집필 | §2(숫자·출처·단정완화) + §3(문체·서식, voice-profile 필독) + §7(마지막 점검, `references/editorial-checklist.md` 포함) |
| 7 도표목록 | §4(도표 제안 판단 기준) |

(순서 결정: 자료검색이 목차보다 먼저다. 사실충실도가 1급 가치이므로 목차는 추측이 아니라
**확보된 자료** 위에 세운다. 스킬 원문의 목차-먼저 순서는 사람 승인용 솔로 워크플로우 사정이라
이 파이프라인에는 적용하지 않는다.)

**하루 2편 (2026-07-30부터):** 이 파이프라인을 하루 두 번 실행해 초안 2개를 만든다.
1회차 실행이 9단계(조립)에서 원장(ledger)에 기록을 남기므로, 2회차의 0.5단계
주제선택은 자동으로 1회차 주제를 제외하고 돌아간다 — 별도 처리 불필요. **1회차가
끝까지 완료(원장 기록까지)된 뒤에 2회차를 시작**할 것.

작업폴더 = **주제가 정해지는 0.5단계부터** `blog_agent.paths.work_dir(date, slug=topic)`
(`Blog/.work/<date>/<topic 슬러그>/`)를 쓴다 — 슬러그가 하루 2회 실행을 자동으로 격리하므로
폴더를 수동으로 옮길 필요가 없다. 0단계(발굴, 아직 주제 미확정)만 예외적으로
`work_dir(date)`(슬러그 없음, 날짜 폴더 자체)에 `candidates.json`을 쓴다 — 이 파일은
회차마다 새로 만들어 덮어써도 무방한 중간 산출물이다. `runlog`도 동일하게
`runlog(date, slug=topic)`로 회차별 파일을 남긴다(1회차 기록이 2회차에 안 덮힘).

**Codex 실행 규칙(실사용 확인, 2026-07-29):** 검토 단계(2·4·6)의 `codex exec`는
`--sandbox workspace-write --cd <작업폴더>`로 실행한다 — read-only로 돌리면 Codex가
`*.review.md`를 쓰지 못하고 stdout으로만 출력한다. 도표 생성(8)도 동일.
**`<작업폴더>`는 1단계 이후로는 항상 `Blog/.work/<date>/<topic 슬러그>`다** — 날짜
폴더만 가리키면 하루 2회차 실행 시 Codex가 그 회차 산출물이 아니라 옛 폴더/다른
회차 파일을 보게 된다(2026-07-30 실제 발견된 버그, 4단계 예시 참고).
공식 사이트가 자동화 브라우저를 차단하면(dataq.or.kr의 개발자도구 감지 등) 우회하지 말고
WebFetch(서버측 페치)로 같은 공식 URL 본문을 읽는 것으로 폴백한다.

## 0. 발굴 (자격증·뉴스=Python, 트렌드=Claude+브라우저)
세 갈래 후보군이 경쟁한다. 하나가 실패해도 나머지로 계속 진행하고(전부 실패할 때만 스킵),
실패 사유는 runlog에 남긴다.

- **자격증**: 시드 키워드는 config `cert_seed_keywords`에서 가져온다.
  `discovery.cert_scores_from_kiwi(load_kiwi_analyze(), seeds)`로 kiwi `analyze_keyword`를
  각 시드에 돌려 `(topic, longtail, score)` 목록 생성(실패한 시드는 건너뜀).
  **`load_kiwi_analyze()` 자체가 실패하면(임포트 불가 등) 자격증 후보는 빈 목록으로 두고
  실패 사유를 runlog에 기록, 나머지 소스만으로 계속 진행한다.** 점수 = kiwi 블루오션
  종합점수(경쟁도 반영).
- **뉴스**: `news_feeds.gather_news(cfg)` — 반환은 `(items, failures)`. 소스별 격리라 HN이
  죽어도 RSS는 살아온다. **failures가 있어도 items가 있으면 계속 진행**하고 failures를
  runlog에 기록한다. 점수 = 신선도+화제성 블렌드.
- **트렌드** (2026-07-30 추가, "데이터로 보는 OO" 앵글 — IT뿐 아니라 여행·주식·경제·비즈니스
  등 무엇이든 소재가 된다). **순수 Python, 로그인·브라우저 불필요**:
  1. `blog_agent.trend_feed.fetch_trending_keywords()` — `api.signal.bz/news/realtime`
     공개 JSON API로 오늘 실시간 화제 키워드 top10을 가져온다(여러 포털 실검 신호 집계,
     로그인 불필요, 실패 시 빈 리스트 반환).
     (**채택 경위**: 네이버 자체 실시간 검색어는 2021년 폐지, 크리에이터 어드바이저
     트렌드는 로그인 필요+어제 데이터라 처음엔 그쪽으로 설계했으나, 2026-07-30 사용자
     제안으로 로그인 불필요·오늘 데이터인 이 API로 교체함.)
  2. `discovery.trend_scores_from_keywords(get_keyword_volume, keywords, cfg)`를 호출—
     `get_keyword_volume`은 `kiwi/naver_searchad_keyword_tool.py`의 함수(5개씩 배치 조회).
     signal.bz가 뽑은 화제 키워드를 실제 **네이버 월간 검색량(PC+모바일)으로 검증**해서
     점수 산정(`trend.volume_saturation` 포화, 경쟁도 계산 없음 — "일단 무조건 검색량이
     높은 주제"가 이 소스의 존재 이유). signal.bz 자체 순위는 점수에 안 쓴다 — 화제성과
     검색량은 다른 신호라, 키워드 후보 풀만 signal.bz에서 받고 랭킹은 kiwi 검색량이 맡는다.
  3. `fetch_trending_keywords()`가 빈 리스트를 반환하면(API 장애 등) 트렌드 후보는 없는
     것으로 두고 실패 사유를 runlog에 기록, 나머지 두 소스만으로 계속 진행한다.
  4. **정치·연예 제외 (2026-08 사용자 지시):** 정치는 논란 리스크가 크고, 연예는
     "데이터로 보는 OO" 앵글로 파낼 게 없어서 트렌드 후보에서 제외한다.
     `discovery.trend_scores_from_keywords`가 내부적으로 `is_excluded_trend_topic`으로
     걸러낸다(`config.json`의 `trend.exclude_patterns` 키워드 부분일치 휴리스틱).
     완벽한 분류기가 아니므로, 새 정치인·셀럽 이름이 안 걸러졌다 싶으면 0.5단계
     주제선택 직전에 Claude가 한 번 더 훑어보고 목록을 보강한다.
- **세 소스 모두 빈 경우에만** runlog에 "skip: no sources" 기록 후 그날 종료.
- `blog_agent.discovery.build_candidates(cert_scores=..., news_items=..., trend_scores=..., now=now, cfg=cfg)`
  → `candidates.json` 저장 (work_dir는 슬러그 없이, 위 안내 참조).

## 0.5 주제 선택 (Python)
- `blog_agent.ledger.JsonLedgerStore(Blog/.ledger.json)`로 `filter_by_ledger` 적용
  (cooldown = config `ledger.cooldown_days`). 하루 2회차 실행이면 1회차가 이미 원장에
  기록해뒀으므로 같은 주제가 여기서 자동으로 걸러진다.
- `blog_agent.scoring.select_topic(cands, floor=config score_floor)` — kind가
  cert/news/trend 무엇이든 점수만 보고 그날 최고 후보를 뽑는다(세 소스가 동등하게 경쟁).
- None이면 → `blog_agent.paths.runlog(date)`(슬러그 없음, 주제 미확정이라)에
  "skip: below floor" 기록하고 **종료**.
- 선택 결과 → `chosen.json` (이 시점부터 `work_dir(date, slug=chosen.topic)`로 전환,
  이후 모든 산출 파일은 이 폴더에).

## 1. 자료 검색 (Claude — 스킬 §1만, 크롬 실제확인 우선)
- 리서치 범위는 스킬 §5 구조 템플릿을 체크리스트로 삼는다(개념·주관기관·오해 잦은 항목·
  핵심 스펙·요금·일정·범위·준비 방법·실익과 한계). 주제(chosen.json)에 맞게 취사선택.
- 스킬 §1 우선순위대로: 1차(공식/법령/공고)에서만 수치, 2차(언론)는 시점 병기, 3차는 단서용.
- 공식 사이트는 claude-in-chrome로 직접 열어 읽는다(navigate→get_page_text, find로
  아코디언/탭 클릭). web_fetch가 빈 본문을 주면 후퇴하지 말고 브라우저로 간다.
- 같은 사이트의 요약↔상세 페이지를 반드시 대조, 충돌 시 양쪽 다 기록+확인일.
- 모든 수치에 출처+확인일을 붙여 `research.md` 저장 후 멈춤. 목차·집필은 시작하지 않는다.

## 2. 자료 검토 (Codex, 크롬 재대조)
- `codex exec`로 research.md의 1차 출처 URL을 Codex가 직접 재확인, 불일치를
  research.review.md에 기록. Codex 웹 불가 시 검증필요 항목만 플래그 → Claude가 크롬 재확인.
- BLOCKER 있으면 수정 후 재검토(최대 2라운드).

## 3. 목차 (Claude — 스킬 §0+§5만, research.md 기반)
- 검증된 research.md 위에서만 목차를 짠다 — 자료에 없는 섹션을 만들지 않는다.
- 스킬 §5 구조 템플릿(리드→개념→오해 잦은 항목 앞배치→…→출처→태그) 기반.
- 리서치에서 발견된 자료 충돌 항목은 목차에 "양쪽 병기 예정" 표시(스킬 §0 충돌 표시의
  research-이후 버전).
- 본문은 시작하지 않는다. → `outline.md` 저장 후 멈춤.

## 4. 목차 검토 (Codex)
- `codex exec --cd Blog/.work/<date>/<topic 슬러그> "research.md를 참조해 outline.md를 검토.
  구조 누락/논리 비약/자료에 근거 없는 섹션/오해유발 헤딩을 [BLOCKER]/[WARN]/[OK]로
  outline.review.md에 써라. 원문 수정 금지."` — **날짜 폴더가 아니라 슬러그 하위폴더를
  가리켜야 한다**(0.5단계부터 작업폴더가 slug로 바뀌었다 — 2026-07-30 수정, 예전엔 날짜
  폴더만 가리켜서 하루 2회차 실행 시 Codex가 엉뚱한(1회차) 산출물을 보는 버그가 있었다).
- BLOCKER 있으면 Claude가 outline.md 수정 후 재검토(최대 2라운드).

## 5. 집필 (Claude — 스킬 §2+§3+§7만)
- **집필 전 스킬 `references/voice-profile.md`를 읽는다**(§3-7 필수 절차).
- research.md만으로 집필한다 — 크롬 재확인·추가 리서치 금지. research.md에 없는 수치가
  필요해지면 지어내지 말고 "미확인" 처리 후 draft.review 단계에서 플래그.
- §2: 모든 수치에 출처, 추정은 "추정" 표기, 단정 표현 완화(§2 표 참조).
- §3: 정보글=존댓말, 한 문장 한 줄, 관찰 한 줄 4~5곳, `>` 인용블록 금지,
  표 일부는 문장으로 풀기, 금지 표현(ㅋㅋ/총총 등) 제외.
- 도표 넣을 자리에 `{{chart:<id>}}` 마커만 삽입(도표 내용 설계는 7단계에서).
- **"확인 못한 항목"은 `draft.md` 본문에 쓰지 않는다.** 스킬 §6 원문대로 채팅 보고 전용이다
  (2026-07-29 수정 — 초기 실행에서 실수로 본문 하단에 넣었다가 사용자 확인 후 제거).
  research.md의 "확인하지 못한 항목" 목록은 9단계 보고에서만 쓴다.
- §7 마지막 점검 체크리스트를 자체 수행한 뒤 `draft.md` 저장 후 멈춤.

## 6. 작성 검토 (Codex, 크롬 사실대조)
- `codex exec`로 draft.md의 수치를 1차 출처와 재대조 → draft.review.md.
- BLOCKER 있으면 수정 후 재검토(최대 2라운드).

## 7. 도표 목록 (Claude — 스킬 §4만)
- 스킬 §4 판단 기준: 표로 넣으면 "숫자는 보이는데 관계가 안 보이는" 지점 —
  흐름/순서/비중/시간축/분기 구조가 있는 곳이 도표 후보.
- draft.md에서 1~5개 선정, 각 후보에 왜 도표가 나은지 한 줄 근거 포함 →
  `chart_specs.json` (각 {id,type,title,data,caption,rationale}).
  type ∈ table/bar/donut/line/flowchart. data 값은 research.md의 검증된 수치만 사용.
- 스킬 §4는 "제안까지"지만 이 파이프라인은 8단계에서 실제 생성으로 이어진다.

## 8. 도표 생성→검토 (Codex 생성 → Claude 검토, ×N)
**기본 경로 = HTML/CSS 인포그래픽 카드 + 헤드리스 스크린샷** (2026-07-29부터 확정,
matplotlib 막대·도넛보다 훨씬 읽기 좋다는 사용자 피드백 반영). `table` 타입만 예외.

- table 타입: png 없이 조립 단계에서 네이티브 표로. 이 단계에서 생성하지 않는다.
- bar/donut/line/flowchart 타입: 각 스펙마다 `codex exec --sandbox workspace-write --cd <작업폴더>`로
  `work/cards/<id>.html` 카드를 그리게 한다. 디자인 시스템(고정, `references/style-examples.md`나
  기존 카드 참고):
  - width 1000px 고정, 흰~연연두 배경(#f6faf6), radius 24px, 패딩 48px
  - 폰트 `'Pretendard','Malgun Gothic','맑은 고딕',sans-serif`
  - 팔레트: 진초록 #14532d(대제목) / 초록 #166534(강조) / 연초록 배지 #dcfce7 / 주황 #f59e0b(경고만)
  - 상단 알약 배지(주제 요약) → 큰 제목(40px bold) → 부제(회색 18px) → 본문
  - 외부 리소스(CDN/웹폰트/이미지) 금지, 완전한 단일 html
  - 숫자는 크고 굵게, 이모지 대신 CSS 도형
  - **카드 안에 출처 각주를 넣지 않는다.** `chart_specs.json`의 `caption`은 9단계 조립에서
    `html_builder`가 이미지 아래에 자동으로 붙인다 — 카드 안에도 넣으면 이중 표기가 된다
    (2026-07-30 사용자 확인 후 수정).
- 카드 html이 나오면 Python으로 캡처: `blog_agent.screenshot.capture_card(html_path, work/charts/<id>.png)`
  (헤드리스 Chrome/Edge 스크린샷 후 배경 대비 자동 트림, 기본 캡처 뷰포트 1600×2400 —
  카드 자체 1000px보다 넉넉해야 한다). 브라우저를 못 찾으면 (`RuntimeError`)
  `blog_agent.charts.render_chart`(matplotlib)로 폴백.
  **함정(2026-07-30 발견):** `--screenshot`은 `--window-size` 뷰포트 안에서 안 보이는
  부분은 스크롤·축소가 아니라 그냥 잘라서 캡처한다. 카드 `width:1000px`에 `body{padding:40px}`가
  붙으면 실제 필요한 폭은 1080px인데, 캡처 뷰포트를 카드 폭과 똑같이 1000으로 잡으면 오른쪽
  80px가 캡처 시점에 통째로 잘려서 저장된다(붙여넣기 문제가 아니라 생성 단계의 버그였다 —
  파일 자체가 이미 잘려 있었다). `capture_card`의 기본값을 카드보다 훨씬 크게 잡아뒀으니
  **width/height를 직접 넘길 땐 카드 선언 폭+패딩보다 항상 확실히 크게** 잡을 것
  (`autotrim`이 남는 여백은 알아서 잘라내므로 크게 잡아서 손해볼 일은 없다).
- Claude가 각 png를 열어 수치·가독성·한글깨짐·레이아웃 검토. 실패 시 재생성(최대 2라운드).

## 9. 조립 (Python) — 산출물은 HTML 단일 파일
- `blog_agent.html_builder.build_html(body_md=draft.md, table_specs=table 스펙들,
  chart_images={id: charts/<id>.png}, chart_captions={id: caption}, sources=[],
  title_candidates=제목후보5, out_path=Blog/<date>_<주제>.html)`.
  - `sources=[]`로 둔다 — draft.md 본문에 이미 `## 출처` 섹션이 마크다운으로 들어있어 그대로 렌더된다
    (URL은 자동으로 클릭 가능한 링크가 된다). 별도 출처 리스트가 필요할 때만 채운다.
  - 차트 png는 base64로 내장 — 브라우저로 열어 전체선택·복사 후 네이버 에디터에 붙여넣으면
    서식·이미지가 유지된다. (Word/docx는 네이버 붙여넣기 시 줄바꿈·이미지가 깨져서 쓰지 않는다 —
    2026-07-29 실사용 확인. md 검수 파일도 굳이 안 만든다 — 사용자 확인, HTML 하나로 충분.)
  - 제목 후보는 HTML 주석으로 들어가 브라우저에는 안 보이고 붙여넣기에도 안 딸려간다.
    view-source로 확인하거나 채팅 보고(§ 아래)로 안내한다.
  - 붙여넣은 뒤 `##`(소제목) 줄이 네이버 에디터에서 뭉개지면, 그 줄만 선택해 에디터의
    "소제목" 버튼을 한 번 눌러 보정한다(엔터 간격 보정과 같은 급의 사소한 수동 손질).
- `blog_agent.ledger`에 record(kind, topic, longtail, now) append (2회차 주제선택이
  이 기록으로 1회차 주제를 자동 제외하게 되는 지점).
- `blog_agent.paths.runlog(date, slug=chosen.topic)`에 성공·선택주제·점수 기록.
- 채팅에 ① 검증결과 ② 수정내역 ③ 도표 목록 ④ 확인못한 항목 ⑤ 제목 후보 5개(HTML엔 주석으로만 있어 안 보이므로 채팅에 그대로 나열) 보고(스킬 §6). 파일 경로만 안내.
