#!/bin/env python3
import shutil
import os
import subprocess
import time
import hashlib
import cv2
from mod import SwfModder, TasLevelParser


def hash_file(filename):
    h = hashlib.sha256()
    b = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()

def combine(vid1, vid2):
    path_out = os.path.join("rec", "out.mkv")
    offset = -5

    subprocess.run('ffmpeg -y -i {0} -i {2} -filter_complex '
                   '"[1:v]trim=start_frame={1},format=rgba,colorchannelmixer=aa=0.65[b];'
                   '[0:v]trim=start_frame={3}[a];[a][b]overlay" -c:v libx265 {4}'
                   .format(vid1, find_vid_start(vid1) + offset, vid2, find_vid_start(vid2) + offset, path_out),
                   shell=True)

def find_vid_start(path):
    tmp_dir = "vid_tmp"
    os.makedirs(tmp_dir, exist_ok=True)
    try:
        # export all images
        subprocess.run("ffmpeg -i '{}' -t 2 '{}'".format(path, os.path.join(tmp_dir, "%05d.png")), shell=True)

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

def compare(level_file, branches=None):
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

        proc_rec = None
        proc_swf = None

        def click_swf():
            output = subprocess.run("xdotool getwindowgeometry --shell "
                                    "`xdotool search --name 'Adobe Flash Player'`", shell=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            window_data = dict([item.split("=") for item in output.stdout.decode("utf8").splitlines()])
            window = window_data["WINDOW"]
            width = int(window_data.get("WIDTH", 929))
            height = int(window_data.get("HEIGHT", 1010))

            # first play button
            subprocess.run("xdotool mousemove --window {} {} {}".format(window, width * 0.5, height * 0.8), shell=True)
            subprocess.run("xdotool click 1".format(window), shell=True)
            # second play button
            subprocess.run("xdotool mousemove --window {} {} {}".format(window, width * 0.5, height * 0.55), shell=True)
            subprocess.run("xdotool click 1".format(window), shell=True)
            # move cursor out of the way
            subprocess.run("xdotool mousemove --window {} {} {}".format(window, width, height), shell=True)
            return window


        def rec_swf(duration, out_path):
            proc_swf = subprocess.Popen("flashplayer 'fbwg-tas.swf'", shell=True)
            time.sleep(0.5)  # wait for window to appear
            window_id = click_swf()
            time.sleep(0.7)
            proc_rec = subprocess.Popen("recordmydesktop --windowid '{}' "
                                        "--on-the-fly-encoding --no-sound -o '{}'".format(window_id, out_path), shell=True)
            # wait duration
            time.sleep(duration + 1)

            proc_rec.kill()
            proc_swf.kill()


        branch_rec_paths = []
        for i, branch in enumerate(branches):
            rel_branch_path = rel_name + branch + ".txt"
            rec_video = os.path.join("rec", rel_name + "-" + str(min(branch_lengths)) + "-" + branch_hashes[i] + ".ogv")
            branch_rec_paths.append(rec_video)
            if not os.path.isfile(rec_video):
                shutil.copy(os.path.join("tas", rel_branch_path), level_file)

                # mod
                m = SwfModder("fbwg-base-dev.swf", "fbwg-tas.swf")
                m.disassemble()
                m.mod_all()
                m.reassemble()

                rec_swf(rec_duration, rec_video)

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

        if combination_hash != existing_combination_hash:
            combine(*branch_rec_paths)

        with open(os.path.join("rec", "combination.txt"), 'w') as f:
            f.write(combination_hash)
    finally:
        # restore level_file
        shutil.move(tmp_level_file, level_file)


if __name__ == '__main__':
    compare("tas/adventure/01.txt", ["a","b"])
    subprocess.run("mpv 'rec/out.mkv'", shell=True)
