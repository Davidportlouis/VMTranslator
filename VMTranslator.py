#!/usr/bin/env python3
import sys
from enum import Enum
from typing import List, Tuple


class Parser:

    COMMAND = Enum(
        "COMMAND", ["ARITHMETIC", "PUSH", "POP", "IF", "FUNCTION", "RETURN", "CALL"]
    )

    def __init__(self, filename: str):
        self.filename: str = filename
        self.file = open(filename, "r")

    def hasMoreLines(self) -> bool:
        line = self.file.readline()
        while line.startswith("//"):
            line = self.file.readline()
        return line.strip()

    def commandType(self, command):
        if command.startswith("push"):
            return Parser.COMMAND.PUSH
        elif command.startswith("pop"):
            return Parser.COMMAND.POP
        elif self._is_arithmetic(command):
            return Parser.COMMAND.ARITHMETIC
        elif self._is_comparator(command):
            return Parser.COMMAND.IF

    def arg1(self, currentCommand, commandType) -> str:
        if commandType == Parser.COMMAND.ARITHMETIC or commandType == Parser.COMMAND.IF:
            return currentCommand
        else:
            return currentCommand.split(" ")[1]

    def arg2(self, currentCommand, commandType) -> int:
        return int(currentCommand.split(" ")[2])

    def _is_arithmetic(self, command):
        return (
            command.startswith("add")
            or command.startswith("sub")
            or command.startswith("neg")
            or command.startswith("eq")
            or command.startswith("gt")
            or command.startswith("lt")
            or command.startswith("and")
            or command.startswith("or")
            or command.startswith("not")
        )

    def _is_comparator(self, command):
        pass

    def parseVMCode(self) -> List[Tuple]:
        vm_codes = []
        for line in self.file:
            if line.startswith("//") or len(line := line.strip()) == 0:
                continue
            current_command = line
            command_type = self.commandType(current_command)
            arg1 = arg2 = None
            if command_type != Parser.COMMAND.RETURN:
                arg1 = self.arg1(current_command, command_type)
            if (
                command_type == Parser.COMMAND.PUSH
                or command_type == Parser.COMMAND.POP
                or command_type == Parser.COMMAND.FUNCTION
                or command_type == Parser.COMMAND.CALL
            ):
                arg2 = self.arg2(current_command, command_type)
            vm_codes.append((command_type, arg1, arg2))
        self.file.close()

        return vm_codes


