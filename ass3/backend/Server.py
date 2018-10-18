from flask import Flask, request, jsonify,make_response
from flask_restplus import Resource, Api, fields, reqparse, abort, cors
from itsdangerous import SignatureExpired, JSONWebSignatureSerializer, BadSignature
from time import time
from functools import wraps
import pandas as pd
import DB
import ML
import re
import json
import math

import configparser as confp

# ------------------------------------------------ INIT ------------------------------------------------
# ------------------- read basic info, db_url and db_name
config = confp.ConfigParser()
config.read(filenames='config.ini')
db_url = config['DEFAULT']['db_url']
db_name = None
limit = 10
if 'db_name' in config['DEFAULT']:
    db_name = config['DEFAULT']['db_name']

parser = reqparse.RequestParser()
parser.add_argument('w')
parser.add_argument('page',type=int)
parser.add_argument('category')

parser2 = reqparse.RequestParser()
parser2.add_argument('w')
parser2.add_argument('category')

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
        if category:
            if self.mdb.__getGenresCollection__().find_one({"genres":category}) is None:
                return {"message": str(category)+" does not exist"},404
        if name!=None and category!=None:
            movie_col = self.mdb.__getAllMovieCollection__().find({'title':re.compile(name),'genres':re.compile(category)}).sort([(sort,-1)]).limit(limit)
        elif name==None and category!=None:
            movie_col = self.mdb.__getAllMovieCollection__().find({'genres': re.compile(category)}).sort([(sort, -1)]).limit(limit)
        elif name!=None and category==None:
            movie_col = self.mdb.__getAllMovieCollection__().find({'title':re.compile(name)}).sort([(sort,-1)]).limit(limit)
        elif name==None and category==None:
            movie_col = self.mdb.__getAllMovieCollection__().find().sort([(sort, -1)]).limit(limit)
        if movie_col.count()==0:
            return {"message":"No movie is found"},404
        m_list = list()
        for row in movie_col:
            m = dict()
            m['movieId'] = row['movieId']
            m['title']   = row['title']
            m['vote_average'] = '-' if row['vote_average'] == 0 else row['vote_average']
            m['popularity'] = '-' if row['popularity']==0 else round(row['popularity'],1)
            m['overview'] = row['overview']
            m['runtime'] = row['runtime']
            m['genres'] = row['genres']
            rate_col = self.mdb.__getRatingCollection__().find({'userId':671, 'movieId': row['movieId']})
            for rrow in rate_col:
                m['rating']=rrow['rating']
                break;
            m_list.append(m)
        #print(m_list)
        return (m_list,200)

    def get_movie_by_id(self, movieId):
        return self.mdb.find_one_movie_collection({'movieId': movieId})

    def get_rating_by_mid_uid(self, user_id, movie_id):
        return self.mdb.find_one_rating_collection({'userId':user_id,'movieId': movie_id})

    def save_rating(self, movieid, rate):
        if not self.get_movie_by_id(movieid):
            return jsonify(message='The movieid is wrong or this collection is not in the database'), 400
        elif not (0 < float(rate) <= 5):
            return jsonify(message = 'The rate is out of range (0,5]'), 400

        movieName = self.mdb.find_one_movie_collection({'movieId':movieid})
        title = movieName['title']

        
        mydict = {"userId": self.admin_user_id, "movieId": movieid, "rating": rate, "name":title}
        if self.get_rating_by_mid_uid(self.admin_user_id, movieid):
            self.mdb.delete_one_rating_collection({'movieId': movieid, 'userId': self.admin_user_id})

        self.mdb.insert_one_rating_collection(mydict)
        return jsonify(
            userId = self.admin_user_id,
            movieId = movieid,
            rating = rate,
            name = title
        ),200

    def get_rate_history(self):
        history = []
        for x in self.mdb.find_many_rating_collection({'userId': self.admin_user_id}, {'_id': 0}):
            history.append(x)
        
        return history

    def get_allMovies(self, category, keyword, page):
        if category:
            if self.mdb.__getGenresCollection__().find_one({"genres":category}) is None:
                return make_response(jsonify({"message":"Category {} does not exist".format(category)}),404)
        if keyword and category is None:
            regx = re.compile(r".*"+keyword+".*")
            all_movies = self.mdb.__getAllMovieCollection__().find({"title":regx})
        if keyword and category:
            t_regx = re.compile(r".*" + keyword + ".*")
            c_regx = re.compile(r".*"+category+".*")
            all_movies = self.mdb.__getAllMovieCollection__().find({"title":t_regx,"genres":c_regx})
        if keyword is None and category:
            c_regx = re.compile(r".*"+category+".*")
            all_movies = self.mdb.__getAllMovieCollection__().find({"genres": c_regx})
        if keyword is None and category is None:
            all_movies = self.mdb.__getAllMovieCollection__().find({})
        if all_movies.count()==0:
            return make_response(jsonify({"message":"No movie is found"}),404)
        r = {}
        total = all_movies.count()
        r['total'] = total
        r['total_pages'] = math.ceil(float(total) / limit)
        m_list= []
        if page:
            if  page > r['total_pages'] or page < 1:
                return make_response(jsonify({"message": 'Invalid page number'}), 400)
            r['current_page'] = page
            for i in all_movies[limit*(page-1):limit*(page-1)+10]:
                rate_col = self.mdb.__getRatingCollection__().find_one({'userId': 671, 'movieId': i['movieId']})
                if rate_col:
                    rating = rate_col['rating']
                else:
                    rating = "-"
                m_list.append({"title": i['title'],
                               "movieId": i['movieId'],
                               "rating":rating,
                               "vote_average": '-' if i['vote_average'] == 0 else i['vote_average'],
                               "genres": i['genres'],
                               "runtime": i['runtime'],
                               "popularity": '-' if i['popularity']==0 else round(i['popularity'],1),
                               "overview": i['overview']})
            r['movies'] = m_list
            return make_response(jsonify(r),200)
        else:
            num = 1
            count = 1
            m_list = []
            for i in all_movies[0:10]:
                rate_col = self.mdb.__getRatingCollection__().find_one({'userId': 671, 'movieId': i['movieId']})
                if rate_col:
                    rating = rate_col['rating']
                else:
                    rating = "-"
                print(i)
                m_list.append({"title": i['title'],
                               "movieId": i['movieId'],
                               "rating":rating,
                               "vote_average": '-' if i['vote_average'] == 0 else i['vote_average'],
                               "genres": i['genres'],
                               "runtime": i['runtime'],
                               "popularity": '-' if i['popularity']==0 else round(i['popularity'],1),
                               "overview": i['overview']})
                r['page_'+str(num)] = m_list
                count += 1
                if count % 11 == 0:
                    count = 1;
                    m_list=[]
                    num += 1
            return jsonify(r), 200

    def get_Movie(self, id):
        movie = self.mdb.__getAllMovieCollection__().find_one({'movieId': id})
        if movie:
            rate_col = self.mdb.__getRatingCollection__().find_one({'userId': 671, 'movieId': movie['movieId']})
            if rate_col:
                rating = rate_col['rating']
            else:
                rating = "-"
            return make_response(jsonify({"title": movie['title'],
                    "id": movie['movieId'],
                    "rating":rating,
                    "vote_average": '-' if movie['vote_average'] == 0 else movie['vote_average'],
                    "genres":movie['genres'],
                    "runtime": movie['runtime'],
                    "popularity": '-' if movie['popularity']==0 else round(movie['popularity'],1),
                    "overview": movie['overview']}), 200)
        return make_response(jsonify({"message": "Movie id = {} does not exist from the database!".format(id)}), 404)

    def delete_rating(self,user_rating):
        if self.mdb.find_one_rating_collection({"userId": self.admin_user_id, "movieId": user_rating}):
            self.mdb.delete_one_rating_collection({"userId": self.admin_user_id, "movieId": user_rating})
            return True
        else:
            return False

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
@api.expect(parser)
class Movies(Resource):
    @cors.crossdomain(origin='*', headers=['content-type'])
    def get(self):
        keyword = parser.parse_args()['w']
        page = parser.parse_args()['page']
        category = parser.parse_args()['category']
        return service.get_allMovies(category,keyword,page)


