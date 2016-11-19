from flask import Flask,render_template,request,abort
from random import randint
import redis

app = Flask(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0)
app.debug = True

def trackUsage(coupon):
    if not r.get('total_coupons_generated'):
        r.set('total_coupons_generated', 1)
    else:
        r.incr('total_coupons_generated')

    visitor_ip = request.remote_addr
    if not r.get(visitor_ip):
        r.set(visitor_ip,1)
    else:
        r.incr(visitor_ip)

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
    coupon = "%05d%05d%04d%01d" % (47000,seed,signature,checksum)
    trackUsage(coupon)
    return coupon

@app.route('/')
@app.route('/<int:count>')
def index(count=1):
    visitor_ip = request.remote_addr
    if r.get('total_coupons_generated') and int(r.get('total_coupons_generated')) > 1000:
        abort(503)

    if r.get(visitor_ip) and int(r.get(visitor_ip)) > 50:
        abort(403)

    ten_percent_off_coupons = []
    fifteen_off_50_coupons = []
    fifty_off_250_coupons = []

    for _ in range(count):
        ten_percent_off_coupons.append(makeCoupon(6035,8))
        fifteen_off_50_coupons.append(makeCoupon(6228,4))
        fifty_off_250_coupons.append(makeCoupon(6209,3))

    total_coupons_generated = r.get('total_coupons_generated')
    return render_template('index.html', **locals())

if __name__ == "__main__":
    app.run(host='0.0.0.0')
