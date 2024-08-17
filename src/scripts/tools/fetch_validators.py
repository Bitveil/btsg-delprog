import base64
import requests
import json
from bip_utils import Bech32Encoder, Bech32Decoder


def fetchValidators(api_addr: str) -> [dict]:
    r = requests.get(f"{api_addr}/staking/validators")
    json_res = json.loads(r.text)
    return json_res['result'] if 'result' in json_res else []

def resolveAddress(rpc_addr: str, api_validators: [dict]) -> [dict]:
    r = requests.get(f"{rpc_addr}/validators?per_page=100")
    json_res = json.loads(r.text)
    if 'result' in json_res and 'validators' in json_res['result']:
        rpc_validators = json_res['result']['validators']
        for v_api in api_validators:
            for v_rpc in rpc_validators:
                if(v_rpc['pub_key']['value'] == v_api['consensus_pubkey']['value']):
                    v_api['address'] = v_rpc['address']
                    break
        return api_validators

def resolveWallets(valdicts: [dict]) -> [dict]:
    for v in valdicts:
        wallet = Bech32Encoder.Encode('bitsong', Bech32Decoder.Decode('bitsongvaloper', v['operator_address']))
        v['wallet'] = wallet
    return valdicts

def saveToCsv(valdicts: [dict]) -> bool:
    with open("validator_list.csv", "w+", encoding='utf-8') as f:
        for v in valdicts:
            v_desc = v['description']
            line = []
            line.append(v['operator_address'])
            line.append(v['wallet'])
            line.append(v['address'])
            line.append(v_desc['moniker'])
            if('details' in v_desc):
                line.append(v_desc['details'].replace("\n",""))
            if('website' in v_desc):
                line.append(v_desc['website'])
            f.write(";".join(line)+"\n")
           
    return True

if __name__ == "__main__":
    validators = resolveWallets(resolveAddress("https://rpc.bitsong.forbole.com", fetchValidators("https://api.bitsong.quokkastake.io")))
    saveToCsv(validators)
