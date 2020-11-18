#!/bin/env python3
import re

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
                    print()
                else:
                    parts = re.split(r"\s+", line)
                    for i in range(int(parts[2])):
                        self.set_frame(cur_frame_index + i, self.__PARSE_MAP[parts[0]][parts[1]])
                    print()

t = TasLevelParser("tas/adventure/01.txt")
t.parse()
print(t.sequence)