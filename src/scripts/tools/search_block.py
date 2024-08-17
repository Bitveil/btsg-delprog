import requests
import time
import json
from datetime import datetime, timedelta, timezone

# Adjust for conversion localtime-gmt
def fetchCurrentHeight(rpc_addr: str) -> int:
    r = requests.get(f"{rpc_addr}/commit")
    json_res = json.loads(r.text)
    return int(json_res['result']['signed_header']['header']['height'])

def fetchBlockTimestamp(rpc_addr: str, block_height: int) -> int:
    r = requests.get(f"{rpc_addr}/block?height={block_height}")
    r_json = json.loads(r.text)
    return -1 if 'error' in r_json else datetime.timestamp(datetime.fromisoformat(r_json['result']['block']['header']['time']))

def checkHeightRange(rpc_addr: str, start_h: int, end_h: int, date_tstamp: int) -> (str,bool):
    if(start_h >= end_h):
        return ("Start height must be lower than end height!", False)
    
    start_tstamp = fetchBlockTimestamp(rpc_addr, start_h)
    end_tstamp = fetchBlockTimestamp(rpc_addr, end_h)
    if(start_tstamp < 0 or end_tstamp < 0):
        return ("Error in JSON response", False)
    return ("Date is in range", True) if date_tstamp >= start_tstamp and date_tstamp < end_tstamp else ("Date is not in range! Input a higher or lower height", False)

#Add check as decorator
def binarySearch_d2h(rpc_addr: str, start_h: int, end_h: int, date_tstamp: int) -> int:
    if(end_h == start_h + 1):
        return start_h
    else:
        cur_h = (start_h + end_h) // 2
        cur_tstamp = fetchBlockTimestamp(rpc_addr, cur_h)

        if cur_tstamp < 0:
            return cur_tstamp
        if(date_tstamp > cur_tstamp):
            return binarySearch_d2h(rpc_addr, cur_h, end_h, date_tstamp)
        else:
            return binarySearch_d2h(rpc_addr, start_h, cur_h, date_tstamp)

if __name__ == "__main__":
    rpc = "https://rpc.explorebitsong.com/"
    start_height = 2966151
    end_height = fetchCurrentHeight(rpc)
    datestr = input("Date to search (%dd-%mm-%yy): ")
    datestr += " 00:00:00-00:00"
    # Gotta add GMT difference, since timestamp on-chain is GMT-format, datetime is local time.
    date_tstamp = int(datetime.timestamp(datetime.strptime(datestr,"%d-%m-%y %H:%M:%S%z")))
    check = checkHeightRange(rpc, start_height, end_height, date_tstamp)
    if(check[1]):
        blockFound = binarySearch_d2h(rpc, start_height, end_height, date_tstamp)
        if blockFound > 0:
            print(f"First block height before date: {blockFound}")
        else:
            print("Binary search stopped due to json error in one of the requests.")
    else:
        print(check[0])
    