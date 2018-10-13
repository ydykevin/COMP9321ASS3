from sklearn.neighbors import NearestNeighbors
import pandas as pd


class MlKnn(object):
    def __init__(self, nb_neighbors):
        # self.df = pd.read_csv(file)
        # self.df = self.df.pivot(index='userId', columns='movieId', values='rating').fillna(0.0)

        # samples = self.df.values
        self.knn = NearestNeighbors(n_neighbors=nb_neighbors, metric='correlation')
        # self.knn.fit(X=samples)

    def fit(self, X):
        self.knn.fit(X=X)

    def predit(self, x):
        dist, kneighbs = self.knn.kneighbors(x)
        dist = dist[0,1:]
        kneighbs = kneighbs[0,1:] + 1
        correlation = 1 - dist
        # return self.df.loc[kneighbs].mul(correlation, axis=0).sum(axis=0).sort_values(ascending=False)
        return correlation,kneighbs


# ml = MlKnn(5)
#
# df = pd.read_csv('ratings_small.csv')
# df = df.pivot(index='userId', columns='movieId', values='rating').fillna(0.0)
# userId = 1
# ml.fit(df.values)
#
# correlation, kneighbs = ml.predit(df.loc[[1]].values)
# print(correlation)
# print(kneighbs)
# print(df.loc[kneighbs].mul(correlation, axis=0).sum(axis=0).sort_values(ascending=False))
# print(ml.predit(ml.df.loc[[1]].values))
