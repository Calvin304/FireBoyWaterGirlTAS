#!/bin/env python3
import os
import re
import subprocess
import shutil
from util import run, run_async, click_swf

class TasLevelParser:
    __PARSE_MAP = [
        {
            "u": 0,
            "r": 1,
            "l": 2,
        },
        {
            "u": 3,
            "r": 4,
            "l": 5,
        }
    ]
    __CHARACTER_PARSE_MAP = [
        "fireboy:",
        "watergirl:"
    ]
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
            cur_time = 0

            character_num = -1  # 0 for fireboy, 1 for watergirl
            character_parse_list = self.__CHARACTER_PARSE_MAP.copy()

            for line in f:
                line = re.sub(r"#[^\n]*", "", line).strip()  # remove comments
                if len(line) <= 0:
                    continue  # empty line so skip

                if line in character_parse_list:
                    cur_time = 0
                    character_num = self.__CHARACTER_PARSE_MAP.index(line)
                    character_parse_list.remove(line)
                else:
                    line_max_duration = -1
                    for part in line.split(","):
                        command, duration = re.split(r"\s+", part.strip())
                        duration = int(duration)

                        if command != "s":
                            for i in range(duration):
                                self.set_frame(cur_time + i, self.__PARSE_MAP[character_num][command])
                        else:
                            # sleep command
                            self.get_frame(cur_time + duration - 1)

                        if duration > line_max_duration:
                            line_max_duration = duration

                    cur_time += line_max_duration

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
    __LEVELS_MAP = ["adventure", "puzzle", "speed"]

    def __init__(self, swf_path, output_swf_path):
        self._swf_path = swf_path
        self._output_swf_path = output_swf_path

        self._swf_name = os.path.splitext(os.path.basename(self._swf_path))[0]
        self._tmp_swf_path = os.path.join(self.__PATH_TMP, self._swf_name + ".swf")
        self._abc_path = os.path.join(self.__PATH_TMP, self._swf_name + "-0")

        self._parsed_tas_levels = {}

    def disassemble(self):
        os.makedirs(self.__PATH_TMP, exist_ok=True)  # make tmp dir
        shutil.copy(self._swf_path, self._tmp_swf_path)  # copy base swf
        run(os.path.join("RABCDAsm","abcexport"), os.path.abspath(self._tmp_swf_path))  # abcexport
        run(os.path.join("RABCDAsm","rabcdasm"), os.path.abspath(os.path.join(self.__PATH_TMP, self._swf_name + "-0.abc")))

    def mod_all(self):
        self.mod_levels()
        self.mod_inputs()

    def _mod_file(self, file_path, start_lines, end_lines, replacement):
        """
        Internal method used for modding/patching asasm files
        """
        start_match_index = 0
        end_match_index = 0

        with open(file_path, "r") as f:
            with open(file_path + ".mod", "w") as g:
                ignoring = False
                for line in f:
                    if start_match_index == len(start_lines):
                        g.write(replacement)
                        start_match_index += 1
                        ignoring = True
                    if end_match_index >= len(end_lines):
                        ignoring = False

                    if len(line.strip()) > 0:
                        if not ignoring:
                            if start_match_index < len(start_lines):
                                start, end = start_lines[start_match_index]
                                if line.lstrip().startswith(start) and line.rstrip().endswith(end):
                                    start_match_index += 1
                                else:
                                    start_match_index = 0
                        else:
                            if end_match_index < len(end_lines):
                                start, end = end_lines[end_match_index]
                                if line.lstrip().startswith(start) and line.rstrip().endswith(end):
                                    end_match_index += 1
                                else:
                                    end_match_index = 0

                    if not ignoring:
                        g.write(line)

                if ignoring:
                    # if still ignoring, could not find end lines
                    raise RuntimeError("Could not find end lines")

        shutil.move(file_path + ".mod", file_path)  # replace file

    def _parse_tas_levels(self):
        levels = {}
        for level_type in os.listdir(self.__PATH_TAS):
            if os.path.isdir(os.path.join(self.__PATH_TAS, level_type)):
                parsed_levels = []

                for tas_file in sorted([x for x in os.listdir(os.path.join(self.__PATH_TAS, level_type))
                                        if os.path.splitext(x)[0].isnumeric()],
                                       key=lambda file: int(os.path.splitext(file)[0])):
                    level_index = int(os.path.splitext(tas_file)[0])
                    tas_file_path = os.path.join(self.__PATH_TAS, level_type, tas_file)

                    for _ in range(level_index - len(parsed_levels)):
                        parsed_levels.append(None)

                    t = TasLevelParser(tas_file_path)
                    t.parse()
                    parsed_levels.append(t)

                levels[level_type] = parsed_levels
        self._parsed_tas_levels = levels

    def mod_inputs(self):
        """
        Inject the TAS inputs into asasm
        """
        self._parse_tas_levels()
        ret = ""
        for level_type, parsed_levels in self._parsed_tas_levels.items():
            ret += "getlocal0\n"
            ret += 'findpropstrict QName(PackageNamespace(""), "Array")\n'

            for tas_level in parsed_levels:
                if tas_level is None:
                    ret += "pushnull\n"
                else:
                    ret += tas_level.to_asm()

            ret += 'constructprop QName(PackageNamespace(""), "Array"), ' + str(len(parsed_levels)) + '\n'
            ret += 'setproperty QName(PackageInternalNs(""), "pz' + level_type.title() + 'Inputs")\n'

        try:
            self._mod_file(os.path.join(self._abc_path, "level.class.asasm"), [
                ("pushdouble", "0.0384615384615385"),
                ("convert_d", ""),
                ("setproperty", 'QName(PackageNamespace(""), "m_timeStep")'),
            ], [
                ("constructprop", 'QName(PackageNamespace(""), "Array"), 23'),
                ("constructprop", 'QName(PackageNamespace(""), "Array"), 2'),
                ("setproperty", 'QName(PackageInternalNs(""), "pzPuzzleInputs")')

            ], ret)
        except RuntimeError:
            self._mod_file(os.path.join(self._abc_path, "level.class.asasm"), [
                ("pushdouble", "0.0384615384615385"),
                ("convert_d", ""),
                ("setproperty", 'QName(PackageNamespace(""), "m_timeStep")'),
            ], [
               ("constructprop", 'QName(PackageNamespace(""), "Array"), 0'),
               ("constructprop", 'QName(PackageNamespace(""), "Array"), 2'),
               ("setproperty", 'QName(PackageInternalNs(""), "pzPuzzleInputs")')

           ], ret)

    def _get_levels_asm(self):
        levels = []
        with open(os.path.join("tas", "levels.txt"), "r") as f:
            for line in f:
                levels.append([int(x) for x in line.strip().split(",")])

        ret = 'findpropstrict QName(PackageNamespace(""), "Array")\n'
        for level in reversed(levels):
            ret += 'findpropstrict QName(PackageNamespace(""), "Array")\n'
            for val in level:
                ret += "pushbyte " + str(val) + "\n"
            ret += 'constructprop QName(PackageNamespace(""), "Array"), ' + str(len(level)) + "\n"

        ret += 'constructprop QName(PackageNamespace(""), "Array"), ' + str(len(levels)) + "\n"
        ret += 'setproperty QName(PackageInternalNs(""), "pzLevels")\n'
        return ret

    def mod_levels(self):
        """
        Inject the TAS level visit order into asasm
        """
        self._mod_file(os.path.join(self._abc_path, "Game.class.asasm"), [
            ("getlocal0", ""),
            ("pushscope", ""),
            ("debug", '1, "_loc1_", 0, 118'),
            ("getlocal0", "")
        ], [
            ('constructprop', 'QName(PackageNamespace(""), "Array"), 2'),
            ('constructprop', 'QName(PackageNamespace(""), "Array"), 2'),
            ('setproperty', 'QName(PackageInternalNs(""), "pzLevels")')
        ], self._get_levels_asm())

    def reassemble(self):
        run(os.path.join("RABCDAsm","rabcasm"), os.path.abspath(os.path.join(self.__PATH_TMP, self._swf_name + "-0", self._swf_name + "-0.main.asasm")))
        run(os.path.join("RABCDAsm","abcreplace"), os.path.abspath(self._tmp_swf_path), "0", os.path.abspath(os.path.join(self._abc_path, self._swf_name + "-0.main.abc")))
        shutil.move(self._tmp_swf_path, self._output_swf_path)
        shutil.rmtree(self.__PATH_TMP)

    def launch(self):
        if os.name == "posix":
            import time
            proc = subprocess.Popen("flashplayer '" + os.path.abspath(self._output_swf_path) + "'", shell=True)
            time.sleep(0.5)
            click_swf()
            proc.wait()
        else:
            return run("flashplayer", os.path.abspath(self._output_swf_path))

    def launch_async(self):
        if os.name == "posix":
            import time
            proc = subprocess.Popen("flashplayer '" + os.path.abspath(self._output_swf_path) + "'", shell=True)
            time.sleep(0.5)
            click_swf()
            return proc
        else:
            return run_async("flashplayer", os.path.abspath(self._output_swf_path))

if __name__ == '__main__':
    m = SwfModder(os.path.join("swf", "fbwg-base-dev.swf"), os.path.join("swf", "fbwg-tas.swf"))
    m.disassemble()
    m.mod_all()
    m.reassemble()
    m.launch()
