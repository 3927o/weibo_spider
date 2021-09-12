import logging
import re
import csv


path = r"G:\Documents\Tencent Files\1624497311\FileRecv\Tweetsall0629.csv"


def test():
    f1 = open(path, encoding="utf-8")
    f2 = open("test.txt", "w", encoding="utf-8")
    for line in f1.readlines():
        content = ",".join(line.split(",")[:-1])
        content = content + "\n"
        f2.write(content)

    f1.close()
    f2.close()


if __name__ == '__main__':
    test()
    logging.info("test")
