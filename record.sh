#!/bin/sh
wid=`xdotool search --name 'Adobe Flash Player'`
if ! [[ $wid =~ ^[0-9]+$ ]] ; then
   echo "error: Could not locate window id" >&2; exit 1
fi

rm -f "rec_tmp/*"

record(){
  echo "Recording"

  echo -n "Waiting for first frame..."
  while true; do
    frameNo="`xsel -ob`"
    if [[ $frameNo =~ ^[0-9]+$ ]] ; then
      break
    fi
  done
  echo "[OK]"

  while true; do
    frameNo="00000000`xsel -ob`"
    xwd -id $wid -out "rec_tmp/${frameNo:(-8)}.xwd" -silent;
  done
}

render(){
  echo "Rendering"

  echo "Duplicating frames"
  files=(`echo rec_tmp/* | sort -nr`)

  # get last frame no
  dupFramesCount=0
  file=$(basename "${files[-1]}")
  lastFrameNo=${file%.*}
  lastFrameNo=$(expr $lastFrameNo + 0)

  lastValidPath=${files[1]}
  for ((i=0;i<=lastFrameNo;i++)); do
    frameNo="00000000$i"
    curPath="rec_tmp/${frameNo:(-8)}.xwd"
    if [ ! -f $curPath ]; then
        cp $lastValidPath $curPath
        dupFramesCount=$((dupFramesCount+1))
    else
      lastValidPath="$curPath"
    fi
  done
  echo "Duplicated $dupFramesCount frames"

  echo "Rendering to video"
  ffmpeg -y -loglevel error -i "rec_tmp/%08d.xwd" "rec_tmp/out.mkv"
  echo "Rendered to rec_tmp/out.mkv"

  rm -f rec_tmp/*.xwd

  exit 255
}
trap 'render' EXIT

record
