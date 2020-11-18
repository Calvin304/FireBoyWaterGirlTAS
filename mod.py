#!/bin/env python3
import os
import re
import subprocess
import shutil

class TasLevelParser:
    __PARSE_MAP = {
        "f": {
            "u": 0,
            "r": 1,
            "l": 2,
        },
        "w": {
            "u": 3,
            "r": 4,
            "l": 5
        }
    }
    __NO_OP = [0, 0, 0, 0, 0, 0]

    def __init__(self, path):
        self.path = path
        self.sequence = []

    def get_frame(self, index):
        if index > len(self.sequence) - 1:
            for _ in range(index - len(self.sequence) + 1):
                self.sequence.append(self.__NO_OP.copy())
            return self.get_frame(index)
        else:
            return self.sequence[index].copy()

    def set_frame(self, index, key_index):
        frame = self.get_frame(index)
        frame[key_index] = 1
        self.sequence[index] = frame

    def parse(self):
        with open(self.path, "r") as f:
            cur_frame_index = 0
            for line in f:
                line = re.sub(r"#[^\n]*", "", line).strip()  # remove comments
                if len(line) <= 0:
                    continue

                if line.isnumeric():
                    cur_frame_index = int(line)
                    self.get_frame(cur_frame_index)
                else:
                    parts = re.split(r"\s+", line)
                    for i in range(int(parts[2])):
                        self.set_frame(cur_frame_index + i, self.__PARSE_MAP[parts[0]][parts[1]])

    def to_asm(self):
        ret = 'findpropstrict QName(PackageNamespace(""), "Array")\n'
        for frame in reversed(self.sequence):
            ret += 'findpropstrict QName(PackageNamespace(""), "Array")\n'
            for val in frame:
                ret += "pushbyte " + str(val) + "\n"
            ret += 'constructprop QName(PackageNamespace(""), "Array"), ' + str(len(frame)) + "\n"

        ret += 'constructprop QName(PackageNamespace(""), "Array"), ' + str(len(self.sequence)) + "\n"
        return ret

class SwfModder:
    __PATH_TMP = "tmp"
    __PATH_TAS = "tas"

    def __init__(self, swf_path, output_swf_path):
        self._swf_path = swf_path
        self._output_swf_path = output_swf_path

        self._swf_name = os.path.splitext(self._swf_path)[0]
        self._tmp_swf_path = os.path.join(self.__PATH_TMP, self._swf_name + ".swf")
        self._abc_path = os.path.join(self.__PATH_TMP, self._swf_name + "-0")

    def disassemble(self):
        os.makedirs(self.__PATH_TMP, exist_ok=True)  # make tmp dir
        shutil.copy(self._swf_path, self._tmp_swf_path)  # copy base swf
        subprocess.run(["abcexport", os.path.abspath(self._tmp_swf_path)])  # abcexport
        subprocess.run(["rabcdasm", os.path.abspath(os.path.join(self.__PATH_TMP, self._swf_name + "-0.abc"))])

    def mod_inputs(self):
        level_class_path = os.path.join(self._abc_path, "level.class.asasm")
        with open(level_class_path, "r") as f:
            with open(level_class_path+".mod", "w") as g:
                flags = 0
                ignoring = False
                for line in f:
                    if flags == 3:

                        # proof of concept: just setting lvl 1-1
                        g.write("getlocal0\n")
                        g.write('findpropstrict QName(PackageNamespace(""), "Array")\n')
                        g.write('pushnull\n')

                        t = TasLevelParser("tas/adventure/01.txt")
                        t.parse()
                        g.write(t.to_asm())

                        g.write('constructprop QName(PackageNamespace(""), "Array"), 2\n')
                        g.write('setproperty QName(PackageInternalNs(""), "pzAdventureInputs")\n')

                        ignoring = True
                    if flags == -3:
                        ignoring = False

                    if line.lstrip().startswith("pushdouble") and line.rstrip().endswith("0.0384615384615385"):
                        flags += 1
                    elif flags > 0 and line.strip() == "convert_d":
                        flags += 1
                    elif flags > 0 and line.lstrip().startswith("setproperty") and line.rstrip().endswith('QName(PackageNamespace(""), "m_timeStep")'):
                        flags += 1
                    elif ignoring and line.lstrip().startswith("constructprop") and line.rstrip().endswith('QName(PackageNamespace(""), "Array"), 23'):
                        flags -= 1
                    elif ignoring and flags < 0 and line.lstrip().startswith("constructprop") and line.rstrip().endswith('QName(PackageNamespace(""), "Array"), 2'):
                        flags -= 1
                    elif ignoring and flags < 0 and line.lstrip().startswith("setproperty") and line.rstrip().endswith('QName(PackageInternalNs(""), "pzPuzzleInputs")'):
                        flags -= 1
                    else:
                        flags = 0

                    if not ignoring:
                        g.write(line)

        shutil.move(level_class_path+".mod", level_class_path)  # replace file

    def reassemble(self):
        subprocess.run(["rabcasm", os.path.abspath(os.path.join(self.__PATH_TMP, self._swf_name + "-0", self._swf_name + "-0.main.asasm"))])
        subprocess.run(["abcreplace", os.path.abspath(self._tmp_swf_path), "0", os.path.abspath(os.path.join(self._abc_path, self._swf_name + "-0.main.abc"))])
        shutil.move(self._tmp_swf_path, self._output_swf_path)
        shutil.rmtree(self.__PATH_TMP)

    def launch(self):
        subprocess.run(["flashplayer", self._output_swf_path])

m = SwfModder("fbwg-base.swf", "fbwg-tas.swf")
m.disassemble()
m.mod_inputs()
m.reassemble()
m.launch()