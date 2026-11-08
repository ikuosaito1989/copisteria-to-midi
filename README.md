# copisteria-to-midi

Docker ComposeでPDF楽譜を認識し、MusicXMLと標準MIDIを出力するCLIです。OMRにはKobiMusicのOSS [copisteria](https://github.com/kobimusic/copisteria) を外部依存として利用します。copisteria本体は変更しません。

## 必要環境

- Docker Desktop (macOS Intel / Apple Silicon、Linuxでも動作)
- 初回ビルドとモデル取得時のインターネット接続

ホストへのPython、PyTorch、Popplerのインストールは不要です。コンテナはPython 3.12、CPU版PyTorch、Popplerを使用します。

## セットアップと実行

```sh
docker compose build
mkdir -p input output
# input/ に score.pdf を置く
docker compose run --rm omr score.pdf
```

生成先は `output/score.mid`, `output/score.musicxml` と `output/debug/score/page-001.musicxml` のようになります。相対入力名は `/input` 基準です。空白・日本語を含む名前はシェルで引用符を付けてください。

```sh
docker compose run --rm omr "ピアノ 楽譜.pdf" --model 2m
docker compose run --rm omr --input /input/score.pdf --output /output/custom.mid --model 28m
docker compose run --rm omr --help
```

`28m` が既定の高精度モデル、`2m` は軽量モデルです。出力MusicXMLはMIDIと同じ出力パスの拡張子を `.musicxml` に置き換えます。`--output` を省略した場合、入力名から両方の名前を作ります。

## モデルの取得とキャッシュ

選択したモデルの初回実行時にHugging Faceから必要な重みを取得します。Hugging Face Hubのキャッシュとcopisteria用重みは名前付きDocker volumeに保存され、再実行時に再利用されます。モデル重みはリポジトリに含みません。取得できない場合は対象リポジトリと原因を表示して失敗します。

## 制限事項

- Copisteriaはページを個別に認識します。このツールはページ内のパート順を維持し、同じパート数であることを検証して小節をページ順に連結します。ページごとにパートの分割・統合・順序が変わる譜面は自動照合できず、誤ったファイルを出さないため停止します。
- 小節番号はページ間で重複し得ます。MusicXML結合時は小節オブジェクトの順序を維持し、music21に番号を再採番させます。ページ境界のタイ、連続する調号・拍子・テンポ記号の意味がすべての譜面で保持される保証はありません。出力MusicXMLをMuseScore等で検証してください。
- OCR精度は入力画像や楽譜の状態に依存し、MIDIノートが存在しない結果はエラーとして扱います。

## トラブルシューティング

- `入力PDFが見つかりません`: PDFを `input/` に置き、ファイル名を指定してください。
- モデル取得エラー: ネットワーク接続とHugging Faceの公開モデルへのアクセスを確認してください。
- 複数ページ結合エラー: `output/debug/<入力名>/` のページ別MusicXMLを確認してください。
- Apple SiliconでもCPU実行です。初回はイメージの取得、重みの取得、OMR処理に時間がかかります。

## クレジットとライセンス

copisteriaはKobiMusicのプロジェクトで、リポジトリのライセンスはApache-2.0です。モデルカード記載の重みの利用条件も確認してください。music21はBSDライセンスです。
