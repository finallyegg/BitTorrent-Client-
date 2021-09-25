import signal
import random
import hashlib
from src.serverConnection import ServerConnection
from src.config import MAX_CONNECTION
import heapq
import datetime
from src.cache_file import Cache_file
from src.connection import Connection
from src.message import MessageUtil
from src.tracker import Tracker
from src.torrent import Torrent
import sys
import asyncio
import ssl
import random
ssl._create_default_https_context = ssl._create_unverified_context


class Client:

    def __init__(self, torrentFileName):
        self.completed = False
        self.event = "started"

        self.torrent = Torrent(torrentFileName)
        self.info_hash = self.torrent.infoHash()
        self.blockHashList = self.torrent.pieceList()
        self.piece_length = self.torrent.piece_length()

        self.isSingleFile = self.torrent.isSingleFile()

        self.totalSizeinBytes = 0
        if self.isSingleFile:
            self.totalSizeinBytes = self.torrent.singleFileSize()
        else:
            self.files = self.torrent.metainfo['info']['files']
            for temp_fileDict in self.files:
                self.totalSizeinBytes += temp_fileDict['length']

        self.fileBuffer = None

        self.uploaded = 0
        self.downloaded = 0

        self.lastIdx = len(self.blockHashList) - 1
        self.lastLength = self.totalSizeinBytes - \
            self.piece_length * (len(self.blockHashList) - 1)

        # self.lock = asyncio.Lock()
        self.downloadedSet = set()
        self.pL_inUse = []

        self.bitField = [[] for _ in range(MAX_CONNECTION)]
        for i in range(MAX_CONNECTION):
            self.bitField[i] = [0 for _ in range(len(self.blockHashList))]

        self.blockStatus = [0 for _ in range(len(self.blockHashList))]

        self.rareList = []  # rarest item first
        self.rareMap = {}
        for i in range(len(self.blockHashList)):
            self.rareMap[i] = 0

        if self.isSingleFile:
            temp_file = Cache_file(path=[self.torrent.singleFileName()], size=self.torrent.singleFileSize(), data=[
                                   bytes() for _ in range(len(self.blockHashList))], isSingle=True, verifyHash=self.verifyHash)
            self.fileBuffer = temp_file
            self.left = self.totalSizeinBytes
            having = self.fileBuffer.getDownloadedList()
            for i in having:
                self.downloadedSet.add(i)
                self.blockStatus[i] = 2
                if i == self.lastIdx:
                    continue
                self.downloaded += self.piece_length
                self.left -= self.piece_length
        else:
            temp_file = Cache_file(path=[self.info_hash], size=self.totalSizeinBytes, data=[bytes(
            ) for _ in range(len(self.blockHashList))], isSingle=False, verifyHash=self.verifyHash)
            self.fileBuffer = temp_file
            self.left = self.totalSizeinBytes
            having = temp_file.getDownloadedList()
            for i in having:
                self.downloadedSet.add(i)
                self.blockStatus[i] = 2
                if i == self.lastIdx:
                    continue
                self.downloaded += self.piece_length
                self.left -= self.piece_length

        if len(self.downloadedSet) == len(self.blockHashList):
            self.completed = True
            self.downloaded = self.totalSizeinBytes
            self.left = 0
            self.event = "completed"

        self.tracker = Tracker(info_hash=self.info_hash,
                               port=60683, announce=self.torrent.announce())
        self.tracker.sendReq(
            uploaded=self.uploaded, downloaded=self.downloaded, left=self.left, event=self.event)
        self.peerListPool = self.tracker.getPeerList()
        self.interval = self.tracker.getInterval()

        self.calRareList()
        self.endgame = False

        self.connections = []

        self.clientsConnections = []

    async def start(self):
        # print(self.piece_length,self.totalSizeinBytes,len(self.blockHashList))
        if self.completed:
            return

        for i in range(MAX_CONNECTION):
            connection = Connection(onGetNextPeer=self.getNextPeer, cid=i, info_hash=self.info_hash,
                                    onRequest=self.request, pieceList_length=len(self.blockHashList), onUpdateBitfield=self.onUpdateBitfield, onHave=self.onUpdateHave,
                                    piece_length=self.piece_length, onSuccessPiece=self.onSuccessPiece, lastIdx=self.lastIdx, lastLength=self.lastLength)
            self.connections.append(connection)
            # await connection.run()

        while True:
            await asyncio.sleep(self.interval)
            self.tracker.sendReq(
                uploaded=self.uploaded, downloaded=self.downloaded, left=self.left, event="")
            self.peerListPool = self.tracker.getPeerList()
            self.pL_inUse = []

            if self.completed:
                return

    def signal_handler(self, sig, frame):
        print('You pressed Ctrl+C!')
        self.tracker.sendReq(
            uploaded=self.uploaded, downloaded=self.downloaded, left=self.left, event="stopped")
        sys.exit(0)

    def getNextPeer(self):
        while len(self.peerListPool) <= 0:
            print("NO REFRESH PEER")
            # os.sleep(6)
            self.tracker.sendReq(
                uploaded=self.uploaded, downloaded=self.downloaded, left=self.left, event="")
            self.peerListPool = self.tracker.getPeerList()
            self.pL_inUse = []

        peer = random.choice(self.peerListPool)
        self.peerListPool.remove(peer)
        self.pL_inUse.append(peer)
        return peer

    def calRareList(self):
        temp = [k for k, v in sorted(self.rareMap.items(), key=lambda x:x[1])]
        self.rareList = temp

    def request(self, cid):
        for i in range(len(self.rareList)):
            idx = self.rareList[i]
            if self.bitField[cid][idx] == 1 and (self.blockStatus[i] == 0 or (self.endgame and self.blockStatus == 1)):
                self.blockStatus[i] = 1
                return idx
        return -1

    def onUpdateBitfield(self, cid, newbitField):
        old = self.bitField[cid]
        self.bitField[cid] = newbitField[:]
        for i in range(len(old)):
            if old[i] == 0 and newbitField[i] == 1:
                self.rareMap[i] += 1
        self.calRareList()

    def onUpdateHave(self, cid, idx):
        self.bitField[cid][idx] = 1
        self.rareMap[idx] += 1
        self.calRareList()

    def onSuccessPiece(self, pieceIdx, payload):
        if self.blockStatus[pieceIdx] == 2:
            return True

        if self.verifyHash(pieceIdx, payload):
            self.blockStatus[pieceIdx] = 2
        else:
            self.blockStatus[pieceIdx] = 0
            print("Wrong piece")
            return False

        self.downloadedSet.add(pieceIdx)
        self.downloaded += len(payload)
        self.left -= len(payload)

        self.fileBuffer.onSuccessPiece(payload, pieceIdx)
        print(len(self.downloadedSet), "/", len(self.blockHashList))
        # trigger endgame

        if len(self.downloadedSet) / len(self.blockHashList) > 0.9:
            self.endgame = True

        return True

    async def checkFinish(self):

        while True:
            await asyncio.sleep(1)
            if len(self.downloadedSet) == len(self.blockHashList):
                self.left = 0
                self.downloaded = self.totalSizeinBytes
                self.tracker.sendReq(
                    uploaded=self.uploaded, downloaded=self.downloaded, left=self.left, event="completed")

                if self.isSingleFile:
                    self.fileBuffer.assembe()
                else:
                    fileSpec = []
                    for temp_fileDict in self.files:
                        fileSpec.append(
                            [temp_fileDict['length'], temp_fileDict['path']])
                    self.fileBuffer.assFile(self.piece_length, fileSpec)
                self.completed = True
                for conn in self.connections:
                    conn.queue.put_nowait("stop")
                return

    def verifyHash(self, pinx, payload):
        hashs = hashlib.sha1(payload).hexdigest()
        return hashs == self.blockHashList[pinx].hex()

    async def startServer(self):
        server = await asyncio.start_server(self.handleConn, port=6881)

        # signal.signal(signal.SIGINT, self.signal_handler)

        async with server:
            await server.serve_forever()

    async def ocu(self):
        while True:
            await asyncio.sleep(10)
            self.clientsConnections.sort(
                key=lambda x: x.currentSpeed, reverse=True)
            if len(self.clientsConnections) == 0:
                continue
            for i in range(len(self.clientsConnections)):
                con = self.clientsConnections[i]
                if i < 4:
                    if con.choking:
                        await con.sendUnchoke()
                else:
                    if not con.choking:
                        await con.sendchoke()

            print("send unchole")

            await asyncio.sleep(10)
            self.clientsConnections.sort(
                key=lambda x: x.currentSpeed, reverse=True)
            if len(self.clientsConnections) == 0:
                continue
            for i in range(len(self.clientsConnections)):
                con = self.clientsConnections[i]
                if i < 4:
                    if con.choking:
                        await con.sendUnchoke()
                else:
                    if not con.choking:
                        await con.sendchoke()

            print("send unchole")

            await asyncio.sleep(10)
            self.clientsConnections.sort(
                key=lambda x: x.currentSpeed, reverse=True)
            if len(self.clientsConnections) == 0:
                continue
            for i in range(len(self.clientsConnections)):
                con = self.clientsConnections[i]
                if i < 4:
                    if con.choking:
                        await con.sendUnchoke()
                else:
                    if not con.choking:
                        await con.sendchoke()

            print("send unchole")

            if len(self.clientsConnections) > 4:
                inx = random.randint(4, len(self.clientsConnections))
                await self.clientsConnections[i].sendUnchoke()

    async def handleConn(self, reader, writer):
        # print("Handle Connection")
        # print(self.fileBuffer.data[0][:16384])
        serverConnection = ServerConnection(
            reader, writer, self.info_hash, self.blockStatus, self.fileBuffer)
        self.clientsConnections.append(serverConnection)
        # pass


def run(torrentFileName):

    client = Client(torrentFileName=torrentFileName)
    # asyncio.run(client.start())
    # asyncio.run(client.startServer())
    loop = asyncio.get_event_loop()
    task = loop.create_task(client.start())
    task2 = loop.create_task(client.checkFinish())
    task3 = loop.create_task(client.startServer())
    task4 = loop.create_task(client.ocu())
    loop.run_until_complete(asyncio.gather(task, task2, task3))


# keep global piece list
# class connnection()
# multiple instances have shared variable

# class client
