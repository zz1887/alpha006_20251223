# Alpha191因子库参考文档

## 📋 概述

Alpha191因子库包含191个Alpha因子，源自聚宽(JQData)平台。本文档提取每个因子的Inputs、Outputs和公式，用于参考和实现。

---

## 因子列表 (001-191)

### Alpha_001
**公式**: `(-1 * CORR(RANK(DELTA(LOG(VOLUME),1)),RANK(((CLOSE-OPEN)/OPEN)),6)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_002
**公式**: `-1 * delta((((close-low)-(high-close))/((high-low)),1))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_003
**公式**: `SUM((CLOSE=DELAY(CLOSE,1)?0:CLOSE-(CLOSE>DELAY(CLOSE,1)?MIN(LOW,DELAY(CLOSE,1)):MAX(HIGH,DELAY(CLOSE,1)))),6)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_004
**公式**: `((((SUM(CLOSE,8)/8)+STD(CLOSE,8))<(SUM(CLOSE,2)/2))?(-1*1):(((SUM(CLOSE,2)/2)<((SUM(CLOSE,8)/8)-STD(CLOSE,8)))?1:(((1<(VOLUME/MEAN(VOLUME,20)))||((VOLUME/MEAN(VOLUME,20))==1))?1:(-1*1))))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_005
**公式**: `(-1*TSMAX(CORR(TSRANK(VOLUME,5),YSRANK(HIGH,5),5),3))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_006
**公式**: `(RANK(SIGN(DELTA((((OPEN*0.85)+(HIGH*0.15))),4)))*-1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_007
**公式**: `((RANK(MAX((VWAP-CLOSE),3))+RANK(MIN((VWAP-CLOSE),3)))*RANK(DELTA(VOLUME,3)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_008
**公式**: `RANK(DELTA(((((HIGH+LOW)/2)*0.2)+(VWAP*0.8)),4)*-1`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_009
**公式**: `SMA(((HIGH+LOW)/2-(DELAY(HIGH,1)+DELAY(LOW,1))/*(HIGH-LOW)/VOLUME,7，2)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_010
**公式**: `(RANK(MAX(((RET<0)?STD(RET,20):CLOSE)^2),5))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_011
**公式**: `SUM(((CLOSE-LOW)-(HIGH-CLOSE))./(HIGH-LOW).*VOLUME,6)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_012
**公式**: `(RANK((OPEN-(SUM(VWAP,10)/10))))*(-1*(RANK(ABS((CLOSE-VWAP)))))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_013
**公式**: `(((HIGH*LOW)^0.5)-VWAP)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_014
**公式**: `CLOSE-DELAY(CLOSE,5)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_015
**公式**: `OPEN/DELAY(CLOSE,1)-1`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_016
**公式**: `(-1*TSMAX(RANK(CORR(RANK(VOLUME),RANK(VWAP),5)),5))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_017
**公式**: `RANK((VWAP-MAX(VWAP,15)))^DELTA(CLOSE,5)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_018
**公式**: `CLOSE/DELAY(CLOSE,5)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_019
**公式**: `(CLOSE<DELAY(CLOSE,5)?(CLOSE-DELAY(CLOSE,5))/DELAY(CLOSE,5):(CLOSE=DELAY(CLOSE,5)?0:(CLOSE-DELAY(CLOSE,5))/CLOSE))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_020
**公式**: `(CLOSE-DELAY(CLOSE,6))/DELAY(CLOSE,6)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_021
**公式**: `REGBETA(MEAN(CLOSE,6),SEQUENCE(6))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_022
**公式**: `SMEAN(((CLOSE-MEAN(CLOSE,6))/MEAN(CLOSE,6)-DELAY((CLOSE-MEAN(CLOSE,6))/MEAN(CLOSE,6),3)),12,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_023
**公式**: `SMA((CLOSE>DELAY(CLOSE,1)?STD(CLOSE:20),0),20,1)/(SMA((CLOSE>DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1)+SMA((CLOSE<=DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1))*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_024
**公式**: `SMA(CLOSE-DELAY(CLOSE,5),5,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_025
**公式**: `((-1  *  RANK((DELTA(CLOSE,  7)  *  (1  -  RANK(DECAYLINEAR((VOLUME  /  MEAN(VOLUME,20)),  9))))))  *  (1  + RANK(SUM(RET, 250))))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_026
**公式**: `((((SUM(CLOSE, 7) / 7) - CLOSE)) + ((CORR(VWAP, DELAY(CLOSE, 5), 230))))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_027
**公式**: `WMA((CLOSE-DELAY(CLOSE,3))/DELAY(CLOSE,3)*100+(CLOSE-DELAY(CLOSE,6))/DELAY(CLOSE,6)*100,12)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_028
**公式**: `3*SMA((CLOSE-TSMIN(LOW,9))/(TSMAX(HIGH,9)-TSMIN(LOW,9))*100,3,1)-2*SMA(SMA((CLOSE-TSMIN(LOW,9))/( MAX(HIGH,9)-TSMAX(LOW,9))*100,3,1),3,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_029
**公式**: `(CLOSE-DELAY(CLOSE,6))/DELAY(CLOSE,6)*VOLUME`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_030
**公式**: `WMA((REGRESI(CLOSE/DELAY(CLOSE)-1,MKT,SMB,HML，60))^2,20)`
**Inputs**: code, end_date
**Outputs**: 因子的值
**备注**: 未实现

### Alpha_031
**公式**: `LOSE-MEAN(CLOSE,12))/MEAN(CLOSE,12)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_032
**公式**: `(-1 * SUM(RANK(CORR(RANK(HIGH), RANK(VOLUME), 3)), 3))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_033
**公式**: `(((-1  *  TSMIN(LOW,  5))  +  DELAY(TSMIN(LOW,  5),  5))  *  RANK(((SUM(RET,  240)  -  SUM(RET,  20))  /  220)))    * TSRANK(VOLUME, 5)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_034
**公式**: `MEAN(CLOSE,12)/CLOSE`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_035
**公式**: `(MIN(RANK(DECAYLINEAR(DELTA(OPEN,  1),  15)),  RANK(DECAYLINEAR(CORR((VOLUME),  ((OPEN  *  0.65)  + (OPEN *0.35)), 17),7))) * -1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_036
**公式**: `RANK(SUM(CORR(RANK(VOLUME), RANK(VWAP)), 6), 2)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_037
**公式**: `(-1 * RANK(((SUM(OPEN, 5) * SUM(RET, 5)) - DELAY((SUM(OPEN, 5) * SUM(RET, 5)), 10))))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_038
**公式**: `(((SUM(HIGH, 20) / 20) < HIGH) ? (-1 * DELTA(HIGH, 2)) : 0)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_039
**公式**: `((RANK(DECAYLINEAR(DELTA((CLOSE), 2),8)) - RANK(DECAYLINEAR(CORR(((VWAP * 0.3) + (OPEN * 0.7)), SUM(MEAN(VOLUME,180), 37), 14), 12))) * -1`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_040
**公式**: `SUM((CLOSE>DELAY(CLOSE,1)?VOLUME:0),26)/SUM((CLOSE<=DELAY(CLOSE,1)?VOLUME:0),26)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_041
**公式**: `(RANK(MAX(DELTA((VWAP), 3), 5))* -1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_042
**公式**: `(-1 * RANK(STD(HIGH, 10))) * CORR(HIGH, VOLUME, 10))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_043
**公式**: `SUM((CLOSE>DELAY(CLOSE,1)?VOLUME:(CLOSE<DELAY(CLOSE,1)?-VOLUME:0)),6)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_044
**公式**: `(TSRANK(DECAYLINEAR(CORR(((LOW )), MEAN(VOLUME,10), 7), 6),4) + TSRANK(DECAYLINEAR(DELTA((VWAP), 3), 10), 15))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_045
**公式**: `(RANK(DELTA((((CLOSE * 0.6) + (OPEN *0.4))), 1)) * RANK(CORR(VWAP, MEAN(VOLUME,150), 15)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_046
**公式**: `(MEAN(CLOSE,3)+MEAN(CLOSE,6)+MEAN(CLOSE,12)+MEAN(CLOSE,24))/(4*CLOSE)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_047
**公式**: `SMA((TSMAX(HIGH,6)-CLOSE)/(TSMAX(HIGH,6)-TSMIN(LOW,6))*100,9,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_048
**公式**: `(-1*((RANK(((SIGN((CLOSE-DELAY(CLOSE,1)))+SIGN((DELAY(CLOSE,1) - DELAY(CLOSE,2))))+SIGN((DELAY(CLOSE,2)-DELAY(CLOSE,3))))))*SUM(VOLUME,5))/SUM(VOLUME,20))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_049
**公式**: `SUM(((HIGH+LOW)>=(DELAY(HIGH,1)+DELAY(LOW,1))?0:MAX(ABS(HIGH-DELAY(HIGH,1)),ABS(LOW-DELAY(L OW,1)))),12)/(SUM(((HIGH+LOW)>=(DELAY(HIGH,1)+DELAY(LOW,1))?0:MAX(ABS(HIGH-DELAY(HIGH,1)),ABS(L OW-DELAY(LOW,1)))),12)+SUM(((HIGH+LOW)<=(DELAY(HIGH,1)+DELAY(LOW,1))?0:MAX(ABS(HIGH-DELAY(HI GH,1)),ABS(LOW-DELAY(LOW,1)))),12))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_050
**公式**: `SUM(((HIGH+LOW)<=(DELAY(HIGH,1)+DELAY(LOW,1))?0:MAX(ABS(HIGH-DELAY(HIGH,1)),ABS(LOW-DELAY(L OW,1)))),12)/(SUM(((HIGH+LOW)<=(DELAY(HIGH,1)+DELAY(LOW,1))?0:MAX(ABS(HIGH-DELAY(HIGH,1)),ABS(L OW-DELAY(LOW,1)))),12)+SUM(((HIGH+LOW)>=(DELAY(HIGH,1)+DELAY(LOW,1))?0:MAX(ABS(HIGH-DELAY(HI GH,1)),ABS(LOW-DELAY(LOW,1)))),12))-SUM(((HIGH+LOW)>=(DELAY(HIGH,1)+DELAY(LOW,1))?0:MAX(ABS(HIGH-DELAY(HIGH,1)),ABS(LOW-DELAY(LOW,1)))),12)/(SUM(((HIGH+LOW)>=(DELAY(HIGH,1)+DELAY(LOW,1))?0: MAX(ABS(HIGH-DELAY(HIGH,1)),ABS(LOW-DELAY(LOW,1)))),12)+SUM(((HIGH+LOW)<=(DELAY(HIGH,1)+DELA Y(LOW,1))?0:MAX(ABS(HIGH-DELAY(HIGH,1)),ABS(LOW-DELAY(LOW,1)))),12))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_051
**公式**: `SUM(((HIGH+LOW)<=(DELAY(HIGH,1)+DELAY(LOW,1))?0:MAX(ABS(HIGH-DELAY(HIGH,1)),ABS(LOW-DELAY(L OW,1)))),12)/(SUM(((HIGH+LOW)<=(DELAY(HIGH,1)+DELAY(LOW,1))?0:MAX(ABS(HIGH-DELAY(HIGH,1)),ABS(L OW-DELAY(LOW,1)))),12)+SUM(((HIGH+LOW)>=(DELAY(HIGH,1)+DELAY(LOW,1))?0:MAX(ABS(HIGH-DELAY(HI GH,1)),ABS(LOW-DELAY(LOW,1)))),12))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_052
**公式**: `SUM(MAX(0,HIGH-DELAY((HIGH+LOW+CLOSE)/3,1)),26)/SUM(MAX(0,DELAY((HIGH+LOW+CLOSE)/3,1)-L),26)* 100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_053
**公式**: `COUNT(CLOSE>DELAY(CLOSE,1),12)/12*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_054
**公式**: `(-1 * RANK((STD(ABS(CLOSE - OPEN)) + (CLOSE - OPEN)) + CORR(CLOSE, OPEN,10)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_055
**公式**: `SUM(16*(CLOSE-DELAY(CLOSE,1)+(CLOSE-OPEN)/2+DELAY(CLOSE,1)-DELAY(OPEN,1))/((ABS(HIGH-DELAY(CL OSE,1))>ABS(LOW-DELAY(CLOSE,1))&ABS(HIGH-DELAY(CLOSE,1))>ABS(HIGH-DELAY(LOW,1))?ABS(HIGH-DELAY(CLOSE,1))+ABS(LOW-DELAY(CLOS E,1))/2+ABS(DELAY(CLOSE,1)-DELAY(OPEN,1))/4:(ABS(LOW-DELAY(CLOSE,1))>ABS(HIGH-DELAY(LOW,1))   & ABS(LOW-DELAY(CLOSE,1))>ABS(HIGH-DELAY(CLOSE,1))?ABS(LOW-DELAY(CLOSE,1))+ABS(HIGH-DELAY(CLO SE,1))/2+ABS(DELAY(CLOSE,1)-DELAY(OPEN,1))/4:ABS(HIGH-DELAY(LOW,1))+ABS(DELAY(CLOSE,1)-DELAY(OP EN,1))/4)))*MAX(ABS(HIGH-DELAY(CLOSE,1)),ABS(LOW-DELAY(CLOSE,1))),20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_056
**公式**: `(RANK((OPEN-TSMIN(OPEN,12)))<RANK((RANK(CORR(SUM(((HIGH+LOW)/2),19),SUM(MEAN(VOLUME,40),19),13))^5)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_057
**公式**: `SMA((CLOSE-TSMIN(LOW,9))/(TSMAX(HIGH,9)-TSMIN(LOW,9))*100,3,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_058
**公式**: `COUNT(CLOSE>DELAY(CLOSE,1),20)/20*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_059
**公式**: `SUM((CLOSE=DELAY(CLOSE,1)?0:CLOSE-(CLOSE>DELAY(CLOSE,1)?MIN(LOW,DELAY(CLOSE,1)):MAX(HIGH,D ELAY(CLOSE,1)))),20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_060
**公式**: `SUM(((CLOSE-LOW)-(HIGH-CLOSE))./(HIGH-LOW).*VOLUME,20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_061
**公式**: `(MAX(RANK(DECAYLINEAR(DELTA(VWAP,   1), 12)),RANK(DECAYLINEAR(RANK(CORR((LOW),MEAN(VOLUME,80), 8)), 17))) * -1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_062
**公式**: `(-1 * CORR(HIGH, RANK(VOLUME), 5))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_063
**公式**: `SMA(MAX(CLOSE-DELAY(CLOSE,1),0),6,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),6,1)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_064
**公式**: `(MAX(RANK(DECAYLINEAR(CORR(RANK(VWAP),  RANK(VOLUME),   4), 4)),RANK(DECAYLINEAR(MAX(CORR(RANK(CLOSE), RANK(MEAN(VOLUME,60)), 4), 13), 14))) * -1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_065
**公式**: `MEAN(CLOSE,6)/CLOSE`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_066
**公式**: `(CLOSE-MEAN(CLOSE,6))/MEAN(CLOSE,6)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_067
**公式**: `SMA(MAX(CLOSE-DELAY(CLOSE,1),0),24,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),24,1)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_068
**公式**: `SMA(((HIGH+LOW)/2-(DELAY(HIGH,1)+DELAY(LOW,1))/2)*(HIGH-LOW)/VOLUME,15,2)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_069
**公式**: `(SUM(DTM,20)>SUM(DBM,20)？(SUM(DTM,20)-SUM(DBM,20))/SUM(DTM,20)：(SUM(DTM,20)=SUM(DBM,20)？0：(SUM(DTM,20)-SUM(DBM,20))/SUM(DBM,20)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_070
**公式**: `STD(AMOUNT,6)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_071
**公式**: `(CLOSE-MEAN(CLOSE,24))/MEAN(CLOSE,24)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_072
**公式**: `SMA((TSMAX(HIGH,6)-CLOSE)/(TSMAX(HIGH,6)-TSMIN(LOW,6))*100,15,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_073
**公式**: `((TSRANK(DECAYLINEAR(DECAYLINEAR(CORR((CLOSE),  VOLUME, 10),    16),    4), 5)  -RANK(DECAYLINEAR(CORR(VWAP, MEAN(VOLUME,30), 4),3))) * -1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_074
**公式**: `(RANK(CORR(SUM(((LOW *   0.35)   +   (VWAP   *   0.65)), 20),    SUM(MEAN(VOLUME,40),    20),    7)) +RANK(CORR(RANK(VWAP), RANK(VOLUME), 6)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_075
**公式**: `BANCHMARKINDEXCLOSE<BANCHMARKINDEXOPEN,50)/COUNT(BANCHMARKINDEXCLOSE<BANCHMARKIN DEXOPEN,50)`
**Inputs**: code, benchmark, end_date
**Outputs**: 因子的值

### Alpha_076
**公式**: `STD(ABS((CLOSE/DELAY(CLOSE,1)-1))/VOLUME,20)/MEAN(ABS((CLOSE/DELAY(CLOSE,1)-1))/VOLUME,20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_077
**公式**: `MIN(RANK(DECAYLINEAR(((((HIGH + LOW) / 2) + HIGH)  -  (VWAP + HIGH)), 20)), RANK(DECAYLINEAR(CORR(((HIGH + LOW) / 2), MEAN(VOLUME,40), 3), 6)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_078
**公式**: `((HIGH+LOW+CLOSE)/3-MA((HIGH+LOW+CLOSE)/3,12))/(0.015*MEAN(ABS(CLOSE-MEAN((HIGH+LOW+CLOSE)/3,12)),12))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_079
**公式**: `SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_080
**公式**: `(VOLUME-DELAY(VOLUME,5))/DELAY(VOLUME,5)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_081
**公式**: `SMA(VOLUME,21,2)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_082
**公式**: `SMA((TSMAX(HIGH,6)-CLOSE)/(TSMAX(HIGH,6)-TSMIN(LOW,6))*100,20,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_083
**公式**: `(-1 * RANK(COVIANCE(RANK(HIGH), RANK(VOLUME), 5)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_084
**公式**: `SUM((CLOSE>DELAY(CLOSE,1)?VOLUME:(CLOSE<DELAY(CLOSE,1)?-VOLUME:0)),20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_085
**公式**: `(TSRANK((VOLUME / MEAN(VOLUME,20)), 20) * TSRANK((-1 * DELTA(CLOSE, 7)), 8))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_086
**公式**: `((0.25 < (((DELAY(CLOSE, 20) - DELAY(CLOSE, 10)) / 10) - ((DELAY(CLOSE, 10) - CLOSE) / 10))) ? (-1 * 1) :(((((DELAY(CLOSE, 20) - DELAY(CLOSE, 10)) / 10) - ((DELAY(CLOSE, 10) - CLOSE) / 10)) < 0) ? 1 : ((-1 * 1) * (CLOSE - DELAY(CLOSE, 1)))))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_087
**公式**: `((RANK(DECAYLINEAR(DELTA(VWAP, 4), 7)) + TSRANK(DECAYLINEAR(((((LOW * 0.9) + (LOW * 0.1)) - VWAP) / (OPEN - ((HIGH + LOW) / 2))), 11), 7)) * -1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_088
**公式**: `(CLOSE-DELAY(CLOSE,20))/DELAY(CLOSE,20)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_089
**公式**: `2*(SMA(CLOSE,13,2)-SMA(CLOSE,27,2)-SMA(SMA(CLOSE,13,2)-SMA(CLOSE,27,2),10,2))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_090
**公式**: `( RANK(CORR(RANK(VWAP), RANK(VOLUME), 5)) * -1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_091
**公式**: `((RANK((CLOSE - MAX(CLOSE, 5)))*RANK(CORR((MEAN(VOLUME,40)), LOW, 5))) * -1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_092
**公式**: `(MAX(RANK(DECAYLINEAR(DELTA(((CLOSE  *   0.35)   +   (VWAP   *0.65)),    2), 3)),TSRANK(DECAYLINEAR(ABS(CORR((MEAN(VOLUME,180)), CLOSE, 13)), 5), 15)) * -1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_093
**公式**: `SUM((OPEN>=DELAY(OPEN,1)?0:MAX((OPEN-LOW),(OPEN-DELAY(OPEN,1)))),20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_094
**公式**: `SUM((CLOSE>DELAY(CLOSE,1)?VOLUME:(CLOSE<DELAY(CLOSE,1)?-VOLUME:0)),30)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_095
**公式**: `STD(AMOUNT,20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_096
**公式**: `SMA(SMA((CLOSE-TSMIN(LOW,9))/(TSMAX(HIGH,9)-TSMIN(LOW,9))*100,3,1),3,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_097
**公式**: `STD(VOLUME,10)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_098
**公式**: `(((((DELTA((SUM(CLOSE, 100) / 100), 100) / DELAY(CLOSE, 100)) < 0.05) || ((DELTA((SUM(CLOSE, 100) / 100), 100) /DELAY(CLOSE, 100)) == 0.05)) ? (-1 * (CLOSE - TSMIN(CLOSE, 100))) : (-1 * DELTA(CLOSE, 3)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_099
**公式**: `(-1 * RANK(COVIANCE(RANK(CLOSE), RANK(VOLUME), 5)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_100
**公式**: `STD(VOLUME,20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_101
**公式**: `((RANK(CORR(CLOSE, SUM(MEAN(VOLUME,30), 37), 15)) < RANK(CORR(RANK(((HIGH * 0.1) + (VWAP * 0.9))),RANK(VOLUME), 11))) * -1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_102
**公式**: `SMA(MAX(VOLUME-DELAY(VOLUME,1),0),6,1)/SMA(ABS(VOLUME-DELAY(VOLUME,1)),6,1)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_103
**公式**: `((20-LOWDAY(LOW,20))/20)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_104
**公式**: `(-1 * (DELTA(CORR(HIGH, VOLUME, 5), 5) * RANK(STD(CLOSE, 20))))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_105
**公式**: `(-1 * CORR(RANK(OPEN), RANK(VOLUME), 10))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_106
**公式**: `CLOSE-DELAY(CLOSE,20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_107
**公式**: `(((-1 * RANK((OPEN - DELAY(HIGH, 1)))) * RANK((OPEN - DELAY(CLOSE, 1)))) * RANK((OPEN - DELAY(LOW, 1))))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_108
**公式**: `((RANK((HIGH - MIN(HIGH, 2)))^RANK(CORR((VWAP), (MEAN(VOLUME,120)), 6))) * -1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_109
**公式**: `SMA(HIGH-LOW,10,2)/SMA(SMA(HIGH-LOW,10,2),10,2)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_110
**公式**: `SUM(MAX(0,HIGH-DELAY(CLOSE,1)),20)/SUM(MAX(0,DELAY(CLOSE,1)-LOW),20)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_111
**公式**: `SMA(VOL*((CLOSE-LOW)-(HIGH-CLOSE))/(HIGH-LOW),11,2)-SMA(VOL*((CLOSE-LOW)-(HIGH-CLOSE))/(HIGH-L OW),4,2)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_112
**公式**: `(SUM((CLOSE-DELAY(CLOSE,1)>0?CLOSE-DELAY(CLOSE,1):0),12)-SUM((CLOSE-DELAY(CLOSE,1)<0?ABS(CLOS E-DELAY(CLOSE,1)):0),12))/(SUM((CLOSE-DELAY(CLOSE,1)>0?CLOSE-DELAY(CLOSE,1):0),12)+SUM((CLOSE-DE LAY(CLOSE,1)<0?ABS(CLOSE-DELAY(CLOSE,1)):0),12))*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_113
**公式**: `(-1 * ((RANK((SUM(DELAY(CLOSE, 5), 20) / 20)) * CORR(CLOSE, VOLUME, 2)) * RANK(CORR(SUM(CLOSE, 5),SUM(CLOSE, 20), 2))))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_114
**公式**: `((RANK(DELAY(((HIGH - LOW) / (SUM(CLOSE, 5) / 5)), 2)) * RANK(RANK(VOLUME))) / (((HIGH - LOW) / (SUM(CLOSE, 5) / 5)) / (VWAP - CLOSE)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_115
**公式**: `(RANK(CORR(((HIGH * 0.9) + (CLOSE * 0.1)), MEAN(VOLUME,30), 10))^RANK(CORR(TSRANK(((HIGH + LOW) /  2), 4), TSRANK(VOLUME, 10), 7)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_116
**公式**: `REGBETA(CLOSE,SEQUENCE,20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_117
**公式**: `((TSRANK(VOLUME,32)*(1-TSRANK(((CLOSE+HIGH)-LOW),16)))*(1-TSRANK(RET,32)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_118
**公式**: `SUM(HIGH-OPEN,20)/SUM(OPEN-LOW,20)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_119
**公式**: `(RANK(DECAYLINEAR(CORR(VWAP,SUM(MEAN(VOLUME,5),26),5),7))-RANK(DECAYLINEAR(TSRANK(MIN(CORR(RANK(OPEN),RANK(MEAN(VOLUME,15)),21),9),7),8)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_120
**公式**: `(RANK((VWAP-CLOSE))/RANK((VWAP+CLOSE)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_121
**公式**: `((RANK((VWAP-MIN(VWAP,12)))^TSRANK(CORR(TSRANK(VWAP,20),TSRANK(MEAN(VOLUME,60),2),18),3))*-1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_122
**公式**: `(SMA(SMA(SMA(LOG(CLOSE),13,2),13,2),13,2)-DELAY(SMA(SMA(SMA(LOG(CLOSE),13,2),13,2),13,2),1))/DELAY(SM A(SMA(SMA(LOG(CLOSE),13,2),13,2),13,2),1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_123
**公式**: `((RANK(CORR(SUM(((HIGH+LOW)/2),20),SUM(MEAN(VOLUME,60),20),9))<RANK(CORR(LOW,VOLUME,6)))*-1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_124
**公式**: `(CLOSE-VWAP)/DECAYLINEAR(RANK(TSMAX(CLOSE,30)),2)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_125
**公式**: `(RANK(DECAYLINEAR(CORR((VWAP),MEAN(VOLUME,80),17),20))/RANK(DECAYLINEAR(DELTA(((CLOSE*0.5)+ (VWAP*0.5)),3),16)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_126
**公式**: `(CLOSE+HIGH+LOW)/3`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_127
**公式**: `(MEAN((100*(CLOSE-MAX(CLOSE,12))/(MAX(CLOSE,12)))^2))^(1/2)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_128
**公式**: `100-(100/(1+SUM(((HIGH+LOW+CLOSE)/3>DELAY((HIGH+LOW+CLOSE)/3,1)?(HIGH+LOW+CLOSE)/3*VOLUM E:0),14)/SUM(((HIGH+LOW+CLOSE)/3<DELAY((HIGH+LOW+CLOSE)/3,1)?(HIGH+LOW+CLOSE)/3*VOLUME:0), 14)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_129
**公式**: `SUM((CLOSE-DELAY(CLOSE,1)<0?ABS(CLOSE-DELAY(CLOSE,1)):0),12)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_130
**公式**: `(RANK(DECAYLINEAR(CORR(((HIGH+LOW)/2), MEAN(VOLUME,40),9),10))/RANK(DECAYLINEAR(CORR(RANK(VWAP),RANK(VOLUME),7),3)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_131
**公式**: `(RANK(DELAT(VWAP, 1))^TSRANK(CORR(CLOSE,MEAN(VOLUME,50), 18), 18))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_132
**公式**: `MEAN(AMOUNT,20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_133
**公式**: `((20-HIGHDAY(HIGH,20))/20)*100-((20-LOWDAY(LOW,20))/20)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_134
**公式**: `(CLOSE-DELAY(CLOSE,12))/DELAY(CLOSE,12)*VOLUME`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_135
**公式**: `SMA(DELAY(CLOSE/DELAY(CLOSE,20),1),20,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_136
**公式**: `((-1*RANK(DELTA(RET,3)))*CORR(OPEN,VOLUME,10))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_137
**公式**: `16*(CLOSE-DELAY(CLOSE,1)+(CLOSE-OPEN)/2+DELAY(CLOSE,1)-DELAY(OPEN,1))/((ABS(HIGH-DELAY(CLOSE,1))>ABS(LOW-DELAY(CLOSE,1)) &ABS(HIGH-DELAY(CLOSE,1))>ABS(HIGH-DELAY(LOW,1))?ABS(HIGH-DELAY(CLOSE,1))+ABS(LOW-DELAY(CLOS E,1))/2+ABS(DELAY(CLOSE,1)-DELAY(OPEN,1))/4:(ABS(LOW-DELAY(CLOSE,1))>ABS(HIGH-DELAY(LOW,1))&ABS(LOW-DELAY(CLOSE,1))>ABS(HIGH-DELAY(CLOSE,1))?ABS(LOW-DELAY(CLOSE,1))+ABS(HIGH-DELAY(CLO SE,1))/2+ABS(DELAY(CLOSE,1)-DELAY(OPEN,1))/4:ABS(HIGH-DELAY(LOW,1))+ABS(DELAY(CLOSE,1)-DELAY(OP EN,1))/4)))*MAX(ABS(HIGH-DELAY(CLOSE,1)),ABS(LOW-DELAY(CLOSE,1)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_138
**公式**: `((RANK(DECAYLINEAR(DELTA((((LOW*0.7)+(VWAP*0.3))),3),20))-TSRANK(DECAYLINEAR(TSRANK(CORR(TSRANK(LOW,8),TSRANK(MEAN(VOLUME,60),17),5),19),16),7))*-1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_139
**公式**: `(-1 * CORR(OPEN, VOLUME, 10))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_140
**公式**: `MIN(RANK(DECAYLINEAR(((RANK(OPEN)+RANK(LOW))-(RANK(HIGH)+RANK(CLOSE))),8)),TSRANK(DECAYLINEAR(CORR(TSRANK(CLOSE,8),TSRANK(MEAN(VOLUME,60), 20), 8), 7), 3))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_141
**公式**: `(RANK(CORR(RANK(HIGH),RANK(MEAN(VOLUME,15)),9))*-1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_142
**公式**: `((-1*RANK(TSRANK(CLOSE,10)))*RANK(DELTA(DELTA(CLOSE,1),1)))*RANK(TSRANK((VOLUME/MEAN(VOLUME,20)), 5)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_143
**公式**: `CLOSE>DELAY(CLOSE,1)?(CLOSE-DELAY(CLOSE,1))/DELAY(CLOSE,1)*SELF:SELF`
**Inputs**: code, end_date
**Outputs**: 因子的值
**备注**: 未实现

### Alpha_144
**公式**: `SUMIF(ABS(CLOSE/DELAY(CLOSE,1)-1)/AMOUNT,20,CLOSE<DELAY(CLOSE,1))/COUNT(CLOSE<DELAY(CLOSE, 1),20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_145
**公式**: `(MEAN(VOLUME,9)-MEAN(VOLUME,26))/MEAN(VOLUME,12)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_146
**公式**: `MEAN((CLOSE-DELAY(CLOSE,1))/DELAY(CLOSE,1)-SMA((CLOSE-DELAY(CLOSE,1))/DELAY(CLOSE,1),61,2),20)*(( CLOSE-DELAY(CLOSE,1))/DELAY(CLOSE,1)-SMA((CLOSE-DELAY(CLOSE,1))/DELAY(CLOSE,1),61,2))/SMA(((CLOS E-DELAY(CLOSE,1))/DELAY(CLOSE,1)-((CLOSE-DELAY(CLOSE,1))/DELAY(CLOSE,1)-SMA((CLOSE-DELAY(CLOSE, 1))/DELAY(CLOSE,1),61,2)))^2,60);`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_147
**公式**: `REGBETA(MEAN(CLOSE,12),SEQUENCE(12))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_148
**公式**: `((RANK(CORR((OPEN),SUM(MEAN(VOLUME,60),9),6))<RANK((OPEN-TSMIN(OPEN,14))))*-1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_149
**公式**: `REGBETA(FILTER(CLOSE/DELAY(CLOSE,1)-1,BANCHMARKINDEXCLOSE<DELAY(BANCHMARKINDEXCLOSE,1)),FILTER(BANCHMARKINDEXCLOSE/DELAY(BANCHMARKINDEXCLOSE,1)-1,BANCHMARKINDEXCLOSE<DELAY(BANCHMARKINDEXCLOSE,1)),252)`
**Inputs**: code, benchmark, end_date
**Outputs**: 因子的值

### Alpha_150
**公式**: `(CLOSE+HIGH+LOW)/3*VOLUME`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_151
**公式**: `SMA(CLOSE-DELAY(CLOSE,20),20,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_152
**公式**: `SMA(MEAN(DELAY(SMA(DELAY(CLOSE/DELAY(CLOSE,9),1),9,1),1),12)-MEAN(DELAY(SMA(DELAY(CLOSE/DELAY(CLOSE,9),1),9,1),1),26),9,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_153
**公式**: `(MEAN(CLOSE,3)+MEAN(CLOSE,6)+MEAN(CLOSE,12)+MEAN(CLOSE,24))/4`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_154
**公式**: `(((VWAP-MIN(VWAP,16)))<(CORR(VWAP,MEAN(VOLUME,180),18)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_155
**公式**: `SMA(VOLUME,13,2)-SMA(VOLUME,27,2)-SMA(SMA(VOLUME,13,2)-SMA(VOLUME,27,2),10,2)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_156
**公式**: `(MAX(RANK(DECAYLINEAR(DELTA(VWAP,5),3)),RANK(DECAYLINEAR(((DELTA(((OPEN*0.15)+(LOW*0.85)),2)/((OPEN*0.15)+(LOW*0.85)))*-1),3)))*-1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_157
**公式**: `(MIN(PROD(RANK(RANK(LOG(SUM(TSMIN(RANK(RANK((-1*RANK(DELTA((CLOSE-1),5))))),2),1)))),1), 5) +TSRANK(DELAY((-1*RET),6),5))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_158
**公式**: `((HIGH-SMA(CLOSE,15,2))-(LOW-SMA(CLOSE,15,2)))/CLOSE`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_159
**公式**: `((CLOSE-SUM(MIN(LOW,DELAY(CLOSE,1)),6))/SUM(MAX(HGIH,DELAY(CLOSE,1))-MIN(LOW,DELAY(CLOSE,1)),6)*12*24+(CLOSE-SUM(MIN(LOW,DELAY(CLOSE,1)),12))/SUM(MAX(HGIH,DELAY(CLOSE,1))-MIN(LOW,DELAY(CLOSE,1)),12)*6*24+(CLOSE-SUM(MIN(LOW,DELAY(CLOSE,1)),24))/SUM(MAX(HGIH,DELAY(CLOSE,1))-MIN(LOW,DELAY(CLOSE,1)),24)*6*24)*100/(6*12+6*24+12*24)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_160
**公式**: `SMA((CLOSE<=DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_161
**公式**: `MEAN(MAX(MAX((HIGH-LOW),ABS(DELAY(CLOSE,1)-HIGH)),ABS(DELAY(CLOSE,1)-LOW)),12)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_162
**公式**: `(SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100-MIN(SMA(MAX(CLOS E-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100,12))/(MAX(SMA(MAX(CLOSE-DELAY(C LOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100,12)-MIN(SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12, 1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100,12))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_163
**公式**: `RANK(((((-1 * RET) * MEAN(VOLUME,20)) * VWAP) * (HIGH - CLOSE)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_164
**公式**: `SMA((((CLOSE>DELAY(CLOSE,1))?1/(CLOSE-DELAY(CLOSE,1)):1)-MIN(((CLOSE>DELAY(CLOSE,1))?1/(CLOSE-D ELAY(CLOSE,1)):1),12))/(HIGH-LOW)*100,13,2)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_165
**公式**: `MAX(SUMAC(CLOSE-MEAN(CLOSE,48)))-MIN(SUMAC(CLOSE-MEAN(CLOSE,48)))/STD(CLOSE,48)`
**Inputs**: code, end_date
**Outputs**: 因子的值
**备注**: 未实现

### Alpha_166
**公式**: `-20*(20-1)^1.5*SUM(CLOSE/DELAY(CLOSE,1)-1-MEAN(CLOSE/DELAY(CLOSE,1)-1,20),20)/((20-1)*(20-2)(SUM((CLOSE/DELA Y(CLOSE,1),20)^2,20))^1.5)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_167
**公式**: `SUM((CLOSE-DELAY(CLOSE,1)>0?CLOSE-DELAY(CLOSE,1):0),12)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_168
**公式**: `(-1*VOLUME/MEAN(VOLUME,20))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_169
**公式**: `SMA(MEAN(DELAY(SMA(CLOSE-DELAY(CLOSE,1),9,1),1),12)-MEAN(DELAY(SMA(CLOSE-DELAY(CLOSE,1),9,1),1), 26),10,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_170
**公式**: `(((RANK((1/CLOSE))*VOLUME)/MEAN(VOLUME,20))*((HIGH*RANK((HIGH-CLOSE)))/(SUM(HIGH, 5)/5)))-RANK((VWAP-DELAY(VWAP, 5))))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_171
**公式**: `((-1 * ((LOW - CLOSE) * (OPEN^5))) / ((CLOSE - HIGH) * (CLOSE^5)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_172
**公式**: `MEAN(ABS(SUM((LD>0&LD>HD)?LD:0,14)*100/SUM(TR,14)-SUM((HD>0&HD>LD)?HD:0,14)*100/SUM(TR,14))/(SUM((LD>0 & LD>HD)?LD:0,14)*100/SUM(TR,14)+SUM((HD>0 & HD>LD)?HD:0,14)*100/SUM(TR,14))*100,6)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_173
**公式**: `3*SMA(CLOSE,13,2)-2*SMA(SMA(CLOSE,13,2),13,2)+SMA(SMA(SMA(LOG(CLOSE),13,2),13,2),13,2);`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_174
**公式**: `SMA((CLOSE>DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_175
**公式**: `MEAN(MAX(MAX((HIGH-LOW),ABS(DELAY(CLOSE,1)-HIGH)),ABS(DELAY(CLOSE,1)-LOW)),6)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_176
**公式**: `CORR(RANK(((CLOSE-TSMIN(LOW, 12))/(TSMAX(HIGH, 12)-TSMIN(LOW,12)))), RANK(VOLUME), 6)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_177
**公式**: `((20-HIGHDAY(HIGH,20))/20)*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_178
**公式**: `(CLOSE-DELAY(CLOSE,1))/DELAY(CLOSE,1)*VOLUME`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_179
**公式**: `(RANK(CORR(VWAP,VOLUME,4))*RANK(CORR(RANK(LOW), RANK(MEAN(VOLUME,50)), 12)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_180
**公式**: `((MEAN(VOLUME,20)<VOLUME)?((-1*TSRANK(ABS(DELTA(CLOSE,7)),60)) * SIGN(DELTA(CLOSE,7)):(-1*VOLUME)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_181
**公式**: `SUM(((CLOSE/DELAY(CLOSE,1)-1)-MEAN((CLOSE/DELAY(CLOSE,1)-1),20))-(BANCHMARKINDEXCLOSE-MEAN(BANCHMARKINDEXCLOSE,20))^2,20)/SUM((BANCHMARKINDEXCLOSE-MEAN(BANCHMARKINDEXCLOSE,20))^3)`
**Inputs**: code, benchmark, end_date
**Outputs**: 因子的值

### Alpha_182
**公式**: `COUNT((CLOSE>OPEN&BANCHMARKINDEXCLOSE>BANCHMARKINDEXOPEN)OR(CLOSE<OPEN&BANCHMARKINDEXCLOSE<BANCHMARKINDEXOPEN),20)/20`
**Inputs**: code, benchmark, end_date
**Outputs**: 因子的值

### Alpha_183
**公式**: `MAX(SUMAC(CLOSE-MEAN(CLOSE,24)))-MIN(SUMAC(CLOSE-MEAN(CLOSE,24)))/STD(CLOSE,24)`
**Inputs**: code, end_date
**Outputs**: 因子的值
**备注**: 未实现

### Alpha_184
**公式**: `(RANK(CORR(DELAY((OPEN - CLOSE), 1), CLOSE, 200)) + RANK((OPEN - CLOSE)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_185
**公式**: `RANK((-1 * ((1 - (OPEN / CLOSE))^2)))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_186
**公式**: `(MEAN(ABS(SUM((LD>0&LD>HD)?LD:0,14)*100/SUM(TR,14)-SUM((HD>0&HD>LD)?HD:0,14)*100/SUM(TR,14))/(SUM((LD>0 & LD>HD)?LD:0,14)*100/SUM(TR,14)+SUM((HD>0 & HD>LD)?HD:0,14)*100/SUM(TR,14))*100,6)+DELAY(MEAN(ABS(SUM((LD>0   & LD>HD)?LD:0,14)*100/SUM(TR,14)-SUM((HD>0 & HD>LD)?HD:0,14)*100/SUM(TR,14))/(SUM((LD>0 & LD>HD)?LD:0,14)*100/SUM(TR,14)+SUM((HD>0 & HD>LD)?HD:0,14)*100/SUM(TR,14))*100,6),6))/2`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_187
**公式**: `SUM((OPEN<=DELAY(OPEN,1)?0:MAX((HIGH-OPEN),(OPEN-DELAY(OPEN,1)))),20)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_188
**公式**: `((HIGH-LOW–SMA(HIGH-LOW,11,2))/SMA(HIGH-LOW,11,2))*100`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_189
**公式**: `MEAN(ABS(CLOSE-MEAN(CLOSE,6)),6)`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_190
**公式**: `LOG((COUNT(CLOSE/DELAY(CLOSE)-1>((CLOSE/DELAY(CLOSE,19))^(1/20)-1),20)-1)*(SUMIF(((CLOSE/DELAY(C LOSE)-1-(CLOSE/DELAY(CLOSE,19))^(1/20)-1))^2,20,CLOSE/DELAY(CLOSE)-1<(CLOSE/DELAY(CLOSE,19))^(1/20)- 1))/((COUNT((CLOSE/DELAY(CLOSE)-1<(CLOSE/DELAY(CLOSE,19))^(1/20)-1),20))*(SUMIF((CLOSE/DELAY(CLOS E)-1-((CLOSE/DELAY(CLOSE,19))^(1/20)-1))^2,20,CLOSE/DELAY(CLOSE)-1>(CLOSE/DELAY(CLOSE,19))^(1/20)-1))))`
**Inputs**: code, end_date
**Outputs**: 因子的值

### Alpha_191
**公式**: `((CORR(MEAN(VOLUME,20),LOW,5)+((HIGH+LOW)/2))-CLOSE)`
**Inputs**: code, end_date
**Outputs**: 因子的值

---

## 统计信息

- **总因子数**: 191个
- **已实现**: 77个 (Alpha101)
- **未实现**: 114个 (需要进一步开发)
- **需要行业中性化**: 24个 (在Alpha101中)

## 来源

- **原始**: 聚宽(JQData) alpha191.py
- **提取时间**: 2026-01-03
- **用途**: 因子库参考和实现指南

---

**注意**: 本文档仅保留因子公式和输入输出定义，已移除聚宽特定的API调用和装饰器代码。
