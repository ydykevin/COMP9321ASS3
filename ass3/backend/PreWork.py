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

    df = df.pivot(index='userId', columns='movieId', values='rating').fillna(0.0)
    # print(df)

    l = list()
    total = len(df.values)
    print('total row:', total)
    for i, r in enumerate(df.values):
        if i > 0 and i % 100 == 0:
            print((i + 1), 'rows loaded')
            print('\tinsert to mlab')
            mdb.insert_many_rating_collection(l)
            l.clear()
            print('\tfinish insert')
        userId = i + 1
        for j, rating in enumerate(r):
            dt = dict()
            movieId = j + 1
            if rating == 0:
                continue
            dt['userId'] = userId
            dt['movieId'] = movieId
            dt['rating'] = rating
            l.append(dt)

    print(total, 'rows loaded')
    print('\tinsert to mlab')
    mdb.insert_many_rating_collection(l)
    l.clear()
    print('\tfinish insert')
    print('finish')
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
def insert_movie_info():
    df_movie = pd.read_csv('movies_metadata.csv', low_memory=False)

    df_movie = df_movie[['id', 'title', 'vote_average', 'popularity', 'overview', 'runtime']].set_index('id').loc[get_movieIds()]

    df_movie['title'] = df_movie['title'].fillna('').astype(str)
    df_movie['overview'] = df_movie['overview'].fillna('').astype(str)

    df_movie['vote_average'] = df_movie['vote_average'].fillna(0.0).astype(float)
    df_movie['popularity'] = df_movie['popularity'].fillna(0.0).astype(float)
    df_movie['runtime'] = df_movie['runtime'].fillna(0.0).astype(float)

    movie_info_list = list()
    count = 0;
    for row in df_movie.itertuples():
        if row.Index == '4912' and count >=1:
            continue
        m_d = dict()
        m_d['movieId'] = int(row.Index)
        m_d['title'] = str(row.title)
        if row.title is '':
            m_d['title'] = 'movie' + row.Index
        m_d['vote_average'] = row.vote_average
        m_d['popularity'] = row.popularity
        m_d['overview'] = str(row.overview)
        if row.overview is '':
            m_d['overview'] = '...'
        m_d['runtime'] = row.runtime
        movie_info_list.append(m_d)
        if row.Index == '4912':
            count+=1
    mdb.insert_many_movie_collection(movie_info_list)
    # print(len(movie_info_list))
    print('finish')

def extrace_category(df_movie):
    df = df_movie[['genres']]
    # df_movie.join(df_movie['genres'].apply(json.loads).apply(pd.Series))
    # df_moive = pd.read_csv(df_movie, converters = {'genres': CustomParser}, header = 0)
    # df_moive[sorted(df_movie['genres'][0].keys())] = df_movie['genres'].apply(pd.Series)

    count = 0
    genresList = []
    for row in df.itertuples():
        if row == []:
            continue
        genres = re.findall(r"name\': \'(.+?)\'}", row.genres)
        i = 0
        while (i < len(genres)):
            if genresList.count(genres[i]) == 0:
                genresList.append(genres[i])
            i = i + 1

    genresList.sort()
    i = 0
    #data = list()

    d = dict()
    d['genres'] = genresList
    #data.append(d)

    print(d)
    print(len(d))

    mdb.insert_genres(d)





# local
# mdb = DB.MongoDB('mongodb://127.0.0.1:27017', db_name='local')

# online
mdb = DB.MongoDB('mongodb://9321ass3:9321ass3@ds129344.mlab.com:29344/comp9321ass3')


# insert_rating()
# insert_movie_info()
df_movie = pd.read_csv('movies_metadata.csv', low_memory=False)
extrace_category(df_movie)