# -*- coding: utf-8 -*-

"""
KIS Open Trading API에서 사용하는 컬럼명과 한글 설명 매핑 정보
"""

PRICE_COLUMN_MAPPING = {
    'iscd_stat_cls_code': '종목 상태 구분 코드', 'marg_rate': '증거금 비율',
    'rprs_mrkt_kor_name': '대표 시장 한글 명', 'new_hgpr_lwpr_cls_code': '신 고가 저가 구분 코드',
    'bstp_kor_isnm': '업종 한글 종목명', 'temp_stop_yn': '임시 정지 여부',
    'oprc_rang_cont_yn': '시가 범위 연장 여부', 'clpr_rang_cont_yn': '종가 범위 연장 여부',
    'crdt_able_yn': '신용 가능 여부', 'grmn_rate_cls_code': '보증금 비율 구분 코드',
    'elw_pblc_yn': 'ELW 발행 여부', 'stck_prpr': '주식 현재가', 'prdy_vrss': '전일 대비',
    'prdy_vrss_sign': '전일 대비 부호', 'prdy_ctrt': '전일 대비율',
    'acml_tr_pbmn': '누적 거래 대금', 'acml_vol': '누적 거래량',
    'prdy_vrss_vol_rate': '전일 대비 거래량 비율', 'stck_oprc': '주식 시가',
    'stck_hgpr': '주식 최고가', 'stck_lwpr': '주식 최저가', 'stck_mxpr': '주식 상한가',
    'stck_llam': '주식 하한가', 'stck_sdpr': '주식 기준가',
    'wghn_avrg_stck_prc': '가중 평균 주식 가격', 'hts_frgn_ehrt': 'HTS 외국인 소진율',
    'frgn_ntby_qty': '외국인 순매수 수량', 'pgtr_ntby_qty': '프로그램매매 순매수 수량',
    'pvt_scnd_dmrs_prc': '피벗 2차 저항 가격', 'pvt_frst_dmrs_prc': '피벗 1차 저항 가격',
    'pvt_pont_val': '피벗 포인트 값', 'pvt_frst_dmsp_prc': '피벗 1차 지지 가격',
    'pvt_scnd_dmsp_prc': '피벗 2차 지지 가격', 'dmrs_val': '저항 값', 'dmsp_val': '지지 값',
    'cpfn': '자본금', 'rstc_wdth_prc': '제한 폭 가격', 'stck_fcam': '주식 액면가',
    'stck_sspr': '주식 대용가', 'aspr_unit': '호가단위',
    'hts_deal_qty_unit_val': 'HTS 매매 수량 단위 값', 'lstn_stcn': '상장 주수',
    'hts_avls': 'HTS 시가총액', 'per': 'PER', 'pbr': 'PBR', 'stac_month': '결산 월',
    'vol_tnrt': '거래량 회전율', 'eps': 'EPS', 'bps': 'BPS', 'd250_hgpr': '250일 최고가',
    'd250_hgpr_date': '250일 최고가 일자', 'd250_hgpr_vrss_prpr_rate': '250일 최고가 대비 현재가 비율',
    'd250_lwpr': '250일 최저가', 'd250_lwpr_date': '250일 최저가 일자',
    'd250_lwpr_vrss_prpr_rate': '250일 최저가 대비 현재가 비율', 'stck_dryy_hgpr': '주식 연중 최고가',
    'dryy_hgpr_vrss_prpr_rate': '연중 최고가 대비 현재가 비율', 'dryy_hgpr_date': '연중 최고가 일자',
    'stck_dryy_lwpr': '주식 연중 최저가', 'dryy_lwpr_vrss_prpr_rate': '연중 최저가 대비 현재가 비율',
    'dryy_lwpr_date': '연중 최저가 일자', 'w52_hgpr': '52주일 최고가',
    'w52_hgpr_vrss_prpr_ctrt': '52주일 최고가 대비 현재가 대비', 'w52_hgpr_date': '52주일 최고가 일자',
    'w52_lwpr': '52주일 최저가', 'w52_lwpr_vrss_prpr_ctrt': '52주일 최저가 대비 현재가 대비',
    'w52_lwpr_date': '52주일 최저가 일자', 'whol_loan_rmnd_rate': '전체 융자 잔고 비율',
    'ssts_yn': '공매도가능여부', 'stck_shrn_iscd': '주식 단축 종목코드',
    'fcam_cnnm': '액면가 통화명', 'cpfn_cnnm': '자본금 통화명', 'apprch_rate': '접근도',
    'frgn_hldn_qty': '외국인 보유 수량', 'vi_cls_code': 'VI적용구분코드',
    'ovtm_vi_cls_code': '시간외단일가VI적용구분코드', 'last_ssts_cntg_qty': '최종 공매도 체결 수량',
    'invt_caful_yn': '투자유의여부', 'mrkt_warn_cls_code': '시장경고코드',
    'short_over_yn': '단기과열여부', 'sltr_yn': '정리매매여부', 'mang_issu_cls_code': '관리종목여부'
}

