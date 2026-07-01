#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_rag_kb.py — CampusFlow RAG 지식베이스 35문서 생성 (knowledge/<domain>/*.md) + index.json.
cases.jsonl의 related_rag_paths와 1:1 매칭. applies_to_case_types는 데이터셋에서 자동 도출.
모든 문서 synthetic_demo. 사용: python3 generate_rag_kb.py
"""
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
KB = ROOT / "knowledge"
CASES = [json.loads(l) for l in open(ROOT / "data/cases.jsonl") if l.strip()]

# rag_path -> case_types (데이터셋에서 도출)
PATH_CT = defaultdict(set)
for c in CASES:
    for p in c["related_rag_paths"]:
        PATH_CT[p].add(c["case_type"])

DOM_KO = {"practicum": "현장실습", "scholarship": "장학", "academic": "학사",
          "complaint": "민원", "international": "유학생", "student-success": "학생성공"}

# slug -> 콘텐츠 (title, purpose, steps[], docs[], criteria[(항목,기준)], exceptions[], related[slug])
C = {
 # ── practicum ──
 "practicum/early-withdrawal": ("현장실습 중도 포기 처리 규정",
   "건강·기관 사정 등으로 현장실습을 중도 포기하는 경우의 승인·학점 처리 기준을 정한다.",
   ["학생이 포기 의사를 학생포털/지도교수에게 제출","사유 증빙(진단서·기관확인서) 접수","지도교수 면담 및 학점 처리 기준 안내","산학협력팀 검토 후 승인","결과 통보 및 학점/등록 처리"],
   ["실습협약서","진단서(해당 시)","기관확인서","지도교수확인서"],
   [("정당 사유","진단서 등 증빙 시 학점 인정/유예 가능"),("단순 변심","학점 미인정, 재수강 안내")],
   ["보험 가입 상태·잔여 실습시간 확인 필수","기관과의 협약 위반 여부 점검"],
   ["practicum/credit-recognition","practicum/insurance-guide"]),
 "practicum/credit-recognition": ("현장실습 학점 인정 기준",
   "현장실습 시간·평가에 따른 학점 인정 및 중도 종료 시 부분 인정 기준을 정한다.",
   ["실습시간·실습일지·기관평가서 확인","최소 이수시간 충족 여부 판정","부분 이수 시 학점 산정","성적 처리"],
   ["실습일지","출근부","기관평가서"],
   [("정상 이수","규정 시간 충족 시 정규 학점"),("부분 이수","정당 사유 + 일정 비율 충족 시 부분 인정")],
   ["중도 포기 건은 early-withdrawal 규정과 함께 적용"],
   ["practicum/early-withdrawal","practicum/evaluation"]),
 "practicum/attendance": ("현장실습 출근·근태 관리 지침",
   "현장실습 출근 불량·무단결근 발생 시 확인 및 조치 절차를 정한다.",
   ["기관의 출근 이상 통보 접수","출근부·실습일지 대조","학생 면담 및 사유 확인","경고/시정 또는 중단 검토"],
   ["출근부","실습일지","기관확인서"],
   [("경미","경고 후 시정"),("반복·무단","실습 중단·학점 미인정 검토")],
   ["질병·경조사 등 정당 사유는 증빙 시 결근 제외"],
   ["practicum/journal","practicum/attendance"]),
 "practicum/journal": ("실습일지 작성·제출 지침",
   "주별 실습일지 작성·제출 기준과 미제출 시 조치를 정한다.",
   ["주별 실습일지 작성","지도교수 확인","미제출 시 독려 및 마감 안내","최종 평가에 반영"],
   ["실습일지","출근부"],
   [("정상 제출","평가 반영"),("미제출","감점 또는 학점 처리 보류")],
   ["마감 후 미제출 지속 시 출근 관리 지침과 연계"],
   ["practicum/attendance","practicum/evaluation"]),
 "practicum/evaluation": ("기관 평가서 처리 지침",
   "실습 종료 후 기관 평가서 수령·반영 및 지연 시 처리 기준을 정한다.",
   ["기관에 평가서 요청","수령·검토","성적 반영","지연 시 독촉 및 잠정 처리"],
   ["기관평가서","실습일지"],
   [("정상 수령","성적 반영"),("지연","잠정 보류 후 수령 시 정정")],
   ["기관 미회신 장기화 시 지도교수 직접 평가 보완"],
   ["practicum/journal","practicum/credit-recognition"]),
 "practicum/insurance-guide": ("현장실습 산재·상해보험 가이드",
   "실습 전 보험 의무 가입과 미가입·사고 시 처리 기준을 정한다.",
   ["실습 시작 전 보험 가입","보험가입증명서 제출","미가입 시 실습 보류","사고 시 경위서·진단서 접수 및 보험 처리"],
   ["보험가입증명서","실습협약서","사고경위서(사고 시)"],
   [("가입 완료","실습 진행"),("미가입","실습 불가 — 가입 후 진행")],
   ["사고 발생 시 즉시 기관·지도교수 통보 후 보험 청구"],
   ["practicum/early-withdrawal"]),
 "practicum/site-change": ("실습기관 변경 처리 절차",
   "실습 중 기관 변경 요청의 승인 요건과 절차를 정한다.",
   ["변경 사유 접수","신규 기관 적격성 검토","신규 협약·서약서 체결","승인 및 학점 연속성 처리"],
   ["실습기관변경신청서","신규협약서","학생서약서"],
   [("정당 사유","승인 후 변경"),("부적격 기관","반려")],
   ["기존 기관 실습시간은 합산 인정 여부 별도 판정"],
   ["practicum/credit-recognition"]),
 # ── scholarship ──
 "scholarship/duplicate-award": ("장학금 중복 수혜 심사 기준",
   "교내·국가·외부 장학 동시 수혜 시 중복 여부 판정 및 조정 기준을 정한다.",
   ["수혜내역확인서로 중복 여부 확인","등록금 초과 수혜분 산정","조정/환수 대상 판정","승인 라인 상신"],
   ["장학신청서","수혜내역확인서","성적증명서"],
   [("등록금 이내","중복 허용"),("등록금 초과","초과분 조정·환수")],
   ["성적우수+가계곤란 중복은 규정상 1개로 제한"],
   ["scholarship/payment-policy","scholarship/clawback"]),
 "scholarship/payment-policy": ("장학금 지급 규정",
   "장학금 종류별 지급 시기·방식·중복 처리 원칙을 정한다.",
   ["선발 확정","지급 대상·금액 산정","중복 수혜 점검","지급 처리"],
   ["장학신청서","통장사본"],
   [("정상","규정 시기 지급"),("중복","초과분 조정")],
   ["휴학·자퇴 시 일할 계산 및 환수 적용"],
   ["scholarship/duplicate-award","scholarship/clawback"]),
 "scholarship/clawback": ("장학금 환수 처리 가이드",
   "부정 수혜·중복·학적 변동 시 장학금 환수 기준과 절차를 정한다.",
   ["환수 사유 확인","환수액 산정","환수통지서 발송","납부 확인"],
   ["환수통지서","수혜내역확인서"],
   [("학적 변동","일할 환수"),("부정 수혜","전액 환수")],
   ["분할 납부 신청 가능, 미납 시 성적/증명 발급 제한 검토"],
   ["scholarship/payment-policy","scholarship/duplicate-award"]),
 "scholarship/documents": ("장학 신청 서류 기준",
   "장학 신청 시 제출 서류와 미비 시 보완 절차를 정한다.",
   ["신청서·증빙 접수","서류 완비 점검","미비 시 보완 요청","심사 진행"],
   ["장학신청서","소득증빙서류","통장사본"],
   [("완비","심사 진행"),("미비","보완 후 재접수")],
   ["마감 후 보완 불가 항목 사전 안내"],
   ["scholarship/income-bracket"]),
 "scholarship/income-bracket": ("소득분위 확인 절차",
   "가계곤란 장학의 소득분위 확인 및 증빙 기준을 정한다.",
   ["소득분위 산정자료 제출","한국장학재단 분위 확인","자격 판정","결과 반영"],
   ["소득증빙서류","가족관계증명서"],
   [("8분위 이하","자격 충족"),("초과","자격 미달")],
   ["분위 미산정자는 별도 증빙으로 잠정 심사"],
   ["scholarship/documents"]),
 "scholarship/recommendation": ("추천서 처리 기준",
   "추천 장학의 추천서 요건과 누락 시 처리 절차를 정한다.",
   ["추천서 접수","추천 요건 확인","누락 시 보완 요청","심사 반영"],
   ["추천서","장학신청서"],
   [("적격 추천","반영"),("누락","보완 후 심사")],
   ["추천인 자격(지도교수 등) 확인 필요"],
   ["scholarship/documents"]),
 # ── academic ──
 "academic/grade-appeal": ("성적 이의신청 처리 지침",
   "성적 공시 후 이의신청의 접수·검토·정정 절차를 정한다.",
   ["성적공시 후 기한 내 이의신청 접수","담당 교수 근거 검토","정정 사유 시 정정, 아닐 시 사유 통보","결과 통보"],
   ["성적이의신청서","근거자료"],
   [("정정 사유","성적 정정"),("사유 없음","원 성적 유지")],
   ["접수 기한(공시 후 일정일) 경과 시 불수리"],
   ["academic/graduation-audit"]),
 "academic/enrollment-change": ("수강 정정 처리 지침",
   "수강 정정 기간 내 신청 처리와 정원·선수과목 기준을 정한다.",
   ["수강변경원 접수","정원·선수과목 확인","지도교수 승인","정정 반영"],
   ["수강변경원","지도교수확인서"],
   [("정원 내","정정 승인"),("정원 초과","불가/대기")],
   ["정정 기간 외 변경 불가"],
   ["academic/grade-appeal"]),
 "academic/leave-policy": ("휴학 처리 규정",
   "일반·군·질병 휴학의 신청 요건과 처리 절차를 정한다.",
   ["휴학원·사유증빙 접수","학적 처리","등록금 처리(이월/환불)","결과 통보"],
   ["휴학원","사유증빙"],
   [("일반 휴학","연한 내 허용"),("질병/군","증빙 시 허용")],
   ["등록 후 휴학은 등록금 처리 규정 적용"],
   ["academic/return-policy"]),
 "academic/return-policy": ("복학 처리 규정",
   "복학 신청 요건·등록 절차와 미등록 시 처리를 정한다.",
   ["복학원 접수","휴학 사유 종료 확인","등록금 납부","학적 복원"],
   ["복학원","등록금납부확인서"],
   [("기한 내","정상 복학"),("미등록","제적 검토")],
   ["수강신청 일정과 연계 안내"],
   ["academic/leave-policy"]),
 "academic/graduation-audit": ("졸업요건 사정 지침",
   "졸업 요건(학점·필수·성적) 충족 여부 사정 및 미충족 시 안내를 정한다.",
   ["졸업사정표 작성","요건 충족 점검","미충족 항목 안내","추가 이수 계획 수립"],
   ["졸업사정표","성적증명서"],
   [("충족","졸업 사정 통과"),("미충족","추가 이수 안내")],
   ["전공·교양·졸업학점 별도 점검"],
   ["academic/grade-appeal"]),
 "academic/academic-warning": ("학사경고 처리 규정",
   "학사경고 부과 기준과 상담·관리 연계 절차를 정한다.",
   ["성적 기준 미달자 추출","학사경고 부과·통보","상담 연계","후속 관리"],
   ["학사경고확인서","상담일지"],
   [("1회","경고+상담"),("연속","제적 검토")],
   ["학생성공센터 상담(warning-care)과 연계"],
   ["academic/leave-policy"]),
 "academic/transfer": ("전과 처리 절차",
   "전과 신청 요건·심사·학점 인정 기준을 정한다.",
   ["전과신청서 접수","성적·정원 심사","지도교수 의견","승인 및 학적 변경"],
   ["전과신청서","성적증명서","지도교수확인서"],
   [("요건 충족","승인"),("정원 초과","경쟁 선발")],
   ["전적 학과 이수학점 인정 범위 판정"],
   ["academic/enrollment-change"]),
 # ── complaint ──
 "complaint/handling-policy": ("민원 처리 표준 절차",
   "일반 민원의 접수·처리·통보 표준 절차와 처리기한을 정한다.",
   ["민원접수서 접수","담당 배정","사실 확인·처리","처리결과 통보"],
   ["민원접수서","처리경위서"],
   [("일반","법정 처리기한 내 회신"),("반복·악성","별도 관리")],
   ["처리 지연 시 중간 안내 의무"],
   ["complaint/refund-policy"]),
 "complaint/grade-info-policy": ("성적정보 제공 기준",
   "성적 등 학생 정보의 제3자(학부모 포함) 제공 가능 범위를 정한다.",
   ["요청자·대상 확인","본인 동의 여부 확인","동의 시 범위 내 제공, 미동의 시 거절·안내","기록 보존"],
   ["개인정보동의서","본인확인서류"],
   [("본인 동의 있음","범위 내 제공"),("동의 없음","제공 불가 — 절차 안내")],
   ["성인 학생 성적은 본인 동의 없이 학부모 제공 불가"],
   ["complaint/privacy-guideline"]),
 "complaint/privacy-guideline": ("개인정보 보호 지침",
   "학생 개인정보의 수집·이용·제3자 제공 원칙과 동의 절차를 정한다.",
   ["개인정보 처리 목적 고지","동의 수령","최소 수집·목적 내 이용","제3자 제공 시 별도 동의"],
   ["개인정보동의서"],
   [("동의 범위 내","처리 가능"),("범위 외","처리 불가")],
   ["민감정보(성적·건강 등) 별도 동의, 미동의 시 제공 금지"],
   ["complaint/grade-info-policy"]),
 "complaint/refund-policy": ("등록금 환불 처리 절차",
   "등록금 환불 요청의 사유별 환불 비율·절차를 정한다.",
   ["환불신청서 접수","사유·시점 확인","환불액 산정","지급 처리"],
   ["환불신청서","통장사본","증빙자료"],
   [("학기 초","규정 비율 환불"),("기간 경과","비율 차등/불가")],
   ["휴학·자퇴 시점에 따른 환불 비율 적용"],
   ["complaint/handling-policy"]),
 "complaint/misconduct": ("부정행위 제보 처리 지침",
   "시험 부정행위 등 제보의 접수·조사·조치 절차를 정한다.",
   ["제보 접수","사실 조사","위원회 심의","징계·조치 및 통보"],
   ["제보접수서","증빙자료"],
   [("경미","경고"),("중대","성적 무효·징계")],
   ["제보자 보호 및 비밀 유지"],
   ["complaint/handling-policy"]),
 # ── international ──
 "international/visa-documents": ("유학생 비자 서류 안내",
   "D-2 등 유학 비자 발급·유지를 위한 필수 서류와 누락 시 처리를 정한다.",
   ["필요 서류 안내","서류 접수·점검","누락분 보완 요청","제출 완료 확인"],
   ["비자사본","표준입학허가서","재정증명서"],
   [("완비","정상 처리"),("누락","보완 후 처리 — 체류에 영향")],
   ["만료 임박 건은 stay-management와 함께 처리"],
   ["international/stay-management","international/alien-registration"]),
 "international/alien-registration": ("외국인등록·신고 절차",
   "입국 후 외국인등록 및 주소·체류지 변경 신고 절차를 정한다.",
   ["입국 후 기한 내 외국인등록","외국인등록증 수령","주소 변경 시 14일 내 신고","기록 갱신"],
   ["외국인등록증","체류지변경신고서"],
   [("기한 내","정상"),("지연","과태료·체류 영향")],
   ["출입국 신고 누락 시 체류 관리 불이익"],
   ["international/visa-documents","international/stay-management"]),
 "international/stay-management": ("체류기간 관리 지침",
   "체류기간 만료 임박자의 연장 신청 관리와 모니터링을 정한다.",
   ["만료 1개월 전 대상자 추출","연장 서류 안내","연장 신청 지원","결과 확인"],
   ["외국인등록증","체류기간연장신청서","재학증명서"],
   [("정상 연장","체류 유지"),("미신청","불법체류 위험")],
   ["만료 임박은 최우선 처리(리스크 높음)"],
   ["international/visa-documents","international/alien-registration"]),
 "international/insurance": ("유학생 보험 가입 가이드",
   "유학생 의무 보험 가입 기준과 미가입 시 안내를 정한다.",
   ["보험 가입 안내","가입·증서 제출","미가입자 관리","갱신 안내"],
   ["보험증서","외국인등록증"],
   [("가입","정상"),("미가입","가입 독려·등록 제한 검토")],
   ["체류·등록 요건과 연계"],
   ["international/stay-management"]),
 "international/korean": ("한국어 능력 요건 안내",
   "수학에 필요한 한국어(TOPIK) 요건과 미달 시 지원을 정한다.",
   ["TOPIK 성적 확인","요건 미달자 파악","한국어 수업 연계","수강계획 조정"],
   ["TOPIK성적표","수강계획서"],
   [("요건 충족","정상 수강"),("미달","한국어 지원 프로그램 연계")],
   ["전공 수강과 한국어 보충 병행"],
   ["international/visa-documents"]),
 "international/tuition": ("유학생 등록금 분납 안내",
   "등록금 분납 신청 요건과 절차를 정한다.",
   ["분납신청서 접수","재정 상황 확인","분납 일정 승인","납부 관리"],
   ["분납신청서","재정증명서"],
   [("요건 충족","분납 승인"),("미납","제적·체류 영향")],
   ["분납 미이행 시 체류 관리와 연계"],
   ["international/stay-management"]),
 # ── student-success ──
 "student-success/warning-care": ("학사경고 상담 매뉴얼",
   "학사경고 학생 대상 상담·학습계획 수립 및 후속 관리를 정한다.",
   ["대상자 추출(평점 기준)","상담 동의 수령","1:1 상담·학습계획 수립","튜터링·심리상담 연계","후속 모니터링"],
   ["상담일지","학습계획서","상담동의서"],
   [("개선","모니터링 종료"),("미개선","집중관리·제적 검토")],
   ["상담 동의 없으면 기록·연계 제한(consent 절차 우선)"],
   ["student-success/counseling-consent","student-success/dropout-prevention"]),
 "student-success/dropout-prevention": ("중도탈락 위험 관리 지침",
   "중도탈락 위험 학생의 위험도 평가와 개입 절차를 정한다.",
   ["위험도 평가(출석·성적·상담)","위험군 분류","맞춤 개입(상담·튜터링·장학 연계)","효과 모니터링"],
   ["위험도평가서","상담일지","상담동의서"],
   [("고위험","집중 개입"),("중위험","정기 모니터링")],
   ["개인정보·상담 동의 범위 내 데이터 활용"],
   ["student-success/warning-care","student-success/counseling-consent"]),
 "student-success/counseling-consent": ("상담 동의 절차",
   "상담·개입 시 개인정보·상담 동의 수령과 활용 범위를 정한다.",
   ["동의서 고지·수령","동의 범위 기록","범위 내 상담·연계","동의 철회 처리"],
   ["상담동의서","연계의뢰서(해당 시)"],
   [("동의","상담·연계 진행"),("미동의","기록·제3자 연계 제한")],
   ["민감정보(심리·건강) 별도 동의 필수"],
   ["student-success/warning-care","student-success/dropout-prevention"]),
 "student-success/career": ("진로 상담 운영 지침",
   "진로 상담 신청·운영과 취업 연계 절차를 정한다.",
   ["진로상담 신청 접수","상담 진행·기록","진로 계획 수립","취업·인턴 연계"],
   ["진로상담신청서","상담일지"],
   [("정상","상담 진행"),("연계 필요","취업지원 연계")],
   ["상담 기록은 동의 범위 내 보관"],
   ["student-success/counseling-consent"]),
 "student-success/attendance-alert": ("출석 경고 관리 지침",
   "출석 미달 경고 발생 시 확인·상담 연계 절차를 정한다.",
   ["출석 현황 모니터링","경고 대상 통보","상담 연계","개선 확인"],
   ["출석현황표","상담일지"],
   [("개선","종료"),("미개선","학사경고·중도탈락 관리 연계")],
   ["질병 등 정당 사유는 증빙 시 제외"],
   ["student-success/warning-care","student-success/dropout-prevention"]),
}


def make_md(slug, conf):
    domain_dir = slug.split("/")[0]
    domain_id = "student_success" if domain_dir == "student-success" else domain_dir
    title, purpose, steps, docs, criteria, exc, related = conf
    path = f"knowledge/{slug}.md"
    cts = sorted(PATH_CT.get(path, []))
    fm = (f"---\ndoc_id: {slug.replace('/', '-')}\ndomain: {domain_id}\ntitle: {title}\n"
          f"applies_to_case_types: [{', '.join(cts)}]\nversion: \"1.0\"\nlast_updated: \"2026-07-01\"\nsource_type: synthetic_demo\n---\n")
    body = [f"# {title}", "",
            "## 1. 목적·적용 범위", purpose, "",
            "## 2. 처리 절차"]
    body += [f"{i}. {s}" for i, s in enumerate(steps, 1)]
    body += ["", "## 3. 필요 서류"]
    body += [f"- {d}" for d in docs]
    body += ["", "## 4. 판정·승인 기준", "| 구분 | 기준 |", "|---|---|"]
    body += [f"| {a} | {b} |" for a, b in criteria]
    body += ["", "## 5. 예외·유의사항"]
    body += [f"- {e}" for e in exc]
    body += ["", "## 6. 관련 문서"]
    body += [f"- knowledge/{r}.md" for r in related]
    body += ["", f"> ※ 본 문서는 synthetic_demo 입니다. 적용 case_type: {', '.join(cts) or '(미참조)'}"]
    return path, fm + "\n".join(body) + "\n"


def main():
    KB.mkdir(exist_ok=True)
    index = []
    written = 0
    for slug, conf in C.items():
        path, content = make_md(slug, conf)
        fp = ROOT / path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
        domain_dir = slug.split("/")[0]
        index.append({"path": path, "doc_id": slug.replace("/", "-"),
                      "domain": "student_success" if domain_dir == "student-success" else domain_dir,
                      "title": conf[0], "applies_to_case_types": sorted(PATH_CT.get(path, []))})
        written += 1
    (KB / "index.json").write_text(json.dumps({"source_type": "synthetic_demo", "count": len(index),
                                                "documents": index}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ RAG 지식문서 {written}개 생성 + index.json")
    from collections import Counter
    print(dict(Counter(d["domain"] for d in index)))


if __name__ == "__main__":
    main()
