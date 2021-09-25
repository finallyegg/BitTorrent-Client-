import struct


class MessageUtil:

    def __init__(self):
        self.peer_id = str.encode("-qq0000000000000000-")

    def handshakeMSG(self, info_hash):
        pstrlen = struct.pack("!b", 19)
        pstr = str.encode("BitTorrent protocol")
        reverse = bytes.fromhex("0000000000000000")
        return pstrlen + pstr + reverse + bytes.fromhex(info_hash) + self.peer_id

    def keepAliveMSG(self):
        return struct.pack("!I", 0)

    def chokeMSG(self):
        return struct.pack("!I", 1) + struct.pack("!b", 0)

    def unchokeMSG(self):
        return struct.pack("!I", 1) + struct.pack("!b", 1)

    def insterestedMSG(self):
        return struct.pack("!I", 1) + struct.pack("!b", 2)

    def notInsterestedMSG(self):
        return struct.pack("!I", 1) + struct.pack("!b", 3)

    def haveMSG(self, piece_index):
        return struct.pack("!I", 5) + struct.pack("!b", 4) + struct.pack("!I", piece_index)

    def bitfieldMSG(self, bitfieldArr):
        temp = bitfieldArr[:]
        reminder = len(temp) % 8
        for i in range(8-reminder):
            temp.append(0)
        byte = bytes()
        for i in range(0, len(temp), 8):
            temp_byte = 0
            temp_byte = temp_byte | temp[i]

            for j in range(1, 8):
                temp_byte = temp_byte << 1
                temp_byte = temp_byte | temp[i+j]
            byte += bytes([temp_byte])
        return struct.pack("!I", len(byte)+1) + struct.pack("!b", 5) + byte

    def requestMSG(self, index, begin, size=16384):
        return struct.pack("!I", 13) + struct.pack("!b", 6) + struct.pack("!I", index) + struct.pack("!I", begin) + struct.pack("!I", size)

    def pieceMSG(self, index, begin, payload):
        if type(payload) == str:
            payload = bytes(payload, encoding="utf-8")
        return struct.pack("!I", 9+len(payload)) + struct.pack("!b", 7) + struct.pack("!I", index) + struct.pack("!I", begin) + payload

    def cancelMG(self, index, begin):
        return struct.pack("!I", 13) + struct.pack("!b", 8) + struct.pack("!I", index) + struct.pack("!I", begin) + struct.pack("!I", 16384)

    def portMSG(self, port):
        return struct.pack("!I", 3) + struct.pack("!b", 9) + struct.pack("!H", port)

    def parseType(self, data_raw):
        return [int.from_bytes(data_raw[0:4], byteorder="big"), int.from_bytes(data_raw[4:5], byteorder="big")]
