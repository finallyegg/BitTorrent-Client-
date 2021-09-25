import bencode

f = open("l1","wb")
d1 = {4:bytes.fromhex("deadbeef")}

f.write(bencode.encode(d1))
f.close()

def appendToFile(filename):
    f = open(filename,"wb")
    temp = f.read()
    print(temp[-1] == "e")

appendToFile(l1)


