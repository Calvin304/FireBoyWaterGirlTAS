import os
from util import run
import pyperclip as clip
from mod import SwfModder

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

def format_raw_replay(path_rec, path_out):
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

def record_replay(m):
    proc = m.launch_async()
    input("Press enter when done recording...")
    print(clip.paste())
    proc.kill()

def auto_workflow():
    m = SwfModder("fbwg-replay.swf", "fbwg-tas.swf")
    while True:
        format_raw_replay()
        m.disassemble()
        m.mod_all()
        m.reassemble()

        print("Recording")
        record_replay(m)

        print("Replaying")
        m.disassemble()
        m.mod_all()
        m.reassemble()
        proc = m.launch_async()
        input("Press enter when done watching...")
        proc.kill()

        input("Press enter to go again...")

if __name__ == '__main__':
    # auto_workflow()

    format_raw_replay(os.path.join("tas", "replay.txt"),
                      os.path.join("tas", "adventure", "01.txt"))