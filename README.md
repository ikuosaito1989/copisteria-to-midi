# copisteria-to-midi

Docker ComposeでPDF楽譜をSMT++で認識し、MusicXMLとMIDIに変換するCLIです。SMT++の公式実装を固定したコミットから取得し、推論はCPUで実行します。

## 実行

```sh
docker compose build
mkdir -p input output
# input/ に score.pdf を置く
docker compose run --rm omr score.pdf
```

出力は `output/score.mid`、`output/score.musicxml`、ページ別bekernは `output/debug/score/page-001.krn` です。初回はモデルのダウンロードに時間がかかります。Hugging Faceのキャッシュは名前付きDocker volumeに保存されます。

```sh
docker compose run --rm omr "ピアノ 楽譜.pdf" --model grandstaff
docker compose run --rm omr --input /input/score.pdf --output /output/custom.mid
docker compose run --rm omr --help
```

`grandstaff` は公開チェックポイント `antoniorv6/smt-grandstaff` です。モデルの変更は環境変数 `SMT_MODEL_GRANDSTAFF` でHugging FaceリポジトリIDを指定できます。SMT++にはポーランド楽譜向けの微調整モデル `PRAIG/smt-fp-polish-scores` もあります。ゲート付きの場合はHugging Faceで利用条件に同意し、Composeの `environment` に `HF_TOKEN` を渡して `SMT_MODEL_GRANDSTAFF` をそのモデルIDに設定してください。

## 動作上の注意

- 各PDFページを300dpiで画像化して個別に推論します。複数ページの譜面はパート数が一致することを確認し、小節をページ順に結合します。ページ間でパート構成が変わる場合は停止します。
- ページ境界のタイや記号の継続は自動補正しません。デバッグ用 `.krn` と出力MusicXMLをMuseScoreなどで確認してください。
- SMT++の出力はbekernです。Humdrumとして解析してMusicXML/MIDIに変換し、ノートイベントのないMIDIはエラーにします。
- `--output` を指定するとMusicXMLは同じパスの拡張子を `.musicxml` にした名前で出力されます。

## クレジット

[SMT++](https://github.com/antoniorv6/SMT) はMITライセンスです。モデル重みの利用条件は各モデルカードを確認してください。Music21はBSDライセンスです。
