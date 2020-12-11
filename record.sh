#!/bin/sh
# This script records the Adobe Flash Player window in a frame-synchronised fashion.
# fbwg-base-dev-clip.swf must be used for this to work -- that swf file has been modded
# so that the clipboard is updated with the current frame number for every frame that is run.

# The key benefit of recording in this way is that it tries to stabilise the time-differences in
# adjacent frames of the resulting videos, which is introduced due to the game running at a variable fps.
# (NB: the fps seems to fluctuate particularly greatly for the initial second or so of each level)

# This allows for better direct comparison between recordings of different runs as it
# reduces the likelihood that the recordings will fall out of sync with each other.

# When dealing with time improvements in the order of fractions of seconds, the stability
# of the game is insufficient for the direct comparison of unsynchronised screen recordings.

# Technical details:
# xwd is used to quickly dump screen data many times per second while recording
# frames are then duplicated as necessary to stabilise fps
# then the frames are stiched together into a video file using Ffmpeg

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
