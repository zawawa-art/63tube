# 目的
- 撮りためた動画をキャストやテーマに沿って公開するWebサイト/PWAを作成する
- メインターゲットはスマホでYoutube ショート動画、tiktok, IGリールのようなUIを実現したい
- FAN/FUNサイトなので、パロディ的なもので良い
- ユーザ登録や認証は求めないカジュアルなものに
- キャストへの感謝の気持ちを伝えたい

# 構成
- ローカル mac mini の特定ディレクトリに配信元動画を配置
- 動画自体は Cloudflare tunnelでインターネットへ公開する想定。CFのキャッシュを存分に活かして、家への通信はほとんど無しでユーザ体験も損なわないように
- 動画だけどCFキャッシュで怒られない範囲のサイズにしたい
- 本体はCF Pages/Workersで実装する想定

# 初期構築
- https://63tube.zawawa.uk という新アプリにしようかな
- 今後も育てて行きたいけど、まずは来週卒業のChocoちゃん向けに /choco だけのコンテンツを想定
- 動画は縦も横もあるので、90' Rotate したりもして出来るだけ大きく見せたい
- いいね、ハート連打でアニメーション、コメント付けたり出来るようにしたい
- それを保存して他の人も見られるように
- スワイプして次の動画見れる感じに。スムースに見せられるように裏で読み込む仕組みを
- 

# 技術スタック（案）
- フロントエンド: Vanilla HTML/CSS/JS（Swiper.js は後で検討）
- ホスティング: Cloudflare Pages
- ストレージ: まずは JSON ファイル（後で D1 移行）
- 動画配信: Cloudflare Tunnel → mac mini（代替: R2）

# UX重視のポイント
- スマホ縦持ちでスワイプ再生（TikTok/Reels 風）
- いいね・コメントでアニメーション
- キャストごとにテーマ色・見た目を変更
- 卒業カウントダウンと記念バッジ

# データモデル（JSON案）
videos.json:
- id, cast, title, url, duration, width, height

comments.json:
- video_id, nickname, body, created_at

# API風エンドポイント（Pages で static JSON を配信）
GET /videos.json → 動画一覧
GET /comments.json → コメント一覧

# 初期プロトタイプ（今日中に動かす）
- index.html / style.css / script.js / videos.json / comments.json
- スワイプで次の動画、いいね、コメント表示

---

# 実装記録（2026-11-05）

## ファイル構成
```
63tube/
├── index.html          # プロトタイプ本体
├── style.css           # スマホ縦持ちUI（スワイプ・アニメーション）
├── script.js           # スワイプ・いいね・コメント・プリロードロジック
├── videos.json         # 動画メタデータ（id, cast, title, date, url, duration, width, height, orientation）
├── comments.json       # コメントデータ（video_id, nickname, body, created_at）
└── video/              # 動画ファイル（.MOV 2本、mac mini からコピー）
```

## 実装した機能
- **スワイプ再生**：上スワイプで次の動画、下スワイプで前の動画（ループ対応：最初↔最後）
- **自動再生**：iOS Safari でも `muted` + `playsinline` で自動再生。ブロック時はタップで開始
- **タップ再生/一時停止**：動画タップで再生・一時停止をトグル
- **ミュート切り替え**：🔊/🔇 ボタンで音のオン/オフを明示的に切り替え（localStorage 保存）
- **いいね**：ハート連打アニメーション、カウントアップ（localStorage 保存、IP ベース重複抑制は後で D1 移行時に検討）
- **コメント**：ニックネーム任意、投稿で即表示、作成日時付き
- **撮影日表示**：動画の右上に独立バッジとして表示
- **裏キャッシュ（プリロード）**：前後 1 本を `video.preload='auto'` + `vid.load()` で先読み、スムーズに切り替え
- **カウントダウン**：卒業日までの残り日数をヘッダーに表示（2026-11-14 設定、変更可能）
- **横向き動画対応**：`orientation: landscape` で 90° 回転表示

## 技術スタック（確定）
- フロントエンド: Vanilla HTML/CSS/JS（フレームワーク不使用）
- ホスティング: Cloudflare Pages（静的ファイル配信）
- ストレージ: JSON ファイル（videos.json / comments.json）→ 後で D1 移行
- 動画配信: Cloudflare Tunnel → mac mini（代替: Cloudflare R2）

## iOS Safari での注意点
- 自動再生は `muted` が必須。`playsinline` 属性を明示
- video タグに直接タッチイベントを付けるとフルスクリーンになるので、wrapper でタップを処理
- video タグは毎回新規作成ではなく、preloadedVideos で使い回し（状態汚染防止）

## Cloudflare Tunnel 設定（動画配信用）

### 配信先（現行踏襲）
- 動画置き場: `/Volumes/SUNEAST2TB/63archive/data/63tube/`（mac mini）
- 公開 URL: `https://media.zawawa.uk/63tube/<ファイル名>`
- ssh mini でアクセス可能

### videos.json の url 書き換え
`videos.json` の `url` を以下のように設定：

```json
{
  "url": "https://media.zawawa.uk/63tube/2025-09-11_21-10-39_IMG_7835.MOV"
}
```

### CF キャッシュの活用
- Tunnel 経由で配信しても、CF エッジキャッシュが効くので、同じ動画へのアクセスは mac mini に届かない
- 動画ファイルサイズは 25MiB 未満に抑える（Pages 制限ではなく、CF キャッシュの観点でも推奨）
- 必要なら `.MOV` を `.MP4`（H.264/AAC）に変換して互換性を高める

## 今後のTODO
- [ ] Cloudflare Pages にデプロイ（Git リポジトリ作成・push・Pages 接続）
- [ ] カスタムドメイン `https://63tube.zawawa.uk` に紐付け
- [ ] Cloudflare Tunnel で mac mini の動画ディレクトリを公開、videos.json の url を Tunnel URL に書き換え
- [ ] 動画を R2 に移行（CF キャッシュを存分に活用、家宛トラフィックゼロ）
- [ ] JSON → D1 移行（いいね・コメントの同時書き込み対応）
- [ ] キャスト追加（choco 以外）、テーマ色変更
- [ ] PWA マニフェスト・アイコン、ホーム画面追加対応
- [ ] 卒業カウントダウン・記念バッジの充実