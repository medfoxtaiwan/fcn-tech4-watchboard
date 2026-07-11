# FCN tech4 watchboard

四檔美股（NVDA / AMD / TSLA / META）結構型商品（FCN, Fixed Coupon Note）追蹤看板。

- 進場日 2026-03-27，到期日 2026-11-27
- 下限價（Knock-In）= 進場價 65%，逐日以收盤價判定跌破並記錄
- 提前出場（Knock-Out）= 進場價 100%，滿一個月後皆曾漲過即符合
- 資料：Yahoo Finance 日線收盤，GitHub Actions 於每交易日 22:30 UTC 自動更新 `data.json`
- 看板：https://medfoxtaiwan.github.io/fcn-tech4-watchboard/

僅供個人參考，非投資建議；商品條件以公開說明書為準。
