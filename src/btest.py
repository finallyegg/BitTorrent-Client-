import bencode
a = bencode.encode({"1": bytes.fromhex("deadbeef")})
print(a)
print(type(a))
