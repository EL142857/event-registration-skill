#!/usr/bin/env bash
# 用虚构示例数据把整条流程跑一遍，结果在 out/ 里。用法：bash scripts/run_example.sh
set -euo pipefail
cd "$(dirname "$0")/.."
C=config/event.example.json
python3 scripts/make_sample.py examples
python3 scripts/normalize.py $C out/people.json
python3 scripts/proofs.py $C out/people.json examples/sample_attachments main
cp examples/sample_verdicts.json out/verdicts.json 2>/dev/null || true
python3 scripts/payment.py $C out/people.json out/verdicts.json out/payment.json
python3 scripts/merge.py $C out/people.json out/master.json --payment out/payment.json --checkins examples/sample_checkins.json
python3 scripts/render.py list $C out/people.json out/名单.html
python3 scripts/render.py payment $C out/payment.json out/缴费核对.html
python3 scripts/render.py master $C out/master.json out/总表.html
python3 scripts/render.py checkin $C out/people.json out/签到.html --qr examples/sample_qr.png
python3 scripts/render.py draw $C out/master.json out/抽奖.html
python3 scripts/checkin_xlsx.py $C out/people.json out/签到备份.xlsx
python3 scripts/build_gas.py $C out/people.json out/gas --qr examples/sample_qr.png
echo "完成：打开 out/ 里的 html 看效果"