BALANCE_COLUMN_MAPPING = {
    'pdno': '상품번호', 'prdt_name': '상품명', 'trad_dvsn_name': '매매구분명',
    'bfdy_buy_qty': '전일매수수량', 'bfdy_sll_qty': '전일매도수량', 'thdt_buyqty': '금일매수수량',
    'thdt_sll_qty': '금일매도수량', 'hldg_qty': '보유수량', 'ord_psbl_qty': '주문가능수량',
    'pchs_avg_pric': '매입평균가격', 'pchs_amt': '매입금액', 'prpr': '현재가',
    'evlu_amt': '평가금액', 'evlu_pfls_amt': '평가손익금액', 'evlu_pfls_rt': '평가손익율',
    'evlu_erng_rt': '평가수익율', 'loan_dt': '대출일자', 'loan_amt': '대출금액',
    'stln_slng_chgs': '대주매각대금', 'expd_dt': '만기일자', 'fltt_rt': '등락율',
    'bfdy_cprs_icdc': '전일대비증감', 'item_mgna_rt_name': '종목증거금율명',
    'grta_rt_name': '보증금율명', 'sbst_pric': '대용가격', 'stck_loan_unpr': '주식대출단가',
    'dnca_tot_amt': '예수금총금액', 'nxdy_excc_amt': '익일정산금액',
    'prvs_rcdl_excc_amt': '가수도정산금액', 'cma_evlu_amt': 'CMA평가금액',
    'bfdy_buy_amt': '전일매수금액', 'thdt_buy_amt': '금일매수금액',
    'nxdy_auto_rdpt_amt': '익일자동상환금액', 'bfdy_sll_amt': '전일매도금액',
    'thdt_sll_amt': '금일매도금액', 'd2_auto_rdpt_amt': 'D+2자동상환금액',
    'bfdy_tlex_amt': '전일제비용금액', 'thdt_tlex_amt': '금일제비용금액',
    'tot_loan_amt': '총대출금액', 'scts_evlu_amt': '유가평가금액',
    'tot_evlu_amt': '총평가금액', 'nass_amt': '순자산금액',
    'fncg_gld_auto_rdpt_yn': '융자금자동상환여부', 'pchs_amt_smtl_amt': '매입금액합계금액',
    'evlu_amt_smtl_amt': '평가금액합계금액', 'evlu_pfls_smtl_amt': '평가손익합계금액',
    'tot_stln_slng_chgs': '총대주매각대금', 'bfdy_tot_asst_evlu_amt': '전일총자산평가금액',
    'asst_icdc_amt': '자산증감액', 'asst_icdc_erng_rt': '자산증감수익율'
}

