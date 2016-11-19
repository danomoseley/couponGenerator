from flask import Flask,render_template,request
from random import randint

app = Flask(__name__)
app.debug = True

def makeCoupon(signature, offset):
    seed = randint(0,49999)
    seed_str = "%05d" % seed
    seed_list = list(int(d) for d in seed_str)
    seed_list.reverse()

    checksum = offset
    for i, digit in enumerate(seed_list):
        if i > 3:
            digit -= 1
        if i % 2 == 0:
            checksum -= (digit * 3)%10 #Why 3
        else:
            checksum -= digit%10

    checksum = checksum % 10
    return "%05d%05d%04d%01d" % (47000,seed,signature,checksum)

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
