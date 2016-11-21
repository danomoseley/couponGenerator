from flask import Flask,render_template,request,abort,jsonify
from random import randint
import redis
import json
import sys

app = Flask(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0)
app.debug = True

def getUserIP():
   if 'X-Forwarded-For' in request.headers:
       return request.headers['X-Forwarded-For']
   else:
       return request.remote_addr

def getStats():
   keys = []
   total_users = 0
   generated_coupons = 0
   for key in r.keys():
      if (r.type(key) == 'string' and key != 'total_coupons_generated'):
         val = r.get(key)
         total_users += 1
         keys.append((key,val))
         generated_coupons += int(val)

   sorted_keys = sorted(keys, key=lambda x: int(x[1]), reverse=True)

   return {
      'total_user_generated_coupons': generated_coupons,
      'total_users': total_users,
      'average_generated_coupons': round(float(generated_coupons)/float(total_users),1),
      'total_bad_coupons': r.scard("bad_coupons"),
      'total_used_coupons': r.scard("used_coupons")
   }

def trackUsage(coupon):
   visitor_ip = getUserIP()

   if visitor_ip in ['74.69.161.126']:
       return

   if not r.get('total_coupons_generated'):
      r.set('total_coupons_generated', 1)
   else:
      r.incr('total_coupons_generated')

   if not r.get(visitor_ip):
      r.set(visitor_ip,1)
   else:
      r.incr(visitor_ip)

@app.route('/coupon/generate/<int:coupon_type>')
def generateCoupon(coupon_type):
   coupon = makeCoupon(coupon_type)
   if coupon is not None:
      return jsonify({'success': True, 'coupon': coupon})
   else:
      return jsonify({'success': False})

def makeCoupon(coupon_type):
   visitor_ip = getUserIP()
   if r.get(visitor_ip) and int(r.get(visitor_ip)) >= 30:
      abort(403)

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
   visitor_ip = getUserIP()
   if r.get(visitor_ip) and int(r.get(visitor_ip)) >= 30:
      abort(403)
   if r.get('total_coupons_generated') and int(r.get('total_coupons_generated')) > 10000:
      abort(503)

   stats = getStats()
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
