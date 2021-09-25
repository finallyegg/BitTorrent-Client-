import asyncio
from src.message import MessageUtil
from enum import Enum
from src.config import DEFAULT_CHOKE_RETRY
import time


class Connection_STATUS(Enum):
    FREE = 1
    WORKING = 2


class Connection:
    def __init__(self, onGetNextPeer, cid, info_hash, onRequest, pieceList_length, onUpdateBitfield, onHave, piece_length, onSuccessPiece, lastIdx, lastLength):
        self.hasBitfield = False

        self.id = cid
        self.info_hash = info_hash

        self.bitfield = None
        self.bitfield_decoded = [0 for _ in range(pieceList_length)]

        self.piece_length = piece_length
        self.pieceIdx = 0
        self.choked = True
        self.chokedRetry = DEFAULT_CHOKE_RETRY

        self.onGetNextPeer = onGetNextPeer
        self.onRequest = onRequest
        self.onUpdateBitfield = onUpdateBitfield
        self.onUpdateHave = onHave
        self.onSuccessPiece = onSuccessPiece

        self.pieceData = bytearray(piece_length)
        self.p_offset = 0

        self.reader = None
        self.writer = None

        self.staus = Connection_STATUS.FREE

        self.future = asyncio.ensure_future(self.run())

        self.queue = asyncio.Queue(maxsize=4)
        self.addr = None
        self.port = None

        self.lastIdx = lastIdx
        self.lastLength = lastLength

    async def run(self):
        msgutil = MessageUtil()

        self.addr, self.port = self.onGetNextPeer()

        self.connected = False
        while True:
            if self.queue.qsize() > 0:
                status = self.queue.get_nowait()
                if status == "stop":
                    print(self.id, "stoppeed")
                    self.reader.close()
                    self.writer.close()
                    return
                if status == "cancel":
                    msgutil.cancelMG(self.pieceIdx, self.p_offset)
            try:
                self.startTime = time.time()
                # if not connected to peer, try handshake ONLY
                if not self.connected:
                    print(self.id, ":", "Attempt to connect",
                          self.addr, self.port)
                    try:
                        self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(self.addr, self.port), timeout=5.0)
                    except asyncio.TimeoutError:
                        print("connection timeout")
                        self.resetConnection()
                        continue
                    self.connPrint("Connection success")

                    self.writer.write(msgutil.handshakeMSG(self.info_hash))
                    await self.writer.drain()
                    self.connPrint("HandShake Sent")

                    try:
                        handshake_resp = bytes()
                        handshake_resp = await self.recv(68)

                        self.connPrint("Recv handhsake from peer")
                        self.connPrint(str(handshake_resp))

                        # Validate infohash
                        valid_infoHash = handshake_resp[28:48] == bytes.fromhex(
                            self.info_hash)
                        if not valid_infoHash:
                            self.connPrint("WRONG info HASH")
                            self.resetConnection()
                            continue

                    except asyncio.TimeoutError:
                        print(self.id, ":", "failed to get handshake")
                        self.resetConnection()
                        continue
                    self.connected = True
                    # continue

                # CONNECTED to peer SEND INTERESTET MSG
                if self.hasBitfield:
                    if self.choked:
                        await asyncio.sleep(5)
                        if self.chokedRetry == 0:
                            print(self.id, "choke out")
                            self.resetConnection()
                            continue
                        else:
                            self.chokedRetry -= 1
                            self.writer.write(msgutil.insterestedMSG())
                            await self.writer.drain()
                            self.connPrint("SENT INSTEREST")

                    elif self.staus == Connection_STATUS.FREE:
                        nextIDX = self.getNextPIdx()
                        # print(self.id,"next P idx is ",nextIDX)
                        if nextIDX == -1:
                            print("CHANGE PEER")
                            self.resetConnection()
                            continue
                        else:
                            self.pieceIdx = nextIDX
                            if self.pieceIdx == self.lastIdx:
                                self.piece_length = self.lastLength
                                # print("On last")
                                # print("last length:", self.lastLength)
                            self.staus = Connection_STATUS.WORKING
                            continue

                    elif self.staus == Connection_STATUS.WORKING:
                        if self.pieceIdx == self.lastIdx:
                            self.writer.write(msgutil.requestMSG(
                                self.pieceIdx, self.p_offset, size=min(16384, self.lastLength-self.p_offset)))
                        else:
                            self.writer.write(msgutil.requestMSG(
                                self.pieceIdx, self.p_offset))

                        await self.writer.drain()
                        # print("send request", self.pieceIdx, self.p_offset)
                # else:
                #     self.writer.write(msgutil.insterestedMSG())
                #     await self.writer.drain()
                #     self.connPrint("SENT INSTEREST")

                # read until you cant
                buffer = await self.reading(self.reader)
                if len(buffer) == 0:
                    self.resetConnection()
                else:
                    self.parse(buffer)
            except (ConnectionResetError, ConnectionRefusedError) as e:
                print("Error", e)
                self.resetConnection()

    def getNextPIdx(self):
        ret = self.onRequest(self.id)
        self.p_offset = 0
        self.pieceData = bytearray(self.piece_length)
        if ret == self.lastIdx:
            self.pieceData = bytearray(self.lastLength)
        return ret

    async def recv(self, expectLength):
        temp = bytes()
        while len(temp) < expectLength:
            temp += await asyncio.wait_for(self.reader.read(expectLength - len(temp)), timeout=10.0)
        return temp

    def connPrint(self, msg):
        pass
        # print(self.id,":",msg)

    def resetConnection(self):
        print(self.id, "Reset Connection")
        self.addr, self.port = self.onGetNextPeer()
        print("new addr", self.addr, "port", self.port)
        self.connected = False
        self.p_offset = 0
        self.pieceData = bytearray(self.piece_length)
        self.bitfield = None
        self.bitfield_decoded = []
        self.staus == Connection_STATUS.FREE

        return self.addr, self.port

    async def reading(self, reader):
        buffer = bytes()
        try:
            length_raw = await self.recv(4)
            length = int.from_bytes(bytes=length_raw, byteorder="big")
            data_raw = await self.recv(length)
            buffer += length_raw
            buffer += data_raw
        except asyncio.TimeoutError:
            self.connPrint("Timeout when recving data from peer")
            await asyncio.sleep(1)
            return buffer
        return buffer

    def parse(self, buffer):
        it = 0
        header = bytes()
        while it < len(buffer):
            header = buffer[:5]
            it += 5
            msgutil = MessageUtil()
            dataLength, dataType = msgutil.parseType(header)

            if dataType == 5:  # bitfield:
                self.bitfield = buffer[it:it+dataLength - 1]
                it += dataLength - 1

                temp_bitfield_decoded = ""
                for i in range(len(self.bitfield)):
                    byte = self.bitfield[i:i+1]
                    temp_bitfield_decoded += format(
                        int(byte.hex(), base=16), "08b")
                self.bitfield_decoded = [
                    int(temp_bitfield_decoded[i]) for i in range(len(temp_bitfield_decoded))]
                self.onUpdateBitfield(
                    cid=self.id, newbitField=self.bitfield_decoded)
                self.hasBitfield = True

            elif dataType == 1:
                self.choked = False
                self.chokedRetry = DEFAULT_CHOKE_RETRY
                self.connPrint("unchoked")
            elif dataType == 0:
                self.choked = True
            elif dataType == 4:
                rcvPieceIdxBuffer = bytes()
                rcvPieceIdxBuffer = buffer[it:it+dataLength - 1]
                it += dataLength - 1

                idx = int.from_bytes(rcvPieceIdxBuffer, byteorder="big")
                self.bitfield_decoded[idx] = 1
                self.onUpdateHave(cid=self.id, idx=idx)
            elif dataType == 7:
                databuffer = bytes()
                databuffer = buffer[it:it+dataLength - 1]
                it += dataLength - 1

                self.endTime = time.time()

                idx = int.from_bytes(databuffer[0:4], byteorder="big")
                offset = int.from_bytes(databuffer[4:8], byteorder="big")
                block = databuffer[8:]
                self.pieceData[offset:offset + len(block)] = block
                self.p_offset = max(offset + len(block), self.p_offset)
                # print("ConnThread:",self.id,"index:",idx,str(self.p_offset/self.piece_length * 100) + "%",str(len(block)/1000//(self.endTime-self.startTime))+"kb/s","|||",self.p_offset,self.lastLength)
                if self.p_offset == self.piece_length or (idx == self.lastIdx and self.p_offset == self.lastLength):
                    print("-------", self.id, "Done piece",
                          self.pieceIdx, "----------")
                    result = self.onSuccessPiece(idx, bytes(self.pieceData))
                    if not result:
                        self.resetConnection()
                        return
                    self.staus = Connection_STATUS.FREE
                    self.pieceData = bytearray(self.piece_length)
                    self.p_offset = 0
                return
