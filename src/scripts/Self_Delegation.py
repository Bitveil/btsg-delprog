import requests
import json

class Evaluator:
    def __init__(self, rpc: str, api: str, valid_csv: str = "validator_list.csv"):
        self.__api = api
        self.__rpc = rpc
        self.__valid_csv = valid_csv
        self.__vals_data = self.__load_vals_data()
        self.__fetch_vps()
        self.__evaluate_ratios()
        self.__save_ratios()

    def __load_vals_data(self):
        vals = []
        vals_data = {}
        with open(self.__valid_csv, "r", encoding='utf-8') as f:
            lines = f.readlines()
        for l in lines:
            vals.append(l.split(";"))
        for v in vals:
            hexaddr = v[2]
            vals_data[hexaddr] = {}
            vals_data[hexaddr]['valoper'] = v[0]
            vals_data[hexaddr]['wallet'] = v[1]
            if('bitsong' in v[-1] and (len(v[-1].strip()) == 46 or "," in v[-1])):
                vals_data[hexaddr]['extra_wallets'] = [x.strip() for x in v[-1].split(",")]
        return vals_data

    def __fetch_vps(self, per_page: int = 100):
        res = []
        req_str = f"{self.__rpc}/validators?per_page={per_page}"
        r = requests.get(req_str)
        json_res = json.loads(r.text)
        n_pages = -(int(json_res['result']['total']) // -per_page)
        for i in range(n_pages):
            r = requests.get(f"{req_str}&page={i+1}")
            json_res = json.loads(r.text)
            for v in json_res['result']['validators']:
                #print(v['address'])
                if v['address'] in self.__vals_data:
                    self.__vals_data[v['address']]['vp'] = int(v['voting_power'])
                    continue

    def __evaluate_ratios(self):
        for vd in self.__vals_data:
            self.__vals_data[vd]['self_delegated'] = 0
            self.__vals_data[vd]['ratio'] = 0
            r = requests.get(f"{self.__api}/cosmos/staking/v1beta1/validators/{self.__vals_data[vd]['valoper']}/delegations")
            json_res = json.loads(r.text)
            for delg in json_res['delegation_responses']:
                if delg['delegation']['delegator_address'] == self.__vals_data[vd]['wallet'] or ('extra_wallets' in self.__vals_data[vd] and delg['delegation']['delegator_address'] in self.__vals_data[vd]['extra_wallets']):
                    self.__vals_data[vd]['self_delegated'] = self.__vals_data[vd]['self_delegated'] + int(delg['balance']['amount']) * (10**-6)
                    self.__vals_data[vd]['ratio'] = self.__vals_data[vd]['self_delegated'] / self.__vals_data[vd]['vp']
   
    def __save_ratios(self, savefile = "selfdels.csv"):
        with open(savefile, "w") as f:
            for vd in self.__vals_data:
                csv_data = (f"{vd};"
                            f"{self.__vals_data[vd]['vp']};"
                            f"{self.__vals_data[vd]['self_delegated']};"
                            f"{'{:f}'.format(self.__vals_data[vd]['ratio'])}\n")
                f.write(csv_data)


if __name__ == "__main__":
    DelgEvaluator = Evaluator("https://rpc.explorebitsong.com", "https://api.bitsong.quokkastake.io")
