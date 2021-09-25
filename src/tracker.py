import src.urlencode as urlencode
import src.bencode as bencode
import urllib.request


class Tracker:
    def __init__(self, info_hash, port, compact=1, announce=""):
        self.compact = compact
        self.peer_id = "-00abda00f000000000-"
        self.announce = announce
        info_hash = bytes.fromhex(info_hash)
        self.infoHash_urlencoded = urlencode.encode(info_hash)
        self.port = port

    def sendReq(self, uploaded, downloaded, left, event):
        req_url = self.announce
        req_url += "?"

        req_url += ("info_hash" + "=" + self.infoHash_urlencoded + "&")
        req_url += ("peer_id" + "=" + self.peer_id + "&")
        req_url += ("port" + "=" + str(self.port) + "&")
        req_url += ("uploaded" + "=" + str(uploaded) + "&")
        req_url += ("downloaded" + "=" + str(downloaded) + "&")
        req_url += ("left" + "=" + str(left) + "&")
        req_url += ("compact" + "=" + str(self.compact))

        if event != "":
            req_url += ("&event" + "=" + event)

        # print(req_url)
        contents = urllib.request.urlopen(req_url).read()
        self.track_resp = bencode.decode(contents)

    def getResponse(self):
        return self.track_resp

    def isSuccess(self):
        if "failure reason" in self.track_resp:
            print("track send error message")
            print(self.track_resp["failure reason"])
            return False
        return True

    def getInterval(self):
        return self.track_resp['interval']

    def getTracker_id(self):
        return self.track_resp.get('tracker id')

    def getComplete(self):
        return self.track_resp.get('complete')

    def getIncomplete(self):
        return self.track_resp.get('incomplete')

    def getPeerList(self):
        peers = self.track_resp['peers']
        retval = []
        for i in range(0, len(peers), 6):
            temp = []
            addr = []
            for j in range(i, i+4):
                addr.append(str(peers[j]))
            temp.append(".".join(addr))
            temp.append(str(int.from_bytes(peers[i+4:i+6], "big")))
            retval.append(temp)
        return retval
