from flask import Flask, request, jsonify
from flask_restplus import Resource, Api, fields, reqparse, abort, cors
from itsdangerous import SignatureExpired, JSONWebSignatureSerializer, BadSignature
from time import time
from functools import wraps
import pandas as pd
import DB
import ML
import re
import json

import configparser as confp

# ------------------------------------------------ INIT ------------------------------------------------
# ------------------- read basic info, db_url and db_name
config = confp.ConfigParser()
config.read(filenames='config.ini')
db_url = config['DEFAULT']['db_url']
db_name = None
limit = 20
if 'db_name' in config['DEFAULT']:
    db_name = config['DEFAULT']['db_name']


# ******************* read basic info, db_url and db_name


# -------------------Service class
class Service:
    def __init__(self):
        self.admin_user_id = 671

        self.mdb = DB.MongoDB(db_url, db_name=db_name)
        self.ml = ML.MlKnn()
        self.rating_df = self.__get_rating_df_from_db__()
        self.rating_df_ml = self.rating_df.pivot(index='userId', columns='movieId', values='rating').fillna(0.0)

        self.movie_df = None

    def __get_rating_df_from_db__(self):
        user_id_list = list()
        movie_id_list = list()
        rating_list = list()
        r = self.mdb.find_many_rating_collection()
        for i in r:
            user_id_list.append(i['userId'])
            movie_id_list.append(i['movieId'])
            rating_list.append(i['rating'])
        return pd.DataFrame.from_dict({'userId': user_id_list, 'movieId': movie_id_list, 'rating': rating_list})

    def get_recommendation(self):
        self.ml.fit(self.rating_df_ml)
        if self.admin_user_id in self.rating_df_ml.index:
            x = self.rating_df_ml.loc[self.admin_user_id]
            correlation, kneighbs = self.ml.predit([x])
            result = self.rating_df_ml.loc[kneighbs].mul(correlation, axis=0).sum(axis=0) \
                .sort_values(ascending=False).head(10)
            id_list = result.index.tolist()
            m_list = list()
            # print(self.mdb.find_many_movie_collection({'movieId': id_list}))
            for r in self.mdb.find_many_movie_collection({'movieId': {'$in': id_list}}):
                m = dict()
                m['movieId'] = r['movieId']
                m['title'] = r['title']
                m['vote_average'] = '-' if r['vote_average'] == 0 else r['vote_average']
                m['popularity'] = '-' if r['popularity']==0 else r['popularity']
                m['overview'] = r['overview']
                m['runtime'] = '-' if r['runtime'] <10 else r['runtime']
                m_list.append(m)
            return m_list
        else:
            return None

    def get_search(self,category,name,sort):
        if name!='' and category!='':
            movie_col = self.mdb.__getAllMovieCollection__().find({'title':re.compile(name),'genres':re.compile(category)}).sort([(sort,-1)]).limit(limit)
        elif name=='' and category!='':
            movie_col = self.mdb.__getAllMovieCollection__().find({'genres': re.compile(category)}).sort([(sort, -1)]).limit(limit)
        elif name!='' and category=='':
            movie_col = self.mdb.__getAllMovieCollection__().find({'title':re.compile(name)}).sort([(sort,-1)]).limit(limit)
        elif name=='' and category=='':
            movie_col = self.mdb.__getAllMovieCollection__().find().sort([(sort, -1)]).limit(limit)
        m_list = list()
        for row in movie_col:
            m = dict()
            m['movieId'] = row['movieId']
            m['title']   = row['title']
            m['vote_average'] = row['vote_average']
            m['popularity'] = row['popularity']
            m['overview'] = row['overview']
            m['runtime'] = row['runtime']
            m['genres'] = row['genres']
            m_list.append(m)
        #print(m_list)
        return m_list

    def get_movie_by_id(self, movieId):
        return self.mdb.find_one_movie_collection({'movieId': movieId})

    def get_rating_by_mid_uid(self, user_id, movie_id):
        return self.mdb.find_one_rating_collection({'userId':user_id,'movieId': movie_id})

    def save_rating(self, movieid, rate):
        if not self.get_movie_by_id(movieid):
            return {"message": 'The movieid is wrong or this collection is not in the database'}, 400
        elif not (0 < float(rate) <= 5):
            return {"message": 'The rate is out of range (0,5]'}, 400
        
        mydict = {"userId": self.admin_user_id, "movieId": movieid, "rating": rate}

        if not self.get_rating_by_mid_uid(self.admin_user_id, movieid):
            self.mdb.delete_one_rating_collection({'movieId': movieid, 'userId': self.admin_user_id})

        self.mdb.insert_one_rating_collection(mydict)
        return {
        "userId": self.admin_user_id,
            "movieId": movieid,
            "rating": rate
        },200

    def get_rate_history(self):
        history = []
        for x in self.mdb.find_many_rating_collection({'userId': self.admin_user_id}, {'_id': 0}):
            history.append(x)
        
        return history

