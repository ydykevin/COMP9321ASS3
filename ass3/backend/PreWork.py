import DB
import pandas as pd
import re


def get_movieIds():
    df_rating = pd.read_csv('ratings_small.csv', low_memory=False)
    movieIds = df_rating.pivot(index='userId', columns='movieId', values='rating').fillna(0.0).columns
    # print(movieIds.values)
    return [str(c) for c in movieIds.values]

'''
inser rating.csv data to database
'''
def insert_rating():
    global mdb
    df = pd.read_csv('ratings_small.csv')
    df['userId']=df['userId'].astype(int)
    df['movieId']=df['movieId'].astype(int)
    df['rating']=df['rating'].fillna(0.0).astype(float)
    l = list()

    df_movie = pd.read_csv('movies_metadata.csv', low_memory=False)
    df_movie = df_movie[['id', 'title']].set_index('id').loc[get_movieIds()]
    df_movie.index = df_movie.index.astype(int)
    df_movie['title'] = df_movie['title'].fillna('').astype(str)
    r4912 = df_movie.loc[4912].head(1)
    df_movie = df_movie.drop(4912)
    df_movie = df_movie.append(r4912)
    df_movie = df_movie.reset_index()
    df_movie['id']=df_movie['id'].astype(int)
    df = df.merge(df_movie, left_on='movieId', right_on='id', how='inner')
    print(len(df))
    for i in range(len(df)):
        if (i+1) % 1000 == 0:
            mdb.insert_many_rating_collection(l)
            l.clear()
            print('finish', i)
        rdict = dict()
        r = df.loc[i]
        rdict['userId'] = int(r.userId)
        rdict['movieId'] = int(r.movieId)
        rdict['rating'] = int(r.rating)

        rdict['name'] = r.title
        if r.title == '':
            rdict['name'] = 'movie' + str(int(r.movieId))
        l.append(rdict)
    mdb.insert_many_rating_collection(l)
    print("finish insert rating")
'''
    read rating radata from database
    and return a list
'''
def read_rating_from_db():
    userId_list = list()
    movieId_list = list()
    rating_list = list()
    r = mdb.find_many_rating_collection()
    for i in r:
        print(i['userId'], i['movieId'], i['rating'])
        userId_list.append(i['userId'])
        movieId_list.append(i['movieId'])
        rating_list.append(i['rating'])
    return rating_list
    # [671 rows x 9066 columns]
    df2 = pd.DataFrame.from_dict({'userId': userId_list, 'movieId': movieId_list, 'rating': rating_list})
    print(df2.pivot(index='userId', columns='movieId', values='rating').fillna(0.0))

'''
    insert movie_metedata.csv to database
'''
# def insert_movie_info():
#     df_movie = pd.read_csv('movies_metadata.csv', low_memory=False)

#     df_movie = df_movie[['id', 'title', 'vote_average', 'popularity', 'overview', 'runtime']].set_index('id').loc[get_movieIds()]

#     df_movie['title'] = df_movie['title'].fillna('').astype(str)
#     df_movie['overview'] = df_movie['overview'].fillna('').astype(str)

#     df_movie['vote_average'] = df_movie['vote_average'].fillna(0.0).astype(float)
#     df_movie['popularity'] = df_movie['popularity'].fillna(0.0).astype(float)
#     df_movie['runtime'] = df_movie['runtime'].fillna(0.0).astype(float)

#     movie_info_list = list()
#     count = 0;
#     for row in df_movie.itertuples():
#         if row.Index == '4912' and count >=1:
#             continue
#         m_d = dict()
#         m_d['movieId'] = int(row.Index)
#         m_d['title'] = str(row.title)
#         if row.title is '':
#             m_d['title'] = 'movie' + row.Index
#         m_d['vote_average'] = row.vote_average
#         m_d['popularity'] = row.popularity
#         m_d['overview'] = str(row.overview)
#         if row.overview is '':
#             m_d['overview'] = '...'
#         m_d['runtime'] = row.runtime
#         movie_info_list.append(m_d)
#         if row.Index == '4912':
#             count+=1
#     mdb.insert_many_movie_collection(movie_info_list)
#     # print(len(movie_info_list))
#     print('finish')

