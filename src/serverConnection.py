import asyncio
from src.message import MessageUtil
import time


class ServerConnection:
    def __init__(self, reader, writer, info_hash, blockStatus, fileBuffer):

        self.info_hash = info_hash

        self.blockstatus = blockStatus

        self.fileBuffer = fileBuffer

        self.reader = reader
        self.writer = writer

        self.addr = None
        self.port = None

        self.choking = True

        self.currentSpeed = 0

        self.future = asyncio.ensure_future(self.run())

        self.msgutil = MessageUtil()

    async def sendUnchoke(self):
        self.choking = False
        self.writer.write(self.msgutil.unchokeMSG())
        await self.writer.drain()

    async def sendchoke(self):
        self.choking = True
        self.writer.write(self.msgutil.chokeMSG())
        await self.writer.drain()

    async def run(self):
        msgutil = MessageUtil()

        try:
            startTime = time.time()
            handshake = await self.recv(68)
            valid_infoHash = handshake[28:48] == bytes.fromhex(self.info_hash)
            endTime = time.time()
            self.currentSpeed = 68/(endTime-startTime)
            print("speed is ", self.currentSpeed)

            # print(self.reader._transport.get_extra_info('peername'))
            if not valid_infoHash:
                print("not valid info hash")
                self.writer.close()
                return

            self.writer.write(msgutil.handshakeMSG(self.info_hash))
            await self.writer.drain()

            bitfieldArr = self.blockstatus[:]
            for i in range(len(bitfieldArr)):
                if bitfieldArr[i] == 2:
                    bitfieldArr[i] = 1
                else:
                    bitfieldArr[i] = 0
            print(bitfieldArr)
            self.writer.write(msgutil.bitfieldMSG(bitfieldArr))
            await self.writer.drain()

            while True:
                buffer = await self.reading(self.reader)
                # buffer = await self.reader.read(100000)
                print(len(buffer), buffer)
                header = bytes()

                header = buffer[:5]
                msgutil = MessageUtil()
                dataLength, dataType = msgutil.parseType(header)
                print("dataType", dataType, "Length", dataLength)
                if dataType == 2:
                    # self.choking = False
                    # self.writer.write(msgutil.unchokeMSG())
                    # await self.writer.drain()
                    continue
                elif dataType == 6:
                    index = int.from_bytes(buffer[5:9], byteorder="big")
                    begin = int.from_bytes(buffer[9:13], byteorder="big")
                    length = int.from_bytes(buffer[13:17], byteorder="big")
                    print("recv request", index, begin, length)
                    if self.blockstatus[index] != 2:
                        continue

                    tempLength = len(self.fileBuffer.data[index]) - begin
                    if tempLength < length:
                        print("request more than we have")
                        continue

                    msg = msgutil.pieceMSG(
                        index, begin, self.fileBuffer.data[index][begin:begin+length])
                    self.writer.write(msg)
                    await self.writer.drain()
                else:
                    continue

        except (asyncio.TimeoutError, ConnectionResetError, ConnectionRefusedError):
            print("Server Timeout")
            self.writer.close()
            return

    def connPrint(self, msg):
        pass
        # print(self.id,":",msg)

    async def recv(self, expectLength):
        temp = bytes()
        while len(temp) < expectLength:
            temp += await asyncio.wait_for(self.reader.read(expectLength - len(temp)), timeout=120.0)
        return temp

    async def reading(self, reader):
        buffer = bytes()
        length_raw = await self.recv(4)
        length = int.from_bytes(bytes=length_raw, byteorder="big")
        data_raw = await self.recv(length)
        buffer += length_raw
        buffer += data_raw
        return buffer
