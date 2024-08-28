from flask import Flask, request, render_template
from xrpl.constants import CryptoAlgorithm
from xrpl.clients import WebsocketClient, JsonRpcClient
from xrpl.transaction import autofill_and_sign, sign
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models import requests, Payment
from xrpl.wallet import Wallet
from xrpl.utils.str_conversions import hex_to_str
from xrpl.utils import drops_to_xrp, xrp_to_drops
import toml

CONFIG = toml.load("./config/config.toml")
SEEDS = list(dict.fromkeys([x.strip() for x in open("./config/seeds.txt", "r").read().splitlines() if x.strip().startswith("s")]))
WALLETS = {Wallet.from_seed(seed=seed, algorithm=CryptoAlgorithm.SECP256K1).address: seed for seed in SEEDS}
app = Flask(__name__)

@app.route("/")
def index():
    global SEEDS
    global WALLETS
    
    SEEDS = list(dict.fromkeys([x.strip() for x in open("./config/seeds.txt", "r").read().splitlines() if x.strip().startswith("s")]))
    WALLETS = {Wallet.from_seed(seed=seed, algorithm=CryptoAlgorithm.SECP256K1).address: seed for seed in SEEDS}
    return render_template("index.html", servers=CONFIG["SERVERS"], wallets=WALLETS), 200

@app.route("/payment/send", methods=["POST"])
def payment_send():
    data = request.get_json(force=True)

    req_keys = {
        "destination_address": str,
        "destination_tag": int,
        "currency": dict,
        "amount": float,
        "server": str,
        "wallet": str,
        "password": str
    }

    for key in req_keys:
        key_type = req_keys[key]

        if not key in data:
            return {"error": f"Missing key: {key}"}, 400
        
        if not type(data[key]) == req_keys[key]:
            return {"error": f"{key} expects {req_keys[key]} type, not {type(data[key])}."}, 400
    
    destination_address = data["destination_address"]
    destination_tag = data["destination_tag"]
    currency = data["currency"]
    amount = data["amount"]
    server = data["server"]
    wallet = data["wallet"]
    password = data["password"]
    currency_name = currency["currency"]

    if (destination_tag < 0):
        destination_tag = None
    
    if (amount < 0):
        return {"error": f"Invalid amount: {amount}"}, 400
    
    server_type = get_server_type(server)
    if not server_type:
        return {"error": f"Invalid server: {server}"}, 400
    
    if not wallet in WALLETS:
        return {"error": f"Invalid wallet: {wallet}"}, 400
    
    if not password == CONFIG["UTILITY"]["PASSWORD"]:
        return {"error": "Wrong password!"}, 400
    
    xrpl_wallet = Wallet.from_seed(seed=WALLETS[wallet], algorithm=CryptoAlgorithm.SECP256K1)

    client = JsonRpcClient(server)

    if all([server_type == "XRP", currency_name == "XRP"]) or all([server_type == "Xahau", currency_name == "XAH"]):
        try:
            amount = xrp_to_drops(amount)
        except Exception:
            return {"error": "Amount too small."}
    else:
        currency_issuer = currency["account"]
        amount = IssuedCurrencyAmount(currency=currency_name, issuer=currency_issuer, value=amount)

    #signed = autofill_and_sign(transaction=payment_tx, client=client, wallet=xrpl_wallet)
    try:
        network_id = 21337 if server_type == "Xahau" else None
        payment_tx = Payment(account=xrpl_wallet.address, fee="12", destination=destination_address, destination_tag=destination_tag, amount=amount, network_id=network_id)
        signed = autofill_and_sign(transaction=payment_tx, client=client, wallet=xrpl_wallet)
        result = client.request(request=requests.SubmitOnly(tx_blob=signed.blob())).result
    except Exception as e:
        print(e)
        return str(e), 400
    
    return result, 200

def get_server_type(server_address):
    servers = CONFIG["SERVERS"]
    for server_type in servers:
        for address in servers[server_type]:
            if server_address == address:
                return server_type

@app.route("/wallet/balance", methods=["GET"])
def wallet_info():
    args = request.args

    if not args:
        return "No arguments passed", 400
    
    if not all(["wallet_address" in args, "ws_address" in args]):
        return "No wallet_address or ws_address passed.", 400
    
    wallet_address = args["wallet_address"]
    ws_address = args["ws_address"]
    server_type = get_server_type(ws_address)

    if not server_type:
        return "Invalid server address", 400
    
    client = JsonRpcClient(ws_address)
    account_info = client.request(request=requests.AccountInfo(account=wallet_address)).result

    if "error" in account_info:
        return account_info["error_message"], 400
    
    account_balance = drops_to_xrp(account_info["account_data"]["Balance"])

    currency_name = "XRP"
    if server_type == "Xahau":
        currency_name = "XAH"
    
    return {"balance": account_balance, "currency_name": currency_name}, 200

@app.route("/wallet/trustlines", methods=["GET"])
def wallet_trustlines():
    args = request.args

    if not args:
        return "No arguments passed", 400
    
    if not "wallet_address" in args:
        return "No wallet_address argument passed", 400
    
    if not "ws_address" in args:
        return "No ws_address argument passed", 400
    
    wallet_address = args["wallet_address"]
    ws_address = args["ws_address"]
    server_type = get_server_type(ws_address)

    if not server_type:
        return "Invalid server address", 400

    client = JsonRpcClient(ws_address)
    trustlines = client.request(request=requests.AccountLines(account=wallet_address)).result["lines"]

    for line in trustlines:
        try:
            line_currency = hex_to_str(line["currency"])
            line["currency"] = line_currency.replace("\u0000", "")
        except Exception:
            pass

    return trustlines, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