def extrace_category():
    df_movie = pd.read_csv('movies_metadata.csv', low_memory=False)

    df_movie = df_movie[['id','genres']].set_index('id').loc[get_movieIds()]
    # df_movie.join(df_movie['genres'].apply(json.loads).apply(pd.Series))
    # df_moive = pd.read_csv(df_movie, converters = {'genres': CustomParser}, header = 0)
    # df_moive[sorted(df_movie['genres'][0].keys())] = df_movie['genres'].apply(pd.Series)

    df_movie['genres'] = df_movie['genres'].astype(str)

    count = 0
    genresList = []
    for row in df_movie.itertuples():
        if row.genres == []:
            continue
        genres_reg = re.findall(r"name\': \'(.+?)\'}", row.genres)
        id_reg = re.findall(r"id\': (.+?),", row.genres)
        i = 0
        while (i < len(genres_reg)):
            if genresList.count([genres_reg[i],id_reg[i]]) == 0:
                genresList.append([genres_reg[i],id_reg[i]])
            i = i + 1

    genresList.sort()
    # print(genresList)

    i = 0
    while (i<len(genresList)):
        movieIdList = []

        for row in df_movie.itertuples():
            genres = genresList[i][0]
            reg = re.findall(genres,row.genres)
            if(len(reg)>0):
                movieIdList.append(int(row.Index))
                # print(genresList[i][0])
                # print(row.Index)

        if(len(movieIdList)>0):
            d = dict()
            d['id'] = int(genresList[i][1])
            d['genres'] = genres
            d['movies'] = movieIdList
            # print(d)
            mdb.insert_genres(d)

        i = i + 1


def insert_all_movie_info():
    df_movie = pd.read_csv('movies_metadata.csv', low_memory=False)

    df_movie = df_movie[['id', 'title', 'vote_average', 'popularity', 'overview', 'runtime', 'genres']].set_index('id').loc[
        get_movieIds()]

    df_movie['title'] = df_movie['title'].fillna('').astype(str)
    df_movie['overview'] = df_movie['overview'].fillna('').astype(str)
    df_movie['genres'] = df_movie['genres'].astype(str)

    df_movie['vote_average'] = df_movie['vote_average'].fillna(0.0).astype(float)
    df_movie['popularity'] = df_movie['popularity'].fillna(0.0).astype(float)
    df_movie['runtime'] = df_movie['runtime'].fillna(0.0).astype(float)

    movie_info_list = list()
    count = 0;
    for row in df_movie.itertuples():
        if row.Index == '4912' and count >= 1:
            continue
        m_d = dict()
        m_d['movieId'] = int(row.Index)
        m_d['title'] = str(row.title)
        if row.title is '':
            m_d['title'] = 'movie' + row.Index
        if row.genres=='nan':
            m_d['genres'] = ''
        else:
            genres_reg = re.findall(r"name\': \'(.+?)\'}", row.genres)
            i = 0
            genresString = ''
            while (i<len(genres_reg)):
                genresString += genres_reg[i]
                if i+1<len(genres_reg):
                    genresString += ', '
                i = i + 1
            m_d['genres'] = genresString
        m_d['vote_average'] = row.vote_average
        m_d['popularity'] = row.popularity
        m_d['overview'] = str(row.overview)
        if row.overview is '':
            m_d['overview'] = '...'
        m_d['runtime'] = row.runtime
        movie_info_list.append(m_d)
        if row.Index == '4912':
            count += 1
    mdb.insert_many_all_movie_collection(movie_info_list)
    # print(len(movie_info_list))
    print('finish')







# local
mdb = DB.MongoDB('mongodb://127.0.0.1:27017', db_name='ass3')
# mdb = DB.MongoDB('mongodb://chi:123456a@ds017544.mlab.com:17544/my-db')

# online
# Dayi Yang database
# mdb = DB.MongoDB('mongodb://comp9321ass3:comp9321ass3@ds131323.mlab.com:31323/comp9321ass3')


insert_rating()
extrace_category()
insert_all_movie_info()