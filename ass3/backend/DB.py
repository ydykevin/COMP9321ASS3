import pymongo


class MongoDB:
    def __init__(self, url='mongodb://9321ass3:9321ass3@ds129344.mlab.com:29344/comp9321ass3',db_name=None):

        myclient = pymongo.MongoClient(url)
        if db_name:
            self.db = myclient.get_database(db_name)
        else:
            self.db = myclient.get_database()

    def getCollection(self, name):
        return self.db.get_collection(name)

    def __getRatingCollection__(self):
        return self.getCollection('ratings')

    def __getMovieCollection__(self):
        return self.getCollection('movies')

    def __getGenresCollection__(self):
        return self.getCollection('genres')

    def __getAllMovieCollection__(self):
        return self.__getMovieCollection__()

    def insert_one_movie_collection(self, data):
        return self.__getMovieCollection__().insert_one(data)

    def insert_many_movie_collection(self, data):
        return self.__getMovieCollection__().insert_many(data)

    def insert_one_rating_collection(self, data):
        return self.__getRatingCollection__().insert_one(data)

    def insert_many_rating_collection(self, data):
        return self.__getRatingCollection__().insert_many(data)

    def delete_one_rating_collection(self, data):
        return self.__getRatingCollection__().delete_one(data)
        
    def find_one_movie_collection(self, q=None, arg=None):
        return self.__getMovieCollection__().find_one(q,arg);

    def find_many_movie_collection(self, q=None, arg=None):
        return self.__getMovieCollection__().find(q,arg);

    def find_one_rating_collection(self, q=None, arg=None):
        return self.__getRatingCollection__().find_one(q,arg);

    def find_many_rating_collection(self, q=None, arg=None):
        return self.__getRatingCollection__().find(q,arg);

    def insert_genres(self, data):
        return self.__getGenresCollection__().insert_one(data)

    def insert_many_all_movie_collection(self, data):
        return self.__getAllMovieCollection__().insert_many(data)

