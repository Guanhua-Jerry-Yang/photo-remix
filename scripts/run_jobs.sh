#!/bin/zsh
# photo-remix：并发执行 jobs.txt 里的 Codex 出图任务（已有输出自动跳过）
# 用法: run_jobs.sh <run_dir> [并发数, 默认 4]
# 结束打印 RESULT: 行；失败会区分「基础设施」（额度/登录/模型不可用/超时）和「其他」
RUN=${1:A}; P=${2:-4}
[[ -f $RUN/jobs.txt ]] || { echo "RESULT: FAIL 没有 $RUN/jobs.txt，先跑 make_jobs.py"; exit 1; }
mkdir -p $RUN/logs
export RUN
export PHOTO_REMIX_MODEL=${PHOTO_REMIX_MODEL:-gpt-5.5}   # Codex 默认 gpt-6-luna 对 ChatGPT 账号不可用

one() {
  key=$1; id=$2
  out=$RUN/photos/$key/outputs/$id.png
  [[ -s $out ]] && { echo "SKIP $key $id"; return; }
  for try in 1 2 3; do
    timeout 900 codex exec -m $PHOTO_REMIX_MODEL --skip-git-repo-check -s workspace-write \
      -C $RUN -i $RUN/photos/$key/source.jpg - < $RUN/jobs/${key}__$id.prompt \
      > $RUN/logs/${key}__$id.try$try.log 2>&1
    [[ -s $out ]] && { echo "OK $key $id"; return; }
    # 基础设施故障不重试
    if grep -qiE 'usage limit|rate limit|quota|429|401|unauthorized|not supported|log in|login' $RUN/logs/${key}__$id.try$try.log; then
      echo "FAIL-INFRA $key $id $(grep -oiE 'usage limit|rate limit|quota|429|401|unauthorized|not supported|log in|login' $RUN/logs/${key}__$id.try$try.log | head -1)"; return
    fi
  done
  echo "FAIL $key $id"
}
export -f one 2>/dev/null
start=$(date +%s)
: > $RUN/logs/batch.log
while read key id; do
  [[ -z $key ]] && continue
  while (( $(jobs -r | wc -l) >= P )); do sleep 2; done
  one $key $id >> $RUN/logs/batch.log &
done < $RUN/jobs.txt
wait
cat $RUN/logs/batch.log
ok=$(grep -cE '^(OK|SKIP)' $RUN/logs/batch.log); total=$(grep -c . $RUN/jobs.txt)
infra=$(grep -c '^FAIL-INFRA' $RUN/logs/batch.log); other=$(grep -c '^FAIL ' $RUN/logs/batch.log)
echo "RESULT: $ok/$total 成功；基础设施失败 $infra；其他失败 $other；用时 $(( ($(date +%s)-start)/60 )) 分钟"
