from flask import Flask,render_template,request,abort
from random import randint
import redis
import json

app = Flask(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0)
app.debug = True

def analytics():
   keys = []
   for key in r.keys():
      keys.append((key,int(r.get(key))))
   sorted_keys = sorted(keys, key=lambda tup: tup[1], reverse=True)
   for key in sorted_keys:
      print "%s - %s" % (key[0], key[1])

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

def makeCoupon(coupon_type):
   coupon_types = [(6035,8),(6228,4),(6209,3)]
   signature = coupon_types[coupon_type][0]
   offset = coupon_types[coupon_type][1]

   for _ in range(10):
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
      if not (r.sismember('bad_coupons', coupon) or r.sismember('used_coupons', coupon)):
         trackUsage(coupon)
         return coupon

@app.route('/') 
@app.route('/<int:count>')
def index(count=1):
   visitor_ip = request.remote_addr
   if r.get('total_coupons_generated') and int(r.get('total_coupons_generated')) > 10000:
      abort(503)

   if r.get(visitor_ip) and int(r.get(visitor_ip)) >= 30:
      abort(403)

   ten_percent_off_coupons = []
   fifteen_off_50_coupons = []
   fifty_off_250_coupons = []

   for _ in range(count):
      ten_percent_off_coupons.append(makeCoupon(0))
      fifteen_off_50_coupons.append(makeCoupon(1))
      fifty_off_250_coupons.append(makeCoupon(2))

   total_coupons_generated = r.get('total_coupons_generated')
   return render_template('index.html', **locals())

@app.route('/coupon/mark_bad', methods = ['POST'])
def mark_coupon_bad():
   coupon = request.form['coupon']
   coupon_type = int(request.form['coupon_type'])
   r.sadd('bad_coupons', coupon)
   return json.dumps({'success':True, 'new_coupon':makeCoupon(coupon_type)}), 200, {'ContentType':'application/json'}

@app.route('/coupon/mark_used', methods = ['POST'])
def mark_coupon_used():
   coupon = request.form['coupon']
   r.sadd('used_coupons', coupon)
   return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

if __name__ == "__main__":
   app.run(host='0.0.0.0')