class CodeWriter:

    def __init__(self, filename):
        self.file = open(filename, "w")
        self.static_idx = 16
        self.static_mapping = {i: 0 for i in range(0, 240)}
        self.bool_count = 0

    def writeArithmetic(self, command):
        asm_command = ""
        if command == "add":
            asm_command += """@0\nA=M-1\nD=M\nA=A-1\nM=D+M\n@0\nM=M-1\n"""
        elif command == "sub":
            asm_command += """@0\nA=M-1\nD=M\nA=A-1\nM=M-D\n@0\nM=M-1\n"""
        elif command == "neg":
            asm_command += """@0\nA=M-1\nM=-M\n"""
        elif command == "and":
            asm_command += """@0\nA=M-1\nD=M\nA=A-1\nM=D&M\n@0\nM=M-1\n"""
        elif command == "or":
            asm_command += "@0\nA=M-1\nD=M\nA=A-1\nM=D|M\n@0\nM=M-1\n"
        elif command == "not":
            asm_command += "@0\nA=M-1\nM=!M\n"
        elif command == "lt":
            asm_command += f"@0\nM=M-1\nA=M\nD=M\n@0\nM=M-1\n@0\nA=M\nD=M-D\n@BOOL{self.bool_count}\nD;JLT\n@0\nA=M\nM=0\n@ENDBOOL{self.bool_count}\n0;JMP\n(BOOL{self.bool_count})\n@0\nA=M\nM=-1\n(ENDBOOL{self.bool_count})\n@0\nM=M+1"
            self.bool_count += 1
        elif command == "gt":
            asm_command += f"@0\nM=M-1\nA=M\nD=M\n@0\nM=M-1\n@0\nA=M\nD=M-D\n@BOOL{self.bool_count}\nD;JGT\n@0\nA=M\nM=0\n@ENDBOOL{self.bool_count}\n0;JMP\n(BOOL{self.bool_count})\n@0\nA=M\nM=-1\n(ENDBOOL{self.bool_count})\n@0\nM=M+1"
            self.bool_count += 1
        elif command == "eq":
            asm_command += f"@0\nM=M-1\nA=M\nD=M\n@0\nM=M-1\n@0\nA=M\nD=M-D\n@BOOL{self.bool_count}\nD;JEQ\n@0\nA=M\nM=0\n@ENDBOOL{self.bool_count}\n0;JMP\n(BOOL{self.bool_count})\n@0\nA=M\nM=-1\n(ENDBOOL{self.bool_count})\n@0\nM=M+1"
            self.bool_count += 1
        self.file.writelines(asm_command + "\n")
        self.file.flush()

    def write_command(self, command):
        self.file.writelines("\\\\" + command + "\n")
        self.file.flush()

    def _getSegment(self, segment):
        if segment == "local":
            return "1"
        elif segment == "argument":
            return "2"
        elif segment == "this":
            return "3"
        elif segment == "that":
            return "4"

    def writePushPop(self, command, segment, index):
        asm_command = ""
        if segment in ("local", "argument", "this", "that"):
            seg_symbol = self._getSegment(segment)
            if command == Parser.COMMAND.PUSH:
                asm_command += f"@{seg_symbol}\nD=M\n"  # A={'A+'+str(index) if index != 0 else 'A'}\nD=M\n@0\nA=A+1\nM=D\n"
                if index > 1:
                    asm_command += f"@{index}\nA=D+A\n"
                elif index == 1:
                    asm_command += "A=D+1\n"
                elif index == 0:
                    asm_command += "A=D"
                asm_command += "\nD=M\n@0\nA=M\nM=D\n@0\nM=M+1\n"
            elif command == Parser.COMMAND.POP:
                # asm_command += f"@0\nA=M-1\nD=M\n@0\nM=M-1\n@{seg_symbol}\n"  # A={'A+'+str(index) if index != 0 else 'A'}\nM=D\n"
                # if index > 1:
                #     asm_command += f"D=M\n@{index}\nA=D+A"
                # elif index == 1:
                #     asm_command += "A=M+1\n"
                # elif index == 0:
                #     asm_command += "A=M\n"
                # asm_command += "M=D\n"
                asm_command += f"@{seg_symbol}\n"
                if index > 1:
                    asm_command += f"D=M\n@{index}\nD=D+A\n@13\nM=D\n"
                elif index == 1:
                    asm_command += "D=M+1\n@13\nM=D\n"
                elif index == 0:
                    asm_command += "D=M\n@13\nM=D\n"
                asm_command += "@0\nA=M-1\nD=M\n@0\nM=M-1\n@13\nA=M\nM=D\n"
        elif segment == "constant":
            asm_command += f"@{index}\nD=A\n@0\nA=M\nM=D\n@0\nM=M+1\n"
        elif segment == "temp":
            if command == Parser.COMMAND.PUSH:
                asm_command += f"@{5 + index}\nD=M\n@0\nA=M\nM=D\n@0\nM=M+1\n"
            elif command == Parser.COMMAND.POP:
                asm_command += f"@0\nA=M-1\nD=M\n@0\nM=M-1\n@{5 + index}\nM=D\n"
        elif segment == "pointer":
            seg = "3" if index == 0 else "4"
            if command == Parser.COMMAND.PUSH:
                asm_command += f"@{seg}\nD=M\n@0\nA=M\nM=D\n@0\nM=M+1\n"
            elif command == Parser.COMMAND.POP:
                asm_command += f"@0\nA=M-1\nD=M\n@0\nM=M-1\n@{seg}\nM=D\n"
        elif segment == "static":
            if self.static_mapping[index] == 0:
                self.static_mapping[index] = self.static_idx
                self.static_idx += 1
            seg = self.static_mapping[index]
            if command == Parser.COMMAND.PUSH:
                asm_command += f"@{seg}\nD=M\n@0\nA=M\nM=D\n@0\nM=M+1\n"
            elif command == Parser.COMMAND.POP:
                asm_command += f"@0\nA=M-1\nD=M\n@0\nM=M-1\n@{seg}\nM=D\n"
        self.file.writelines(asm_command + "\n")
        self.file.flush()

    def close(self):
        self.file.close()


"""
parser = Parser(
    "/home/art3mis/Vault/my_works/nand2tetris/projects/07/MemoryAccess/PointerTest/BasicTest.vm"
)
vm_codes = parser.parseVMCode()
print(vm_codes)
writer = CodeWriter(
    "/home/art3mis/Vault/my_works/nand2tetris/projects/07/MemoryAccess/BasicTest/BasicTest.asm"
)
for type, arg1, arg2 in vm_codes:
    if type == Parser.COMMAND.ARITHMETIC:
        # writer.write_command(arg1)
        writer.writeArithmetic(arg1)
    elif type == Parser.COMMAND.POP or type == Parser.COMMAND.PUSH:
        # writer.write_command(str(type) + " " + arg1 + " " + str(arg2))
        writer.writePushPop(type, arg1, arg2)
writer.close()
"""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"USAGE: {sys.argv[0]} <PATH_OF_VM_FILE> (? DEBUG)")
    else:
        src_file = sys.argv[1]
        target_file = src_file.replace(".vm", ".asm")
        debug = False
        if len(sys.argv) == 3:
            debug = True
            target_file = src_file.replace(".vm", ".debug")

        parser = Parser(src_file)
        writer = CodeWriter(target_file)

        vm_codes = parser.parseVMCode()

        for type, arg1, arg2 in vm_codes:
            if type == Parser.COMMAND.ARITHMETIC:
                if debug:
                    writer.write_command(arg1)
                writer.writeArithmetic(arg1)
            elif type == Parser.COMMAND.POP or type == Parser.COMMAND.PUSH:
                if debug:
                    writer.write_command(str(type) + " " + arg1 + " " + str(arg2))
                writer.writePushPop(type, arg1, arg2)
        writer.close()
