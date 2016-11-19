from flask import Flask,render_template,request
from random import randint

app = Flask(__name__)
app.debug = True

def makeCoupon(signature, offset):
    seed = randint(0,9999)
    digit = randint(0,4)
    checksum = (offset - ((digit - 1) * 3) - (seed * 3) - int(seed/10) - int(seed/100) * 3 - int(seed/1000)) % 10
    return "%05d%1d%04d%04d%01d" % (47000,digit,seed,signature,checksum)

@app.route('/')
@app.route('/<int:count>')
def index(count=1):
    ten_percent_off_coupons = []
    fifteen_off_50_coupons = []
    fifty_off_250_coupons = []

    for _ in range(count):
        ten_percent_off_coupons.append(makeCoupon(6035,8))
        fifteen_off_50_coupons.append(makeCoupon(6228,4))
        fifty_off_250_coupons.append(makeCoupon(6209,3))

    return render_template('index.html', **locals())

if __name__ == "__main__":
    app.run(host='0.0.0.0')

