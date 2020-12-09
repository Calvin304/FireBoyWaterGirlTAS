import os
from util import run
import pyperclip as clip
from mod import SwfModder

path_rec = os.path.join("tas", "replay.txt")
path_out = os.path.join("tas", "adventure", "01.txt")

TRIM_END = True
__FORMAT_MAP = ["u", "r", "l"]
def format_frames(frames):
    def _format_frame(frame, hold):
        out_inputs = []
        for i, frame_input in enumerate(frame):
            if frame_input:
                out_inputs.append(__FORMAT_MAP[i] + " " + str(hold))

        if len(out_inputs) > 0:
            return ", ".join(out_inputs) + "\n"
        else:
            return "s " + str(hold) + "\n"

    ret = ""
    last_frame = frames[0]
    hold_count = 0
    for frame in frames:
        hold_count += 1
        if frame != last_frame:
            ret += _format_frame(last_frame, hold_count)

            last_frame = frame
            hold_count = 0
    # flush remaining
    if not(TRIM_END and all([x is False for x in last_frame])):
        ret += _format_frame(last_frame, hold_count)
    return ret

def format_raw_replay():
    with open(path_rec, "r") as frec:
        f_frames = []
        w_frames = []
        for rec_line in frec:
            frame = [(x == "true") for x in rec_line.rstrip().split(",")]
            f_frames.append(frame[:3])
            w_frames.append(frame[3:])

        with open(path_out, "w") as fout:
            fout.write("fireboy: \n")
            fout.write(format_frames(f_frames))

            fout.write("\nwatergirl: \n")
            fout.write(format_frames(w_frames))

def mod_and_launch():
    m = SwfModder("fbwg-replay.swf", "fbwg-tas.swf")
    m.disassemble()
    m.mod_all()
    m.reassemble()
    m.launch()

def record_replay():
    mod_and_launch()
    print(clip.paste())

if __name__ == '__main__':
    while True:
        print("Recording")
        record_replay()
        print("Replaying")
        format_raw_replay()
        input("Press enter to go again...")