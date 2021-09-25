import src.bencode as bencode
import hashlib


class Torrent:
    def __init__(self, filepath):
        torrent_f = open(filepath, 'rb')
        self.metainfo = bencode.decode(torrent_f.read())

    def announce(self):
        return self.metainfo['announce']

    def info(self):
        return self.metainfo['info']

    def infoHash(self):
        return hashlib.sha1(bencode.encode(self.metainfo['info'])).hexdigest()

    def isSingleFile(self):
        info = self.metainfo['info']
        return not "files" in info

    def piece_length(self):
        return self.metainfo['info']['piece length']

    def pieceList(self):
        retval = []
        pieces = self.metainfo['info']['pieces']
        for i in range(0, len(pieces), 20):
            piece_byte = pieces[i:i+20]
            retval.append(piece_byte)
        return retval

    def singleFileName(self):
        return self.metainfo['info']['name']

    def singleFileSize(self):
        return self.metainfo['info']['length']

    def multiFiles(self):
        return self.metainfo['info']['files']
