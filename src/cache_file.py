import os
from pathlib import Path
import src.bencode as bencode
import hashlib


class Cache_file:
    def __init__(self, path, size, data, isSingle, verifyHash):
        self.filePathlist = path[:]
        self.fileSize = size
        self.data = data
        self.count = 0
        self.isSingle = isSingle
        self.path = ""
        self.name = path[-1]
        self.createTempDir()
        self.verifyHash = verifyHash

    def assembe(self):
        path = "./downloaded/"
        path += "/".join(self.filePathlist[:-1])
        Path(path).mkdir(parents=True, exist_ok=True)
        newFile = open(path + "/" + self.filePathlist[-1], "wb")
        newFile.close()

        if self.isSingle:
            # ss = path + "/" + self.filePathlist[-1]
            # print(ss)
            newFile = open(path + "/" + self.filePathlist[-1], "ab")
            for i in range(len(self.data)):
                if type(self.data[i]) == str:
                    self.data[i] = bytes(self.data[i], "utf-8")
                if not self.verifyHash(i, self.data[i]):
                    print("bad record")
                    exit(1)
                newFile.write(self.data[i])
            newFile.close()

            newFile = open(path + "/" + self.filePathlist[-1], "rb")
            print(hashlib.sha256(newFile.read()).hexdigest())
            newFile.close()
            print("finished writing")

    def assFile(self, plength, fileSpec):
        big = bytes()
        for e in self.data:
            if type(e) == str:
                e = bytes(e, "utf-8")
            big += e
        print("start dir")
        currentOffset = 0
        for file_tuple in fileSpec:
            length = file_tuple[0]
            pathlist = file_tuple[1]

            path = "./downloaded/"
            path += "/".join(pathlist[:-1])
            Path(path).mkdir(parents=True, exist_ok=True)
            newFile = open(path + "/" + pathlist[-1], "wb")
            newFile.write(big[currentOffset:currentOffset+length])
            newFile.close()
            currentOffset += length
        print("end dir")

    def onSuccessPiece(self, data, pIdx):
        self.count += 1
        self.data[pIdx] = data

        newFile = open(self.path+"/" + self.name+".temp", "r+b")
        fileSize = os.stat(self.path+"/" + self.name+".temp").st_size
        newFile.seek(fileSize-1)
        ret = bencode.encode({str(pIdx): data})
        ret = bytearray(ret)[1:-1]
        retval = bytes(ret) + b'e'
        newFile.write(retval)
        newFile.close()

    def getDownloadedList(self):
        try:
            temp_file = open(self.path+"/" + self.name+".temp", "rb")
            temp_dict = bencode.decode(temp_file.read())
            ret = []
            for k in temp_dict.keys():
                idx = int(k)
                if idx != -1:
                    self.count += 1
                    self.data[idx] = temp_dict[k]
                    ret.append(idx)
            return ret

        except (FileNotFoundError) as e:
            temp_file = open(self.path+"/" + self.name+".temp", "wb")
            temp_file.write(bencode.encode({"-1": 123}))
            temp_file.close()
            return []

    def createTempDir(self):
        self.path = "./downloaded/"
        self.path += "/".join(self.filePathlist[:-1])
        Path(self.path).mkdir(parents=True, exist_ok=True)
