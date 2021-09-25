# import torrent_parser as tp
# import sys
# data = tp.parse_torrent_file(sys.argv[1])
# # print(len(data['info']['pieces']))
# print(data)

class A:
    def __init__(self):
        self.arr = [1,2,3]

    
class B:
    def __init__(self,arr):
        self.arr = arr
        # print(arr)
    
    def p(self):
        print(self.arr)
a = A()
b = B(a.arr)
b.p()
a.arr[1] = 4
b.p()