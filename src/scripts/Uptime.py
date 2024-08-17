import requests
import threading
import json


def partition(lst, n):
    division = len(lst) / n
    return [lst[round(division * i):round(division * (i + 1))] for i in range(n)]

def ranges(N_start, N_end, nb):
    return ["{},{}".format(r.start, r.stop) for r in partition(range(N_start, N_end), nb)]

class Calculator:
    def __init__(self, rpc: str, sess_csv: str = None, sync: bool = False, valid_csv: str = "validator_list.csv"):
        self.__rpc = rpc
        self.__sess_csv = sess_csv
        self.__valid_csv = valid_csv
        self.__sync = sync
        self.__session = self.__resume_or_start_anew()
        self.__worker_mutex = threading.Lock()
        self.set_threads(10)
        self.set_checkpoint_step(10000)
    
    # If sess_csv is present, session is resumed.
    # If valid_csv is present, new session is created related to that valset.
    # Sync flag enables implicit sync of target height to current height instead of asking for a custom one/resuming session one
    def __resume_or_start_anew(self):
        if self.__sess_csv:
            session = self.__load_session()
            if self.__sync:
                session[2] = self.__fetch_cur_height()
        else:
            print("Starting new uptime session...")
            addrss = self.__load_addresses()
            start_h = int(input("Start height for this session: "))
            end_h = self.__fetch_cur_height() if self.__sync else int(input("End height for this session: "))
            self.__validate_heights(start_h, end_h)
            uptimes = {}
            for hexaddr in addrss:
                uptimes[hexaddr] = 0
            session = [start_h, start_h, end_h, uptimes]
        return session

    
    def __validate_heights(self, start_h, end_h):
        if start_h >= end_h:
            raise ValueError("Start height must be lower than end height")
        elif not self.__fetch_signatures_at_height(start_h):
            raise ValueError("Start height is not queriable with provided RPC.\nPlease set an RPC with adequate pruning setting.")

    def __monitoring_loop(self):
        print(f"Started/resumed at height {self.__session[1]}")
        while(self.__session[1] < self.__session[2]):
            workers = []
            if(self.__session[2] - self.__session[1] < self.__checkpoint_every):
                self.__checkpoint_every = self.__session[2] - self.__session[1]
            per_worker = self.__checkpoint_every // self.__n_threads
            remainder = self.__checkpoint_every % self.__n_threads
            iter_start = self.__session[1] + 1
            iter_end = self.__session[1] + self.__checkpoint_every + 1
            workerRanges = ranges(iter_start, iter_end, self.__n_threads)
            for r in workerRanges:
                parsed = r.split(",")
                parsed_range = range(int(parsed[0]), int(parsed[1]))
                t = threading.Thread(target = self.__chunk_worker_thread, args = (parsed_range,))
                workers.append(t)
            for t in workers:
                t.start()
            for t in workers:
                t.join()
            self.__session[1] = iter_end - 1
            print(f"Saving checkpoint at height {self.__session[1]}...")
            self.__save_sess_to_csv()
        print(f"Saving completed session at height {self.__session[1]}...")
        self.__save_sess_to_csv()
    
    def start_loop(self):
        self.__monitoring_loop()


    def set_threads(self, n_threads: int):
        if n_threads <= 0:
            raise ValueError("Can set only positive and nonzero values")
        self.__n_threads = n_threads
    

    def set_checkpoint_step(self, checkpoint_every: int):
        if checkpoint_every <= 0:
            raise ValueError("Can set only positive and nonzero values")
        self.__checkpoint_every = checkpoint_every


    def __load_session(self) -> [int,int,int,dict]:
        uptimes = {}
        with open(self.__sess_csv, "r", encoding='utf-8') as f:
            lines = f.readlines()
        heights = lines[0].split(";")
        start_h = int(heights[0])
        reached_h = int(heights[1])
        target_h = int(heights[2])
        for l in lines[1:]:
            parsed = l.split(";")
            uptimes[parsed[0]] = int(parsed[1])
        return [start_h, reached_h, target_h, uptimes]


    def __load_addresses(self):
        addresses = []
        with open(self.__valid_csv, "r", encoding='utf-8') as f:
            lines = f.readlines()
        for l in lines:
            addresses.append(l.split(";")[2])
        return addresses

    def __save_sess_to_csv(self):
        fname = self.__sess_csv if self.__sess_csv else "session.csv"
        with open(fname, "w", encoding='utf-8') as f:
            f.write(f"{self.__session[0]};{self.__session[1]};{self.__session[2]}\n")
            for hexaddr in self.__session[3]:
                f.write(f"{hexaddr};{self.__session[3][hexaddr]}\n")
        return True

    def __fetch_cur_height(self):
        r = requests.get(f"{self.__rpc}/commit")
        json_res = json.loads(r.text)
        return int(json_res['result']['signed_header']['header']['height'])


    def __fetch_signatures_at_height(self, height: int) -> [dict]:
        r = requests.get(f"{self.__rpc}/commit?height={height}")
        json_res = json.loads(r.text)
        cond = 'result' in json_res and 'signed_header' in json_res['result'] and 'commit' in json_res['result']['signed_header'] and 'signatures' in json_res['result']['signed_header']['commit']
        return json_res['result']['signed_header']['commit']['signatures'] if cond else []


    def __chunk_worker_thread(self, worker_range: range):
        for i in worker_range:
            sigs = self.__fetch_signatures_at_height(i)
            for s in sigs:
                if s['validator_address'] in self.__session[3]:
                    self.__worker_mutex.acquire()
                    self.__session[3][s['validator_address']] += 1
                    self.__worker_mutex.release()


if __name__ == "__main__":
    UptCalc = Calculator("https://rpc.explorebitsong.com")
    UptCalc.start_loop()