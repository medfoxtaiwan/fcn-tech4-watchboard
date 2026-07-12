# FCN watchboard

三檔美股（NVDA / TSM / GOOG）結構型商品（FCN, Fixed Coupon Note）追蹤看板。

- 進場日 2026-06-17，到期日 2026-10-17（4 個月）
- 下限價（Knock-In）= 進場價 70%，逐日以收盤價判定跌破並記錄
- 執行價（換股票價）= 進場價 75.61%，曾跌破下限價時到期比價用
- 提前出場（Knock-Out）= 進場價 100%，滿一個月（2026-07-17 起）皆曾漲過即符合
- 資料：Yahoo Finance 日線收盤，GitHub Actions 於每交易日 22:30 UTC 自動更新 `data.json`
- 看板：https://medfoxtaiwan.github.io/fcn-tech4-watchboard/

僅供個人參考，非投資建議；商品條件以公開說明書為準。
