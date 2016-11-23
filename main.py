from flask import Flask,render_template,request,abort,jsonify,redirect
import redis
import json
import sys
import string
import random
import os
from ConfigParser import SafeConfigParser

app = Flask(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0)
app.debug = True

DIR = os.path.dirname(os.path.realpath(__file__))
config = SafeConfigParser()
config.read(os.path.join(DIR,'config.ini'))


def getUserIP():
   if 'X-Forwarded-For' in request.headers:
       return request.headers['X-Forwarded-For']
   else:
       return request.remote_addr

def authUser():
   visitor_ip = getUserIP()
   user_key = 'user:%s' % visitor_ip
   if not r.get(user_key) or int(r.get(user_key)) > config.get('limits','coupons_per_user'):
      abort(403)
   if r.get('total_coupons_generated') and int(r.get('total_coupons_generated')) > config.get('limits','total_coupons'):
      abort(503)
   r.expire(user_key, config.get('invites','user_expiration_seconds'))
   return user_key

def getStats():
   generated_coupons = r.get('total_coupons_generated') or 0
   total_users = r.get('total_users') or 1
   return {
      'total_generated_coupons': generated_coupons,
      'total_users': total_users,
      'average_generated_coupons': round(float(generated_coupons)/float(total_users),1),
      'total_bad_coupons': r.scard("bad_coupons"),
      'total_used_coupons': r.scard("used_coupons")
   }

@app.route('/coupon/generate/<int:coupon_type>')
def generateCoupon(coupon_type):
   authUser()
   coupon = makeCoupon(coupon_type)
   if coupon is not None:
      return jsonify({'success': True, 'coupon': coupon})
   else:
      return jsonify({'success': False})

def makeCoupon(coupon_type):
   user_key = authUser()
   coupon_types = [(6035,8),(6228,4),(6209,3)]
   signature = coupon_types[coupon_type][0]
   offset = coupon_types[coupon_type][1]

   for _ in range(10):
      seed = random.randint(0,49999)
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
         r.incr(user_key)
         r.incr('total_coupons_generated')
         return coupon

@app.route('/') 
@app.route('/<inviteCode>')
def index(inviteCode=None):
   if inviteCode is not None:
      if r.get('invite:%s' % inviteCode):
         visitor_ip = getUserIP()
         r.set('user:%s' % visitor_ip, 0)
         r.expire('user:%s' % visitor_ip, config.get('invites','user_expiration_seconds'))
         r.delete('invite:%s' % inviteCode)
         r.incr('total_users')
      else:
         return redirect('/')
   else:
      authUser()

   stats = getStats()
   return render_template('index.html', **locals())

@app.route('/coupon/mark_bad', methods = ['POST'])
def markCouponBad():
   authUser()
   coupon = request.form['coupon']
   coupon_type = int(request.form['coupon_type'])
   r.sadd('bad_coupons', coupon)
   return json.dumps({'success':True, 'new_coupon':makeCoupon(coupon_type)}), 200, {'ContentType':'application/json'}

@app.route('/coupon/mark_used', methods = ['POST'])
def markCouponUsed():
   authUser()
   coupon = request.form['coupon']
   r.sadd('used_coupons', coupon)
   return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

@app.route('/invite/generate/<key>')
def generateInvite(key):
   if key != config.get('invites', 'key'):
      abort(403)
   invite_code = ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(5))
   r.set('invite:%s' % invite_code, 1)
   r.expire('invite:%s' % invite_code, config.get('invites','invite_expiration_seconds'))
   invite_url = request.url_root + invite_code
   return render_template('invite.html', **locals())

if __name__ == "__main__":
   app.run(host='0.0.0.0')
