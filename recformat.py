import os

path_rec = os.path.join("rec", "rec.txt")
path_out = os.path.join("tas", "adventure", "01.txt")

__FORMAT_MAP = ["u", "r", "l"]

def format_frames(frames):
    ret = ""
    for frame in frames:
        out_inputs = []
        for i, frame_input in enumerate(frame):
            if frame_input:
                out_inputs.append(__FORMAT_MAP[i] + " 1")

        if len(out_inputs) > 0:
            ret += ", ".join(out_inputs) + "\n"
        else:
            ret += "s 1\n"
    return ret

if __name__ == '__main__':
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