# 2
@api.route('/movies/<int:id>')
class MovieInfo(Resource):
    @cors.crossdomain(origin='*', headers=['content-type'])
    def get(self, id):
        return service.get_Movie(id)


# 3
@api.route('/movies/popular')
@api.expect(parser2)
class MoviePopular(Resource):
    @cors.crossdomain(origin='*', headers=['content-type'])
    def get(self):
        category = parser2.parse_args()['category']
        name     = parser2.parse_args()['w']
        a,b = service.get_search(category, name, 'popularity')
        if b==404:
            return jsonify(a),b
        else:
            return jsonify({'movies':a}), 200


# 4
@api.route('/movies/highrating')
@api.expect(parser2)
class MovieHighRating(Resource):
    @cors.crossdomain(origin='*', headers=['content-type'])
    def get(self):
        category = parser2.parse_args()['category']
        name = parser2.parse_args()['w']
        a, b = service.get_search(category, name, 'vote_average')
        if b == 404:
            return jsonify(a), b
        else:
            return jsonify({'movies': a}), 200


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
    @cors.crossdomain(origin='*', headers=['content-type'])
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
    @cors.crossdomain(origin='*', headers=['content-type'])
    def get(self):
        try:
            return jsonify(ratings = service.get_rate_history()), 200
        except:
            return jsonify(message='cannot get rating history.'), 400


    #4
    @requires_auth
    @api.doc(params={'movieId': 'movie_id'})
    @cors.crossdomain(origin='*', headers=['content-type'])
    def delete(self):
        parser = reqparse.RequestParser()
        parser.add_argument('movieId', type=str)
        args = parser.parse_args()
        try:
            movieid = int(args.get('movieId'))
        except:
            return {'message': 'arguements are invalid.'}, 400
        if service.delete_rating(movieid):
            return jsonify(message = "movie is removed from the database!"), 200
        else:
            return jsonify(message = "incorrect movieId!"), 400


    @cors.crossdomain(origin='*', headers=['content-type','token'])
    def options(self):
        return {}, 200
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
