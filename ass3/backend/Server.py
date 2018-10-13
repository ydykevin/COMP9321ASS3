from flask import Flask, request, jsonify
from flask_restplus import Resource, Api, fields, reqparse, abort, cors
from itsdangerous import SignatureExpired, JSONWebSignatureSerializer, BadSignature
from time import time
from functools import wraps
import pandas as pd
import DB
import ML

import configparser as confp

# ------------------------------------------------ INIT ------------------------------------------------
# ------------------- read basic info, db_url and db_name
config = confp.ConfigParser()
config.read(filenames='config.ini')
db_url = config['DEFAULT']['db_url']
db_name = None
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
        except BadSignature as e:
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
    def get(self):
        pass


# 4
@api.route('/movies/popular')
class MovieHighRating(Resource):
    def get(self):
        pass


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
    def put(self):
        pass

    # 3
    @requires_auth
    def get(self):
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
