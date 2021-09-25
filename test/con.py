import os
import sys
import time
import datetime
import asyncio
from _thread import start_new_thread
from threading import Thread, Event
class client:
    def __init__(self):
        self.peerList = [1,2,3,4]
    
    def __str__(self):
        return str(self.peerList)

async def listen(c):
    for i in range(20):
        print(datetime.datetime.now())
        print(c)
        await asyncio.sleep(1)

async def modify(target,step,interval,index):
    for i in range(5):
        target.peerList[index] += step
        await asyncio.sleep(interval)



async def main():
    c = client()
    # task1 = asyncio.create_task(listen(c))
    # task2 = asyncio.current_task(modify(c,1,2,0))
    # task3 = asyncio.current_task(modify(c,4,2,1))
    # task4 = asyncio.current_task(modify(c,3,3,3))

    # await task1
    # await task2
    # await task3
    # await task4
    await asyncio.gather(
        listen(c),modify(c,2,2,1)

    )

asyncio.run(main())

def main():
    c = client()
    e = Event()
    t1 = Thread(target=listen,args=(c,))
    t2 = Thread(target=modify,args=(c,2,2,1))
    t1.start()
    t2.start()
    # while True:
    #     time.sleep(10)

# main()
