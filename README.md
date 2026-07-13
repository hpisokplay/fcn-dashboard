# FCN 管理系統

上新莊分行 FCN(結構型商品)KI/KO 監控儀表板。

- 美股/日股報價由 GitHub Actions 每日自動抓取(Yahoo Finance),存於 prices.json
- 網頁讀 prices.json,不需外部代理

## 自動更新
.github/workflows/prices.yml 每交易日 15:00(日股收盤)、05:00(美股收盤)自動更新 prices.json

## 注意
data.csv 為公開檔;請勿放置真實客戶敏感資料(GitHub Pages repo 為公開)。