SEARCH_STOCK_INFO_MAPPING = {
    'pdno': '상품번호', 'prdt_type_cd': '상품유형코드', 'prdt_name': '상품명',
    'prdt_name120': '상품명(120자)', 'prdt_abrv_name': '상품약어명', 'prdt_eng_name': '상품영문명',
    'prdt_eng_name120': '상품영문명(120자)', 'prdt_eng_abrv_name': '상품영문약어명',
    'mket_id_cd': '시장ID코드', 'scty_grp_id_cd': '증권그룹ID코드', 'excg_dvsn_cd': '거래소구분코드',
    'setl_mmdd': '결산월일', 'lstg_stqt': '상장주수', 'lstg_cptl_amt': '상장자본금액',
    'cpta': '자본금', 'papr': '액면가', 'issu_pric': '발행가격', 'kospi200_item_yn': '코스피200종목여부',
    'scts_mket_lstg_dt': '유가증권시장상장일자', 'scts_mket_lstg_abol_dt': '유가증권시장상장폐지일자',
    'kosdaq_mket_lstg_dt': '코스닥시장상장일자', 'kosdaq_mket_lstg_abol_dt': '코스닥시장상장폐지일자',
    'frbd_mket_lstg_dt': '프리보드시장상장일자', 'frbd_mket_lstg_abol_dt': '프리보드시장상장폐지일자',
    'reits_kind_cd': '리츠종류코드', 'etf_dvsn_cd': 'ETF구분코드', 'oilf_fund_yn': '유전펀드여부',
    'idx_bztp_lcls_cd': '지수업종대분류코드', 'idx_bztp_mcls_cd': '지수업종중분류코드',
    'idx_bztp_scls_cd': '지수업종소분류코드', 'idx_bztp_lcls_cd_name': '지수업종대분류코드명',
    'idx_bztp_mcls_cd_name': '지수업종중분류코드명', 'idx_bztp_scls_cd_name': '지수업종소분류코드명',
    'stck_kind_cd': '주식종류코드', 'mfnd_opng_dt': '뮤추얼펀드개시일자', 'mfnd_end_dt': '뮤추얼펀드종료일자',
    'dpsi_erlm_cncl_dt': '예탁등록취소일자', 'etf_cu_qty': 'ETFCU수량', 'std_pdno': '표준상품번호',
    'dpsi_aptm_erlm_yn': '예탁지정등록여부', 'etf_txtn_type_cd': 'ETF과세유형코드',
    'etf_type_cd': 'ETF유형코드', 'lstg_abol_dt': '상장폐지일자', 'nwst_odst_dvsn_cd': '신주구주구분코드',
    'sbst_pric': '대용가격', 'thco_sbst_pric': '당사대용가격', 'thco_sbst_pric_chng_dt': '당사대용가격변경일자',
    'tr_stop_yn': '거래정지여부', 'admn_item_yn': '관리종목여부', 'thdt_clpr': '당일종가',
    'bfdy_clpr': '전일종가', 'clpr_chng_dt': '종가변경일자', 'std_idst_clsf_cd': '표준산업분류코드',
    'std_idst_clsf_cd_name': '표준산업분류코드명', 'ocr_no': 'OCR번호', 'crfd_item_yn': '크라우드펀딩종목여부',
    'elec_scty_yn': '전자증권여부', 'issu_istt_cd': '발행기관코드', 'etf_chas_erng_rt_dbnb': 'ETF추적수익율배수',
    'etf_etn_ivst_heed_item_yn': 'ETFETN투자유의종목여부', 'stln_int_rt_dvsn_cd': '대주이자율구분코드',
    'frnr_psnl_lmt_rt': '외국인개인한도비율', 'lstg_rqsr_issu_istt_cd': '상장신청인발행기관코드',
    'lstg_rqsr_item_cd': '상장신청인종목코드', 'trst_istt_issu_istt_cd': '신탁기관발행기관코드',
    'cptt_trad_tr_psbl_yn': 'NXT 거래종목여부', 'nxt_tr_stop_yn': 'NXT 거래정지여부'
}

# Combine all mappings for easier lookup
ALL_COLUMN_MAPPINGS = {**PRICE_COLUMN_MAPPING, **BALANCE_COLUMN_MAPPING, **SEARCH_STOCK_INFO_MAPPING}
REVERSE_COLUMN_MAPPING = {v: k for k, v in ALL_COLUMN_MAPPINGS.items()}