# *******************Service class

# -------------------AuthenticationToken class
class AuthenticationToken:
    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.expires_in = 60 * 15
        self.serializer = JSONWebSignatureSerializer(secret_key)

    def generate_token(self, username, password):
        info = {
            'username': username,
            'creation_time': time()
        }

        token = self.serializer.dumps(info)
        return token.decode()

    def validate_token(self, token):
        info = self.serializer.loads(token.encode())
        if time() - info['creation_time'] > self.expires_in \
                or info['username'] != 'admin':
            return False
        return True
# *******************AuthenticationToken class

# -------------------valid method
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('token')
        if not token:
            abort(401, 'token is missing')
        try:
            if not auth.validate_token(token):
                abort(401, 'token is incorrect or expired')
        except:
            abort(401, 'token is incorrect or expired')
        return f(*args, **kwargs)

    return decorated


# *******************valid method


auth = AuthenticationToken('9sjadh3289y5uSJ3848FKAJSLJDlskWEJO8234')
app = Flask(__name__)
api = Api(app, authorizations={'API-KEY': {'type': 'apiKey', 'in': 'header', 'name': 'token'}},
          security='API-KEY', default='0X01', default_label='0X01 SERVICE')
login_model = api.model('user', {
    'username': fields.String,
    'password': fields.String
})
service = Service()


# ************************************************ INIT ************************************************


# ------------------------------------------------ PUBLIC ------------------------------------------------
# 1
@api.route('/movies')
class Movies(Resource):
    def get(self):
        pass


# 2
@api.route('/movies/<string:id>')
class MovieInfo(Resource):
    def get(self, id):
        pass


# 3
@api.route('/movies/popular')
class MoviePopular(Resource):
    @cors.crossdomain(origin='*', headers=['content-type'])
    def get(self):
        category = request.args.get('category')
        name     = request.args.get('name')
        if category==None:
            category=''
        if name==None:
            name=''
        return jsonify(movies=service.get_search(category, name, 'popularity')), 200

    @cors.crossdomain(origin='*', headers=['content-type'])
    def options(self):
        return {}, 200


# 4
@api.route('/movies/highrating')
class MovieHighRating(Resource):
    @cors.crossdomain(origin='*', headers=['content-type'])
    def get(self):
        category = request.args.get('category')
        name = request.args.get('name')
        if category == None:
            category = ''
        if name == None:
            name = ''
        return jsonify(movies=service.get_search(category, name, 'vote_average')), 200

    @cors.crossdomain(origin='*', headers=['content-type'])
    def options(self):
        return {}, 200


# ************************************************ PUBLIC ************************************************


# ------------------------------------------------ REGISTER ------------------------------------------------
# 1
@api.route('/movies/recommendation')
class MovieRecommendation(Resource):
    @requires_auth
    @cors.crossdomain(origin='*', headers=['content-type','token'])
    def get(self):
        return jsonify(movies=service.get_recommendation()), 200

    @cors.crossdomain(origin='*', headers=['content-type','token'])
    def options(self):
        return {}, 200


@api.route('/users/rating')
class UserRating(Resource):
    # 2
    @requires_auth
    @api.doc(params={'movieId': 'movie id', 'rate': 'rating'})
    def put(self):
        parser = reqparse.RequestParser()
        parser.add_argument('rate', type=str)
        parser.add_argument('movieId', type=str)
        args = parser.parse_args()
        try:
            movieid = int(args.get('movieId'))
            rate = float(args.get('rate'))
        except:
            return {'message': 'arguements are invalid.'}, 400

        return service.save_rating(movieid, rate)

    # 3
    @requires_auth
    def get(self):
        try:
            return {'rating_history':service.get_rate_history()}, 200
        except:
            return {'message':'cannot get rating history.'}, 400


    #4
    def delete(self):
        pass


# ************************************************ REGISTER ************************************************
# ------------------------------------------------ LOGIN ------------------------------------------------
@api.route('/users/login')
@api.expect(login_model, validate=True)
class UserLogin(Resource):
    @cors.crossdomain(origin='*', headers=['content-type'])
    def post(self):
        global auth
        user = request.json

        if not user:
            return jsonify(message='incorrect username or password'), 400
        if 'admin' == user['username'] and 'admin' == user['password']:
            return jsonify(token=auth.generate_token('admin', 'admin')), 200
        else:
            return jsonify(message='incorrect username or password'), 400

    @cors.crossdomain(origin='*', headers=['content-type'])
    def options(self):
        return {}, 200


# ************************************************ LOGIN ************************************************

app.run(debug=True)
