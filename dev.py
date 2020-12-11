#!/bin/env python3
import shutil
import os
import subprocess
import signal
import time
import hashlib
import cv2
from mod import SwfModder, TasLevelParser
from util import click_swf

def hash_file(filename):
    h = hashlib.sha256()
    b = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()

def combine(vid1, vid2, preview=False):
    path_out = os.path.join("rec", "out.mkv")

    preview_part = "-t 3" if preview else ""
    subprocess.run(('ffmpeg -y -i {0} '+ preview_part +' -i {1} ' + preview_part + ' -filter_complex '
                   '"[1:v]format=rgba,colorchannelmixer=aa=0.65[b];'
                    + '[0:v][b]overlay,pad=ceil(iw/2)*2:ceil(ih/2)*2" -c:v libx265 {2}')
                   .format(vid1, vid2, path_out),
                   shell=True)

def find_vid_start(path):
    tmp_dir = "vid_tmp"
    os.makedirs(tmp_dir, exist_ok=True)
    try:
        # export all images
        subprocess.run("ffmpeg -i '{}' -t 5 '{}'".format(path, os.path.join(tmp_dir, "%05d.png")), shell=True)

        im_start = cv2.imread(os.path.join("tools", "start.png"))
        for i, file in enumerate(sorted(os.listdir(tmp_dir))):
            file_path = os.path.join(tmp_dir, file)
            large_image = cv2.imread(file_path)
            result = cv2.matchTemplate(im_start, large_image, cv2.TM_SQDIFF_NORMED)
            mn, _, _, _ = cv2.minMaxLoc(result)
            if mn < 0.05:
                return i
    finally:
        shutil.rmtree(tmp_dir)

def compare(level_file, branches=None, preview=False):
    if branches is None:
        # default argument
        branches = ["a", "b"]

    rel_level_file = os.path.relpath(level_file, "tas")
    os.makedirs(os.path.dirname(os.path.join("rec", rel_level_file)), exist_ok=True)

    tmp_level_file = level_file + ".tmp"
    try:
        # temporarily preserve original level_file
        shutil.move(level_file, tmp_level_file)

        # compute relative name (e.g: adventure/01)
        rel_name = os.path.splitext(rel_level_file)[0]

        # process branch files
        branch_lengths = []
        branch_hashes = []
        for branch in branches:
            branch_path = os.path.join("tas", rel_name + branch + ".txt")
            t = TasLevelParser(branch_path)
            t.parse()
            branch_lengths.append(len(t.sequence))
            branch_hashes.append(hash_file(branch_path))

        rec_duration = min(branch_lengths) / 23  # in seconds (assume fps never dips below 23fps)

        def rec_swf(swf_file, duration, out_path):
            proc_swf = subprocess.Popen("flashplayer '" + swf_file + "'", shell=True)
            time.sleep(0.5)  # wait for window to appear
            window_id = click_swf()
            # time.sleep(0.7)

            rec_tmp_dir = "rec_tmp"
            os.makedirs(rec_tmp_dir, exist_ok=True)
            try:
                proc_rec = subprocess.Popen("sh record.sh", shell=True)
                # wait duration
                time.sleep(duration + 2)

                proc_rec.send_signal(signal.SIGINT)
                proc_swf.kill()

                proc_rec.wait()
            finally:
                output_video = os.path.join(rec_tmp_dir, "out.mkv")
                if not os.path.isfile(output_video):
                    raise FileNotFoundError("Record script did not produce video")
                shutil.move(output_video, out_path)
                shutil.rmtree(rec_tmp_dir)


        branch_rec_paths = []
        for i, branch in enumerate(branches):
            rel_branch_path = rel_name + branch + ".txt"
            rec_video = os.path.join("rec", rel_name + "-" + str(min(branch_lengths)) + "-" + branch_hashes[i] + ".mkv")
            branch_rec_paths.append(rec_video)
            if not os.path.isfile(rec_video):
                shutil.copy(os.path.join("tas", rel_branch_path), level_file)

                # mod
                m = SwfModder(os.path.join("swf", "fbwg-base-dev-clip.swf"), os.path.join("swf", "fbwg-tas.swf"))
                m.disassemble()
                m.mod_all()
                m.reassemble()

                rec_swf(m._output_swf_path, rec_duration, rec_video)

        # combine videos
        if len(branches) != 2:
            raise ValueError

        combination_hash = hashlib.sha256((rel_name + "-" + str(min(branch_lengths)) + "-" + "-".join(branch_hashes)).encode("utf8")).hexdigest()
        existing_combination_hash = ""
        try:
            with open(os.path.join("rec", "combination.txt")) as f:
                existing_combination_hash = f.read().strip()
        except:
            pass

        if preview or (combination_hash != existing_combination_hash):
            combine(*branch_rec_paths, preview)

        with open(os.path.join("rec", "combination.txt"), 'w') as f:
            f.write(combination_hash)
    finally:
        # restore level_file
        shutil.move(tmp_level_file, level_file)


if __name__ == '__main__':
    compare("tas/adventure/01.txt", ["a", "b"])
    # subprocess.run("mpv 'rec/out.mkv'", shell=True)
